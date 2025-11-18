-- 创建运维故障知识库表
CREATE TABLE IF NOT EXISTS fault_cases (
    id SERIAL PRIMARY KEY,
    fault_type VARCHAR(100) NOT NULL,           -- 故障类型
    symptoms TEXT NOT NULL,                     -- 故障现象描述
    root_cause TEXT,                           -- 根本原因
    solution TEXT NOT NULL,                    -- 解决方案
    severity VARCHAR(20) DEFAULT 'medium',     -- 严重程度: low/medium/high/critical
    frequency VARCHAR(20) DEFAULT 'occasional', -- 发生频率: rare/occasional/frequent
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_fault_type ON fault_cases(fault_type);
CREATE INDEX IF NOT EXISTS idx_severity ON fault_cases(severity);