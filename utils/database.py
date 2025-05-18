"""
Database utilities for Alya Bot.

This module provides database connection and management functions.
"""

import os
import sqlite3
import logging
import json
import time
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path

# Setup logger
logger = logging.getLogger(__name__)

# Database path from config or default
from config.settings import CONTEXT_DB_PATH

def get_connection() -> sqlite3.Connection:
    """Get a connection to the SQLite database.
    
    Returns:
        sqlite3.Connection: Database connection object
    """
    os.makedirs(os.path.dirname(CONTEXT_DB_PATH), exist_ok=True)
    return sqlite3.connect(CONTEXT_DB_PATH)

def init_database() -> None:
    """Initialize the database with required tables and proper schema."""
    conn = get_connection()
    try:
        with conn:
            # Create contexts table with consistent INTEGER type for user_id
            conn.execute('''
            CREATE TABLE IF NOT EXISTS contexts (
                user_id INTEGER,
                chat_id INTEGER,
                context TEXT NOT NULL,
                updated_at INTEGER NOT NULL,
                PRIMARY KEY (user_id, chat_id)
            )
            ''')
            
            # Create conversation history table
            conn.execute('''
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                chat_id INTEGER,
                message_id INTEGER,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                importance REAL DEFAULT 1.0,
                token_count INTEGER DEFAULT 0,
                metadata TEXT
            )
            ''')
            
            # Create personal facts table
            conn.execute('''
            CREATE TABLE IF NOT EXISTS personal_facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                fact_key TEXT NOT NULL,
                fact_value TEXT NOT NULL,
                confidence REAL,
                source TEXT,
                created_at INTEGER NOT NULL,
                expires_at INTEGER NOT NULL,
                UNIQUE(user_id, fact_key)
            )
            ''')
            
            # Add indexes for better performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_history_user_chat ON history(user_id, chat_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_contexts_updated ON contexts(updated_at)")
            
            logger.info("Database initialized with proper schema")
    except sqlite3.Error as e:
        logger.error(f"Database initialization error: {e}")
    finally:
        conn.close()

def reset_database() -> bool:
    """Reset the database by dropping and recreating all tables.
    
    Returns:
        bool: True if reset was successful, False otherwise
    """
    try:
        # Create backup first
        if os.path.exists(CONTEXT_DB_PATH):
            backup_path = f"{CONTEXT_DB_PATH}.backup.{int(time.time())}"
            try:
                if os.path.exists(backup_path):
                    os.remove(backup_path)
                os.rename(CONTEXT_DB_PATH, backup_path)
                logger.info(f"Database backed up to {backup_path}")
            except OSError as e:
                logger.error(f"Failed to create database backup: {e}")
                # Continue with reset even if backup fails
        
        # Reinitialize the database
        init_database()
        logger.info("Database reset successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to reset database: {e}")
        return False

def execute_query(query: str, params: Tuple = (), fetch_all: bool = False) -> Any:
    """Execute an SQL query with error handling.
    
    Args:
        query: SQL query to execute
        params: Query parameters
        fetch_all: Whether to fetch all results
        
    Returns:
        Query results or None if error occurred
    """
    conn = None
    try:
        conn = get_connection()
        with conn:
            cursor = conn.execute(query, params)
            if fetch_all:
                return cursor.fetchall()
            return cursor.fetchone()
    except sqlite3.Error as e:
        logger.error(f"SQL error executing {query}: {e}")
        return None
    finally:
        if conn:
            conn.close()
