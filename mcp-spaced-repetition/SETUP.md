# Detailed Setup Guide for MCP Spaced Repetition Server

This guide explains how to set up the MCP Spaced Repetition server to start and stop automatically with LibreChat.

## Prerequisites

- LibreChat running with Docker
- Docker and Docker Compose installed
- Access to modify LibreChat configuration files

## Setup Methods

### Method 1: Integrated with LibreChat's Docker Compose (Recommended)

This method ensures the MCP server starts and stops with LibreChat automatically.

#### Step 1: Position the MCP Server

Place the `mcp-spaced-repetition` directory at the same level as your LibreChat directory:

```
your-workspace/
├── LibreChat/
│   ├── docker-compose.yml
│   ├── librechat.yaml
│   └── ...
└── mcp-spaced-repetition/
    ├── Dockerfile
    ├── docker-compose.yml
    └── ...
```

#### Step 2: Create docker-compose.override.yml

In your LibreChat directory, create a `docker-compose.override.yml` file:

```yaml
version: '3.8'

services:
  mcp-spaced-repetition:
    build: ../mcp-spaced-repetition
    container_name: mcp-spaced-repetition
    restart: unless-stopped
    volumes:
      - mcp-spaced-repetition-data:/data
    environment:
      - SPACED_REPETITION_DATA_PATH=/data/cards.json
    networks:
      - default
    stdin_open: true
    tty: true
    depends_on:
      - api

volumes:
  mcp-spaced-repetition-data:
```

#### Step 3: Configure LibreChat

Add the MCP server to your `librechat.yaml`:

```yaml
# Other LibreChat configurations...

mcpServers:
  spaced-repetition:
    type: stdio
    command: docker
    args:
      - exec
      - -i
      - mcp-spaced-repetition
      - python
      - -m
      - mcp_spaced_repetition.server
    description: "Spaced repetition learning system with fact and concept cards"
```

#### Step 4: Start Everything Together

From the LibreChat directory:

```bash
# Start all services (including the MCP server)
docker-compose up -d

# Check that all containers are running
docker-compose ps

# View logs if needed
docker-compose logs mcp-spaced-repetition
```

Now the MCP server will:
- ✅ Start automatically when you run `docker-compose up`
- ✅ Stop when you run `docker-compose down`
- ✅ Restart if it crashes (unless-stopped policy)
- ✅ Persist data across restarts

### Method 2: Using a Combined docker-compose.yml

If you prefer to manage everything in one file, add this to LibreChat's main `docker-compose.yml`:

```yaml
  mcp-spaced-repetition:
    build: 
      context: ../mcp-spaced-repetition
      dockerfile: Dockerfile
    container_name: mcp-spaced-repetition
    restart: unless-stopped
    volumes:
      - mcp-spaced-repetition-data:/data
    environment:
      - SPACED_REPETITION_DATA_PATH=/data/cards.json
    networks:
      - default
    stdin_open: true
    tty: true
    depends_on:
      - api
```

### Method 3: Standalone with Network Connection

If you want to run the MCP server separately but still have it accessible:

1. First, find LibreChat's network name:
```bash
docker network ls | grep librechat
```

2. Update the MCP server's `docker-compose.yml`:
```yaml
networks:
  default:
    external:
      name: librechat_default  # Use the actual network name
```

3. Start the MCP server:
```bash
cd mcp-spaced-repetition
docker-compose up -d
```

## Verification

### 1. Check Container Status
```bash
# From LibreChat directory
docker-compose ps

# Should show:
# mcp-spaced-repetition    running
```

### 2. Test MCP Connection
In LibreChat, you can verify the MCP server is connected by:
- Opening the chat interface
- The AI should have access to spaced repetition tools
- Try: "Add a fact card: Q: What is Docker? A: A containerization platform"

### 3. Check Logs
```bash
# View MCP server logs
docker logs mcp-spaced-repetition

# Follow logs in real-time
docker logs -f mcp-spaced-repetition
```

## Data Persistence

The MCP server stores cards in a Docker volume. To manage this data:

### Backup
```bash
# Create a backup
docker run --rm -v mcp-spaced-repetition-data:/data -v $(pwd):/backup alpine tar czf /backup/cards-backup.tar.gz -C /data .
```

### Restore
```bash
# Restore from backup
docker run --rm -v mcp-spaced-repetition-data:/data -v $(pwd):/backup alpine tar xzf /backup/cards-backup.tar.gz -C /data
```

### Direct Access
```bash
# Access the data directly
docker run --rm -it -v mcp-spaced-repetition-data:/data alpine sh
cd /data
cat cards.json
```

## Troubleshooting

### MCP Server Not Responding

1. Check container is running:
```bash
docker ps | grep mcp-spaced-repetition
```

2. Check logs for errors:
```bash
docker logs mcp-spaced-repetition --tail 50
```

3. Test direct execution:
```bash
docker exec -it mcp-spaced-repetition python -m mcp_spaced_repetition.server
```

### Permission Issues

If you see permission errors:
```bash
# Fix data directory permissions
docker exec mcp-spaced-repetition chown -R 1000:1000 /data
```

### Network Connectivity

Verify the container is on the correct network:
```bash
docker inspect mcp-spaced-repetition | grep -A 10 "Networks"
```

## Environment Variables

You can customize the MCP server behavior with these environment variables in your docker-compose file:

```yaml
environment:
  - SPACED_REPETITION_DATA_PATH=/data/cards.json  # Data file location
  - LOG_LEVEL=INFO                                # Logging verbosity
  - MAX_CARDS_PER_REQUEST=10                      # Limit for get_next_due_card
```

## Updating the MCP Server

To update the server after making changes:

```bash
# From LibreChat directory
docker-compose build mcp-spaced-repetition
docker-compose up -d mcp-spaced-repetition
```

## Complete Example

Here's a complete example of how your setup might look:

**LibreChat/docker-compose.override.yml:**
```yaml
version: '3.8'

services:
  mcp-spaced-repetition:
    build: ../mcp-spaced-repetition
    container_name: mcp-spaced-repetition
    restart: unless-stopped
    volumes:
      - mcp-spaced-repetition-data:/data
    environment:
      - SPACED_REPETITION_DATA_PATH=/data/cards.json
    networks:
      - default
    stdin_open: true
    tty: true
    depends_on:
      - api
    healthcheck:
      test: ["CMD", "python", "-c", "import sys; sys.exit(0)"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  mcp-spaced-repetition-data:
```

**LibreChat/librechat.yaml:**
```yaml
version: 1.0.5

endpoints:
  # Your existing endpoints...

mcpServers:
  spaced-repetition:
    type: stdio
    command: docker
    args:
      - exec
      - -i
      - mcp-spaced-repetition
      - python
      - -m
      - mcp_spaced_repetition.server
    description: "Spaced repetition learning system for effective memorization"
    # Optional: Add an icon
    iconPath: "🧠"
```

This setup ensures that:
- The MCP server starts automatically with LibreChat
- It stops cleanly when LibreChat stops
- Data persists across restarts
- The server is accessible to LibreChat's agents
- Logs are available for debugging