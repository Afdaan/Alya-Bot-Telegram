# 🌸 Alya Bot Database Setup Guide 🌸

## Overview

Alya Bot uses **MySQL** as the primary database with **enterprise-grade** connection pooling, transaction management, and performance optimization. The database system is designed to handle production workloads with proper indexing, relationship tracking, and RAG (Retrieval-Augmented Generation) support.

---

## 🔧 Environment Variables

Create a `.env` file with the following MySQL configuration:

```env
# Database Configuration
DB_HOST=localhost
DB_PORT=3306
DB_USERNAME=alya
DB_PASSWORD=your_secure_password
DB_NAME=alya_bot

# Connection Pool Settings (Optional)
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600
DB_ECHO=false
```

### Required Variables:
- `DB_HOST`: MySQL server hostname
- `DB_PORT`: MySQL server port (default: 3306)
- `DB_USERNAME`: MySQL username
- `DB_PASSWORD`: MySQL password
- `DB_NAME`: Database name (will be created if not exists)

### Optional Variables:
- `DB_POOL_SIZE`: Connection pool size (default: 10)
- `DB_MAX_OVERFLOW`: Max overflow connections (default: 20)
- `DB_POOL_TIMEOUT`: Connection timeout in seconds (default: 30)
- `DB_POOL_RECYCLE`: Connection recycle time in seconds (default: 3600)
- `DB_ECHO`: Enable SQL query logging (default: false)

---

## 🚀 Quick Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Setup MySQL Server
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install mysql-server

# Start MySQL service
sudo systemctl start mysql
sudo systemctl enable mysql

# Secure installation
sudo mysql_secure_installation
```

### 3. Create Database User
```sql
-- Connect to MySQL as root
mysql -u root -p

-- Create user and database
CREATE USER 'alya'@'localhost' IDENTIFIED BY 'your_secure_password';
CREATE DATABASE alya_bot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
GRANT ALL PRIVILEGES ON alya_bot.* TO 'alya'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### 4. Initialize Database
```bash
python init_database.py
```

### 5. Start the Bot
```bash
python main.py
```

---

## 📊 Database Schema

### Tables Created:

#### 1. `users` - User Information & Relationship Tracking
- **Primary Key**: `id` (BigInteger) - Telegram User ID
- **Indexes**: username, language_code, relationship_level, interaction_count
- **Features**: Affection points, relationship levels, preferences (JSON)

#### 2. `conversations` - Message History with RAG Support
- **Primary Key**: `id` (BigInteger, Auto-increment)
- **Foreign Key**: `user_id` → users.id
- **Indexes**: user_id+created_at, role, emotion_category, processed_for_rag
- **Features**: Message deduplication, sentiment analysis, RAG processing

#### 3. `conversation_summaries` - AI-Generated Summaries
- **Primary Key**: `id` (BigInteger, Auto-increment)
- **Foreign Key**: `user_id` → users.id
- **Features**: Long-term memory, conversation context preservation

#### 4. `api_usage` - API Cost Tracking (Optional)
- **Primary Key**: `id` (BigInteger, Auto-increment)
- **Features**: Token usage, cost tracking, performance monitoring

---

## 💡 Usage Examples

### Basic Database Operations
```python
from database.database_manager import db_manager

# Get or create user
user_data = db_manager.get_or_create_user(
    user_id=12345,
    username="afdaan",
    first_name="Afdaan"
)

# Save message
success = db_manager.save_message(
    user_id=12345,
    role="user",
    content="Hello Alya!",
    metadata={"emotion": "happy"}
)

# Get conversation history
history = db_manager.get_conversation_history(user_id=12345, limit=10)

# Update user affection
db_manager.update_affection(user_id=12345, points=5)

# Reset conversation
db_manager.reset_conversation(user_id=12345)
```

### Advanced Operations
```python
# Search conversations
results = db_manager.search_conversations(
    user_id=12345, 
    query="anime", 
    limit=5
)

# Apply sliding window (keep only recent messages)
db_manager.apply_sliding_window(user_id=12345, keep_recent=100)

# Track API usage
db_manager.track_api_usage(
    user_id=12345,
    provider="gemini",
    method="generateContent",
    input_tokens=150,
    output_tokens=200,
    cost_cents=5
)

# Get database statistics
stats = db_manager.get_database_stats()
print(f"Total users: {stats['total_users']}")
print(f"Active users: {stats['active_users']}")
```

---

## 🔍 Monitoring & Maintenance

### Health Check
```python
from database.session import health_check, get_connection_info

# Check database health
is_healthy = health_check()

# Get connection pool stats
info = get_connection_info()
print(f"Pool size: {info['pool_size']}")
print(f"Active connections: {info['checked_out']}")
```

### Cleanup Operations
```python
# Clean up old data (based on MEMORY_EXPIRY_DAYS setting)
db_manager.cleanup_old_data()

# Manual conversation cleanup
cutoff_date = datetime.now() - timedelta(days=30)
# Implement custom cleanup logic
```

---

## ⚡ Performance Optimization

### Connection Pooling
- **Pool Size**: 10 connections (configurable)
- **Max Overflow**: 20 additional connections
- **Connection Recycling**: 1 hour (prevents stale connections)
- **Pre-ping**: Validates connections before use

### Indexing Strategy
- **Primary indexes** on all frequently queried columns
- **Composite indexes** for complex queries
- **Foreign key indexes** for join performance
- **Partial indexes** for filtered queries

### Query Optimization
- **Lazy loading** for relationships
- **Batch operations** for bulk inserts
- **Prepared statements** via SQLAlchemy
- **Connection reuse** across requests

---

## 🛡️ Security Features

### Data Protection
- **UTF8MB4** charset for emoji support
- **Parameterized queries** prevent SQL injection
- **Connection encryption** (configure SSL in production)
- **Password hashing** for sensitive data

### Error Handling
- **Graceful degradation** on connection loss
- **Transaction rollback** on errors
- **Connection recovery** with circuit breaker pattern
- **Comprehensive logging** for debugging

---

## 🔧 Troubleshooting

### Common Issues

#### 1. Connection Refused
```bash
# Check MySQL service
sudo systemctl status mysql

# Check port availability
netstat -tlnp | grep 3306
```

#### 2. Authentication Failed
```sql
-- Reset user password
ALTER USER 'alya'@'localhost' IDENTIFIED BY 'new_password';
FLUSH PRIVILEGES;
```

#### 3. Character Set Issues
```sql
-- Check database charset
SELECT DEFAULT_CHARACTER_SET_NAME, DEFAULT_COLLATION_NAME 
FROM information_schema.SCHEMATA 
WHERE SCHEMA_NAME = 'alya_bot';

-- Fix charset if needed
ALTER DATABASE alya_bot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

#### 4. Connection Pool Exhausted
```python
# Check pool stats
from database.session import get_connection_info
print(get_connection_info())

# Increase pool size in .env
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40
```

---

## 📈 Migration Guide

### From SQLite to MySQL
```bash
# Use the migration script
python database/migrate.py path/to/old/sqlite.db
```

### Database Upgrades
```bash
# Backup first
mysqldump -u alya -p alya_bot > backup.sql

# Run migration
python database/migrate_new.py

# Verify data integrity
python -c "from database.database_manager import db_manager; print(db_manager.get_database_stats())"
```

---

## 🌟 Enterprise Features

### Production Deployment
- **Docker support** with docker-compose.yml
- **Environment-based configuration**
- **Health monitoring** endpoints
- **Automated backups** (implement with cron)

### Scaling Considerations
- **Read replicas** for high-traffic scenarios
- **Connection pooling** across multiple app instances
- **Database sharding** for massive user bases
- **Caching layer** with Redis integration

---

Sekarang database lu udah **enterprise-grade** dengan MySQL yang proper! 🚀

Struktur yang clean, connection pooling yang solid, error handling yang bulletproof, dan indexing yang optimal. Siap untuk production deployment di server manapun! 💫
