-- Errata Schema
-- Note: documents table is now in schema.sql

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- ERRATA ITEMS COMPONENT
-- Individual known issues extracted from Errata Sheets
-- ============================================================================
CREATE TABLE IF NOT EXISTS errata_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    
    -- Errata Definition
    code VARCHAR(50), -- e.g. "2.1.3"
    module VARCHAR(100), -- e.g. "I2C"
    title TEXT NOT NULL,
    description TEXT,
    
    -- Mitigation
    workaround TEXT,
    
    -- Scope
    affected_revisions TEXT[], -- Array of revision codes e.g. ['A', 'Z']
    is_fixed BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_errata_module ON errata_items(module);
CREATE INDEX IF NOT EXISTS idx_errata_document ON errata_items(document_id);
