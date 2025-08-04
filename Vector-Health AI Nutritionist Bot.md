# Vector-Health AI Nutritionist Bot

A comprehensive AI-powered Telegram bot that serves as a personal nutritionist, helping users track their nutrition, analyze meals, and achieve their health goals through intelligent coaching and wearable device integration.

## Features

- **AI-Powered Food Logging**: Analyze food from photos or text descriptions using GPT-4o
- **Personalized Nutrition Coaching**: Daily reports and recommendations based on user goals
- **Wearable Device Integration**: Sync data from Garmin, Fitbit, Oura, and Withings via Terra API
- **Conversational Q&A**: Answer nutrition questions and analyze eating patterns
- **Goal-Based Planning**: Customized calorie and macronutrient targets
- **Progress Tracking**: Comprehensive daily summaries and analytics

## Architecture

- **Backend**: Flask with SQLAlchemy ORM
- **Database**: PostgreSQL with pgvector for embeddings
- **AI Models**: OpenAI GPT-4o for vision/text analysis, text-embedding-3-small for vectors
- **Integrations**: Telegram Bot API, Terra API for wearables
- **Deployment**: Docker containerized with health checks

## Quick Start

### 1. Prerequisites

- Python 3.11+
- PostgreSQL database (or Supabase)
- OpenAI API key
- Telegram Bot Token
- Terra API credentials

### 2. Environment Setup

```bash
# Clone the repository
git clone <repository-url>
cd vector-health-bot

# Copy environment template
cp .env.example .env

# Edit .env with your actual credentials
nano .env
```

### 3. Database Setup

#### Option A: Using Supabase (Recommended)

1. Create a new project at [supabase.com](https://supabase.com)
2. Enable the pgvector extension in Database → Extensions
3. Run the SQL schema from `database/schema.sql` in the SQL Editor
4. Update your `.env` file with Supabase credentials

#### Option B: Local PostgreSQL

```bash
# Install PostgreSQL and create database
createdb vector_health

# Install pgvector extension
psql vector_health -c "CREATE EXTENSION vector;"

# Run schema
psql vector_health < database/schema.sql
```

### 4. Installation & Running

#### Option A: Docker (Recommended)

```bash
# Build and run with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f vector-health-bot
```

#### Option B: Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

### 5. Telegram Bot Setup

1. Create a bot with [@BotFather](https://t.me/botfather)
2. Get your bot token and add it to `.env`
3. Set the webhook URL:

```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://your-domain.com/telegram/webhook"}'
```

### 6. Terra API Setup

1. Sign up at [tryterra.co](https://tryterra.co)
2. Create a new application and get your Dev ID and API Key
3. Configure webhook endpoint: `https://your-domain.com/terra/webhook`
4. Add credentials to `.env`

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `OPENAI_API_KEY` | OpenAI API key | Yes |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | Yes |
| `TERRA_DEV_ID` | Terra API developer ID | Yes |
| `TERRA_API_KEY` | Terra API key | Yes |
| `TERRA_WEBHOOK_SECRET` | Terra webhook secret (optional) | No |
| `SECRET_KEY` | Flask secret key | Yes |
| `DEBUG` | Enable debug mode (default: False) | No |

### Database Schema

The application uses three main tables:

- **user_profiles**: User information and calculated targets
- **food_logs**: Food entries with nutritional data and embeddings
- **activity_logs**: Daily activity data from wearables

## API Endpoints

### Telegram Webhook
- `POST /telegram/webhook` - Process Telegram updates
- `POST /telegram/set_webhook` - Set webhook URL

### Terra Webhook
- `POST /terra/webhook` - Process Terra API data
- `POST /terra/auth` - Generate authentication URL

### Health Data
- `GET /health/profile/<user_id>` - Get user profile
- `GET /health/food_logs/<user_id>` - Get food logs
- `GET /health/activity_logs/<user_id>` - Get activity logs
- `GET /health/daily_summary/<user_id>` - Get daily summary

## Bot Commands

- `/start` - Begin onboarding or show welcome message
- `/summary` - Get daily nutrition report
- `/connect_wearable` - Connect fitness tracker
- `/help` - Show help information

## Usage Examples

### Food Logging
- Send a photo of your meal for automatic analysis
- Text: "grilled chicken breast, 200g"
- Text: "apple and peanut butter"

### Questions
- "Is avocado healthy?"
- "How did I do this week?"
- "What should I eat for more protein?"

## Testing

```bash
# Run unit tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_health_utils.py

# Run with coverage
python -m pytest tests/ --cov=src
```

## Deployment

### Production Deployment

1. **Environment**: Set `DEBUG=False` in production
2. **Database**: Use managed PostgreSQL (Supabase, AWS RDS, etc.)
3. **Hosting**: Deploy to cloud platforms (Heroku, Railway, DigitalOcean, etc.)
4. **SSL**: Ensure HTTPS for webhook endpoints
5. **Monitoring**: Set up logging and health checks

### Health Checks

The application includes health check endpoints:
- `GET /` - Basic health check
- Docker health check configured for container monitoring

### Scaling Considerations

- Use Redis for session storage in multi-instance deployments
- Consider database connection pooling for high traffic
- Implement rate limiting for API endpoints
- Use CDN for static assets if needed

## Troubleshooting

### Common Issues

1. **Database Connection**: Verify DATABASE_URL format and credentials
2. **OpenAI API**: Check API key and rate limits
3. **Telegram Webhook**: Ensure HTTPS and correct webhook URL
4. **Terra Integration**: Verify webhook endpoint accessibility

### Logs

Application logs are written to:
- Console output (Docker logs)
- `vector-health-bot.log` file
- Structured JSON logs for production monitoring

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Check the troubleshooting section
- Review application logs
- Open an issue on GitHub

