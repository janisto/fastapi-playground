# FastAPI Playground

A modern FastAPI application with Firebase Authentication, Firestore Database, and Google Cloud integration.

## Features

- **FastAPI**: Modern, fast web framework for building APIs with Python 3.13+
- **Firebase Authentication**: Secure JWT token-based authentication
- **Firestore Database**: NoSQL document database for profile storage
- **Google Cloud Logging**: Centralized logging for production environments
- **Google Secret Manager**: Secure secrets management
- **Type Safety**: Full type annotations and validation with Pydantic
- **Testing**: Comprehensive unit and integration tests with pytest
- **Code Quality**: Linting with Ruff, type checking with ty, formatting

## Project Structure

```
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── dependencies.py         # Application dependencies
│   ├── auth/
│   │   ├── __init__.py
│   │   └── firebase.py         # Firebase authentication
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py           # Application configuration
│   │   ├── firebase.py         # Firebase initialization
│   │   └── logging.py          # Logging configuration
│   ├── models/
│   │   ├── __init__.py
│   │   └── profile.py          # Profile data models
│   ├── routers/
│   │   └── profile.py          # Profile API endpoints
│   └── services/
│       ├── __init__.py
│       └── profile.py          # Profile business logic
├── tests/
│   ├── test_e2e.py            # End-to-end tests
│   ├── test_models.py         # Model validation tests
│   └── test_auth.py           # Authentication tests
├── pyproject.toml             # Project configuration
├── Justfile                   # Task runner commands
└── README.md
```

## API Endpoints

### Root Endpoints
- `GET /` - Hello World message with API docs link
- `GET /health` - Health check endpoint
- `GET /api-docs` - Interactive API documentation (Swagger UI)
- `GET /api-redoc` - Alternative API documentation (ReDoc)

### Profile Endpoints (Protected)
All profile endpoints require Firebase JWT authentication via `Authorization: Bearer <token>` header.

- `POST /profile/` - Create user profile
- `GET /profile/` - Get user profile
- `PUT /profile/` - Update user profile
- `DELETE /profile/` - Delete user profile

## Profile Model

```python
{
  "firstname": str,          # First name (required)
  "lastname": str,           # Last name (required)
  "email": EmailStr,         # Email address (required, validated)
  "phone_number": str,       # Phone number (required)
  "marketing": bool,         # Marketing opt-in (default: false)
  "terms": bool,             # Terms acceptance (required)
  "id": str,                 # User ID (auto-generated)
  "created_at": datetime,    # Creation timestamp (auto-generated)
  "updated_at": datetime     # Update timestamp (auto-generated)
}
```

## Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) - Package manager
- [just](https://github.com/casey/just) - Command runner
- Google Cloud Project with Firebase enabled
- Firebase project with Authentication and Firestore enabled

## Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd fastapi-playground
   ```

2. **Install dependencies**
   ```bash
   uv sync
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your Firebase and Google Cloud configuration
   ```

4. **Configure Firebase**
   - Create a Firebase project at https://console.firebase.google.com/
   - Enable Authentication and Firestore Database
   - Download service account key JSON file
   - Set `GOOGLE_APPLICATION_CREDENTIALS` to the path of your service account key

5. **Set up Google Cloud**
   - Enable required APIs: Firestore, Cloud Logging, Secret Manager
   - Ensure your service account has necessary permissions

## Available Commands (via just)

```bash
# Development
just serve                   # Run development server on localhost:8080
just test                    # Run unit tests
just cov                     # Run tests with coverage
just lint                    # Run linting and formatting
just typing                  # Type checking
just check-all               # Run all quality checks
```

## Development

### Running the Application

```bash
# Start development server
just serve

# Or directly with uv
uv run -m fastapi dev app/main.py --port 8080
```

The application will be available at:
- API: http://localhost:8080
- Documentation: http://localhost:8080/api-docs
- Health Check: http://localhost:8080/health

### Running Tests

```bash
# Run all tests
just test

# Run with coverage
just cov

# Run specific test file
uv run -m pytest tests/test_models.py -v
```

### Code Quality

```bash
# Lint and format code
just lint

# Type checking
just typing

# Run all quality checks
just check-all
```

## Authentication

The API uses Firebase Authentication with JWT tokens. To access protected endpoints:

1. Authenticate users through Firebase Auth (frontend/mobile app)
2. Obtain ID token from Firebase
3. Include token in requests: `Authorization: Bearer <id_token>`

Example using curl:
```bash
# Get profile (replace <token> with actual Firebase ID token)
curl -H "Authorization: Bearer <token>" http://localhost:8080/profile/

# Create profile
curl -X POST \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"firstname":"John","lastname":"Doe","email":"john@example.com","phone_number":"+1234567890","terms":true}' \
  http://localhost:8080/profile/
```

## Deployment

### Google Cloud Run

1. **Build container**
   ```bash
   docker build -t gcr.io/PROJECT_ID/fastapi-playground .
   ```

2. **Push to Container Registry**
   ```bash
   docker push gcr.io/PROJECT_ID/fastapi-playground
   ```

3. **Deploy to Cloud Run**
   ```bash
   gcloud run deploy fastapi-playground \
     --image gcr.io/PROJECT_ID/fastapi-playground \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated
   ```

### Environment Variables for Production

Set these environment variables in your deployment:
- `ENVIRONMENT=production`
- `DEBUG=false`
- `FIREBASE_PROJECT_ID=your-project-id`
- `GCP_PROJECT_ID=your-project-id`

## Testing

The project includes comprehensive testing:

- **Unit Tests**: Model validation, authentication logic
- **Integration Tests**: API endpoint testing with mocked dependencies
- **End-to-End Tests**: Full API workflow testing

Run specific test categories:
```bash
# Model tests
uv run -m pytest tests/test_models.py

# Authentication tests
uv run -m pytest tests/test_auth.py

# End-to-end tests
uv run -m pytest tests/test_e2e.py
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
