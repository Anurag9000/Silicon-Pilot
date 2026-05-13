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
    theta_ja_c_w REAL,
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
-- DATASHEET_PARAMETERS TABLE
-- Deep parameter extraction from PDFs: every min/typ/max row, per section, per page
-- ============================================================================
DROP TABLE IF EXISTS datasheet_parameters CASCADE;
CREATE TABLE IF NOT EXISTS datasheet_parameters (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    part_id UUID NOT NULL REFERENCES parts(id) ON DELETE CASCADE,
    section VARCHAR(100) NOT NULL,      -- e.g. 'absolute_max', 'dc_characteristics', 'thermal'
    parameter VARCHAR(255) NOT NULL,    -- e.g. 'VIH — Input high-level voltage'
    min_value TEXT,
    typ_value TEXT,
    max_value TEXT,
    unit VARCHAR(50),
    conditions TEXT,
    source_page INTEGER,                -- PDF page number
    raw_text TEXT,                      -- Raw extracted snippet
    confidence REAL DEFAULT 1.0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ds_params_part ON datasheet_parameters(part_id);
CREATE INDEX IF NOT EXISTS idx_ds_params_section ON datasheet_parameters(part_id, section);
CREATE INDEX IF NOT EXISTS idx_ds_params_param ON datasheet_parameters(parameter);

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

-- ============================================================================
-- COMPONENT SPEC TABLES (previously missing — required by hard_filter, drc, bom_checker)
-- ============================================================================

CREATE TABLE IF NOT EXISTS ldo_specs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    part_id UUID NOT NULL UNIQUE REFERENCES parts(id) ON DELETE CASCADE,
    vin_min_v  DECIMAL(5,2),
    vin_max_v  DECIMAL(5,2),
    vout_fixed_v DECIMAL(5,2),
    vout_adj_min_v DECIMAL(5,2),
    vout_adj_max_v DECIMAL(5,2),
    iout_max_ma  DECIMAL(8,2),
    dropout_mv   DECIMAL(6,2),
    quiescent_ua DECIMAL(8,2),
    package      VARCHAR(50),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_ldo_specs_part ON ldo_specs(part_id);

CREATE TABLE IF NOT EXISTS pmic_specs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    part_id UUID NOT NULL UNIQUE REFERENCES parts(id) ON DELETE CASCADE,
    vin_min_v  DECIMAL(5,2),
    vin_max_v  DECIMAL(5,2),
    buck_count INTEGER DEFAULT 0,
    ldo_count  INTEGER DEFAULT 0,
    boost_count INTEGER DEFAULT 0,
    total_iout_max_a DECIMAL(6,2),
    has_usb_charger BOOLEAN DEFAULT FALSE,
    has_fuel_gauge  BOOLEAN DEFAULT FALSE,
    interface       VARCHAR(50),  -- I2C, SPI, etc.
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_pmic_specs_part ON pmic_specs(part_id);

CREATE TABLE IF NOT EXISTS can_specs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    part_id UUID NOT NULL UNIQUE REFERENCES parts(id) ON DELETE CASCADE,
    can_fd_support   BOOLEAN DEFAULT FALSE,
    max_baudrate_mbps DECIMAL(4,2),
    vcc_min_v   DECIMAL(5,2),
    vcc_max_v   DECIMAL(5,2),
    has_isolation BOOLEAN DEFAULT FALSE,
    package       VARCHAR(50),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_can_specs_part ON can_specs(part_id);

CREATE TABLE IF NOT EXISTS sensor_specs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    part_id UUID NOT NULL UNIQUE REFERENCES parts(id) ON DELETE CASCADE,
    sensor_type   VARCHAR(50) NOT NULL,  -- temperature, humidity, pressure, accelerometer, etc.
    interface     VARCHAR(50),           -- I2C, SPI, UART
    range_min     DECIMAL(10,4),
    range_max     DECIMAL(10,4),
    range_unit    VARCHAR(20),
    resolution    DECIMAL(10,6),
    accuracy      DECIMAL(8,4),
    current_ua    DECIMAL(10,2),
    vdd_min_v     DECIMAL(5,2),
    vdd_max_v     DECIMAL(5,2),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_sensor_specs_part ON sensor_specs(part_id);
CREATE INDEX IF NOT EXISTS idx_sensor_specs_type ON sensor_specs(sensor_type);

CREATE TABLE IF NOT EXISTS passive_specs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    part_id UUID NOT NULL UNIQUE REFERENCES parts(id) ON DELETE CASCADE,
    component_type VARCHAR(50) NOT NULL,  -- resistor, capacitor, inductor, crystal
    value_nominal  DECIMAL(18,6),
    value_unit     VARCHAR(20),           -- ohm, F, H, Hz
    tolerance_pct  DECIMAL(6,3),
    voltage_rating_v DECIMAL(8,2),
    current_rating_a DECIMAL(8,4),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_passive_specs_part ON passive_specs(part_id);
CREATE INDEX IF NOT EXISTS idx_passive_specs_type ON passive_specs(component_type);

CREATE TABLE IF NOT EXISTS dcdc_specs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    part_id UUID NOT NULL UNIQUE REFERENCES parts(id) ON DELETE CASCADE,
    topology      VARCHAR(50),   -- buck, boost, buck-boost, flyback
    vin_min_v     DECIMAL(5,2),
    vin_max_v     DECIMAL(5,2),
    vout_min_v    DECIMAL(5,2),
    vout_max_v    DECIMAL(5,2),
    iout_max_a    DECIMAL(6,3),
    efficiency_pct DECIMAL(5,2),
    switching_freq_khz INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_dcdc_specs_part ON dcdc_specs(part_id);

-- ============================================================================
-- POWER BUDGET TABLES (required by power_budget_calculator.py)
-- ============================================================================

CREATE TABLE IF NOT EXISTS power_modes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    part_id UUID NOT NULL REFERENCES parts(id) ON DELETE CASCADE,
    mode_name     VARCHAR(50) NOT NULL,  -- run, sleep, stop, standby, shutdown
    voltage_v     DECIMAL(5,3),
    current_typ_ua DECIMAL(12,3),
    frequency_mhz INTEGER,
    wake_latency_us INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(part_id, mode_name)
);
CREATE INDEX IF NOT EXISTS idx_power_modes_part ON power_modes(part_id);

CREATE TABLE IF NOT EXISTS peripheral_power (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    part_id UUID NOT NULL REFERENCES parts(id) ON DELETE CASCADE,
    peripheral_type     VARCHAR(50) NOT NULL,   -- uart, spi, i2c, can, usb, adc, dac, timer
    peripheral_instance VARCHAR(50),            -- UART1, SPI2, etc.
    current_typ_ua DECIMAL(12,3),
    voltage_v      DECIMAL(5,3),
    notes          TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_peripheral_power_part ON peripheral_power(part_id);
CREATE INDEX IF NOT EXISTS idx_peripheral_power_type ON peripheral_power(part_id, peripheral_type);

-- ============================================================================
-- FIRMWARE STACKS TABLE (required by firmware_stack_recommender.py)
-- ============================================================================

CREATE TABLE IF NOT EXISTS firmware_stacks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    stack_name     VARCHAR(200) NOT NULL UNIQUE,
    stack_type     VARCHAR(50) NOT NULL,        -- rtos, tcp_ip, usb, filesystem, crypto, gui, ble
    vendor         VARCHAR(100),
    version        VARCHAR(50),
    license        VARCHAR(100),
    flash_typical_kb INTEGER,
    ram_typical_kb   INTEGER,
    supported_cores  TEXT[],                    -- ["Cortex-M4", "Cortex-M7", ...]
    features         TEXT[],
    protocols        TEXT[],
    documentation_url TEXT,
    repository_url    TEXT,
    popularity_score  INTEGER DEFAULT 50,       -- 0-100
    maturity_score    INTEGER DEFAULT 50,
    community_score   INTEGER DEFAULT 50,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_firmware_stacks_type ON firmware_stacks(stack_type);

-- Seed essential firmware stacks
INSERT INTO firmware_stacks (stack_name, stack_type, vendor, version, license, flash_typical_kb, ram_typical_kb,
    supported_cores, features, protocols, documentation_url, repository_url, popularity_score, maturity_score, community_score)
VALUES
  ('FreeRTOS', 'rtos', 'Amazon', '10.6', 'MIT', 10, 5, ARRAY['Cortex-M0','Cortex-M0+','Cortex-M3','Cortex-M4','Cortex-M7','Cortex-M33'],
   ARRAY['preemptive','tickless','co-routines','idle-hooks'], ARRAY[]::TEXT[],
   'https://freertos.org', 'https://github.com/FreeRTOS/FreeRTOS', 95, 95, 90),
  ('Zephyr RTOS', 'rtos', 'Linux Foundation', '3.5', 'Apache-2.0', 60, 20, ARRAY['Cortex-M0','Cortex-M0+','Cortex-M3','Cortex-M4','Cortex-M7','Cortex-M33'],
   ARRAY['preemptive','tickless','device-model','logging'], ARRAY['BLE','LoRa','CAN','Ethernet'],
   'https://docs.zephyrproject.org', 'https://github.com/zephyrproject-rtos/zephyr', 85, 85, 80),
  ('lwIP', 'tcp_ip', 'Community', '2.2', 'BSD', 100, 80, ARRAY['Cortex-M3','Cortex-M4','Cortex-M7'],
   ARRAY['sockets','raw-api'], ARRAY['IPv4','IPv6','TCP','UDP','HTTP','MQTT','DNS'],
   'https://savannah.nongnu.org/projects/lwip/', 'https://github.com/lwip-tcpip/lwip', 90, 90, 80),
  ('TinyUSB', 'usb', 'hathach', '0.16', 'MIT', 20, 8, ARRAY['Cortex-M0','Cortex-M0+','Cortex-M3','Cortex-M4','Cortex-M7'],
   ARRAY['device','host','cdc','msc','hid','dfu'], ARRAY['USB-FS','USB-HS'],
   'https://docs.tinyusb.org', 'https://github.com/hathach/tinyusb', 85, 80, 85),
  ('FatFs', 'filesystem', 'ChaN', 'R0.15', 'MIT', 12, 2, ARRAY['Cortex-M0','Cortex-M0+','Cortex-M3','Cortex-M4','Cortex-M7'],
   ARRAY['fat12','fat16','fat32','exfat'], ARRAY[]::TEXT[],
   'http://elm-chan.org/fsw/ff/', NULL, 90, 95, 70),
  ('LittleFS', 'filesystem', 'ARM', '2.8', 'BSD', 16, 4, ARRAY['Cortex-M0','Cortex-M0+','Cortex-M3','Cortex-M4','Cortex-M7'],
   ARRAY['power-loss-resilient','wear-leveling'], ARRAY[]::TEXT[],
   'https://github.com/littlefs-project/littlefs', 'https://github.com/littlefs-project/littlefs', 80, 85, 75),
  ('mbedTLS', 'crypto', 'ARM', '3.5', 'Apache-2.0', 200, 50, ARRAY['Cortex-M3','Cortex-M4','Cortex-M7','Cortex-M33'],
   ARRAY['tls','x509','aes','rsa','ecdsa','sha'], ARRAY['TLS1.2','TLS1.3'],
   'https://tls.mbed.org', 'https://github.com/Mbed-TLS/mbedtls', 85, 85, 80),
  ('LVGL', 'gui', 'LVGL Kft', '9.0', 'MIT', 150, 32, ARRAY['Cortex-M4','Cortex-M7'],
   ARRAY['widgets','animations','themes','touchscreen'], ARRAY[]::TEXT[],
   'https://lvgl.io', 'https://github.com/lvgl/lvgl', 90, 85, 90)
ON CONFLICT (stack_name) DO NOTHING;

-- ============================================================================
-- REFERENCE DESIGNS TABLE (required by reference_design_matcher.py)
-- ============================================================================

CREATE TABLE IF NOT EXISTS reference_designs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    design_name      VARCHAR(200) NOT NULL,
    design_code      VARCHAR(100) NOT NULL UNIQUE,
    manufacturer     VARCHAR(100) NOT NULL,
    application_area VARCHAR(100),         -- motor-control, IoT, industrial, audio, etc.
    description      TEXT,
    mcu_part_ids     UUID[],               -- MCUs featured in this design
    required_peripherals TEXT[],
    schematic_url    TEXT,
    bom_url          TEXT,
    gerber_url       TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_ref_designs_app ON reference_designs(application_area);
CREATE INDEX IF NOT EXISTS idx_ref_designs_mfr ON reference_designs(manufacturer);

-- ============================================================================
-- USER SELECTIONS TABLE (required by ml/ranker.py for training)
-- ============================================================================

CREATE TABLE IF NOT EXISTS user_selections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id       UUID REFERENCES user_sessions(id) ON DELETE SET NULL,
    query_text       TEXT NOT NULL,
    query_type       VARCHAR(50) DEFAULT 'search',
    results_shown    UUID[],
    result_count     INTEGER,
    selected_part_id UUID REFERENCES parts(id) ON DELETE SET NULL,
    selection_rank   INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_user_selections_session ON user_selections(session_id);
CREATE INDEX IF NOT EXISTS idx_user_selections_part ON user_selections(selected_part_id);

-- ============================================================================
-- DRC VIOLATIONS TABLE (required by design_rule_checker.py save_violations)
-- ============================================================================

CREATE TABLE IF NOT EXISTS drc_violations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    design_id    UUID,               -- logical design group (not FK — designs not persisted)
    rule_id      VARCHAR(20) NOT NULL,
    rule_name    VARCHAR(200),
    severity     VARCHAR(20) NOT NULL DEFAULT 'error',  -- error, warning, info
    part_id      UUID REFERENCES parts(id) ON DELETE SET NULL,
    component    VARCHAR(100),
    message      TEXT NOT NULL,
    recommendation TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_drc_violations_design ON drc_violations(design_id);
CREATE INDEX IF NOT EXISTS idx_drc_violations_rule   ON drc_violations(rule_id);
CREATE INDEX IF NOT EXISTS idx_drc_violations_sev    ON drc_violations(severity);

