# Domino Boneyard API

A RESTful API for managing domino games with real-time WebSocket updates. This API allows you to create domino sets, manage tiles, and organize them into piles for building multiplayer domino games.

## Live API

The API is live and publicly available at:
- **API URL**: https://domino-boneyard-api.onrender.com
- **API Documentation**: https://domino-boneyard-api.onrender.com/docs
- **Demo Page**: https://bantoinese83.github.io/domino-boneyard-demo/

## Features

- Create and manage domino sets of different types (double-six, double-nine, etc.)
- Draw tiles from the boneyard
- Organize tiles into named piles
- Real-time updates via WebSockets
- Redis integration for persistence and scalability
- Configurable via environment variables
- Production-ready Docker setup

## API Documentation

The interactive API documentation is available at:
- Swagger UI: https://domino-boneyard-api.onrender.com/docs
- ReDoc: https://domino-boneyard-api.onrender.com/redoc

## Basic API Usage Examples

### JavaScript Example: Creating a Game and Drawing Tiles

```javascript
// Create a new domino set
async function createGame() {
  const response = await fetch('https://domino-boneyard-api.onrender.com/api/set/new', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      type: 'double-six',
      sets: 1
    })
  });
  
  const data = await response.json();
  console.log('Game created:', data);
  return data.set_id;
}

// Draw tiles from the boneyard
async function drawTiles(setId, count) {
  const response = await fetch(`https://domino-boneyard-api.onrender.com/api/set/${setId}/draw`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ count: count })
  });
  
  const data = await response.json();
  console.log('Tiles drawn:', data);
  return data.tiles_with_images;
}

// Create a player's pile
async function createPlayerPile(setId, playerName) {
  const response = await fetch(`https://domino-boneyard-api.onrender.com/api/set/${setId}/pile/new`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name: playerName })
  });
  
  const data = await response.json();
  console.log(`Pile created for ${playerName}:`, data);
  return data;
}

// Add tiles to a player's pile
async function addTilesToPile(setId, pileName, tiles) {
  const response = await fetch(`https://domino-boneyard-api.onrender.com/api/set/${setId}/pile/${pileName}/add`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ tiles: tiles })
  });
  
  const data = await response.json();
  console.log(`Tiles added to ${pileName}:`, data);
  return data;
}
```

### Python Example: Complete Game Flow

```python
import requests

API_URL = "https://domino-boneyard-api.onrender.com"

# Create a new domino set
def create_game():
    response = requests.post(
        f"{API_URL}/api/set/new",
        json={"type": "double-six", "sets": 1}
    )
    data = response.json()
    print(f"Game created with ID: {data['set_id']}")
    return data['set_id']

# Draw tiles
def draw_tiles(set_id, count):
    response = requests.post(
        f"{API_URL}/api/set/{set_id}/draw",
        json={"count": count}
    )
    return response.json()

# Create player pile
def create_player_pile(set_id, player_name):
    response = requests.post(
        f"{API_URL}/api/set/{set_id}/pile/new",
        json={"name": player_name}
    )
    return response.json()

# Add tiles to player's pile
def add_tiles_to_pile(set_id, player_name, tiles):
    response = requests.post(
        f"{API_URL}/api/set/{set_id}/pile/{player_name}/add",
        json={"tiles": tiles}
    )
    return response.json()

# Game flow example
def run_game_example():
    # Create a game
    set_id = create_game()
    
    # Create players
    create_player_pile(set_id, "player1")
    create_player_pile(set_id, "player2")
    
    # Draw and deal tiles to player1
    drawn = draw_tiles(set_id, 7)
    add_tiles_to_pile(set_id, "player1", drawn["tiles_drawn"])
    
    # Draw and deal tiles to player2
    drawn = draw_tiles(set_id, 7)
    add_tiles_to_pile(set_id, "player2", drawn["tiles_drawn"])
    
    # Get pile contents
    response = requests.get(f"{API_URL}/api/set/{set_id}/pile/player1/list")
    print(f"Player 1 tiles: {response.json()['pile_tiles']}")

if __name__ == "__main__":
    run_game_example()
```

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