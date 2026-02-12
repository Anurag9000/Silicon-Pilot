
-- Sensor Specifications Table
DROP TABLE IF EXISTS sensor_specs CASCADE;

CREATE TABLE IF NOT EXISTS sensor_specs (
    part_id UUID PRIMARY KEY REFERENCES parts(id) ON DELETE CASCADE,
    sensor_type VARCHAR(50) NOT NULL, -- Accelerometer, Gyroscope, Temperature, Humidity, Pressure, Magnetometer, Microphone
    interface TEXT[], -- I2C, SPI, Analog, Digital
    supply_voltage_min_v NUMERIC(4, 2),
    supply_voltage_max_v NUMERIC(4, 2),
    resolution_bits INTEGER,
    sampling_rate_hz NUMERIC(10, 2),
    package_type TEXT,
    automotive_grade BOOLEAN DEFAULT FALSE
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_sensor_type ON sensor_specs(sensor_type);
CREATE INDEX IF NOT EXISTS idx_sensor_interface ON sensor_specs USING GIN(interface);
