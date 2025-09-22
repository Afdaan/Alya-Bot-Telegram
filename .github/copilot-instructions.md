<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

# Alya Bot v2 - Copilot Instructions

## Project Overview
This is a fresh Python Telegram waifu bot project with clean architecture using:
- Google Gemini Flash 2.0 for AI responses
- HuggingFace models for sentiment analysis
- YAML-based persona system for easy maintenance
- MySQL database with RAG memory system
- Docker/Kubernetes ready structure

## Architecture Guidelines
- Follow clean architecture principles
- Use dependency injection where possible
- Keep business logic separate from framework code
- Make code easily testable and maintainable
- Follow Python best practices (PEP 8, type hints)

## Key Components
- `app/core/` - Core business logic and entities
- `app/infrastructure/` - External services (database, APIs)
- `app/presentation/` - Telegram handlers and routes
- `app/domain/` - Domain models and interfaces
- `config/` - Configuration and settings
- `personas/` - YAML persona definitions
- `database/` - Database models and migrations

## Coding Standards
- Use type hints for all functions and classes
- Follow async/await patterns for I/O operations
- Use dependency injection for services
- Write descriptive docstrings
- Keep functions small and focused
- Use proper error handling and logging

## Bot Features
- Waifu personality with tsundere characteristics
- Context-aware conversations using RAG
- Emotion detection and sentiment analysis
- Sliding window memory system
- Multi-language support (ID/EN)
- Relationship progression system
