-- Pin Mux Database Schema
-- Stores MCU pin functions and alternate function mappings

CREATE TABLE IF NOT EXISTS mcu_pin_functions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- MCU reference
    part_id UUID REFERENCES parts(id) ON DELETE CASCADE,
    
    -- Pin identification
    pin_number INTEGER NOT NULL,
    pin_name VARCHAR(50) NOT NULL,  -- e.g., "PA0", "PB12", "PC13"
    
    -- Alternate functions (AF0-AF15 for STM32)
    af0_function VARCHAR(100),  -- Default function
    af1_function VARCHAR(100),
    af2_function VARCHAR(100),
    af3_function VARCHAR(100),
    af4_function VARCHAR(100),
    af5_function VARCHAR(100),
    af6_function VARCHAR(100),
    af7_function VARCHAR(100),
    af8_function VARCHAR(100),
    af9_function VARCHAR(100),
    af10_function VARCHAR(100),
    af11_function VARCHAR(100),
    af12_function VARCHAR(100),
    af13_function VARCHAR(100),
    af14_function VARCHAR(100),
    af15_function VARCHAR(100),
    
    -- Electrical characteristics
    max_current_ma INTEGER,
    voltage_tolerance VARCHAR(50),  -- e.g., "5V tolerant", "3.3V only"
    
    -- Special features
    is_power_pin BOOLEAN DEFAULT FALSE,
    is_boot_pin BOOLEAN DEFAULT FALSE,
    has_adc BOOLEAN DEFAULT FALSE,
    has_dac BOOLEAN DEFAULT FALSE,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pin_mux_constraints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- MCU reference
    part_id UUID REFERENCES parts(id) ON DELETE CASCADE,
    
    -- Constraint type
    constraint_type VARCHAR(50) NOT NULL,  -- 'exclusive', 'required_pair', 'voltage_level'
    
    -- Affected pins (JSON array of pin names)
    pin_names TEXT[] NOT NULL,
    
    -- Constraint description
    description TEXT,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_pin_functions_part ON mcu_pin_functions(part_id);
CREATE INDEX IF NOT EXISTS idx_pin_functions_name ON mcu_pin_functions(pin_name);
CREATE INDEX IF NOT EXISTS idx_pin_constraints_part ON pin_mux_constraints(part_id);

-- Comments
COMMENT ON TABLE mcu_pin_functions IS 'MCU pin alternate function mappings';
COMMENT ON TABLE pin_mux_constraints IS 'Pin muxing constraints (exclusive groups, required pairs, etc.)';
COMMENT ON COLUMN mcu_pin_functions.af0_function IS 'Default function (usually GPIO)';
COMMENT ON COLUMN pin_mux_constraints.constraint_type IS 'Type: exclusive, required_pair, voltage_level, etc.';
