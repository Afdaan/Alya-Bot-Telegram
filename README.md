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

## 🌸 Project Overview

>Alya-chan is an AI-powered Telegram bot based on Alya from the anime/manga series "時々ボソッとロシア語でデレる隣のアーリャさん" (Alya Sometimes Hides Her Feelings in Russian), commonly known as "Roshidere". The bot features Alya's unique tsundere personality with Russian expressions and provides powerful AI capabilities powered by Google's Gemini model.

## ✨ Key Features

- **🌸 Dynamic Personality** - Tsundere character with evolving relationship levels
- **💫 Memory System** - Context-aware conversations using RAG technology
- **🧠 Emotion Detection** - Recognizes user emotions and responds appropriately  
- **🎭 Multi-mood Responses** - Various response styles based on context
- **🔍 Media Analysis** - Vision capabilities for images and documents
- **🎯 Smart Web Search** - Advanced search capabilities with multiple modes
- **🎤 Voice Messages** - Send and receive voice messages with speech recognition and high-quality TTS using RVC (requires Microservice)

For a complete list of commands and features, see [COMMANDS.md](COMMANDS.md).  
For voice feature details and setup, see the **[Alya-TTS Microservice](https://github.com/Afdaan/Alya-TTS)**.

## 🛠️ Technology Stack

- **Python 3.8+** - Core language
- **python-telegram-bot v21** - Telegram API wrapper with async support
- **Google Gemini 2.5 Flash** - Primary AI language model
- **MySQL** - Database storage
- **ChromaDB** - Vector database for RAG implementation
- **HuggingFace Models** - Emotion detection and NLP tasks
- **aiohttp** - Async HTTP client for API interactions

## 🚀 Installation

### Prerequisites
- Python 3.8 or higher
- Git
- A Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- Google Gemini API Key

### Basic Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/Afdaan/alya-bot-telegram.git
   cd alya-bot-telegram
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

5. **Run the bot**
   ```bash
   python main.py
   ```

For detailed configuration options and deployment instructions, see the [Configuration](#-configuration) section below.

## ⚙️ Configuration

### Required Environment Variables

```properties
# Telegram Bot
TELEGRAM_BOT_TOKEN=your_telegram_bot_token

# Admin Settings
ADMIN_IDS=your_telegram_id  # Comma-separated for multiple admins (e.g., 123456,789012)

# Gemini AI
GEMINI_API_KEYS=your_gemini_api_key  # Comma-separated for key rotation
GEMINI_MODEL=gemini-2.0-flash
```

### Optional Environment Variables

```properties
# External APIs
SAUCENAO_API_KEY=your_saucenao_api_key  # For anime image source detection
GOOGLE_CSE_ID=your_google_search_engine_id  # For web search capabilities
GOOGLE_API_KEYS=your_google_api_key  # For Google Custom Search Engine

# Database Settings (defaults to SQLite)
DATABASE_URL=sqlite:///data/alya.db
# Alternative: DATABASE_URL=postgresql://user:password@localhost/alya

# Performance Settings
MEMORY_LIMIT=200  # Maximum number of messages to remember per user
CACHE_EXPIRY=3600  # Cache expiry time in seconds
```

### API Key Rotation System

Alya supports multiple API keys to ensure reliability and handle rate limits:

```properties
# Multiple comma-separated keys for automatic rotation
GEMINI_API_KEYS=key1,key2,key3
GOOGLE_API_KEYS=key1,key2,key3
```

The bot will automatically:
- Rotate to the next key when rate limits are reached
- Track usage and distribute load across keys
- Fall back gracefully if all keys are exhausted

### Database Configuration
Read on [Database Configuration](DATABASE_SETUP) for detailed instructions on setting up your database.

## 🎙️ Voice Support (Microservice)

Alya-chan now uses a **headless microservice architecture** for voice generation (Text-to-Speech + RVC). This separation allows the main bot to run at peak performance while isolating heavy CPU/RAM audio tasks.

### 🛠️ Setting up Voice
To enable voice responses in your bot:
1. **Main Bot**: Follow the [Basic Setup](#basic-setup) in this repository.
2. **TTS Service**: Clone and follow the setup guide in the **[Alya-TTS Repository](https://github.com/Afdaan/Alya-TTS)**.
3. **Connection**: Ensure `TTS_SERVICE_URL` in your `.env` points to your running TTS service.

> [!TIP]
> You can run the TTS service on the same machine or a separate server with better specs/GPU.

## 🚀 Deployment Options

### Development Mode
```bash
python main.py
```

### Production with TMUX
```bash
tmux new-session -s alya-bot
python main.py
# Ctrl+B then D to detach
# tmux attach -t alya-bot to reconnect
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

## 🏗️ Architecture

### Core Components

- **Bot Core** - Main initialization and command registration
- **Handlers** - Message processors for different commands and features
- **Memory System** - RAG-based conversation context manager
- **NLP Engine** - Emotion detection and intent recognition
- **Persona Manager** - Controls bot's personality and response style
- **Database** - Stores user data, relationships and conversation history

### Database Schema

- **Users** - User profiles with relationship progression
- **Conversations** - Message history and context tracking
- **Memory** - Vector embeddings for RAG implementation
- **Settings** - User preferences and configurations
- **Stats** - Usage statistics and analytics

## 🛡️ Security Features

- Input validation and sanitization
- Protection against prompt injection
- Rate limiting to prevent abuse
- Secure storage of API keys
- Safe HTML/Markdown rendering
- Comprehensive error handling and logging

## 🧪 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes following our coding standards
4. Test your changes thoroughly
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

Before submitting, please make sure your code follows our style guidelines as documented in the repo.

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👥 Contact

- **Creator**: Afdaan
- **Website**: [alif.horn-yastudio.com](https://alif.horn-yastudio.com)
- **GitHub**: [Afdaan](https://github.com/Afdaan)
- **Facebook**: [Afdaan](https://www.facebook.com/DanzdotTardotGz)

## 🤖 Bot Commands
For a complete list of commands and their usage, please refer to the [COMMANDS.md](COMMANDS.md) file.

## 🙏 Acknowledgments

- Alya character from "Roshidere" anime/manga series
- Google Gemini AI for natural language processing
- Telegram for their excellent Bot API
- SauceNAO for anime image source identification
- The open source community for various libraries and tools

---

<p align="center"><i>Crafted with <code>devops && coffee</code> by Afdaan☕⚙️</i></p>