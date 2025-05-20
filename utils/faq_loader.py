"""
FAQ and Knowledge Base Loader for Alya Bot.

This module provides functionality to load and retrieve FAQ and knowledge base
information to enhance Alya's responses with pre-defined answers to common questions.
"""

import os
import yaml
import json
import logging
import time
import re
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

# Base paths
BASE_DIR = Path(__file__).parent.parent
FAQ_PATH = BASE_DIR / "data" / "faq.yaml"
KNOWLEDGE_PATH = BASE_DIR / "data" / "knowledge"

class KnowledgeBase:
    """Knowledge base manager for Alya."""
    
    def __init__(self):
        """Initialize the knowledge base."""
        self.faq_data = {}
        self.kb_data = {}
        self.last_loaded = 0
        self.cache_expiry = 300  # Cache for 5 minutes
        self.load_faq()
    
    def load_faq(self, force_reload: bool = False) -> bool:
        """
        Load FAQ data from YAML file.
        
        Args:
            force_reload: Whether to force reload even if cache is valid
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if file exists
            if not os.path.exists(FAQ_PATH):
                logger.warning(f"FAQ file not found at {FAQ_PATH}")
                return False
                
            # Check if we need to reload
            current_time = time.time()
            if not force_reload and current_time - self.last_loaded < self.cache_expiry:
                # Cache still valid
                return True
                
            # Check file modification time
            mod_time = os.path.getmtime(FAQ_PATH)
            if not force_reload and mod_time <= self.last_loaded:
                # File wasn't modified since last load
                self.last_loaded = current_time  # Update last loaded time but don't reload
                return True
            
            # Load the file
            with open(FAQ_PATH, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                
                # Validate structure
                if not isinstance(data, dict):
                    logger.error(f"Invalid FAQ format: expected dictionary but got {type(data)}")
                    return False
                    
                if 'entries' not in data or not isinstance(data['entries'], list):
                    logger.error("Invalid FAQ format: missing 'entries' list")
                    return False
                
                self.faq_data = data
                
            # Process and index FAQ data for faster searches
            self._process_faq_data()
            
            self.last_loaded = current_time
            logger.info(f"Loaded FAQ data with {len(self.faq_data.get('entries', []))} entries")
            return True
            
        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error in FAQ: {e}")
            return False
        except Exception as e:
            logger.error(f"Error loading FAQ: {e}")
            return False
    
    def _process_faq_data(self) -> None:
        """Process and clean up FAQ data for better matching."""
        entries = self.faq_data.get('entries', [])
        
        for entry in entries:
            # Skip invalid entries
            if not isinstance(entry, dict):
                continue
                
            # Clean up and normalize question
            if 'question' in entry:
                entry['question'] = entry['question'].strip()
                
                # Create clean version for matching
                entry['question_clean'] = self._clean_text(entry['question'])
                
            # Ensure keywords are a list
            if 'keywords' in entry:
                # Convert string keywords to list if needed
                if isinstance(entry['keywords'], str):
                    entry['keywords'] = [k.strip() for k in entry['keywords'].split(',')]
                    
                # Clean up keywords
                if isinstance(entry['keywords'], list):
                    entry['keywords'] = [k.strip().lower() for k in entry['keywords'] if k.strip()]
                else:
                    entry['keywords'] = []
    
    def _clean_text(self, text: str) -> str:
        """
        Clean text for better matching.
        
        Args:
            text: Text to clean
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
            
        # Convert to lowercase
        text = text.lower()
        
        # Remove punctuation
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def find_answer(self, query: str) -> Optional[str]:
        """
        Find answer for a query in the knowledge base.
        
        Args:
            query: User's query string
            
        Returns:
            Answer string if found, None otherwise
        """
        # Reload FAQ if needed
        self.load_faq()
        
        # Check if we have entries
        entries = self.faq_data.get('entries', [])
        if not entries:
            return None
        
        # Clean and normalize query
        clean_query = self._clean_text(query)
        
        # Search for exact match first
        for entry in entries:
            if not isinstance(entry, dict) or 'question_clean' not in entry:
                continue
                
            if entry['question_clean'] == clean_query:
                return entry.get('answer')
        
        # Then try partial matches
        matches = []
        for entry in entries:
            if not isinstance(entry, dict) or 'question' not in entry:
                continue
                
            question = entry['question_clean']
            keywords = entry.get('keywords', [])
            
            # Check if query contains the question or vice versa
            if clean_query in question or question in clean_query:
                matches.append((entry.get('answer'), 0.9))  # High confidence
                continue
                
            # Check keywords
            matched_keywords = [k for k in keywords if k in clean_query]
            if matched_keywords:
                # Confidence based on number of matched keywords
                confidence = 0.5 + (0.1 * min(len(matched_keywords), 3))
                matches.append((entry.get('answer'), confidence))
        
        # If we have matches, return the highest confidence one
        if matches:
            matches.sort(key=lambda x: x[1], reverse=True)
            return matches[0][0]
        
        return None
    
    def get_relevant_knowledge(self, query: str) -> Optional[str]:
        """
        Get relevant knowledge for a query from all knowledge sources.
        
        Args:
            query: User's query
            
        Returns:
            Relevant knowledge or None if not found
        """
        # First try FAQ
        faq_answer = self.find_answer(query)
        if faq_answer:
            return faq_answer
        
        # Try domain-specific knowledge bases
        if "anime" in query.lower() or "manga" in query.lower():
            return self._get_domain_knowledge("anime", query)
        
        if any(term in query.lower() for term in ["programming", "coding", "code", "developer"]):
            return self._get_domain_knowledge("programming", query)
            
        return None
    
    def _get_domain_knowledge(self, domain: str, query: str) -> Optional[str]:
        """
        Get domain-specific knowledge.
        
        Args:
            domain: Knowledge domain
            query: User's query
            
        Returns:
            Relevant knowledge or None
        """
        # This is a placeholder for domain-specific knowledge sources
        # Could be expanded with actual knowledge bases
        domain_file = KNOWLEDGE_PATH / f"{domain}.yaml"
        
        if not domain_file.exists():
            return None
        
        try:
            # Check if we need to load this domain
            if domain not in self.kb_data:
                with open(domain_file, 'r', encoding='utf-8') as f:
                    self.kb_data[domain] = yaml.safe_load(f) or {}
            
            # Look for matches in domain knowledge
            kb = self.kb_data[domain]
            if 'entries' not in kb:
                return None
                
            # Simple keyword matching
            clean_query = self._clean_text(query)
            
            for entry in kb['entries']:
                if 'keywords' in entry and isinstance(entry['keywords'], list):
                    if any(kw in clean_query for kw in entry['keywords']):
                        return entry.get('content')
            
            return None
            
        except Exception as e:
            logger.error(f"Error accessing domain knowledge for {domain}: {e}")
            return None
    
    def add_faq_entry(self, question: str, answer: str, keywords: List[str] = None) -> bool:
        """
        Add a new FAQ entry.
        
        Args:
            question: Question text
            answer: Answer text
            keywords: List of keywords
            
        Returns:
            True if successfully added, False otherwise
        """
        if not question or not answer:
            return False
            
        try:
            # Load the latest FAQ data
            self.load_faq(force_reload=True)
            
            # Create new entry
            new_entry = {
                'question': question,
                'answer': answer,
                'keywords': keywords or []
            }
            
            # Add to entries
            if 'entries' not in self.faq_data:
                self.faq_data['entries'] = []
                
            self.faq_data['entries'].append(new_entry)
            
            # Save back to file
            with open(FAQ_PATH, 'w', encoding='utf-8') as f:
                yaml.dump(self.faq_data, f, default_flow_style=False)
                
            # Process and reload
            self._process_faq_data()
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding FAQ entry: {e}")
            return False

# Create a singleton instance
knowledge_base = KnowledgeBase()

def get_answer(query: str) -> Optional[str]:
    """
    Get an answer for a query from the knowledge base (convenience function).
    
    Args:
        query: User's query
        
    Returns:
        Answer if found, None otherwise
    """
    return knowledge_base.get_relevant_knowledge(query)

def add_knowledge(question: str, answer: str, keywords: List[str] = None) -> bool:
    """
    Add new knowledge to the FAQ (convenience function).
    
    Args:
        question: Question text
        answer: Answer text
        keywords: List of keywords
        
    Returns:
        True if successfully added, False otherwise
    """
    return knowledge_base.add_faq_entry(question, answer, keywords)