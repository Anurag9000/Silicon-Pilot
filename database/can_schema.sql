
-- CAN Transceiver Specifications Table
DROP TABLE IF EXISTS can_specs CASCADE;

CREATE TABLE IF NOT EXISTS can_specs (
    part_id UUID PRIMARY KEY REFERENCES parts(id) ON DELETE CASCADE,
    data_rate_mbps NUMERIC(5, 2),
    supply_voltage_min_v NUMERIC(4, 2),
    supply_voltage_max_v NUMERIC(4, 2),
    has_standby_mode BOOLEAN DEFAULT FALSE,
    has_wakeup_mode BOOLEAN DEFAULT FALSE,
    protection_esd_kv NUMERIC(4, 1),
    automotive_grade BOOLEAN DEFAULT FALSE,
    package_type TEXT
);

-- Index for parametric search
CREATE INDEX IF NOT EXISTS idx_can_data_rate ON can_specs(data_rate_mbps);
CREATE INDEX IF NOT EXISTS idx_can_voltage ON can_specs(supply_voltage_min_v, supply_voltage_max_v);
