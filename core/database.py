"""
Database manager for Alya Bot with SQLite integration for memory and RAG.
"""
import os
import sqlite3
import logging
import json
import time
import hashlib
from typing import Dict, List, Optional, Tuple, Any, Union
from pathlib import Path

from config.settings import (
    SQLITE_DB_PATH, 
    MEMORY_EXPIRY_DAYS,
    RELATIONSHIP_THRESHOLDS,
    RELATIONSHIP_LEVELS,
    AFFECTION_POINTS,
    RELATIONSHIP_ROLE_NAMES
)

logger = logging.getLogger(__name__)

def get_role_by_relationship_level(relationship_level: int, is_admin: bool = False) -> str:
    """Return role name based on relationship level and admin status.

    Args:
        relationship_level: Relationship level (0-4)
        is_admin: Whether the user is admin

    Returns:
        Role name as string
    """
    if is_admin:
        return "Master-sama"
    return RELATIONSHIP_ROLE_NAMES.get(relationship_level, "Alyanation")

class DatabaseManager:
    """SQLite database manager for conversation history and RAG functionality."""

    def __init__(self, db_path: str = SQLITE_DB_PATH) -> None:
        """Initialize the database manager.
        
        Args:
            db_path: Path to the SQLite database file
        """
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self.recent_message_hashes = {}  # Cache for recent message hashes
        self._initialize_db()
        
    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection.
        
        Returns:
            SQLite connection object
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
        
    def _initialize_db(self) -> None:
        """Initialize database tables with the correct schema."""
        conn = self._get_connection()
        try:
            # Create users table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    language TEXT DEFAULT 'id',
                    persona TEXT DEFAULT 'waifu',
                    relationship_level INTEGER DEFAULT 0,
                    interaction_count INTEGER DEFAULT 0,
                    affection_points INTEGER DEFAULT 0,
                    created_at INTEGER,
                    last_interaction INTEGER,
                    is_admin INTEGER DEFAULT 0
                )
            ''')
            
            # Create conversations table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    role TEXT,
                    content TEXT,
                    message TEXT,
                    message_metadata TEXT DEFAULT '{}',
                    is_user BOOLEAN DEFAULT 0,
                    timestamp INTEGER,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')
            
            # Create embeddings table for RAG
            conn.execute('''
                CREATE TABLE IF NOT EXISTS embeddings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    text TEXT,
                    embedding TEXT,
                    metadata TEXT,
                    timestamp INTEGER,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')
            
            # Create user stats table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS user_stats (
                    user_id INTEGER PRIMARY KEY,
                    total_messages INTEGER DEFAULT 0,
                    command_uses INTEGER DEFAULT 0,
                    positive_interactions INTEGER DEFAULT 0,
                    negative_interactions INTEGER DEFAULT 0,
                    last_mood TEXT DEFAULT 'neutral',
                    role TEXT DEFAULT 'Alyanation',
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')
            
            # Create indexes for faster queries
            conn.execute('CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_embeddings_user_id ON embeddings(user_id)')
            
            # Add message_hash column for deduplication
            self._add_column_if_not_exists(conn, "conversations", "message_hash", "TEXT")
            
            try:
                conn.execute('CREATE INDEX IF NOT EXISTS idx_conversations_message_hash ON conversations(message_hash)')
            except sqlite3.OperationalError:
                logger.warning("Could not create index for message_hash - column might not exist yet")
            
            conn.commit()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
        finally:
            conn.close()
    
    def _add_column_if_not_exists(self, conn: sqlite3.Connection, table: str, column: str, type_def: str) -> bool:
        """Add a column to a table if it doesn't exist.
        
        Args:
            conn: The database connection
            table: Table name
            column: Column to add
            type_def: Column type definition
            
        Returns:
            True if column was added or already exists, False if error
        """
        try:
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [info[1] for info in cursor.fetchall()]
            
            if column not in columns:
                logger.info(f"Adding missing column '{column}' to table '{table}'")
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {type_def}")
                conn.commit()
                logger.info(f"Successfully added column '{column}' to '{table}'")
            
            return True
        except Exception as e:
            logger.error(f"Error adding column {column} to {table}: {e}")
            return False
            
    def _ensure_table_columns(self, conn: sqlite3.Connection) -> None:
        """Ensure all tables have the expected columns."""
        try:
            expected_columns = {
                'conversations': {
                    'message_hash': 'TEXT'
                },
                'user_stats': {
                    'role': "TEXT DEFAULT 'Alyanation'"
                }
            }

            for table_name, columns in expected_columns.items():
                cursor = conn.cursor()
                cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
                if not cursor.fetchone():
                    continue

                cursor.execute(f"PRAGMA table_info({table_name})")
                existing_columns = {column[1] for column in cursor.fetchall()}

                for column_name, column_def in columns.items():
                    if column_name not in existing_columns:
                        logger.info(f"Adding missing column {column_name} to {table_name}")
                        try:
                            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}")
                            conn.commit()
                        except Exception as e:
                            logger.error(f"Error adding column {column_name} to {table_name}: {e}")

            logger.info("Column verification completed")
        except Exception as e:
            logger.error(f"Error ensuring table columns: {e}")
            conn.rollback()

    def get_or_create_user(self, user_id: int, username: str = "", first_name: str = "", 
                           last_name: str = "", is_admin: bool = False) -> Dict[str, Any]:
        """Get or create a user record.
        
        Args:
            user_id: Telegram user ID
            username: Telegram username
            first_name: User's first name
            last_name: User's last name
            is_admin: Whether the user is an admin
            
        Returns:
            User record as dictionary
        """
        conn = self._get_connection()
        try:
            user = conn.execute(
                'SELECT * FROM users WHERE user_id = ?', 
                (user_id,)
            ).fetchone()
            
            current_time = int(time.time())
            
            if not user:
                # Create new user
                conn.execute(
                    '''INSERT INTO users 
                       (user_id, username, first_name, last_name, created_at, last_interaction, is_admin)
                       VALUES (?, ?, ?, ?, ?, ?, ?)''',
                    (user_id, username, first_name, last_name, current_time, current_time, 1 if is_admin else 0)
                )
                
                conn.execute(
                    'INSERT INTO user_stats (user_id) VALUES (?)',
                    (user_id,)
                )
                
                conn.commit()
                
                user = conn.execute(
                    'SELECT * FROM users WHERE user_id = ?', 
                    (user_id,)
                ).fetchone()
            else:
                # Update existing user
                conn.execute(
                    '''UPDATE users SET 
                       username = ?, 
                       first_name = ?, 
                       last_name = ?, 
                       last_interaction = ?,
                       is_admin = ?
                       WHERE user_id = ?''',
                    (username, first_name, last_name, current_time, 1 if is_admin else user['is_admin'], user_id)
                )
                conn.commit()
            
            return dict(user)
        except Exception as e:
            logger.error(f"Error getting/creating user: {e}")
            return {}
        finally:
            conn.close()
    
    def save_message(self, user_id: int, role: str, content: str) -> bool:
        """Save a message to the conversation history and update stats/relationship."""
        conn = self._get_connection()
        try:
            timestamp = int(time.time())
            is_user = 1 if role == "user" else 0
            
            # Deduplication
            message = {
                'user_id': user_id,
                'content': content,
                'role': role
            }
            
            message_hash = self._calculate_message_hash(message)
            has_message_hash = self._check_column_exists(conn, "conversations", "message_hash")
            
            # Check duplicates in memory cache
            if user_id in self.recent_message_hashes and message_hash in self.recent_message_hashes[user_id]:
                logger.warning(f"Skipping duplicate message for user {user_id} (memory cache hit)")
                return False
                
            # Check duplicates in database
            if has_message_hash and self._check_db_for_duplicate(conn, user_id, message_hash):
                logger.warning(f"Skipping duplicate message for user {user_id} (database hit)")
                return False
                
            # Update recent message cache
            if user_id not in self.recent_message_hashes:
                self.recent_message_hashes[user_id] = set()
                
            self.recent_message_hashes[user_id].add(message_hash)
            if len(self.recent_message_hashes[user_id]) > 100:
                self.recent_message_hashes[user_id].pop()
                
            # Insert message with dynamic column handling
            if has_message_hash:
                conn.execute(
                    '''INSERT INTO conversations 
                       (user_id, role, content, message, message_metadata, is_user, timestamp, message_hash)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                    (user_id, role, content, content, '{}', is_user, timestamp, message_hash)
                )
            else:
                conn.execute(
                    '''INSERT INTO conversations 
                       (user_id, role, content, message, message_metadata, is_user, timestamp)
                       VALUES (?, ?, ?, ?, ?, ?, ?)''',
                    (user_id, role, content, content, '{}', is_user, timestamp)
                )
            
            # Update stats for user messages
            if role == 'user':
                conn.execute(
                    'UPDATE user_stats SET total_messages = total_messages + 1 WHERE user_id = ?',
                    (user_id,)
                )
                conn.execute(
                    'UPDATE users SET interaction_count = interaction_count + 1 WHERE user_id = ?',
                    (user_id,)
                )
                self._process_relationship_update(conn, user_id)
            
            conn.commit()
            
            # Store significant messages for RAG
            if len(content) > 20:
                self.save_for_rag(user_id, content, {"role": role, "timestamp": timestamp})
                
            return True
        except Exception as e:
            logger.error(f"Error saving message: {e}")
            return False
        finally:
            conn.close()
    
    def _process_relationship_update(self, conn: sqlite3.Connection, user_id: int) -> None:
        """Process potential relationship level update."""
        try:
            user_info = conn.execute(
                '''SELECT relationship_level, interaction_count, affection_points, is_admin
                   FROM users WHERE user_id = ?''',
                (user_id,)
            ).fetchone()

            if not user_info:
                return

            relationship_level = user_info['relationship_level']
            interaction_count = user_info['interaction_count']
            is_admin = bool(user_info['is_admin'])

            new_level = relationship_level
            interaction_thresholds = RELATIONSHIP_THRESHOLDS["interaction_count"]

            # Check if user meets threshold for next level
            for level, threshold in sorted(interaction_thresholds.items()):
                if interaction_count >= threshold and relationship_level < level:
                    new_level = level

            # Apply level update if needed
            if new_level > relationship_level:
                conn.execute(
                    'UPDATE users SET relationship_level = ? WHERE user_id = ?',
                    (new_level, user_id)
                )
                new_role = get_role_by_relationship_level(new_level, is_admin)
                conn.execute(
                    'UPDATE user_stats SET role = ? WHERE user_id = ?',
                    (new_role, user_id)
                )
                logger.info(f"User {user_id} relationship progressed to level {new_level} and role '{new_role}'")
        except Exception as e:
            logger.error(f"Error processing relationship update: {e}")

    def update_affection(self, user_id: int, points: int) -> bool:
        """Update user's affection points."""
        conn = self._get_connection()
        try:
            conn.execute(
                'UPDATE users SET affection_points = affection_points + ? WHERE user_id = ?',
                (points, user_id)
            )
            
            # Track interaction type
            if points > 0:
                conn.execute(
                    'UPDATE user_stats SET positive_interactions = positive_interactions + 1 WHERE user_id = ?',
                    (user_id,)
                )
            elif points < 0:
                conn.execute(
                    'UPDATE user_stats SET negative_interactions = negative_interactions + 1 WHERE user_id = ?',
                    (user_id,)
                )
                
            conn.commit()
            self._check_affection_level_change(user_id)
            return True
        except Exception as e:
            logger.error(f"Error updating affection: {e}")
            return False
        finally:
            conn.close()
    
    def _check_affection_level_change(self, user_id: int) -> None:
        """Check if affection points warrant relationship level change."""
        conn = self._get_connection()
        try:
            user_info = conn.execute(
                'SELECT relationship_level, affection_points, is_admin FROM users WHERE user_id = ?',
                (user_id,)
            ).fetchone()

            if not user_info:
                return

            level = user_info['relationship_level']
            points = user_info['affection_points']
            is_admin = bool(user_info['is_admin'])
            affection_thresholds = RELATIONSHIP_THRESHOLDS["affection_points"]

            # Check for level up
            new_level = level
            for next_level, threshold in sorted(affection_thresholds.items()):
                if points >= threshold and level < next_level:
                    new_level = next_level

            # Check for level down (negative affection)
            if points < -100 and level > 0:
                new_level = max(0, level - 1)

            # Apply level change if needed
            if new_level != level:
                conn.execute(
                    'UPDATE users SET relationship_level = ? WHERE user_id = ?',
                    (new_level, user_id)
                )
                new_role = get_role_by_relationship_level(new_level, is_admin)
                conn.execute(
                    'UPDATE user_stats SET role = ? WHERE user_id = ?',
                    (new_role, user_id)
                )
                conn.commit()
                logger.info(f"User {user_id} relationship changed to level {new_level} and role '{new_role}' due to affection")
        except Exception as e:
            logger.error(f"Error checking affection level change: {e}")
        finally:
            conn.close()

    def get_user_relationship_info(self, user_id: int) -> Dict[str, Any]:
        """Get relationship info for user."""
        conn = self._get_connection()
        try:
            user = conn.execute(
                '''SELECT user_id, first_name, relationship_level, 
                          interaction_count, affection_points, is_admin
                   FROM users WHERE user_id = ?''',
                (user_id,)
            ).fetchone()
            
            stats = conn.execute(
                '''SELECT total_messages, command_uses, 
                          positive_interactions, negative_interactions, role
                   FROM user_stats WHERE user_id = ?''',
                (user_id,)
            ).fetchone()
            
            if not user or not stats:
                return {}
                
            # Calculate relationship data
            level_number = user['relationship_level']
            level_name = RELATIONSHIP_LEVELS.get(level_number, "Unknown")
            interaction_thresholds = RELATIONSHIP_THRESHOLDS["interaction_count"]
            affection_thresholds = RELATIONSHIP_THRESHOLDS["affection_points"]
            
            # Find next level thresholds
            next_interaction_threshold = float('inf')
            next_affection_threshold = float('inf')
            
            for next_level, threshold in sorted(interaction_thresholds.items()):
                if level_number < next_level:
                    next_interaction_threshold = threshold
                    break
                    
            for next_level, threshold in sorted(affection_thresholds.items()):
                if level_number < next_level:
                    next_affection_threshold = threshold
                    break
            
            # Format data with all fields
            relationship_info = {
                "user_id": user['user_id'],
                "name": user['first_name'],
                "is_admin": bool(user['is_admin']),
                "relationship": {
                    "level": level_number,
                    "name": level_name,
                    "interactions": user['interaction_count'],
                    "next_level_at": next_interaction_threshold,
                    "progress_percent": min(100, (user['interaction_count'] / next_interaction_threshold) * 100) if next_interaction_threshold < float('inf') else 100
                },
                "affection": {
                    "points": user['affection_points'],
                    "next_level_at": next_affection_threshold,
                    "progress_percent": min(100, (user['affection_points'] / next_affection_threshold) * 100) if user['affection_points'] > 0 and next_affection_threshold < float('inf') else 0
                },
                "stats": {
                    "total_messages": stats['total_messages'] or 0,  
                    "command_uses": stats['command_uses'] or 0,
                    "positive_interactions": stats['positive_interactions'] or 0,
                    "negative_interactions": stats['negative_interactions'] or 0,
                    "role": stats['role'] if 'role' in stats.keys() else "user"
                }
            }
            
            return relationship_info
            
        except Exception as e:
            logger.error(f"Error getting relationship info: {e}")
            return {}
        finally:
            conn.close()
    
    def get_conversation_history(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent conversation history for a user."""
        conn = self._get_connection()
        try:
            rows = conn.execute(
                '''SELECT role, content FROM conversations 
                   WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?''',
                (user_id, limit)
            ).fetchall()
            
            # Return in chronological order (oldest first)
            history = [dict(row) for row in rows]
            history.reverse()
            
            return history
        except Exception as e:
            logger.error(f"Error retrieving conversation history: {e}")
            return []
        finally:
            conn.close()
    
    def reset_conversation(self, user_id: int) -> bool:
        """Reset a user's conversation history."""
        conn = self._get_connection()
        try:
            conn.execute('DELETE FROM conversations WHERE user_id = ?', (user_id,))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error resetting conversation: {e}")
            return False
        finally:
            conn.close()
    
    def apply_sliding_window(self, user_id: int, keep_recent: int) -> bool:
        """Keep only the most recent messages and delete older ones."""
        conn = self._get_connection()
        try:
            # Get timestamp of the oldest message to keep
            oldest_to_keep = conn.execute(
                '''SELECT timestamp FROM conversations
                   WHERE user_id = ?
                   ORDER BY timestamp DESC
                   LIMIT 1 OFFSET ?''',
                (user_id, keep_recent - 1)
            ).fetchone()
            
            if oldest_to_keep:
                conn.execute(
                    'DELETE FROM conversations WHERE user_id = ? AND timestamp < ?',
                    (user_id, oldest_to_keep['timestamp'])
                )
                conn.commit()
                logger.info(f"Applied sliding window for user {user_id}, keeping {keep_recent} recent messages")
                return True
            else:
                logger.debug(f"Not enough messages to apply sliding window for user {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error applying sliding window: {e}")
            return False
        finally:
            conn.close()
    
    def save_for_rag(self, user_id: int, text: str, metadata: Dict[str, Any]) -> bool:
        """Save text for RAG processing."""
        conn = self._get_connection()
        try:
            conn.execute(
                '''INSERT INTO embeddings 
                   (user_id, text, embedding, metadata, timestamp)
                   VALUES (?, ?, ?, ?, ?)''',
                (
                    user_id, 
                    text, 
                    "[]",  # Placeholder for embeddings
                    json.dumps(metadata), 
                    int(time.time())
                )
            )
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error saving RAG data: {e}")
            return False
        finally:
            conn.close()
    
    def get_rag_texts(self, user_id: int) -> List[Dict[str, Any]]:
        """Get stored texts for RAG processing."""
        conn = self._get_connection()
        try:
            cutoff_time = int(time.time()) - (MEMORY_EXPIRY_DAYS * 24 * 60 * 60)
            
            rows = conn.execute(
                '''SELECT text, metadata FROM embeddings
                   WHERE user_id = ? AND timestamp > ?
                   ORDER BY timestamp DESC''',
                (user_id, cutoff_time)
            ).fetchall()
            
            results = []
            for row in rows:
                item = {
                    "text": row["text"],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else {}
                }
                results.append(item)
                
            return results
        except Exception as e:
            logger.error(f"Error retrieving RAG texts: {e}")
            return []
        finally:
            conn.close()
    
    def update_last_mood(self, user_id: int, mood: str) -> bool:
        """Update the last detected mood for a user."""
        conn = self._get_connection()
        try:
            conn.execute(
                'UPDATE user_stats SET last_mood = ? WHERE user_id = ?',
                (mood, user_id)
            )
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating user mood: {e}")
            return False
        finally:
            conn.close()
    
    def track_command_use(self, user_id: int) -> None:
        """Track command usage for stats."""
        conn = self._get_connection()
        try:
            conn.execute(
                'UPDATE user_stats SET command_uses = command_uses + 1 WHERE user_id = ?',
                (user_id,)
            )
            conn.commit()
        except Exception as e:
            logger.error(f"Error tracking command use: {e}")
        finally:
            conn.close()
    
    def cleanup_old_data(self) -> None:
        """Clean up old conversations and embeddings."""
        conn = self._get_connection()
        try:
            cutoff_time = int(time.time()) - (MEMORY_EXPIRY_DAYS * 24 * 60 * 60)
            
            deleted_convos = conn.execute(
                'DELETE FROM conversations WHERE timestamp < ?',
                (cutoff_time,)
            ).rowcount
            
            deleted_embeds = conn.execute(
                'DELETE FROM embeddings WHERE timestamp < ?',
                (cutoff_time,)
            ).rowcount
            
            conn.commit()
            logger.info(f"Cleaned up {deleted_convos} old conversations and {deleted_embeds} embeddings older than {MEMORY_EXPIRY_DAYS} days")
        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")
        finally:
            conn.close()
            
    def is_admin(self, user_id: int) -> bool:
        """Check if a user is an admin."""
        conn = self._get_connection()
        try:
            result = conn.execute(
                'SELECT is_admin FROM users WHERE user_id = ?',
                (user_id,)
            ).fetchone()
            
            return bool(result and result['is_admin'])
        except Exception as e:
            logger.error(f"Error checking admin status: {e}")
            return False
        finally:
            conn.close()
    
    def _calculate_message_hash(self, message: Dict[str, Any]) -> str:
        """Calculate a hash for the message to prevent duplicates."""
        user_id = message.get('user_id', 0)
        content = message.get('content', '')
        role = message.get('role', 1)
        
        hash_input = f"{user_id}:{content}:{role}"
        return hashlib.md5(hash_input.encode()).hexdigest()
    
    def _is_duplicate_message(self, message_hash: str, user_id: int) -> bool:
        """Check if a message with this hash was recently added."""
        # Check memory cache first
        user_hashes = self.recent_message_hashes.get(user_id, set())
        if message_hash in user_hashes:
            return True
            
        # Check database for recent duplicates
        conn = None
        try:
            conn = self._get_connection()
            
            if self._check_column_exists(conn, "conversations", "message_hash"):
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id FROM conversations 
                    WHERE user_id = ? AND message_hash = ? 
                    AND timestamp >= ?
                ''', (user_id, message_hash, int(time.time()) - 10))
                
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Error checking for duplicates in DB: {e}")
        finally:
            if conn:
                conn.close()
                
        return False
    
    def _check_column_exists(self, conn: sqlite3.Connection, table: str, column: str) -> bool:
        """Check if a column exists in a table."""
        try:
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [info[1] for info in cursor.fetchall()]
            return column in columns
        except Exception as e:
            logger.error(f"Error checking if column exists: {e}")
            return False
            
    def _check_db_for_duplicate(self, conn: sqlite3.Connection, user_id: int, message_hash: str) -> bool:
        """Check database for duplicate message."""
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id FROM conversations 
                WHERE user_id = ? AND message_hash = ? 
                AND timestamp >= ?
            ''', (user_id, message_hash, int(time.time()) - 10))
            
            return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Error checking for duplicates: {e}")
            return False