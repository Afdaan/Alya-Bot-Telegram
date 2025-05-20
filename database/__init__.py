"""
Database package for Alya Bot.

This package handles all database operations including connections, memory management,
context storage, and retrieval augmented generation capabilities.
"""

# Import database core components first
from .database import DatabaseManager, db_manager, get_connection, execute_query

# Define lazy imports for memory_retrieval to avoid circular dependency
from typing import Dict, Any, Optional

def get_memory_retriever():
    """Get memory retriever singleton instance."""
    from .memory_retrieval import memory_retriever
    return memory_retriever

async def retrieve_memories(user_id: int, query: str, chat_id: Optional[int] = None):
    """Lazy loaded function for retrieve_memories."""
    from .memory_retrieval import retrieve_memories as _retrieve_memories
    return await _retrieve_memories(user_id, query, chat_id)
    
async def generate_memory_response(user_id: int, query: str, chat_id=None, persona=None):
    """Lazy loaded function for generate_memory_response."""
    from .memory_retrieval import generate_memory_response as _generate_memory_response
    return await _generate_memory_response(user_id, query, chat_id, persona)

def get_memory_retrieval_system():
    """Get MemoryRetrievalSystem class."""
    from .memory_retrieval import MemoryRetrievalSystem
    return MemoryRetrievalSystem

# Export symbols with core DB functions and lazy functions
__all__ = [
    # Database core
    'DatabaseManager',
    'db_manager',
    'get_connection',
    'execute_query',
    
    # Memory retrieval - lazy loaded functions
    'get_memory_retriever',
    'retrieve_memories',
    'generate_memory_response',
    'get_memory_retrieval_system'
]
