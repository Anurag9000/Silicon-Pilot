-- HardwareGenius PostgreSQL Schema
-- Engineering-grade hardware selection system with evidence tracking

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- PARTS TABLE
-- Core part information (manufacturer, family, status, package, temp range)
-- ============================================================================
CREATE TABLE parts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mpn VARCHAR(100) NOT NULL UNIQUE,
    manufacturer VARCHAR(100) NOT NULL,
    family VARCHAR(100),
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    package_family VARCHAR(50),
    package_name VARCHAR(100),
    pin_count INTEGER,
    temp_min_c INTEGER,
    temp_max_c INTEGER,
    datasheet_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indices for fast filtering
CREATE INDEX idx_parts_manufacturer ON parts(manufacturer);
CREATE INDEX idx_parts_status ON parts(status);
CREATE INDEX idx_parts_package_family ON parts(package_family);
CREATE INDEX idx_parts_temp_range ON parts(temp_min_c, temp_max_c);
CREATE INDEX idx_parts_composite ON parts(manufacturer, status, package_family);

-- ============================================================================
-- MCU_SPECS TABLE
-- Typed queryable fields for MCU specifications
-- ============================================================================
CREATE TABLE mcu_specs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    part_id UUID NOT NULL UNIQUE REFERENCES parts(id) ON DELETE CASCADE,
    
    -- Core specifications
    core VARCHAR(100),
    max_mhz INTEGER,
    flash_kb INTEGER,
    sram_kb INTEGER,
    eeprom_kb INTEGER,
    
    -- Peripherals (counts)
    can_count INTEGER DEFAULT 0,
    can_fd_count INTEGER DEFAULT 0,
    uart_count INTEGER DEFAULT 0,
    spi_count INTEGER DEFAULT 0,
    i2c_count INTEGER DEFAULT 0,
    usb_fs BOOLEAN DEFAULT FALSE,
    usb_hs BOOLEAN DEFAULT FALSE,
    ethernet BOOLEAN DEFAULT FALSE,
    adc_channels INTEGER DEFAULT 0,
    dac_channels INTEGER DEFAULT 0,
    timers_count INTEGER DEFAULT 0,
    pwm_channels INTEGER DEFAULT 0,
    
    -- Features
    has_fpu BOOLEAN DEFAULT FALSE,
    has_dsp BOOLEAN DEFAULT FALSE,
    has_crypto BOOLEAN DEFAULT FALSE,
    has_wireless BOOLEAN DEFAULT FALSE,
    
    -- Electrical
    vdd_min_v DECIMAL(4,2),
    vdd_max_v DECIMAL(4,2),
    
    -- Power consumption (optional, often incomplete)
    active_ma DECIMAL(8,2),
    standby_ua DECIMAL(8,2),
    sleep_ua DECIMAL(8,2),
    
    -- Cost (optional, volatile)
    cost_usd DECIMAL(8,2),
    
    -- Extensibility for fields not yet normalized
    extras JSONB,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indices for fast filtering on common constraints
CREATE INDEX idx_mcu_specs_core ON mcu_specs(core);
CREATE INDEX idx_mcu_specs_flash ON mcu_specs(flash_kb);
CREATE INDEX idx_mcu_specs_sram ON mcu_specs(sram_kb);
CREATE INDEX idx_mcu_specs_can ON mcu_specs(can_count, can_fd_count);
CREATE INDEX idx_mcu_specs_peripherals ON mcu_specs(uart_count, spi_count, i2c_count);
CREATE INDEX idx_mcu_specs_composite ON mcu_specs(core, flash_kb, sram_kb);

-- ============================================================================
-- DOCUMENTS TABLE
-- Source tracking with hash, version, fetch timestamp
-- ============================================================================
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_url TEXT NOT NULL,
    source_type VARCHAR(50) NOT NULL, -- mfg_pdf, mfg_html, dist_html, other
    doc_hash VARCHAR(64) NOT NULL, -- SHA-256
    content_type VARCHAR(100),
    storage_key TEXT NOT NULL, -- S3 key
    version INTEGER NOT NULL DEFAULT 1,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(source_url, doc_hash)
);

CREATE INDEX idx_documents_hash ON documents(doc_hash);
CREATE INDEX idx_documents_url ON documents(source_url);
CREATE INDEX idx_documents_type ON documents(source_type);

-- ============================================================================
-- EVIDENCE TABLE
-- Provenance tracking for every extracted field
-- ============================================================================
CREATE TABLE evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    part_id UUID NOT NULL REFERENCES parts(id) ON DELETE CASCADE,
    field_path VARCHAR(200) NOT NULL, -- e.g., "mcu_specs.flash_kb"
    
    -- Extraction
    extracted_value_raw TEXT,
    normalized_value JSONB, -- {"value": 2048, "unit": "kb"}
    
    -- Source
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    page INTEGER,
    bbox JSONB, -- {"x0": ..., "y0": ..., "x1": ..., "y1": ...}
    snippet_storage_key TEXT, -- S3 key for snippet image
    
    -- Quality
    confidence DECIMAL(4,3), -- 0.000 to 1.000
    parser_version VARCHAR(50),
    
    extracted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_evidence_part ON evidence(part_id);
CREATE INDEX idx_evidence_field ON evidence(part_id, field_path);
CREATE INDEX idx_evidence_document ON evidence(document_id);
CREATE INDEX idx_evidence_confidence ON evidence(confidence);

-- ============================================================================
-- CONFLICTS TABLE
-- Cross-source validation and resolution workflow
-- ============================================================================
CREATE TABLE conflicts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    part_id UUID NOT NULL REFERENCES parts(id) ON DELETE CASCADE,
    field_path VARCHAR(200) NOT NULL,
    evidence_ids UUID[] NOT NULL, -- Array of conflicting evidence IDs
    status VARCHAR(50) NOT NULL DEFAULT 'open', -- open, resolved, ignored
    resolution JSONB, -- {"chosen_value": ..., "reason": "..."}
    resolved_by VARCHAR(100),
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_conflicts_part ON conflicts(part_id);
CREATE INDEX idx_conflicts_status ON conflicts(status);

-- ============================================================================
-- REQUIREMENT_SPECS TABLE
-- Store user specs with uncertainty tracking
-- ============================================================================
CREATE TABLE requirement_specs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    spec JSONB NOT NULL, -- Full RequirementSpec object
    source_text TEXT,
    mode VARCHAR(50), -- constraint, intent
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_requirement_specs_mode ON requirement_specs(mode);

-- ============================================================================
-- QUESTION_TURNS TABLE
-- Conversation history for question-answer flow
-- ============================================================================
CREATE TABLE question_turns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    spec_id UUID NOT NULL REFERENCES requirement_specs(id) ON DELETE CASCADE,
    turn_index INTEGER NOT NULL,
    questions JSONB NOT NULL, -- Array of Question objects
    answers JSONB, -- Array of Answer objects
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_question_turns_spec ON question_turns(spec_id);
CREATE INDEX idx_question_turns_turn ON question_turns(spec_id, turn_index);

-- ============================================================================
-- RECOMMENDATION_LOGS TABLE
-- Audit trail with explanations
-- ============================================================================
CREATE TABLE recommendation_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    spec_id UUID NOT NULL REFERENCES requirement_specs(id) ON DELETE CASCADE,
    candidates JSONB NOT NULL, -- Array of {mpn, score, score_breakdown}
    explanations JSONB, -- Constraint checks, ranking reasons
    near_miss JSONB, -- Near-miss suggestions
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_recommendation_logs_spec ON recommendation_logs(spec_id);

-- ============================================================================
-- EXTRACTION_RUNS TABLE
-- Track ingestion pipeline runs
-- ============================================================================
CREATE TABLE extraction_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    parser_version VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL, -- success, partial, failed
    error_message TEXT,
    stats JSONB, -- {"fields_extracted": 15, "confidence_avg": 0.92, ...}
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_extraction_runs_document ON extraction_runs(document_id);
CREATE INDEX idx_extraction_runs_status ON extraction_runs(status);

-- ============================================================================
-- TEMPLATES TABLE (for v2: intent → architecture)
-- ============================================================================
CREATE TABLE templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL UNIQUE,
    description TEXT,
    subsystems JSONB NOT NULL, -- Array of subsystem definitions
    questions JSONB NOT NULL, -- Array of Question templates
    mapping_rules JSONB NOT NULL, -- Rules for answers → constraints
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_templates_name ON templates(name);

-- ============================================================================
-- FUNCTIONS & TRIGGERS
-- ============================================================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_parts_updated_at BEFORE UPDATE ON parts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_mcu_specs_updated_at BEFORE UPDATE ON mcu_specs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_requirement_specs_updated_at BEFORE UPDATE ON requirement_specs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_templates_updated_at BEFORE UPDATE ON templates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================================

-- Complete part view with specs and evidence count
CREATE VIEW parts_with_specs AS
SELECT 
    p.*,
    m.core,
    m.max_mhz,
    m.flash_kb,
    m.sram_kb,
    m.can_count,
    m.can_fd_count,
    m.has_fpu,
    m.has_wireless,
    m.cost_usd,
    COUNT(DISTINCT e.id) as evidence_count
FROM parts p
LEFT JOIN mcu_specs m ON p.id = m.part_id
LEFT JOIN evidence e ON p.id = e.part_id
GROUP BY p.id, m.id;

-- Parts needing review (low confidence or conflicts)
CREATE VIEW parts_needing_review AS
SELECT DISTINCT
    p.id,
    p.mpn,
    p.manufacturer,
    'low_confidence' as reason,
    MIN(e.confidence) as min_confidence
FROM parts p
JOIN evidence e ON p.id = e.part_id
WHERE e.confidence < 0.85
GROUP BY p.id, p.mpn, p.manufacturer
UNION
SELECT DISTINCT
    p.id,
    p.mpn,
    p.manufacturer,
    'conflict' as reason,
    NULL as min_confidence
FROM parts p
JOIN conflicts c ON p.id = c.part_id
WHERE c.status = 'open';

-- ============================================================================
-- SEED DATA (for testing)
-- ============================================================================

-- Insert a sample manufacturer source type enum values
COMMENT ON COLUMN documents.source_type IS 'mfg_pdf, mfg_html, dist_html, other';
COMMENT ON COLUMN parts.status IS 'active, nrnd, eol, unknown';
COMMENT ON COLUMN conflicts.status IS 'open, resolved, ignored';
COMMENT ON COLUMN extraction_runs.status IS 'success, partial, failed';
