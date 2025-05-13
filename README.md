# Alya-chan Telegram Bot

## Description
Alya is a kawaii AI waifu bot powered by Google's Gemini AI. With multiple personalities from sweet waifu to toxic queen, she can chat, analyze images, reverse search anime sources, and more!

## Key Features
- 🌸 Waifu Chat Mode
- 💅 Toxic Queen Mode
- 🔍 Image/Document Analysis
- 🎨 Source Image Search
- 🤖 AI-Powered Responses
- 👥 Group Chat Support

## Tech Stack
- Python 3.8+
- Google Gemini AI
- Telegram Bot API
- SauceNAO API

## Installation

1. Clone repository:
```bash
git clone https://github.com/yourusername/alya-bot-telegram.git
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