
-- PASSIVE COMPONENT SPECIFICATIONS
-- Resistors, Capacitors, Inductors (Generic)

CREATE TABLE IF NOT EXISTS passive_specs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    part_id UUID NOT NULL UNIQUE REFERENCES parts(id) ON DELETE CASCADE,
    
    -- Type
    component_type VARCHAR(20) NOT NULL, -- 'Resistor', 'Capacitor', 'Inductor'
    
    -- Value
    value_primary DECIMAL(18,9) NOT NULL, -- Ohms, Farads, Henries (Base units)
    value_formatted VARCHAR(20), -- '10k', '100nF' (For display)
    
    -- Specs
    tolerance_percent DECIMAL(5,2), -- e.g. 1.0, 5.0, 20.0
    power_rating_w DECIMAL(8,3), -- Resistors
    voltage_rating_v DECIMAL(8,2), -- Capacitors
    dielectric_type VARCHAR(20), -- X7R, C0G (Caps)
    
    -- Package
    package_case VARCHAR(20), -- '0402', '0603', '0805'
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_passive_type ON passive_specs(component_type);
CREATE INDEX IF NOT EXISTS idx_passive_value ON passive_specs(value_primary);
CREATE INDEX IF NOT EXISTS idx_passive_package ON passive_specs(package_case);

-- Trigger
CREATE TRIGGER update_passive_specs_updated_at BEFORE UPDATE ON passive_specs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
