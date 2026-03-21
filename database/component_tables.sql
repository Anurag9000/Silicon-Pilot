-- Additional Component Category Tables for HardwareGenius
-- Extends schema.sql with POWER, COMMUNICATION, SENSOR, MEMORY, PASSIVE, CONNECTOR, PROTECTION

-- ============================================================================
-- POWER COMPONENT TABLES
-- ============================================================================

-- PMICs (Power Management ICs)




-- DC-DC Converters (Buck, Boost, Buck-Boost)




-- LDOs (Low-Dropout Regulators)





-- ============================================================================
-- COMMUNICATION COMPONENT TABLES
-- ============================================================================

-- CAN Transceivers
CREATE TABLE IF NOT EXISTS can_transceiver_specs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    part_id UUID NOT NULL UNIQUE REFERENCES parts(id) ON DELETE CASCADE,
    
    -- Protocol support
    supports_can_2_0b BOOLEAN DEFAULT TRUE,
    supports_can_fd BOOLEAN DEFAULT FALSE,
    max_bitrate_mbps DECIMAL(5,2),
    
    -- Electrical
    supply_voltage_min_v DECIMAL(4,2),
    supply_voltage_max_v DECIMAL(4,2),
    standby_current_ua DECIMAL(8,2),
    
    -- Protection
    esd_protection_kv INTEGER,
    has_thermal_shutdown BOOLEAN DEFAULT FALSE,
    has_short_circuit_protection BOOLEAN DEFAULT FALSE,
    
    -- Features
    has_silent_mode BOOLEAN DEFAULT FALSE,
    has_slope_control BOOLEAN DEFAULT FALSE,
    isolation_voltage_v INTEGER DEFAULT 0,
    
    extras JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_can_transceiver_fd ON can_transceiver_specs(supports_can_fd);

-- Ethernet PHYs
CREATE TABLE IF NOT EXISTS ethernet_phy_specs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    part_id UUID NOT NULL UNIQUE REFERENCES parts(id) ON DELETE CASCADE,
    
    -- Speed support
    supports_10mbps BOOLEAN DEFAULT TRUE,
    supports_100mbps BOOLEAN DEFAULT TRUE,
    supports_1000mbps BOOLEAN DEFAULT FALSE,
    
    -- Interface
    interface_type VARCHAR(50),  -- RMII, RGMII, MII, SGMII
    
    -- Features
    has_auto_negotiation BOOLEAN DEFAULT TRUE,
    has_cable_diagnostics BOOLEAN DEFAULT FALSE,
    has_wol BOOLEAN DEFAULT FALSE,  -- Wake-on-LAN
    has_eee BOOLEAN DEFAULT FALSE,  -- Energy Efficient Ethernet
    
    -- Power
    power_consumption_mw INTEGER,
    
    extras JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ethernet_phy_speed ON ethernet_phy_specs(supports_1000mbps, supports_100mbps);


-- ============================================================================
-- SENSOR TABLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS sensor_specs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    part_id UUID NOT NULL UNIQUE REFERENCES parts(id) ON DELETE CASCADE,
    
    -- Type
    sensor_type VARCHAR(100),  -- IMU, temperature, pressure, current, proximity, etc.
    
    -- Measurement range
    range_min DECIMAL(12,4),
    range_max DECIMAL(12,4),
    range_unit VARCHAR(20),  -- °C, Pa, A, V, m, etc.
    
    -- Accuracy
    accuracy DECIMAL(8,4),
    accuracy_unit VARCHAR(20),
    resolution_bits INTEGER,
    
    -- Interface
    interface_type VARCHAR(50),  -- I2C, SPI, analog, UART
    i2c_address_hex VARCHAR(10),
    
    -- Performance
    sample_rate_hz INTEGER,
    power_consumption_ua DECIMAL(8,2),
    
    -- Features (sensor-specific)
    has_fifo BOOLEAN DEFAULT FALSE,
    has_interrupt BOOLEAN DEFAULT FALSE,
    has_self_test BOOLEAN DEFAULT FALSE,
    
    extras JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sensor_type ON sensor_specs(sensor_type);
CREATE INDEX IF NOT EXISTS idx_sensor_interface ON sensor_specs(interface_type);


-- ============================================================================
-- MEMORY TABLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS memory_specs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    part_id UUID NOT NULL UNIQUE REFERENCES parts(id) ON DELETE CASCADE,
    
    -- Type
    memory_type VARCHAR(50),  -- Flash (NOR/NAND), EEPROM, SRAM, FRAM, MRAM
    
    -- Capacity
    capacity_kb INTEGER,
    capacity_mb INTEGER,
    
    -- Organization
    word_size_bits INTEGER,
    page_size_bytes INTEGER,
    sector_size_kb INTEGER,
    
    -- Interface
    interface_type VARCHAR(50),  -- SPI, I2C, parallel, QSPI
    max_clock_mhz INTEGER,
    
    -- Performance
    read_speed_mbps DECIMAL(8,2),
    write_speed_mbps DECIMAL(8,2),
    erase_time_ms INTEGER,
    
    -- Endurance
    write_cycles INTEGER,
    data_retention_years INTEGER,
    
    -- Power
    active_current_ma DECIMAL(6,2),
    standby_current_ua DECIMAL(8,2),
    
    extras JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_memory_type ON memory_specs(memory_type);
CREATE INDEX IF NOT EXISTS idx_memory_capacity ON memory_specs(capacity_kb, capacity_mb);


-- ============================================================================
-- PASSIVE COMPONENT TABLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS passive_specs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    part_id UUID NOT NULL UNIQUE REFERENCES parts(id) ON DELETE CASCADE,
    
    -- Type
    component_type VARCHAR(50),  -- capacitor, resistor, inductor
    
    -- Capacitor fields
    capacitance_pf BIGINT,
    capacitance_uf DECIMAL(12,6),
    capacitor_type VARCHAR(50),  -- ceramic, electrolytic, tantalum, film
    dielectric VARCHAR(50),  -- X7R, X5R, C0G/NP0, Y5V
    esr_mohm DECIMAL(8,3),  -- Equivalent Series Resistance
    
    -- Resistor fields
    resistance_ohm DECIMAL(12,3),
    resistance_kohm DECIMAL(12,3),
    resistance_mohm DECIMAL(12,3),
    tolerance_percent DECIMAL(5,2),
    power_rating_w DECIMAL(6,3),
    
    -- Inductor fields
    inductance_uh DECIMAL(12,3),
    inductance_mh DECIMAL(12,3),
    dcr_ohm DECIMAL(8,3),  -- DC Resistance
    saturation_current_a DECIMAL(6,2),
    
    -- Common
    voltage_rating_v INTEGER,
    temperature_coefficient VARCHAR(50),
    
    extras JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_passive_type ON passive_specs(component_type);
CREATE INDEX IF NOT EXISTS idx_passive_capacitance ON passive_specs(capacitance_uf);
CREATE INDEX IF NOT EXISTS idx_passive_resistance ON passive_specs(resistance_ohm);


-- ============================================================================
-- CONNECTOR TABLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS connector_specs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    part_id UUID NOT NULL UNIQUE REFERENCES parts(id) ON DELETE CASCADE,
    
    -- Type
    connector_type VARCHAR(100),  -- USB, header, terminal block, RF, etc.
    
    -- Physical
    pin_count INTEGER,
    pitch_mm DECIMAL(6,3),
    mounting_type VARCHAR(50),  -- through-hole, SMD, panel-mount
    orientation VARCHAR(50),  -- vertical, right-angle
    
    -- Electrical
    current_rating_a DECIMAL(6,2),
    voltage_rating_v INTEGER,
    contact_resistance_mohm DECIMAL(6,3),
    
    -- Mechanical
    mating_cycles INTEGER,
    insertion_force_n DECIMAL(6,2),
    
    -- Features
    has_locking BOOLEAN DEFAULT FALSE,
    has_shielding BOOLEAN DEFAULT FALSE,
    waterproof_rating VARCHAR(20),  -- IP67, IP68, etc.
    
    extras JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_connector_type ON connector_specs(connector_type);
CREATE INDEX IF NOT EXISTS idx_connector_pins ON connector_specs(pin_count);


-- ============================================================================
-- PROTECTION COMPONENT TABLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS protection_specs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    part_id UUID NOT NULL UNIQUE REFERENCES parts(id) ON DELETE CASCADE,
    
    -- Type
    protection_type VARCHAR(50),  -- TVS, ESD, fuse, PTC, varistor
    
    -- TVS/ESD fields
    breakdown_voltage_v DECIMAL(8,2),
    clamping_voltage_v DECIMAL(8,2),
    peak_pulse_current_a DECIMAL(8,2),
    capacitance_pf DECIMAL(8,2),
    esd_rating_kv DECIMAL(6,2),
    
    -- Fuse fields
    rated_current_a DECIMAL(6,2),
    voltage_rating_v INTEGER,
    breaking_capacity_a INTEGER,
    time_constant VARCHAR(50),  -- fast, slow, time-delay
    
    -- Common
    bidirectional BOOLEAN DEFAULT FALSE,
    response_time_ns INTEGER,
    
    extras JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_protection_type ON protection_specs(protection_type);
CREATE INDEX IF NOT EXISTS idx_protection_voltage ON protection_specs(breakdown_voltage_v);


-- ============================================================================
-- AUTO-UPDATE TRIGGERS
-- ============================================================================

-- PMIC
CREATE TRIGGER update_pmic_specs_updated_at
    BEFORE UPDATE ON pmic_specs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- DC-DC
CREATE TRIGGER update_dcdc_specs_updated_at
    BEFORE UPDATE ON dcdc_specs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- LDO
CREATE TRIGGER update_ldo_specs_updated_at
    BEFORE UPDATE ON ldo_specs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- CAN Transceiver
CREATE TRIGGER update_can_transceiver_specs_updated_at
    BEFORE UPDATE ON can_transceiver_specs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Ethernet PHY
CREATE TRIGGER update_ethernet_phy_specs_updated_at
    BEFORE UPDATE ON ethernet_phy_specs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Sensor
CREATE TRIGGER update_sensor_specs_updated_at
    BEFORE UPDATE ON sensor_specs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Memory
CREATE TRIGGER update_memory_specs_updated_at
    BEFORE UPDATE ON memory_specs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Passive
CREATE TRIGGER update_passive_specs_updated_at
    BEFORE UPDATE ON passive_specs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Connector
CREATE TRIGGER update_connector_specs_updated_at
    BEFORE UPDATE ON connector_specs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Protection
CREATE TRIGGER update_protection_specs_updated_at
    BEFORE UPDATE ON protection_specs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
