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

# Alya Bot for Telegram

A conversational AI Telegram bot with a personality system, memory, and contextual awareness.

## Description

Alya-chan is an AI-powered Telegram bot based on Alya from the anime/manga series "時々ボソッとロシア語でデレる隣のアーリャさん" (Alya Sometimes Hides Her Feelings in Russian), commonly known as "Roshidere". With her unique personality and Russian-Japanese background, Alya occasionally mutters her true feelings in Russian when she can't express them directly in Japanese. This bot brings her charm to your Telegram chats while providing powerful AI features powered by Google's Gemini!

> 🌟 Your personal Alya AI assistant that combines the charm of Roshidere with cutting-edge AI technology

---

## Features

- 🌸 **Multiple Personas**: Switch between tsundere, waifu, informative, or toxic queen mode
- 🧠 **Memory System**: Remembers conversations and user facts for natural interactions
- 💬 **Natural Language Understanding**: Detects intent and context in user messages
- 🖼️ **Media Processing**: Handles images, documents, and provides content analysis
- 🔍 **Source Image Search**: Find anime/artwork sources with SauceNAO & Google Lens
- 🤖 **AI-Powered Responses**: Context-aware, roleplay, and multi-turn conversations
- 👥 **Group Chat Support**: Use `!` prefix for commands in groups
- 🌐 **Multi-language Support**: English & Indonesian (and more on request)
- 🧠 **Retrieval Augmented Generation (RAG)**: Enhanced responses with knowledge base
- ⚡ **Performance Optimizations**: Caching, API key rotation, efficient token usage

---

## NEW FEATURES

- **Image Search with Results**: `!search picture <query>` or `!search foto <query>`
- **Automatic Fallbacks**: Reliable image search with clickable previews if source fails
- **Multiple Google Search API Keys**: Automatic rotation to avoid rate limits
- **Enhanced Error Handling**: Markdown-safe, retry system, and better SauceNAO recovery
- **Context-Aware Conversations**: Multi-turn, follow-up, and memory recall
- **Flexible Language Switching**: `/lang [code]` or ask Alya directly

---

## Requirements

- Python 3.8+
- Telegram Bot Token (from @BotFather)
- Google Gemini API key
- SauceNAO API key
- (Optional) Multiple Google Search API keys

---

## Installation

1. **Clone repository:**
    ```bash
    git clone https://github.com/Afdaan/alya-bot-telegram.git
    cd alya-bot-telegram
    ```

2. **Create virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # Windows: venv\Scripts\activate
    ```

3. **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4. **Configure environment:**
    ```bash
    cp .env.example .env
    ```
    Edit `.env` and fill in your API keys:
    ```properties
    TELEGRAM_BOT_TOKEN=   # From @BotFather
    GEMINI_API_KEY=       # From Google AI Studio
    SAUCENAO_API_KEY=     # From SauceNAO
    DEVELOPER_IDS=        # Your Telegram User ID
    GOOGLE_SEARCH_API_KEY=your_primary_google_api_key_here
    GOOGLE_SEARCH_API_KEY_2=your_second_google_api_key_here
    # Add more keys as needed (up to GOOGLE_SEARCH_API_KEY_10)
    ```

---

## Setup

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Configure your API keys in `.env` (recommended) or `config/settings.py`
4. Run the bot: `python main.py`

---

## Deployment

### Running with Python
```bash
python main.py
```

### Using TMUX (Recommended)
```bash
tmux new-session -s alya-bot
python main.py
# Ctrl+B then D to detach
```

### How to Update
```bash
tmux attach -t alya-bot
# Ctrl+C to stop
git pull
python main.py
```

---

## Architecture

- **Core**: Main bot logic, persona management, and memory systems
- **Handlers**: Command and message handling
- **Database**: SQLite persistence with migration system
- **Utils**: Helper functions for natural language processing, media handling, etc.
- **Config**: Settings and persona YAMLs

---

## Model Settings

- Default Model: `gemini-2.0-flash` (free plan)
- Optimized token usage & API call efficiency
- Response caching system for frequently asked questions
- Reduced API calls through smart preprocessing

---

## Performance Optimizations

1. **Response Caching**: Stores answers to popular questions
2. **Rate Limiting**: Manages API calls to avoid quota errors
3. **Token Optimization**: Efficient prompts to maximize free quota usage
4. **Multiple API Keys**: Rotation system to handle rate limits
5. **Image Analysis Caching**: Stores results for previously analyzed images

---

## Commands

See [COMMANDS.md](COMMANDS.md) for a complete list of available commands and usage examples.

---

## Developer Contact

- Creator: Afdaan
- Website: [alif.horn-yastudio.com](https://alif.horn-yastudio.com)

---

## License

MIT License. See `LICENSE` for details.