# Domino Boneyard API

A RESTful API for managing domino games with real-time WebSocket updates. This API allows you to create domino sets, manage tiles, and organize them into piles for building multiplayer domino games.

## Features

- Create and manage domino sets of different types (double-six, double-nine, etc.)
- Draw tiles from the boneyard
- Organize tiles into named piles
- Real-time updates via WebSockets
- Redis integration for persistence and scalability
- Configurable via environment variables
- Production-ready Docker setup

## API Documentation

Once the server is running, access the interactive API documentation at:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Setup & Installation

### Prerequisites

- Python 3.10+
- Redis (optional, for persistence)

### Local Development

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/domino-boneyard-api.git
   cd domino-boneyard-api
   ```

2. Create a virtual environment and install dependencies:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Create a `.env` file from the example:
   ```
   cp .env.example .env
   # Edit .env with your desired configuration
   ```

4. Run the development server:
   ```
   python main.py
   ```

### Docker Deployment

For production environments, use Docker Compose:

```
docker-compose up -d
```

This will start both the API and Redis with proper configuration.

## Free Deployment Options

### Deploy to Render.com (Free Tier)

1. Create a [Render.com](https://render.com) account
2. Click "New +" and select "Web Service"
3. Connect your GitHub repository
4. Configure the service:
   - Name: domino-boneyard-api
   - Environment: Python
   - Build Command: `pip install -r requirements-prod.txt`
   - Start Command: `gunicorn main:app -k uvicorn.workers.UvicornWorker`
   - Select the Free plan
5. Add environment variables:
   - `DOMINO_ENV`: production
   - `DOMINO_CORS_ORIGINS`: *
6. Click "Create Web Service"

### Deploy to Railway.app (Free Tier with Limitations)

1. Create a [Railway.app](https://railway.app) account
2. Click "New Project" and select "Deploy from GitHub repo"
3. Connect your GitHub repository
4. Add the required variables in the "Variables" tab:
   - `DOMINO_ENV`: production
   - `DOMINO_CORS_ORIGINS`: *
5. In the "Settings" tab, add a custom domain (optional)

### Deploy to Fly.io (Free Tier for Small Apps)

1. Install the [Fly CLI](https://fly.io/docs/hands-on/install-flyctl/)
2. Login to Fly: `fly auth login`
3. Launch your app:
   ```
   fly launch --name domino-boneyard-api
   ```
4. Deploy changes:
   ```
   fly deploy
   ```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DOMINO_ENV` | Environment (production, development, testing) | `production` |
| `DOMINO_HOST` | Host address to bind server | `0.0.0.0` |
| `DOMINO_PORT` | Port to run server on | `8000` |
| `DOMINO_CORS_ORIGINS` | Comma-separated list of allowed origins | `*` |
| `DOMINO_USE_REDIS` | Enable Redis for persistence | `false` |
| `DOMINO_REDIS_URL` | Redis connection URL | `redis://localhost:6379/0` |
| `DOMINO_SET_EXPIRY_SECONDS` | Time before sets expire | `1209600` (14 days) |

## Usage Examples

### Creating a Domino Set

```bash
curl -X POST http://localhost:8000/api/set/new \
  -H "Content-Type: application/json" \
  -d '{"type": "double-six", "sets": 1}'
```

### Drawing Tiles

```bash
curl -X POST http://localhost:8000/api/set/{set_id}/draw \
  -H "Content-Type: application/json" \
  -d '{"count": 7}'
```

### WebSocket Connection

```javascript
const socket = new WebSocket('ws://localhost:8000/ws/set/{set_id}');

socket.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Received update:', data);
};
```

## Architecture

The API follows a clean architecture with:

- **Models**: Data schemas for requests and responses
- **Services**: Business logic separated by domain
- **API Endpoints**: Route definitions organized by feature
- **Core**: Configuration and application setup

## Similar Projects

This project is similar in concept to the [Deck of Cards API](https://deckofcardsapi.com/), but specialized for domino games.

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 