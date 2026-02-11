-- Firmware Stack Database Schema
-- Stores RTOS, middleware, and library information

CREATE TABLE IF NOT EXISTS firmware_stacks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Stack identification
    stack_name VARCHAR(200) NOT NULL,
    stack_type VARCHAR(50) NOT NULL,  -- 'rtos', 'tcp_ip', 'usb', 'filesystem', 'crypto', 'gui', 'ble', 'library'
    version VARCHAR(50),
    
    -- Vendor/Source
    vendor VARCHAR(100),  -- 'FreeRTOS', 'Zephyr', 'ARM', 'ST', 'lwIP', etc.
    license VARCHAR(100),  -- 'MIT', 'Apache 2.0', 'GPL', 'BSD', 'Proprietary'
    
    -- Resource requirements
    flash_min_kb INTEGER,
    flash_typical_kb INTEGER,
    ram_min_kb INTEGER,
    ram_typical_kb INTEGER,
    
    -- Supported architectures
    supported_cores TEXT[],  -- ['Cortex-M0', 'Cortex-M3', 'Cortex-M4', 'Cortex-M7']
    supported_manufacturers TEXT[],  -- ['ST', 'NXP', 'TI', 'Microchip']
    
    -- Features
    features TEXT[],  -- ['preemptive', 'tickless', 'smp', 'mpu_support']
    protocols TEXT[],  -- ['IPv4', 'IPv6', 'TCP', 'UDP', 'HTTP', 'MQTT']
    
    -- Documentation
    documentation_url TEXT,
    repository_url TEXT,
    examples_url TEXT,
    
    -- Ratings
    popularity_score INTEGER,  -- 1-100
    maturity_score INTEGER,  -- 1-100 (based on age, stability)
    community_score INTEGER,  -- 1-100 (based on GitHub stars, forum activity)
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS stack_dependencies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Stack reference
    stack_id UUID REFERENCES firmware_stacks(id) ON DELETE CASCADE,
    
    -- Dependency
    depends_on_stack_id UUID REFERENCES firmware_stacks(id) ON DELETE CASCADE,
    dependency_type VARCHAR(50),  -- 'required', 'optional', 'recommended'
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS stack_mcu_compatibility (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- References
    stack_id UUID REFERENCES firmware_stacks(id) ON DELETE CASCADE,
    part_id UUID REFERENCES parts(id) ON DELETE CASCADE,
    
    -- Compatibility
    is_officially_supported BOOLEAN DEFAULT FALSE,
    is_community_tested BOOLEAN DEFAULT FALSE,
    notes TEXT,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_firmware_stacks_type ON firmware_stacks(stack_type);
CREATE INDEX IF NOT EXISTS idx_firmware_stacks_vendor ON firmware_stacks(vendor);
CREATE INDEX IF NOT EXISTS idx_stack_deps_stack ON stack_dependencies(stack_id);
CREATE INDEX IF NOT EXISTS idx_stack_compat_stack ON stack_mcu_compatibility(stack_id);
CREATE INDEX IF NOT EXISTS idx_stack_compat_part ON stack_mcu_compatibility(part_id);

-- Comments
COMMENT ON TABLE firmware_stacks IS 'RTOS, middleware, and library catalog';
COMMENT ON TABLE stack_dependencies IS 'Dependencies between firmware stacks';
COMMENT ON TABLE stack_mcu_compatibility IS 'MCU compatibility matrix for firmware stacks';
COMMENT ON COLUMN firmware_stacks.popularity_score IS 'Popularity score 1-100 based on usage';
