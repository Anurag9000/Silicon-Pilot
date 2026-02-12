import asyncio
import asyncpg
import os

async def main():
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:1Anurag2Basistha@localhost:5432/hardwaregenius")
    conn = await asyncpg.connect(db_url)
    try:
        # Step 1: Enforce extensions
        print("Enabling extensions...")
        await conn.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
        await conn.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
        
        # Step 2: Create Evidence Table
        print("Creating evidence table...")
        query = """
        CREATE TABLE IF NOT EXISTS evidence (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            part_id UUID NOT NULL REFERENCES parts(id) ON DELETE CASCADE,
            field_path VARCHAR(255) NOT NULL,
            raw_value TEXT,
            normalized_value JSONB,
            confidence DECIMAL(3,2) NOT NULL DEFAULT 1.0,
            document_id UUID REFERENCES documents(id) ON DELETE SET NULL,
            page_number INTEGER,
            bbox JSONB,
            snippet_image_path TEXT,
            verified BOOLEAN DEFAULT FALSE,
            verified_by UUID,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
        await conn.execute(query)
        print("✓ Evidence table created successfully!")
        
        # Step 3: Create indices
        print("Creating indices...")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_evidence_part ON evidence(part_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_evidence_field ON evidence(part_id, field_path)")
        print("✓ Indices created!")
        
    except Exception as e:
        print(f"FAILED: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
