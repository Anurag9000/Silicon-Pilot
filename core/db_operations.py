"""
Database Operations

CRUD operations for all database entities with asyncpg.
"""

import logging
from typing import Dict, List, Any, Optional
from uuid import UUID
from datetime import datetime
import asyncpg

from core.models import (
    RequirementSpec,
    EvidenceRecord,
    Question,
    Answer,
    RecommendationResult,
)

logger = logging.getLogger(__name__)


class DatabaseOperations:
    """Database CRUD operations"""
    
    def __init__(self, db_pool: asyncpg.Pool):
        """
        Initialize database operations.
        
        Args:
            db_pool: AsyncPG connection pool
        """
        self.db_pool = db_pool
    
    # ==================== Parts ====================
    
    async def get_part_by_mpn(self, mpn: str) -> Optional[Dict[str, Any]]:
        """
        Get part by manufacturer part number.
        
        Args:
            mpn: Manufacturer part number
        
        Returns:
            Part data with specs, or None if not found
        """
        query = """
        SELECT 
            p.*,
            m.*
        FROM parts p
        LEFT JOIN mcu_specs m ON p.id = m.part_id
        WHERE p.mpn = $1
        """
        
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(query, mpn)
        
        if row:
            return dict(row)
        return None
    
    async def get_part_by_id(self, part_id: UUID) -> Optional[Dict[str, Any]]:
        """Get part by ID"""
        query = """
        SELECT 
            p.*,
            m.*
        FROM parts p
        LEFT JOIN mcu_specs m ON p.id = m.part_id
        WHERE p.id = $1
        """
        
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(query, part_id)
        
        if row:
            return dict(row)
        return None
    
    async def search_parts(
        self,
        manufacturer: Optional[str] = None,
        family: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Search parts with filters.
        
        Args:
            manufacturer: Filter by manufacturer
            family: Filter by family
            status: Filter by status
            limit: Maximum results
        
        Returns:
            List of parts
        """
        where_clauses = []
        params = []
        param_idx = 1
        
        if manufacturer:
            where_clauses.append(f"p.manufacturer = ${param_idx}")
            params.append(manufacturer)
            param_idx += 1
        
        if family:
            where_clauses.append(f"p.family = ${param_idx}")
            params.append(family)
            param_idx += 1
        
        if status:
            where_clauses.append(f"p.status = ${param_idx}")
            params.append(status)
            param_idx += 1
        
        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        query = f"""
        SELECT 
            p.*,
            m.*
        FROM parts p
        LEFT JOIN mcu_specs m ON p.id = m.part_id
        WHERE {where_sql}
        ORDER BY p.mpn ASC
        LIMIT ${param_idx}
        """
        params.append(limit)
        
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
        
        return [dict(row) for row in rows]
    
    # ==================== Evidence ====================
    
    async def get_evidence_for_part(
        self,
        part_id: UUID,
    ) -> List[Dict[str, Any]]:
        """
        Get all evidence records for a part.
        
        Args:
            part_id: Part ID
        
        Returns:
            List of evidence records
        """
        query = """
        SELECT 
            e.*,
            d.source_url,
            d.source_type,
            d.doc_hash
        FROM evidence e
        JOIN documents d ON e.document_id = d.id
        WHERE e.part_id = $1
        ORDER BY e.field_path, e.confidence DESC
        """
        
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, part_id)
        
        return [dict(row) for row in rows]
    
    async def get_evidence_by_id(self, evidence_id: UUID) -> Optional[Dict[str, Any]]:
        """Get evidence by ID"""
        query = """
        SELECT 
            e.*,
            d.source_url,
            d.source_type,
            d.doc_hash
        FROM evidence e
        JOIN documents d ON e.document_id = d.id
        WHERE e.id = $1
        """
        
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(query, evidence_id)
        
        if row:
            return dict(row)
        return None
    
    # ==================== Requirements ====================
    
    async def create_requirement_spec(
        self,
        spec: RequirementSpec,
        source_text: str,
    ) -> UUID:
        """
        Create a requirement specification.
        
        Args:
            spec: Requirement specification
            source_text: Original user text
        
        Returns:
            Spec ID
        """
        from uuid import uuid4
        
        spec_id = uuid4()
        
        query = """
        INSERT INTO requirement_specs (
            id, spec, source_text, mode, created_at
        ) VALUES ($1, $2, $3, $4, NOW())
        """
        
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                query,
                spec_id,
                spec.model_dump_json(),
                source_text,
                spec.mode.value if spec.mode else 'constraint',
            )
        
        return spec_id
    
    async def get_requirement_spec(self, spec_id: UUID) -> Optional[RequirementSpec]:
        """Get requirement specification by ID"""
        query = "SELECT spec FROM requirement_specs WHERE id = $1"
        
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(query, spec_id)
        
        if row:
            return RequirementSpec.model_validate_json(row['spec'])
        return None
    
    async def update_requirement_spec(
        self,
        spec_id: UUID,
        spec: RequirementSpec,
    ):
        """Update requirement specification"""
        query = """
        UPDATE requirement_specs
        SET spec = $2, updated_at = NOW()
        WHERE id = $1
        """
        
        async with self.db_pool.acquire() as conn:
            await conn.execute(query, spec_id, spec.model_dump_json())
    
    # ==================== Questions ====================
    
    async def create_question_turn(
        self,
        spec_id: UUID,
        turn_index: int,
        questions: List[Question],
        answers: Optional[List[Answer]] = None,
    ) -> UUID:
        """
        Create a question turn.
        
        Args:
            spec_id: Requirement spec ID
            turn_index: Turn number
            questions: Questions asked
            answers: Answers provided (optional)
        
        Returns:
            Turn ID
        """
        from uuid import uuid4
        
        turn_id = uuid4()
        
        questions_json = [q.model_dump() for q in questions]
        answers_json = [a.model_dump() for a in answers] if answers else []
        
        query = """
        INSERT INTO question_turns (
            id, spec_id, turn_index, questions, answers, created_at
        ) VALUES ($1, $2, $3, $4, $5, NOW())
        """
        
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                query,
                turn_id,
                spec_id,
                turn_index,
                questions_json,
                answers_json,
            )
        
        return turn_id
    
    async def update_question_turn_answers(
        self,
        turn_id: UUID,
        answers: List[Answer],
    ):
        """Update answers for a question turn"""
        answers_json = [a.model_dump() for a in answers]
        
        query = """
        UPDATE question_turns
        SET answers = $2, updated_at = NOW()
        WHERE id = $1
        """
        
        async with self.db_pool.acquire() as conn:
            await conn.execute(query, turn_id, answers_json)
    
    async def get_question_turns(
        self,
        spec_id: UUID,
    ) -> List[Dict[str, Any]]:
        """Get all question turns for a spec"""
        query = """
        SELECT * FROM question_turns
        WHERE spec_id = $1
        ORDER BY turn_index ASC
        """
        
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, spec_id)
        
        return [dict(row) for row in rows]
    
    # ==================== Recommendations ====================
    
    async def log_recommendation(
        self,
        spec_id: UUID,
        result: RecommendationResult,
    ) -> UUID:
        """
        Log a recommendation result.
        
        Args:
            spec_id: Requirement spec ID
            result: Recommendation result
        
        Returns:
            Log ID
        """
        from uuid import uuid4
        
        log_id = uuid4()
        
        # Extract candidates and explanations
        candidates_data = [
            {
                'mpn': c.mpn,
                'manufacturer': c.manufacturer,
                'score': c.total_score,
                'score_breakdown': c.score_breakdown,
            }
            for c in result.candidates
        ]
        
        explanations_data = {
            'constraint_checks': result.constraint_checks,
            'ranking_explanation': result.ranking_explanation,
        }
        
        query = """
        INSERT INTO recommendation_logs (
            id, spec_id, candidates, explanations, created_at
        ) VALUES ($1, $2, $3, $4, NOW())
        """
        
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                query,
                log_id,
                spec_id,
                candidates_data,
                explanations_data,
            )
        
        return log_id
    
    async def get_recommendation_logs(
        self,
        spec_id: UUID,
    ) -> List[Dict[str, Any]]:
        """Get all recommendation logs for a spec"""
        query = """
        SELECT * FROM recommendation_logs
        WHERE spec_id = $1
        ORDER BY created_at DESC
        """
        
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, spec_id)
        
        return [dict(row) for row in rows]
    
    # ==================== Conflicts ====================
    
    async def get_open_conflicts(
        self,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get open conflicts for review"""
        query = """
        SELECT 
            c.*,
            p.mpn,
            p.manufacturer
        FROM conflicts c
        JOIN parts p ON c.part_id = p.id
        WHERE c.status = 'open'
        ORDER BY c.created_at DESC
        LIMIT $1
        """
        
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, limit)
        
        return [dict(row) for row in rows]
    
    async def resolve_conflict(
        self,
        conflict_id: UUID,
        resolution: Dict[str, Any],
        resolved_by: str,
    ):
        """Resolve a conflict"""
        query = """
        UPDATE conflicts
        SET 
            status = 'resolved',
            resolution = $2,
            resolved_by = $3,
            resolved_at = NOW()
        WHERE id = $1
        """
        
        async with self.db_pool.acquire() as conn:
            await conn.execute(query, conflict_id, resolution, resolved_by)
    
    # ==================== Statistics ====================
    
    async def get_stats(self) -> Dict[str, int]:
        """Get database statistics"""
        queries = {
            'total_parts': "SELECT COUNT(*) FROM parts",
            'total_evidence': "SELECT COUNT(*) FROM evidence",
            'total_conflicts': "SELECT COUNT(*) FROM conflicts WHERE status = 'open'",
            'total_specs': "SELECT COUNT(*) FROM requirement_specs",
        }
        
        stats = {}
        
        async with self.db_pool.acquire() as conn:
            for key, query in queries.items():
                stats[key] = await conn.fetchval(query)
        
        return stats
