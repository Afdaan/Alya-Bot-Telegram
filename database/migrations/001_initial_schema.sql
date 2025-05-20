-- Initial Schema Migration for Alya Bot Database
-- Version: 1.0.0
-- Created: 2024

-- Context table for general context storage
CREATE TABLE IF NOT EXISTS contexts (
    user_id INTEGER,
    chat_id INTEGER,
    context TEXT,
    updated_at INTEGER,
    PRIMARY KEY (user_id, chat_id)
);

-- History table for message history
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    chat_id INTEGER,
    message_id INTEGER,
    role TEXT,  -- 'user' or 'assistant'
    content TEXT,
    timestamp INTEGER,
    importance REAL DEFAULT 1.0,
    token_count INTEGER DEFAULT 0,
    metadata TEXT  -- JSON string for additional data
);

-- Create index on history table for faster retrieval
CREATE INDEX IF NOT EXISTS idx_history_user_chat_time 
ON history(user_id, chat_id, timestamp);

-- Personal facts table
CREATE TABLE IF NOT EXISTS personal_facts (
    user_id INTEGER,
    fact_key TEXT,
    fact_value TEXT,
    confidence REAL DEFAULT 1.0,
    source TEXT,
    created_at INTEGER,
    expires_at INTEGER,
    PRIMARY KEY (user_id, fact_key)
);

-- User memory table for topic tracking and summary
CREATE TABLE IF NOT EXISTS user_memory (
    user_id INTEGER PRIMARY KEY,
    nickname TEXT,
    topics TEXT,  -- Comma-separated topics
    summary TEXT,
    last_updated INTEGER
);
