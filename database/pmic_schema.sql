
-- PMIC SPECIFICATIONS
-- Power Management ICs (STPMIC1, Automotive LDOs, etc.)

CREATE TABLE IF NOT EXISTS pmic_specs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    part_id UUID NOT NULL UNIQUE REFERENCES parts(id) ON DELETE CASCADE,
    
    -- Structure
    has_buck BOOLEAN DEFAULT FALSE,
    buck_count INTEGER DEFAULT 0,
    
    has_boost BOOLEAN DEFAULT FALSE,
    boost_count INTEGER DEFAULT 0,
    
    has_ldo BOOLEAN DEFAULT FALSE,
    ldo_count INTEGER DEFAULT 0,
    
    -- Performance
    vin_min_v DECIMAL(6,2),
    vin_max_v DECIMAL(6,2),
    
    -- Interfaces
    interface_type VARCHAR(50), -- I2C, SPI, GPIO
    
    -- Specific Features
    is_automotive BOOLEAN DEFAULT FALSE, -- AEC-Q100
    has_watchdog BOOLEAN DEFAULT FALSE,
    has_battery_charger BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pmic_buck ON pmic_specs(buck_count);
CREATE INDEX IF NOT EXISTS idx_pmic_ldo ON pmic_specs(ldo_count);
CREATE INDEX IF NOT EXISTS idx_pmic_automotive ON pmic_specs(is_automotive);

-- Trigger for updated_at
CREATE TRIGGER update_pmic_specs_updated_at BEFORE UPDATE ON pmic_specs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
