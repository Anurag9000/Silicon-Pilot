
-- SENSOR SPECIFICATIONS
-- MEMS (Accel, Gyro) and Environmental (Temp, Humidity)

CREATE TABLE IF NOT EXISTS sensor_specs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    part_id UUID NOT NULL UNIQUE REFERENCES parts(id) ON DELETE CASCADE,
    
    -- Type
    sensor_type VARCHAR(50), -- 'Accelerometer', 'Gyroscope', 'Temperature', 'Pressure'
    
    -- Interfaces
    interface_type VARCHAR(50), -- 'I2C', 'SPI', 'I2C/SPI', 'Analog'
    
    -- Power
    supply_voltage_min_v DECIMAL(4,2),
    supply_voltage_max_v DECIMAL(4,2),
    current_consumption_ua DECIMAL(8,2), -- Active current
    
    -- Performance
    resolution_bits INTEGER,
    output_rate_max_hz DECIMAL(8,1), -- ODR
    measurement_range VARCHAR(50), -- e.g. '+/- 2g/4g/8g/16g' or '-40 to +125C'
    
    -- Package
    package_type VARCHAR(50), -- LGA, DFN, SOT
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sensor_type ON sensor_specs(sensor_type);
CREATE INDEX IF NOT EXISTS idx_sensor_interface ON sensor_specs(interface_type);

-- Trigger
CREATE TRIGGER update_sensor_specs_updated_at BEFORE UPDATE ON sensor_specs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
