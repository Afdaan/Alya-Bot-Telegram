# Alya Telegram Bot

## Description
Alya is an intelligent Telegram bot powered by Google's Gemini AI, capable of chat interactions, document analysis, and image generation.

## Features
- Natural language conversation
- Document and image analysis
- Chat mode with waifu personality
- Group and private chat support

## Prerequisites
- Python 3.8+
- Telegram Bot Token
- Google Gemini API Key
- (Optional) Stability AI API Key for image generation

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/alya-bot-telegram.git
cd alya-bot-telegram
```

2. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create and configure `.env` file:
```bash
cp .env.example .env
```
Edit `.env` with your API keys:
- Get Telegram Bot Token from [@BotFather](https://t.me/botfather)
- Get Gemini API Key from [Google AI Studio](https://makersuite.google.com/app/apikey)
- (Optional) Get Stability AI Key from [Stability AI](https://platform.stability.ai/)

## Running the Bot
```bash
python main.py
```

## Environment Variables
- `TELEGRAM_BOT_TOKEN`: Your Telegram Bot Token
- `GEMINI_API_KEY`: Google Gemini API Key
- `STABILITY_API_KEY`: (Optional) Stability AI API Key for image generation

## Contributing
1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License
Distributed under the MIT License. See `LICENSE` for more information.

## Contact
Afdaan - [alif@horn-yastudio.com]

Project Link: [https://github.com/Afdaan/alya-bot-telegram](https://github.com/Afdaan/alya-bot-telegram)