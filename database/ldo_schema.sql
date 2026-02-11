
-- LDO Regulator Schema

-- ============================================================================
-- LDO SPECIFICATIONS TABLE
-- Stores electrical characteristics for Linear Regulators
-- ============================================================================
CREATE TABLE IF NOT EXISTS ldo_specs (
    part_id UUID PRIMARY KEY REFERENCES parts(id) ON DELETE CASCADE,
    
    -- Input Voltage
    vin_min_v DECIMAL(5,2),
    vin_max_v DECIMAL(5,2),
    
    -- Output Voltage
    vout_type VARCHAR(20) CHECK (vout_type IN ('fixed', 'adjustable')),
    vout_fixed_v DECIMAL(5,2), -- NULL if adjustable
    vout_min_v DECIMAL(5,2),   -- Min adjustable or Same as fixed
    vout_max_v DECIMAL(5,2),   -- Max adjustable or Same as fixed
    
    -- Current
    iout_max_ma DECIMAL(10,2),
    quiescent_current_ua DECIMAL(10,2),
    
    -- Performance
    dropout_voltage_v DECIMAL(5,3), -- @ Iout Max
    psrr_db DECIMAL(5,2),           -- @ 1kHz or 10kHz usually
    noise_uv_rms DECIMAL(10,2),
    
    -- Features
    enable_pin BOOLEAN DEFAULT FALSE,
    soft_start BOOLEAN DEFAULT FALSE,
    power_good BOOLEAN DEFAULT FALSE,
    aec_q100 BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indices for LDO parametric search
CREATE INDEX IF NOT EXISTS idx_ldo_vin_max ON ldo_specs(vin_max_v);
CREATE INDEX IF NOT EXISTS idx_ldo_vout_fixed ON ldo_specs(vout_fixed_v);
CREATE INDEX IF NOT EXISTS idx_ldo_iout ON ldo_specs(iout_max_ma);
CREATE INDEX IF NOT EXISTS idx_ldo_dropout ON ldo_specs(dropout_voltage_v);
