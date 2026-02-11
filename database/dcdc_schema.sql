
-- DC-DC CONVERTER SPECIFICATIONS
-- Buck, Boost, Buck-Boost, etc.

CREATE TABLE IF NOT EXISTS dcdc_specs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    part_id UUID NOT NULL UNIQUE REFERENCES parts(id) ON DELETE CASCADE,
    
    -- Topology
    topology VARCHAR(50), -- buck, boost, buck-boost, flyback, unknown
    is_synchronous BOOLEAN DEFAULT FALSE,
    num_outputs INTEGER DEFAULT 1,
    
    -- Inputs
    vin_min_v DECIMAL(6,2),
    vin_max_v DECIMAL(6,2),
    
    -- Outputs
    vout_min_v DECIMAL(6,2),
    vout_max_v DECIMAL(6,2), -- identical if fixed
    vout_fixed BOOLEAN DEFAULT FALSE,
    
    -- Performance
    iout_max_a DECIMAL(6,3), -- Amps
    frequency_khz_min INTEGER,
    frequency_khz_max INTEGER,
    efficiency_percent_typ DECIMAL(5,2),
    
    -- Features
    iq_ua DECIMAL(8,2), -- Quiescent current
    has_enable BOOLEAN,
    has_soft_start BOOLEAN,
    has_power_good BOOLEAN,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dcdc_topology ON dcdc_specs(topology);
CREATE INDEX IF NOT EXISTS idx_dcdc_vin ON dcdc_specs(vin_min_v, vin_max_v);
CREATE INDEX IF NOT EXISTS idx_dcdc_vout ON dcdc_specs(vout_min_v, vout_max_v);
CREATE INDEX IF NOT EXISTS idx_dcdc_iout ON dcdc_specs(iout_max_a);

-- Trigger for updated_at
CREATE TRIGGER update_dcdc_specs_updated_at BEFORE UPDATE ON dcdc_specs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
