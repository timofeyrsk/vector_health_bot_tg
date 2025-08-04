# Vector-Health AI Nutritionist Bot - Project Structure

```
vector-health-bot/
├── main.py                     # Application entry point
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Docker container configuration
├── docker-compose.yml          # Docker Compose setup
├── README.md                   # Comprehensive documentation
├── .env.example               # Environment variables template
├── todo.md                    # Development progress tracker
│
├── src/
│   └── app.py                 # Flask application factory
│
├── config/
│   └── settings.py            # Configuration management
│
├── database/
│   ├── connection.py          # Database connection and session management
│   └── schema.sql             # PostgreSQL schema with pgvector
│
├── models/
│   ├── __init__.py           # Models package initialization
│   ├── user_profile.py       # User profile model
│   ├── food_log.py           # Food logging model with embeddings
│   └── activity_log.py       # Activity tracking model
│
├── routes/
│   ├── telegram_routes.py    # Telegram webhook endpoints
│   ├── terra_routes.py       # Terra API webhook endpoints
│   └── health_routes.py      # Health data API endpoints
│
├── services/
│   ├── openai_service.py     # OpenAI GPT-4o and embeddings integration
│   ├── terra_service.py      # Terra API integration for wearables
│   ├── telegram_service.py   # Telegram bot logic and conversation flow
│   └── health_service.py     # Health calculations and data processing
│
├── utils/
│   └── health_utils.py       # Health calculation utilities and meal planning
│
└── tests/
    ├── test_config.py        # Test configuration and base classes
    └── test_health_utils.py  # Unit tests for health utilities
```

## Key Components

### Core Application (`src/app.py`)
- Flask application factory with CORS enabled
- Blueprint registration for modular routing
- Error handling and logging configuration
- Database initialization

### Configuration (`config/settings.py`)
- Environment variable management
- Configuration validation
- Support for development and production settings

### Database Layer (`database/`, `models/`)
- SQLAlchemy ORM models for PostgreSQL
- pgvector integration for food embeddings
- Relationship management between entities
- Database connection pooling and session management

### API Integration (`services/`)
- **OpenAI Service**: GPT-4o vision for food analysis, text embeddings, daily reports
- **Terra Service**: Wearable device data synchronization and authentication
- **Telegram Service**: Complete bot conversation flow and command handling
- **Health Service**: Business logic for nutrition calculations and data processing

### Routing (`routes/`)
- **Telegram Routes**: Webhook processing for bot interactions
- **Terra Routes**: Webhook processing for wearable data
- **Health Routes**: REST API for health data access

### Utilities (`utils/`)
- **Health Calculator**: BMR, TDEE, BMI calculations
- **Meal Planner**: Meal distribution and macro adjustment suggestions
- Comprehensive nutrition analysis functions

### Testing (`tests/`)
- Unit tests for core functionality
- Mock configurations for external API testing
- Health calculation validation

## Features Implemented

### 1. User Onboarding
- Complete profile setup via Telegram conversation
- Goal-based configuration (lose/maintain/gain weight)
- BMR and TDEE calculation with personalized targets

### 2. AI-Powered Food Logging
- Photo analysis using GPT-4o vision model
- Text description processing
- Automatic nutritional information extraction
- Vector embedding generation for semantic search

### 3. Wearable Integration
- Terra API integration for multiple device types
- Activity data synchronization (steps, calories, sleep)
- Authentication flow for device connection

### 4. Intelligent Coaching
- Daily summary generation with AI insights
- Personalized recommendations based on goals
- Conversational Q&A for nutrition questions
- Progress tracking and analytics

### 5. Data Management
- PostgreSQL with pgvector for embeddings
- Comprehensive data models for users, food, and activity
- RESTful API endpoints for data access

### 6. Production Ready
- Docker containerization with health checks
- Environment-based configuration
- Comprehensive logging and error handling
- Security best practices implemented

## Deployment Options

1. **Docker Compose**: Local development and testing
2. **Cloud Platforms**: Heroku, Railway, DigitalOcean
3. **Kubernetes**: Scalable production deployment
4. **Serverless**: AWS Lambda with API Gateway

## External Dependencies

- **OpenAI API**: GPT-4o for vision and text processing
- **Telegram Bot API**: Bot interactions and messaging
- **Terra API**: Wearable device data integration
- **PostgreSQL**: Primary database with pgvector extension
- **Supabase**: Managed PostgreSQL option with built-in pgvector

The application is fully functional and ready for deployment with proper environment configuration.

