-- Errata Database Schema Extension
-- Stores silicon bugs, limitations, and workarounds for parts

CREATE TABLE IF NOT EXISTS errata (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    part_id UUID REFERENCES parts(id) ON DELETE CASCADE,
    
    -- Errata identification
    errata_id VARCHAR(50) NOT NULL,  -- e.g., "2.3.1", "ES0206-1.2"
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('critical', 'major', 'minor', 'info')),
    
    -- Content
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    workaround TEXT,
    
    -- Applicability
    affected_revisions VARCHAR(100),  -- e.g., "Rev A, Rev B", "All revisions"
    fixed_in_revision VARCHAR(50),    -- e.g., "Rev C", NULL if not fixed
    
    -- Documentation
    document_id UUID REFERENCES documents(id),
    page_number INTEGER,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_errata_part ON errata(part_id);
CREATE INDEX IF NOT EXISTS idx_errata_severity ON errata(severity);
CREATE INDEX IF NOT EXISTS idx_errata_id ON errata(errata_id);
CREATE INDEX IF NOT EXISTS idx_errata_document ON errata(document_id);

-- Trigger to update updated_at
CREATE OR REPLACE FUNCTION update_errata_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER errata_update_timestamp
    BEFORE UPDATE ON errata
    FOR EACH ROW
    EXECUTE FUNCTION update_errata_timestamp();

-- Comments
COMMENT ON TABLE errata IS 'Silicon errata (bugs, limitations, workarounds) for parts';
COMMENT ON COLUMN errata.errata_id IS 'Errata identifier from datasheet (e.g., 2.3.1)';
COMMENT ON COLUMN errata.severity IS 'Impact level: critical, major, minor, info';
COMMENT ON COLUMN errata.affected_revisions IS 'Which silicon revisions are affected';
COMMENT ON COLUMN errata.fixed_in_revision IS 'Silicon revision where issue was fixed';
