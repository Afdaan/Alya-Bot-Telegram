<!-- Meta tags for SEO -->
<meta name="keywords" content="telegram bot, ai bot, waifu bot, anime bot, alya bot, roshidere bot, python telegram bot, gemini ai bot">
<meta name="description" content="Alya-chan: A Telegram Bot based on Alya from Roshidere with AI capabilities powered by Google Gemini">

<div align="center">
  <h1>
    Alya-chan Telegram Bot
    <img src="https://i.imgur.com/GUwqdRw.gif" width="174px" style="margin-left: 10px; vertical-align: middle;">
  </h1>

  <!-- Badges -->
  <p>
    <img src="https://img.shields.io/github/stars/Afdaan/alya-bot-telegram?style=for-the-badge&color=pink" alt="Stars">
    <img src="https://img.shields.io/github/forks/Afdaan/alya-bot-telegram?style=for-the-badge&color=lightblue" alt="Forks">
    <img src="https://img.shields.io/github/issues/Afdaan/alya-bot-telegram?style=for-the-badge&color=violet" alt="Issues">
    <img src="https://img.shields.io/badge/License-MIT-lightgreen.svg?style=for-the-badge" alt="License">
    <br>
    <img src="https://img.shields.io/badge/Python-3.8+-blue.svg?style=for-the-badge&logo=python" alt="Python">
    <img src="https://img.shields.io/badge/Telegram-Bot-blue.svg?style=for-the-badge&logo=telegram" alt="Telegram">
    <img src="https://img.shields.io/badge/Google-Gemini-orange.svg?style=for-the-badge&logo=google" alt="Gemini">
    <img src="https://img.shields.io/badge/Powered%20by-Waifu-ff69b4.svg?style=for-the-badge" alt="Waifu">
  </p>
</div>

## Description

Alya-chan is an AI-powered Telegram bot based on Alya from the anime/manga series "時々ボソッとロシア語でデレる隣のアーリャさん" (Alya Sometimes Hides Her Feelings in Russian), commonly known as "Roshidere". With her unique personality and Russian-Japanese background, Alya occasionally mutters her true feelings in Russian when she can't express them directly in Japanese. This bot brings her charm to your Telegram chats while providing powerful AI features powered by Google's Gemini!

> 🌟 Your personal Alya AI assistant that combines the charm of Roshidere with cutting-edge AI technology

## Key Features

- 🌸 **Waifu Chat Mode** - Tsundere personality with Russian expressions
- 💅 **Toxic Queen Mode** - Savage roasting capabilities
- 🔍 **Image Analysis** - Analyze images and documents with AI
- 🎨 **Anime Source Search** - Find anime/manga sources with SauceNAO
- 🔍 **Web Search** - Smart search with Google Custom Search
- 👥 **Group Chat Support** - Works in both private and group chats
- 🧠 **Context Awareness** - Remembers conversation history
- 🗣️ **Multi-language Support** - Primarily Indonesian with flexible language switching

## Core Features

### 🤖 AI-Powered Conversations
- **Context-aware responses** using conversation memory
- **Emotion detection** for natural interactions
- **Relationship progression** system (stranger → friend → close friend)
- **Russian expressions** triggered by emotional states
- **Dynamic personality** adapting to user relationship level

### 🔍 Enhanced Search Engine
- **Web Search**: `/search <query>` - Search information across the web
- **Profile Search**: `/search -p <name>` - Find social media profiles
- **News Search**: `/search -n <topic>` - Find latest news
- **Image Search**: `/search -i <description>` - Find images
- **Google CSE integration** with automatic API key rotation

### 🎨 Media Analysis
- **SauceNAO Integration**: `!sauce` - Find anime/manga sources
- **Image Analysis**: `!trace` - Analyze image content with AI
- **Document Analysis**: Upload documents for AI analysis

### 💬 Chat Modes
- **Normal Mode**: Tsundere responses with caring undertones
- **Roast Mode**: Savage roasting with creative insults
- **Admin Mode**: Special treatment for bot administrators

## Installation

### 1. Clone Repository
```bash
git clone https://github.com/Afdaan/alya-bot-telegram.git
cd alya-bot-telegram
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment
```bash
cp .env.example .env
```

Edit `.env` with your API keys:

```properties
# Required Configuration
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_from_botfather
ADMIN_IDS=your_telegram_user_id  # Can be multiple IDs: 123456,789012

# Gemini AI Configuration
GEMINI_API_KEYS=your_gemini_api_key  # Can be multiple keys: key1,key2,key3
GEMINI_MODEL=gemini-2.0-flash

# Optional Services
SAUCENAO_API_KEY=your_saucenao_api_key
GOOGLE_CSE_ID=your_google_custom_search_engine_id
GOOGLE_API_KEYS=your_google_api_key  # Can be multiple keys: key1,key2

# Optional: Self-hosted LLM (alternative to Gemini)
LLM_PROVIDER=gemini  # Options: gemini, self
LLM_MODEL_PATH=data/models/your_model.gguf  # Only if LLM_PROVIDER=self
```

### 5. Run the Bot
```bash
python main.py
```

## Configuration Guide

### API Keys Setup

#### Required APIs
1. **Telegram Bot Token**: Get from [@BotFather](https://t.me/BotFather)
2. **Gemini API Key**: Get from [Google AI Studio](https://makersuite.google.com/app/apikey)

#### Optional APIs
1. **SauceNAO API**: Get from [SauceNAO](https://saucenao.com/user.php)
2. **Google Custom Search**: Setup from [Google Cloud Console](https://console.cloud.google.com/)

### Multi-API Key Rotation

The bot supports multiple API keys for better reliability:

```properties
# Multiple Gemini keys (comma-separated)
GEMINI_API_KEYS=key1,key2,key3

# Multiple Google Search keys
GOOGLE_API_KEYS=key1,key2,key3
```

Benefits:
- **Automatic rotation** when rate limits are hit
- **Seamless operation** without interruption
- **Higher availability** and reliability

### Database Configuration

By default, the bot uses SQLite:
```properties
SQLITE_DB_PATH=data/alya.db  # Default location
```

### Self-hosted LLM Option

Instead of Gemini, you can use a local model:

```properties
LLM_PROVIDER=self
LLM_MODEL_PATH=data/models/your_model.gguf
LLM_CONTEXT_SIZE=4096
LLM_N_GPU_LAYERS=0  # 0 = CPU only, >0 = GPU layers
```

## Deployment

### Development
```bash
python main.py
```

### Production with TMUX
```bash
tmux new-session -s alya-bot
python main.py
# Ctrl+B then D to detach
```

### Docker Deployment
```bash
# Build image
docker build -t alya-bot .

# Run container
docker run -d \
  --name alya-bot \
  --restart unless-stopped \
  --env-file .env \
  -v ./data:/app/data \
  alya-bot
```

### Update Bot
```bash
# If using TMUX
tmux attach -t alya-bot
# Ctrl+C to stop
git pull
python main.py

# Or use admin command (if you're admin)
/update
```

## Bot Architecture

### Core Components
- **Core Bot**: Main bot logic and initialization
- **Handlers**: Message and command processors
- **Database**: User data and conversation storage
- **Memory**: Context-aware conversation management
- **NLP Engine**: Emotion detection and sentiment analysis
- **Persona System**: Personality and mood management

### Database Schema
- **Users**: User profiles and relationship data
- **Conversations**: Message history and context
- **Memory**: RAG-based conversation memory
- **Stats**: Usage statistics and analytics

## Features Overview

### Conversation System
- **RAG-powered memory** for context awareness
- **Emotion detection** using NLP models
- **Relationship progression** tracking
- **Dynamic responses** based on user relationship
- **Russian expressions** for emotional moments

### Search Capabilities
- **Intent detection** for different search types
- **Profile search** across social media platforms
- **News search** with date sorting
- **Image search** with thumbnail display
- **Smart query enhancement** for better results

### Admin Features
- **Bot statistics** and usage analytics
- **User management** and admin controls
- **System monitoring** and health checks
- **Deployment management** with git integration
- **Database cleanup** and maintenance

## Tech Stack

- **Python 3.8+** - Core programming language
- **python-telegram-bot v21** - Telegram API wrapper
- **Google Gemini 2.5 Flash** - AI language model
- **SQLite/PostgreSQL** - Database storage
- **SentenceTransformers** - Text embeddings for RAG
- **HuggingFace Models** - Emotion detection and NLP
- **aiohttp** - Async HTTP client
- **Docker** - Containerization support

## Performance Optimizations

1. **Response Caching** - Stores frequently asked questions
2. **API Key Rotation** - Automatic fallback for rate limits
3. **Memory Management** - Efficient conversation history handling
4. **Async Operations** - Non-blocking request processing
5. **Database Indexing** - Optimized query performance

## Security Features

- **Input validation** for all user inputs
- **SQL injection protection** with parameterized queries
- **Rate limiting** to prevent abuse
- **Admin-only commands** with proper authorization
- **Safe HTML/Markdown** rendering

## Commands

See [COMMANDS.md](COMMANDS.md) for complete list of available commands and usage examples.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Developer Contact

- **Creator**: Afdaan
- **Website**: [alif.horn-yastudio.com](https://alif.horn-yastudio.com)
- **GitHub**: [Afdaan](https://github.com/Afdaan)

## Acknowledgments

- Alya character from "Roshidere" anime/manga series
- Google Gemini AI for natural language processing
- Telegram Bot API for messaging platform
- SauceNAO for anime source identification
- Open source community for various libraries and tools