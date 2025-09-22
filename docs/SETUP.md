# 🌸 Setup Guide - Alya Bot v2

## Prerequisites

Before setting up Alya Bot v2, make sure you have:

- **Python 3.11+** installed
- **MySQL 8.0+** server running
- **Telegram Bot Token** from [@BotFather](https://t.me/BotFather)
- **Google Gemini API Key** from [Google AI Studio](https://makersuite.google.com/)

## Installation Steps

### 1. Clone and Setup Environment

```bash
# Clone the repository
git clone <repository-url>
cd alya-bot-v2

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Linux/Mac:
source venv/bin/activate
# Windows:
venv\Scripts\activate
```

### 2. Install Dependencies

```bash
# Install core dependencies
pip install -r requirements.txt

# For development (optional)
pip install -e ".[dev]"
```

### 3. Database Setup

#### Option A: Using Docker (Recommended)

```bash
# Start MySQL with docker-compose
docker-compose up mysql -d

# Wait for MySQL to be ready, then initialize
python scripts/init_database.py
```

#### Option B: Manual MySQL Setup

```bash
# Connect to MySQL as root
mysql -u root -p

# Create database and user
CREATE DATABASE alya_bot_v2 CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'alya_bot'@'localhost' IDENTIFIED BY 'your_secure_password';
GRANT ALL PRIVILEGES ON alya_bot_v2.* TO 'alya_bot'@'localhost';
FLUSH PRIVILEGES;
EXIT;

# Initialize tables
python scripts/init_database.py
```

### 4. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your credentials
nano .env
```

**Required environment variables:**
```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
GEMINI_API_KEY=your_gemini_api_key_here
DB_PASSWORD=your_database_password
```

### 5. Test Components (Optional)

```bash
# Test all components
python scripts/test_components.py
```

### 6. Run the Bot

```bash
# Development mode
python main.py

# Or with Docker
docker-compose up
```

## Persona Customization

Edit `personas/alya.yaml` to customize Alya's personality:

```yaml
# Example: Adding new emotional responses
emotion_responses:
  id:
    excited:
      - "Kyaa~! что это?! Aku excited banget! ✨"
      - "W-wow... это круто! Tapi jangan salah sangka ya! 😤"
```

## HuggingFace Models

You can easily change sentiment analysis models by updating `.env`:

```env
# Sentiment analysis model
SENTIMENT_MODEL=cardiffnlp/twitter-roberta-base-sentiment-latest

# Emotion detection model  
EMOTION_MODEL=j-hartmann/emotion-english-distilroberta-base
```

## Troubleshooting

### Common Issues

1. **Import Errors**
   ```bash
   # Make sure you're in the virtual environment
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Database Connection Failed**
   ```bash
   # Check MySQL is running
   systemctl status mysql
   
   # Verify credentials in .env
   mysql -u alya_bot -p alya_bot_v2
   ```

3. **HuggingFace Model Download Issues**
   ```bash
   # Clear cache and retry
   rm -rf ~/.cache/huggingface/
   python scripts/test_components.py
   ```

4. **Telegram API Errors**
   - Verify bot token is correct
   - Check bot is not running elsewhere
   - Ensure bot has proper permissions

### Logs

Check logs for detailed error information:
```bash
# View recent logs
tail -f logs/alya_bot.log

# View with filtering
grep ERROR logs/alya_bot.log
```

## Production Deployment

### Docker Deployment

```bash
# Build and run with docker-compose
docker-compose up -d

# View logs
docker-compose logs -f alya_bot
```

### Kubernetes Deployment

```bash
# Apply Kubernetes manifests (if available)
kubectl apply -f k8s/

# Check pod status
kubectl get pods -l app=alya-bot
```

### Environment Variables for Production

```env
ENVIRONMENT=production
LOG_LEVEL=WARNING
DEBUG=false
DB_POOL_SIZE=20
MAX_REQUESTS_PER_MINUTE=120
```

## Development

### Code Formatting

```bash
# Format code
black .
isort .

# Type checking
mypy app/
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/
```

### Adding New Features

1. Follow clean architecture patterns
2. Add tests for new functionality
3. Update persona YAML if needed
4. Update documentation

## Support

For issues and questions:
- Check the [troubleshooting section](#troubleshooting)
- Review logs in `logs/alya_bot.log`
- Create an issue on GitHub

---

**Happy coding with Alya! 🌸**
