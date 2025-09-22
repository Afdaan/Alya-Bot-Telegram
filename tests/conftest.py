"""
Test configuration and fixtures.
"""
import pytest
import asyncio
from typing import Generator, AsyncGenerator

from app.domain.entities import User, RelationshipLevel
from app.infrastructure.repositories import (
    SQLAlchemyUserRepository,
    SQLAlchemyMessageRepository,
    SQLAlchemyMemoryRepository
)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_user() -> User:
    """Create a test user."""
    return User(
        id=12345,
        username="test_user",
        first_name="Test", 
        last_name="User",
        language_code="id",
        relationship_level=RelationshipLevel.STRANGER
    )


@pytest.fixture
async def user_repo() -> AsyncGenerator[SQLAlchemyUserRepository, None]:
    """Create user repository for testing."""
    repo = SQLAlchemyUserRepository()
    yield repo
    # Cleanup would go here if needed


@pytest.fixture
async def message_repo() -> AsyncGenerator[SQLAlchemyMessageRepository, None]:
    """Create message repository for testing."""
    repo = SQLAlchemyMessageRepository()
    yield repo


@pytest.fixture
async def memory_repo() -> AsyncGenerator[SQLAlchemyMemoryRepository, None]:
    """Create memory repository for testing."""
    repo = SQLAlchemyMemoryRepository()
    yield repo
