
-- CAN TRANSCEIVER SPECIFICATIONS
-- High Speed, Low Speed, FD, etc.

CREATE TABLE IF NOT EXISTS can_specs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    part_id UUID NOT NULL UNIQUE REFERENCES parts(id) ON DELETE CASCADE,
    
    -- Performance
    max_data_rate_mbps DECIMAL(4,1), -- e.g. 1.0, 5.0 (FD)
    supply_voltage_min_v DECIMAL(4,2),
    supply_voltage_max_v DECIMAL(4,2),
    
    -- Features
    has_standby_mode BOOLEAN DEFAULT FALSE,
    has_wakeup_frame BOOLEAN DEFAULT FALSE,
    has_split_termination BOOLEAN DEFAULT FALSE,
    
    -- Protection
    esd_protection_kv DECIMAL(4,1), -- e.g. 8.0, 15.0
    fault_protection_v DECIMAL(5,1), -- e.g. +/- 40V
    
    -- Type
    protocol_type VARCHAR(20), -- 'CAN', 'CAN-FD', 'LIN'
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_can_rate ON can_specs(max_data_rate_mbps);
CREATE INDEX IF NOT EXISTS idx_can_standby ON can_specs(has_standby_mode);

-- Trigger
CREATE TRIGGER update_can_specs_updated_at BEFORE UPDATE ON can_specs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
