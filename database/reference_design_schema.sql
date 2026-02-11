-- Reference Design Library Schema
-- Stores reference designs from ST, TI, NXP, and community sources

CREATE TABLE IF NOT EXISTS reference_designs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Design identification
    design_name VARCHAR(200) NOT NULL,
    design_id VARCHAR(100),  -- e.g., "STEVAL-ISA207V1", "TIDA-01234"
    manufacturer VARCHAR(100) NOT NULL,  -- ST, TI, NXP, Community
    
    -- Design description
    description TEXT,
    application_area VARCHAR(100),  -- e.g., "Motor Control", "IoT Gateway", "Power Management"
    
    -- Documentation
    schematic_url TEXT,
    bom_url TEXT,
    gerber_url TEXT,
    firmware_url TEXT,
    documentation_url TEXT,
    
    -- Specifications
    input_voltage_v DECIMAL(10, 2),
    output_power_w DECIMAL(10, 2),
    efficiency_percent INTEGER,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS reference_design_parts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- References
    design_id UUID REFERENCES reference_designs(id) ON DELETE CASCADE,
    part_id UUID REFERENCES parts(id) ON DELETE CASCADE,
    
    -- Part details in design
    reference_designator VARCHAR(50),  -- e.g., "U1", "C5", "R12"
    quantity INTEGER DEFAULT 1,
    is_critical BOOLEAN DEFAULT FALSE,  -- Critical to design function
    notes TEXT,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_ref_designs_manufacturer ON reference_designs(manufacturer);
CREATE INDEX IF NOT EXISTS idx_ref_designs_application ON reference_designs(application_area);
CREATE INDEX IF NOT EXISTS idx_ref_design_parts_design ON reference_design_parts(design_id);
CREATE INDEX IF NOT EXISTS idx_ref_design_parts_part ON reference_design_parts(part_id);

-- Comments
COMMENT ON TABLE reference_designs IS 'Reference hardware designs from manufacturers and community';
COMMENT ON TABLE reference_design_parts IS 'Bill of materials for reference designs';
COMMENT ON COLUMN reference_design_parts.is_critical IS 'Whether part is critical to design function (vs optional)';
