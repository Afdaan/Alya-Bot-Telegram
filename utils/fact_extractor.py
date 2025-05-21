"""
Fact Extraction Utilities for Alya Bot.

This module provides functionality to extract, store, and retrieve facts
about users from conversations for better context awareness.
"""

import re
import logging
import time
from typing import Dict, Any, List, Optional, Tuple, Set
import sqlite3

# Fix incorrect import path
from database.database import get_connection
from transformers import pipeline

logger = logging.getLogger(__name__)

class FactExtractor:
    """
    Extract and manage facts about users from conversation data.
    
    This class processes messages to identify key facts about users
    and stores them for context-aware conversations.
    """
    
    def __init__(self):
        """Initialize fact extractor dengan NER pipeline."""
        self.ner_pipeline = pipeline("ner", model="cahya/bert-base-indonesian-NER", aggregation_strategy="simple")

    def extract_facts_from_text(self, text: str) -> Dict[str, str]:
        """Extract facts menggunakan NER model."""
        entities = self.ner_pipeline(text)
        facts = {}
        for entity in entities:
            if entity["entity_group"] in ["PER", "LOC", "ORG"]:
                facts[entity["entity_group"].lower()] = entity["word"]
        return facts
    
    def _validate_fact(self, fact_type: str, value: str) -> bool:
        """
        Validate extracted fact for quality and relevance.
        
        Args:
            fact_type: Type of fact
            value: Extracted fact value
            
        Returns:
            True if fact is valid, False otherwise
        """
        # Discard very short values or likely irrelevant content
        if not value or len(value) < 2:
            return False
            
        if fact_type == 'name':
            # Discard very long names or likely non-name content
            if len(value.split()) > 5 or len(value) > 40:
                return False
                
            # Discard names that are just pronouns or common words
            if value.lower() in self.common_words:
                return False
                
        elif fact_type == 'age':
            # Validate age is a reasonable number
            try:
                age = int(value)
                if age < 5 or age > 120:
                    return False
            except ValueError:
                return False
                
        elif fact_type == 'location':
            # Discard very short or generic location names
            if value.lower() in self.common_words:
                return False
                
        return True
    
    def store_facts(self, user_id: int, facts: Dict[str, Any], confidence: float = 0.8, ttl_days: int = 365) -> bool:
        """
        Store extracted facts in persistent storage.
        
        Args:
            user_id: User ID
            facts: Dictionary of facts to store
            confidence: Confidence score for the facts (0.0-1.0)
            ttl_days: Time-to-live in days
            
        Returns:
            True if successfully stored, False otherwise
        """
        if not facts:
            return False
            
        try:
            # Calculate expiration timestamp
            expires_at = int(time.time()) + (ttl_days * 86400)
            
            # Get database connection from database utility
            conn = get_connection()
            cursor = conn.cursor()
            
            stored_count = 0
            
            # Begin transaction
            conn.execute("BEGIN TRANSACTION")
            
            try:
                # Store each fact
                for fact_key, fact_value in facts.items():
                    cursor.execute(
                        """INSERT OR REPLACE INTO personal_facts 
                           (user_id, fact_key, fact_value, confidence, source, created_at, expires_at) 
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (
                            user_id, 
                            fact_key, 
                            fact_value,
                            confidence, 
                            "conversation", 
                            int(time.time()),
                            expires_at
                        )
                    )
                    stored_count += 1
                
                # Commit transaction
                conn.commit()
            except sqlite3.Error as e:
                logger.error(f"Database error in transaction: {e}")
                conn.rollback()
                return False
            finally:
                conn.close()
            
            logger.debug(f"Stored {stored_count} facts for user {user_id}")
            return stored_count > 0
            
        except sqlite3.Error as e:
            logger.error(f"Database error storing facts: {e}")
            return False
        except Exception as e:
            logger.error(f"Error storing user facts: {e}")
            return False
    
    def get_user_facts(self, user_id: int, fact_types: Optional[List[str]] = None) -> Dict[str, str]:
        """
        Get stored facts about a user.
        
        Args:
            user_id: User ID
            fact_types: Optional list of specific fact types to retrieve
            
        Returns:
            Dictionary of facts
        """
        try:
            # Get database connection
            conn = get_connection()
            cursor = conn.cursor()
            
            current_time = int(time.time())
            
            # Build query based on inputs
            if fact_types:
                placeholders = ','.join(['?' for _ in fact_types])
                query = f"""SELECT fact_key, fact_value 
                            FROM personal_facts 
                            WHERE user_id = ? 
                            AND fact_key IN ({placeholders})
                            AND expires_at > ?
                            ORDER BY confidence DESC, created_at DESC"""
                params = [user_id] + fact_types + [current_time]
            else:
                query = """SELECT fact_key, fact_value 
                           FROM personal_facts 
                           WHERE user_id = ?
                           AND expires_at > ?
                           ORDER BY confidence DESC, created_at DESC"""
                params = (user_id, current_time)
            
            # Execute query
            cursor.execute(query, params)
            facts = {}
            
            # Process results (take highest confidence entry for each fact type)
            seen_facts = set()
            for row in cursor.fetchall():
                fact_key, fact_value = row
                if fact_key not in seen_facts:
                    facts[fact_key] = fact_value
                    seen_facts.add(fact_key)
            
            conn.close()
            return facts
            
        except sqlite3.Error as e:
            logger.error(f"Database error getting facts: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error getting user facts: {e}")
            return {}
    
    def merge_facts(self, user_id: int, new_facts: Dict[str, str], overwrite: bool = False) -> bool:
        """
        Merge new facts with existing facts for a user.
        
        Args:
            user_id: User ID
            new_facts: New facts to merge
            overwrite: Whether to overwrite existing facts
            
        Returns:
            True if successfully merged, False otherwise
        """
        if not new_facts:
            return False
            
        try:
            # Get existing facts
            existing_facts = self.get_user_facts(user_id)
            
            # Merge facts - either overwrite all or only add missing
            merged_facts = {}
            merged_facts.update(existing_facts)
            
            if overwrite:
                # Overwrite existing facts with new ones
                merged_facts.update(new_facts)
            else:
                # Only add facts that don't exist yet
                for key, value in new_facts.items():
                    if key not in existing_facts:
                        merged_facts[key] = value
            
            # Store merged facts if different from existing
            if merged_facts != existing_facts:
                # Only store facts that changed
                changed_facts = {k: v for k, v in merged_facts.items() 
                               if k not in existing_facts or existing_facts[k] != v}
                return self.store_facts(user_id, changed_facts)
                
            return True
            
        except Exception as e:
            logger.error(f"Error merging facts: {e}")
            return False

# Create singleton instance
fact_extractor = FactExtractor()

def extract_facts(text: str) -> Dict[str, str]:
    """
    Extract facts from text (convenience function).
    
    Args:
        text: Text to extract facts from
        
    Returns:
        Dictionary of extracted facts
    """
    return fact_extractor.extract_facts_from_text(text)
