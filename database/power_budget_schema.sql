-- Power Budget Database Schema
-- Stores power consumption data for MCUs in different operating modes

CREATE TABLE IF NOT EXISTS power_modes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- MCU reference
    part_id UUID REFERENCES parts(id) ON DELETE CASCADE,
    
    -- Operating mode
    mode_name VARCHAR(50) NOT NULL,  -- 'run', 'sleep', 'stop', 'standby', 'shutdown'
    
    -- Power consumption
    voltage_v DECIMAL(4, 2) NOT NULL,
    current_typ_ua DECIMAL(12, 2),  -- Typical current in microamps
    current_max_ua DECIMAL(12, 2),  -- Maximum current in microamps
    
    -- Operating conditions
    frequency_mhz DECIMAL(10, 2),  -- CPU frequency (NULL for low-power modes)
    temperature_c INTEGER,  -- Temperature (25°C typical)
    
    -- Additional details
    peripherals_active TEXT[],  -- List of active peripherals
    notes TEXT,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS peripheral_power (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- MCU reference
    part_id UUID REFERENCES parts(id) ON DELETE CASCADE,
    
    -- Peripheral identification
    peripheral_type VARCHAR(50) NOT NULL,  -- 'uart', 'spi', 'i2c', 'adc', 'dac', 'timer', etc.
    peripheral_instance VARCHAR(50),  -- 'USART1', 'SPI2', etc.
    
    -- Power consumption
    current_typ_ua DECIMAL(12, 2),
    current_max_ua DECIMAL(12, 2),
    
    -- Operating conditions
    operating_frequency_mhz DECIMAL(10, 2),
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_power_modes_part ON power_modes(part_id);
CREATE INDEX IF NOT EXISTS idx_power_modes_mode ON power_modes(mode_name);
CREATE INDEX IF NOT EXISTS idx_peripheral_power_part ON peripheral_power(part_id);
CREATE INDEX IF NOT EXISTS idx_peripheral_power_type ON peripheral_power(peripheral_type);

-- Comments
COMMENT ON TABLE power_modes IS 'MCU power consumption in different operating modes';
COMMENT ON TABLE peripheral_power IS 'Peripheral power consumption data';
COMMENT ON COLUMN power_modes.current_typ_ua IS 'Typical current consumption in microamps';
COMMENT ON COLUMN power_modes.peripherals_active IS 'List of peripherals active in this mode';
