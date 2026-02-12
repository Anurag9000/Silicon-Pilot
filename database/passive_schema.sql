
-- Passive Component Specifications Table
DROP TABLE IF EXISTS passive_specs CASCADE;

CREATE TABLE IF NOT EXISTS passive_specs (
    part_id UUID PRIMARY KEY REFERENCES parts(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL, -- Resistor, Capacitor, Inductor
    value_primary NUMERIC(15, 6), -- Ohms, Farads, Henries
    tolerance_percent NUMERIC(5, 2),
    power_rating_w NUMERIC(6, 3), -- for resistors
    voltage_rating_v NUMERIC(6, 2), -- for capacitors
    package_case VARCHAR(50), -- 0402, 0603, etc.
    dielectric_type VARCHAR(50) -- X7R, C0G, etc. (for caps)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_passive_type_val ON passive_specs(type, value_primary);
CREATE INDEX IF NOT EXISTS idx_passive_package ON passive_specs(package_case);
