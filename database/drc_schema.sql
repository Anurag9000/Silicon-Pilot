
-- DESIGN RULE CHECK VIOLATIONS
-- Stores results of DRC runs

CREATE TABLE IF NOT EXISTS drc_violations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    design_id UUID NOT NULL, -- Reference to a user design (nullable if generic check)
    
    rule_id VARCHAR(50) NOT NULL, -- e.g. P001, C002
    rule_name VARCHAR(100) NOT NULL,
    severity VARCHAR(20) NOT NULL, -- 'error', 'warning', 'info'
    
    component_ref VARCHAR(100), -- MPN or RefDes involved
    message TEXT NOT NULL,
    recommendation TEXT,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_drc_design ON drc_violations(design_id);
CREATE INDEX IF NOT EXISTS idx_drc_severity ON drc_violations(severity);
