-- HardwareGenius PostgreSQL Schema
-- Engineering-grade hardware selection system with evidence tracking

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- RESET: Drop all tables to ensure clean schema application
DROP TABLE IF EXISTS ldo_specs CASCADE;
DROP TABLE IF EXISTS errata_items CASCADE;
DROP TABLE IF EXISTS documents CASCADE;
DROP TABLE IF EXISTS evidence CASCADE;
DROP TABLE IF EXISTS conflicts CASCADE;
DROP TABLE IF EXISTS question_turns CASCADE;
DROP TABLE IF EXISTS recommendation_logs CASCADE;
DROP TABLE IF EXISTS extraction_runs CASCADE;
DROP TABLE IF EXISTS templates CASCADE;
DROP TABLE IF EXISTS requirement_specs CASCADE;
DROP TABLE IF EXISTS mcu_specs CASCADE;
DROP TABLE IF EXISTS pinned_parts CASCADE;
DROP TABLE IF EXISTS user_sessions CASCADE;
DROP TABLE IF EXISTS parts CASCADE;

-- ============================================================================
-- PARTS TABLE
-- Core part information (manufacturer, family, status, package, temp range)
-- ============================================================================
CREATE TABLE IF NOT EXISTS parts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    mpn VARCHAR(100) NOT NULL UNIQUE,
    manufacturer VARCHAR(100) NOT NULL,
    family VARCHAR(100),
    description TEXT,
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
CREATE INDEX IF NOT EXISTS idx_parts_manufacturer ON parts(manufacturer);
CREATE INDEX IF NOT EXISTS idx_parts_status ON parts(status);
CREATE INDEX IF NOT EXISTS idx_parts_package_family ON parts(package_family);
CREATE INDEX IF NOT EXISTS idx_parts_temp_range ON parts(temp_min_c, temp_max_c);
CREATE INDEX IF NOT EXISTS idx_parts_composite ON parts(manufacturer, status, package_family);

-- ============================================================================
-- USER SESSIONS & PINNED PARTS TABLES
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_key VARCHAR(100) UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_active_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pinned_parts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES user_sessions(id) ON DELETE CASCADE,
    part_id UUID REFERENCES parts(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(session_id, part_id)
);

-- ============================================================================
-- MCU_SPECS TABLE
-- Typed queryable fields for MCU specifications
-- ============================================================================
CREATE TABLE IF NOT EXISTS mcu_specs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    part_id UUID NOT NULL UNIQUE REFERENCES parts(id) ON DELETE CASCADE,

    -- Core specifications
    core VARCHAR(100),
    max_mhz INTEGER,
    flash_kb INTEGER,
    sram_kb INTEGER,
    ram_kb INTEGER,
    eeprom_kb INTEGER,

    -- Peripherals (counts)
    can_count INTEGER DEFAULT 0,
    can_fd_count INTEGER DEFAULT 0,
    usb_fs INTEGER DEFAULT 0,
    usb_hs INTEGER DEFAULT 0,
    usb_count INTEGER DEFAULT 0,
    uart_count INTEGER DEFAULT 0,
    i2c_count INTEGER DEFAULT 0,
    spi_count INTEGER DEFAULT 0,
    adc_channels INTEGER DEFAULT 0,
    adc_count INTEGER DEFAULT 0,
    dac_channels INTEGER DEFAULT 0,
    dac_count INTEGER DEFAULT 0,
    ethernet INTEGER DEFAULT 0,
    ethernet_count INTEGER DEFAULT 0,
    timers_count INTEGER DEFAULT 0,
    timer_count INTEGER DEFAULT 0,
    pwm_channels INTEGER DEFAULT 0,

    -- Features
    has_fpu INTEGER DEFAULT 0,
    has_dsp INTEGER DEFAULT 0,
    has_crypto INTEGER DEFAULT 0,
    has_wireless INTEGER DEFAULT 0,

    -- Voltages
    vdd_min_v DECIMAL(4,2),
    vdd_max_v DECIMAL(4,2),
    voltage_min_v DECIMAL(4,2),
    voltage_max_v DECIMAL(4,2),

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
CREATE INDEX IF NOT EXISTS idx_mcu_specs_core ON mcu_specs(core);
CREATE INDEX IF NOT EXISTS idx_mcu_specs_flash ON mcu_specs(flash_kb);
CREATE INDEX IF NOT EXISTS idx_mcu_specs_sram ON mcu_specs(sram_kb);
CREATE INDEX IF NOT EXISTS idx_mcu_specs_can ON mcu_specs(can_count); -- removed can_fd_count as it was removed from table
CREATE INDEX IF NOT EXISTS idx_mcu_specs_peripherals ON mcu_specs(uart_count, spi_count, i2c_count);
CREATE INDEX IF NOT EXISTS idx_mcu_specs_composite ON mcu_specs(core, flash_kb, sram_kb);

-- ============================================================================
-- DOCUMENTS TABLE
-- Source tracking with hash, version, fetch timestamp
-- ============================================================================
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
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

CREATE INDEX IF NOT EXISTS idx_documents_hash ON documents(doc_hash);
CREATE INDEX IF NOT EXISTS idx_documents_url ON documents(source_url);
CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(source_type);

-- ============================================================================
-- EVIDENCE TABLE
-- Provenance tracking for every extracted field
-- ============================================================================
CREATE TABLE IF NOT EXISTS evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    part_id UUID NOT NULL REFERENCES parts(id) ON DELETE CASCADE,
    field_path VARCHAR(255) NOT NULL, -- dot notation: "voltage_min_v"
    raw_value TEXT,
    normalized_value JSONB,
    confidence DECIMAL(3,2) NOT NULL DEFAULT 1.0, -- 0.0 to 1.0
    
    document_id UUID REFERENCES documents(id) ON DELETE SET NULL,
    page_number INTEGER,
    bbox JSONB, -- [x0, y0, x1, y1] normalized coords
    snippet_image_path TEXT, -- path to image snippet
    
    verified BOOLEAN DEFAULT FALSE,
    verified_by UUID, -- user_id
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_evidence_part ON evidence(part_id);
CREATE INDEX IF NOT EXISTS idx_evidence_field ON evidence(part_id, field_path);
CREATE INDEX IF NOT EXISTS idx_evidence_document ON evidence(document_id);
CREATE INDEX IF NOT EXISTS idx_evidence_confidence ON evidence(confidence);

-- ============================================================================
-- CONFLICTS TABLE
-- Cross-source validation and resolution workflow
-- ============================================================================
CREATE TABLE IF NOT EXISTS conflicts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    part_id UUID NOT NULL REFERENCES parts(id) ON DELETE CASCADE,
    field_path VARCHAR(255) NOT NULL,
    
    status VARCHAR(50) NOT NULL DEFAULT 'open', -- open, resolved, ignored
    resolution TEXT,
    resolved_by UUID,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conflicts_part ON conflicts(part_id);
CREATE INDEX IF NOT EXISTS idx_conflicts_status ON conflicts(status);

-- ============================================================================
-- REQUIREMENT_SPECS TABLE
-- Store user specs with uncertainty tracking
-- ============================================================================
CREATE TABLE IF NOT EXISTS requirement_specs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_text TEXT,
    spec JSONB,
    mode VARCHAR(50) DEFAULT 'discovery', -- discovery, comparison, verification
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_requirement_specs_mode ON requirement_specs(mode);

-- ============================================================================
-- QUESTION_TURNS TABLE
-- Conversation history for question-answer flow
-- ============================================================================
CREATE TABLE IF NOT EXISTS question_turns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    spec_id UUID REFERENCES requirement_specs(id) ON DELETE CASCADE,
    turn_index INTEGER NOT NULL,
    question_text TEXT,
    user_answer TEXT,
    parsed_answer JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_question_turns_spec ON question_turns(spec_id);
CREATE INDEX IF NOT EXISTS idx_question_turns_turn ON question_turns(spec_id, turn_index);

-- ============================================================================
-- RECOMMENDATION_LOGS TABLE
-- Audit trail with explanations
-- ============================================================================
CREATE TABLE IF NOT EXISTS recommendation_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    spec_id UUID REFERENCES requirement_specs(id) ON DELETE SET NULL,
    candidates_count INTEGER,
    top_candidate_id UUID,
    latency_ms INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_recommendation_logs_spec ON recommendation_logs(spec_id);

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
    CAST(NULL AS NUMERIC) as min_confidence
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
