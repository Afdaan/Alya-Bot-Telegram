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
# Edit .env with your API keys
```

Required API Keys:
- `TELEGRAM_BOT_TOKEN` - Get from [@BotFather](https://t.me/botfather)
- `GEMINI_API_KEY` - Get from [Google AI Studio](https://makersuite.google.com/app/apikey)
- `SAUCENAO_API_KEY` - Get from [SauceNAO](https://saucenao.com/user.php)

## Deployment

### Regular Python
```bash
python main.py
```

### Using TMUX (Recommended)
```bash
tmux new-session -s alya-bot
python main.py
# Ctrl+B then D to detach
```

To update bot:
```bash
tmux attach -t alya-bot
# Ctrl+C to stop
git pull
python main.py
```

## Developer Contact
- Creator: Afdaan
- Email: [alif@horn-yastudio.com]
- Website: [alif.horn-yastudio.com]

## License
MIT License. See `LICENSE` for details.