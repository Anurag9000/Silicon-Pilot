"""
Advanced RAG Module

Implements retrieval techniques from RigorousRAG:
1. HyDe (Hypothetical Document Embeddings)
2. Multi-Query Expansion
"""
import logging
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

class AdvancedRAG:
    def __init__(self, api_key: str, base_url: Optional[str] = None, model: str = "gpt-4o-mini"):
        import httpx
        self.client = AsyncOpenAI(
            api_key=api_key, 
            base_url=base_url,
            timeout=httpx.Timeout(300.0, connect=10.0)
        )
        self.model = model

    async def generate_hyde_query(self, query: str) -> str:
        """
        Generates a hypothetical technical answer to use for embedding retrieval.
        Mirroring RigorousRAG implementation.
        """
        logger.info(f"Generating HyDe expansion for query: {query}")
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a hardware expert. Generate a technical, data-rich hypothetical paragraph from a datasheet that would perfectly answer the user's query. Include specific metric names and units."},
                    {"role": "user", "content": query}
                ],
                max_tokens=200
            )
            hyde_answer = response.choices[0].message.content or query
            return f"{query}\n{hyde_answer}"
        except Exception as e:
            logger.error(f"HyDe generation failed: {e}")
            return query

    async def expand_technical_query(self, query: str) -> List[str]:
        """
        Generates technical variations of a query to maximize recall across datasheets.
        Mirroring RigorousRAG Multi-Query logic.
        """
        logger.info(f"Expanding technical query: {query}")
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a hardware research assistant. Generate 3 unique search variations of the technical query to maximize datasheet recall. Focus on alternative parameter names (e.g. 'Icc' vs 'Supply Current'). Output as a comma-separated list."},
                    {"role": "user", "content": query}
                ],
                max_tokens=100
            )
            variations = response.choices[0].message.content.split(',')
            return [query] + [v.strip() for v in variations if v.strip()]
        except Exception as e:
            logger.error(f"Query expansion failed: {e}")
            return [query]
