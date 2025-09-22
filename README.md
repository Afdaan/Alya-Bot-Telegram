# Alya Bot v2 🌸

A fresh, clean, and maintainable Python Telegram waifu bot featuring Alya's tsundere personality with advanced AI capabilities.

## 🏗️ Architecture

This project follows clean architecture principles with clear separation of concerns:

```
app/
├── core/           # Business logic and use cases
├── domain/         # Domain models and entities
├── infrastructure/ # External services (DB, APIs)
└── presentation/   # Telegram handlers and controllers

config/             # Configuration management
personas/           # YAML personality definitions
database/           # Database models and migrations
scripts/            # Utility scripts
tests/              # Test suite
```

## ✨ Features

- 🤖 **AI-Powered**: Google Gemini Flash 2.0 integration
- 🧠 **Smart Memory**: RAG-based conversation context with sliding window
- 💭 **Emotion Detection**: HuggingFace sentiment analysis (customizable models)
- 🎭 **YAML Personas**: Easy-to-maintain personality system
- 🗄️ **MySQL Database**: Robust data persistence with relationship progression
- 🐳 **Docker Ready**: Containerized deployment with docker-compose
- 📊 **Clean Architecture**: Maintainable, testable, and extensible code
- 🔄 **Relationship System**: Progressive relationship levels with affection points
- 🌍 **Multi-language**: Indonesian and English support
- 📈 **Scalable**: Ready for Kubernetes deployment

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- MySQL 8.0+
- Telegram Bot Token from [@BotFather](https://t.me/BotFather)
- Google Gemini API Key from [Google AI Studio](https://makersuite.google.com/)

### Installation

1. **Clone and setup**
   ```bash
   git clone <repository-url>
   cd alya-bot-v2
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # venv\Scripts\activate   # Windows
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

4. **Setup database**
   ```bash
   # Option 1: Docker (recommended)
   docker-compose up mysql -d
   
   # Option 2: Manual MySQL setup
   # See docs/SETUP.md for detailed instructions
   
   # Initialize database
   python scripts/init_database.py
   ```

5. **Run the bot**
   ```bash
   python main.py
   ```

## 🔧 Configuration

All configuration is managed through environment variables in `.env`:

### Required Settings
```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
GEMINI_API_KEY=your_gemini_api_key_here
DB_PASSWORD=your_secure_password
```

### HuggingFace Models (Customizable)
```env
SENTIMENT_MODEL=cardiffnlp/twitter-roberta-base-sentiment-latest
EMOTION_MODEL=j-hartmann/emotion-english-distilroberta-base
```

### Bot Configuration
```env
BOT_NAME=Alya
COMMAND_PREFIX=!ai
DEFAULT_LANGUAGE=id
LOG_LEVEL=INFO
```

## 🎭 Persona System

Alya's personality is defined in `personas/alya.yaml` and includes:

- **Multi-language support** (Indonesian/English)
- **Relationship progression** (5 levels: Stranger → Intimate)
- **Emotion-based responses** (Happy, Sad, Angry, etc.)
- **Russian phrases** for authentic tsundere experience
- **Context-aware interactions** based on user history

Example persona customization:
```yaml
emotion_responses:
  id:
    happy:
      - "Senang mendengarnya! Meski... b-bukan berarti aku peduli atau apa 😊"
      - "Bagus deh~ хорошо!"
```

## 🧠 Memory & RAG System

- **Sliding Window Memory**: Maintains conversation context
- **Vector Embeddings**: Uses sentence-transformers for semantic search
- **Smart Context**: Retrieves relevant past conversations
- **Conversation Summarization**: Automatically summarizes long conversations
- **Relationship Tracking**: Remembers user preferences and interaction history

## 📦 Docker Deployment

```bash
# Quick start with docker-compose
docker-compose up -d

# View logs
docker-compose logs -f alya_bot

# Stop services
docker-compose down
```

The docker-compose setup includes:
- MySQL 8.0 database
- Alya Bot application
- Persistent volume for database
- Health checks
- Automatic restart policies

## 🧪 Development

### Code Quality Tools
```bash
# Format code
black .
isort .

# Type checking
mypy app/

# Run tests
pytest
pytest --cov=app tests/  # with coverage
```

### Testing Components
```bash
# Test individual components
python scripts/test_components.py

# Test specific functionality
pytest tests/test_entities.py -v
```

### VS Code Tasks
Pre-configured tasks available in VS Code:
- **Run Alya Bot v2** (Ctrl+Shift+P → Tasks: Run Task)
- **Initialize Database**
- **Test Components**
- **Install Dependencies**

## 🏛️ Architecture Principles

This project follows **Clean Architecture** with:

### Domain Layer (`app/domain/`)
- **Entities**: Core business objects (User, Message, etc.)
- **Repositories**: Data access interfaces
- **Services**: Business logic interfaces

### Infrastructure Layer (`app/infrastructure/`)
- **Database**: SQLAlchemy models and repositories
- **Services**: External API implementations (Gemini, HuggingFace)
- **Persona**: YAML-based personality management

### Core Layer (`app/core/`)
- **Use Cases**: Business logic implementation
- **Conversation**: Main conversation processing

### Presentation Layer (`app/presentation/`)
- **Handlers**: Telegram bot handlers
- **Container**: Dependency injection

## 📊 Database Schema

- **Users**: User profiles with relationship progression
- **Messages**: Conversation history with emotion analysis
- **ConversationContexts**: RAG context storage
- **MemoryEmbeddings**: Vector embeddings for similarity search

## 🚀 Production Deployment

### Environment Variables
```env
ENVIRONMENT=production
LOG_LEVEL=WARNING
DEBUG=false
DB_POOL_SIZE=20
MAX_REQUESTS_PER_MINUTE=120
```

### Kubernetes (Optional)
Ready for Kubernetes deployment with proper:
- ConfigMaps for configuration
- Secrets for sensitive data
- Persistent volumes for database
- Health checks and resource limits

## 🤝 Contributing

1. Follow the existing architecture patterns
2. Add tests for new features
3. Use type hints and docstrings
4. Format code with `black` and `isort`
5. Update persona YAML files when needed

## 📝 Documentation

- [Setup Guide](docs/SETUP.md) - Detailed installation instructions
- [Architecture Overview](docs/ARCHITECTURE.md) - System design details
- [Persona Guide](docs/PERSONAS.md) - Customizing Alya's personality
- [API Reference](docs/API.md) - Code documentation

## 🐛 Troubleshooting

### Common Issues

1. **Import Errors**: Ensure virtual environment is activated
2. **Database Connection**: Check MySQL credentials in `.env`
3. **Model Downloads**: Clear HuggingFace cache if needed
4. **API Limits**: Verify Gemini API key and quotas

Check `logs/alya_bot.log` for detailed error information.

## 🌟 Features Comparison

| Feature | Alya Bot v1 | Alya Bot v2 |
|---------|-------------|-------------|
| Architecture | Spaghetti | Clean Architecture |
| Database | SQLite | MySQL with RAG |
| AI Model | Basic | Gemini Flash 2.0 |
| Memory | Simple | Sliding Window + Vector |
| Persona | Hardcoded | YAML-based |
| Testing | None | Comprehensive |
| Docker | Basic | Production-ready |
| Maintenance | Difficult | Easy |

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Based on Alya from "Roshidere" (時々ボソッとロシア語でデレる隣のアーリャさん)
- Built with Google Gemini Flash 2.0
- Powered by HuggingFace Transformers
- Clean Architecture principles

---

**Made with ❤️ and a lot of tsundere energy! 🌸**

*"B-bukan berarti aku senang kamu pakai bot ini atau apa... дурак!"* - Alya
