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
- 🌸 Waifu Chat Mode
- 💅 Toxic Queen Mode
- 🔍 Image/Document Analysis
- 🎨 Source Image Search
- 🤖 AI-Powered Responses
- 👥 Group Chat Support
- 🗣️ Multi-language Support
- 🧠 Context Awareness

## NEW FEATURES

### 🖼️ Image Search with Results
- Search for images with `!search picture <query>` or `!search foto <query>`
- Receive both text information and actual images
- Images include title and source information
- Works with any topic: landmarks, people, animals, etc.

### ⚡ Performance Optimizations
- **Response Caching**: Stores answers to common questions
- **Efficient Token Usage**: Gets more out of your Gemini API quota
- **Multiple API Keys**: Automatic rotation system for handling rate limits
- **Image Analysis Caching**: Saves results for previously analyzed images

### 🔍 Enhanced Error Handling
- Better SauceNAO error recovery
- Improved markdown formatting in responses
- Format-safe username references
- Automatic retry system for failed API calls

## 🔍 Enhanced Global Search Engine

- **Global Results**: Search now covers the entire web, not just regional results
- **Improved Image Results**: Automatic fallback system for failed image URLs
- **Natural Language Understanding**: Intent detection for more accurate searches
- **Optimized Query Processing**: Query reformulation for more relevant results
- **Error Handling**: Better Markdown error handling for search results

## 🌐 Multiple Search Options

- **Regular Web Search**: Search for information across the entire web
- **Image Search**: Find images with directly displayed results
- **Social Media Profiles**: Find user profiles across various platforms
- **Specialized Searches**: Dedicated search options for schedules, news, locations, etc.

## Context-Aware Conversations
- Alya remembers previous messages in your conversation
- Ask follow-up questions without re-explaining
- Bot understands the context of ongoing discussions
- Example: Ask "What causes it?" after discussing a topic, and Alya knows what "it" refers to
- Great for multi-turn interactions and complex conversations
- Works in both English and Indonesian (and other languages upon request)

## Language Features
- Default languages: English & Indonesian
- Flexible language switching: Ask Alya to speak in any language!
- Usage: `/lang [code]` to set default language (en/id)
- Example: "Can you speak in Japanese?" or "Bisakah bicara dalam bahasa Jawa?"

## Tech Stack
- Python 3.8+
- Google Gemini AI
- Telegram Bot API
- SauceNAO API

## Installation

1. Clone repository:
```bash
git clone https://github.com/Afdaan/alya-bot-telegram.git
cd alya-bot-telegram
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment:
```bash
cp .env.example .env
```

Required API Keys in `.env`:
```properties
TELEGRAM_BOT_TOKEN=   # From @BotFather
GEMINI_API_KEY=       # From Google AI Studio
SAUCENAO_API_KEY=     # From SauceNAO
DEVELOPER_IDS=        # Your Telegram User ID
```

## Multiple Google Search API Keys

The bot now supports using multiple Google Search API keys to overcome rate limits:

### How It Works
- Configure multiple API keys in your `.env` file
- Bot automatically rotates through keys when rate limits are hit
- Seamlessly continues searching without interruption

### Setting Up Multiple API Keys
1. Create several Google Search API keys from Google Cloud Console
2. Add them to your `.env` file:
```properties
GOOGLE_SEARCH_API_KEY=your_primary_google_api_key_here
GOOGLE_SEARCH_API_KEY_2=your_second_google_api_key_here
GOOGLE_SEARCH_API_KEY_3=your_third_google_api_key_here
# Add more keys as needed (up to GOOGLE_SEARCH_API_KEY_10)
```

## Model Settings

This bot uses the Gemini AI model with configuration in `config/settings.py`:

- Default Model: `gemini-2.0-flash` (free plan)
- Optimized token usage & API call efficiency
- Response caching system for frequently asked questions
- Reduced API calls through smart preprocessing

### Performance Optimizations

This bot is designed for cost efficiency with several optimizations:

1. **Response Caching**: Stores answers to popular questions
2. **Rate Limiting**: Manages API calls to avoid quota errors
3. **Token Optimization**: Efficient prompts to maximize free quota usage
4. **Multiple API Keys**: Rotation system to handle rate limits
5. **Image Analysis Caching**: Stores results for previously analyzed images

These strategies provide high performance with minimal cost.

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

## Commands
See [COMMANDS.md](COMMANDS.md) for complete list of available commands and usage examples.

## Developer Contact
- Creator: Afdaan
- Website: [alif.horn-yastudio.com](https://alif.horn-yastudio.com)

## License
MIT License. See `LICENSE` for details.