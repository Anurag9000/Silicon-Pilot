
-- PMIC Specifications Table
DROP TABLE IF EXISTS pmic_specs CASCADE;
CREATE TABLE IF NOT EXISTS pmic_specs (
    part_id UUID PRIMARY KEY REFERENCES parts(id) ON DELETE CASCADE,
    input_voltage_min_v NUMERIC(5, 2),
    input_voltage_max_v NUMERIC(5, 2),
    output_count INTEGER,
    buck_count INTEGER DEFAULT 0,
    ldo_count INTEGER DEFAULT 0,
    boost_count INTEGER DEFAULT 0,
    control_interface TEXT[], -- e.g., ARRAY['I2C', 'SPI']
    automotive_grade BOOLEAN DEFAULT FALSE,
    operating_temp_min_c INTEGER,
    operating_temp_max_c INTEGER,
    package_type TEXT
);

-- Index for parametric search
CREATE INDEX IF NOT EXISTS idx_pmic_input_v ON pmic_specs(input_voltage_min_v, input_voltage_max_v);
CREATE INDEX IF NOT EXISTS idx_pmic_out_count ON pmic_specs(output_count);
