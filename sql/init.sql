-- GoTimeCloud WhatsApp Bot - Database Schema

CREATE TABLE IF NOT EXISTS routes (
    id SERIAL PRIMARY KEY,
    phone VARCHAR(20) NOT NULL UNIQUE,
    company_name VARCHAR(200) DEFAULT '',
    gtc_url VARCHAR(500) NOT NULL,
    company VARCHAR(100) NOT NULL,
    username VARCHAR(200) NOT NULL,
    password VARCHAR(200) NOT NULL,
    gtc_utc INTEGER DEFAULT 2,
    language VARCHAR(5) DEFAULT 'es',
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    route_id INTEGER REFERENCES routes(id) ON DELETE SET NULL,
    phone VARCHAR(20) NOT NULL,
    direction VARCHAR(10) NOT NULL,  -- 'inbound' or 'outbound'
    message TEXT,
    intent VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_routes_phone ON routes(phone);
CREATE INDEX IF NOT EXISTS idx_conversations_phone ON conversations(phone, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversations_created ON conversations(created_at DESC);
