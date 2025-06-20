# MCP Spaced Repetition Server

A Model Context Protocol (MCP) server that implements a spaced repetition learning system for LibreChat. It uses the FSRS (Free Spaced Repetition Scheduler) algorithm to optimize learning intervals.

## Features

- **Two Card Types**:
  - **Fact Cards**: Simple question-answer pairs
  - **Concept Cards**: AI generates varied questions to test understanding
  
- **FSRS Scheduling**: Advanced spaced repetition algorithm for optimal learning intervals
- **Persistent Storage**: Cards are stored in a Docker volume
- **Integrated with LibreChat**: Runs as part of the LibreChat container

## Integration with LibreChat

This MCP server is integrated into LibreChat using the "sidecar" pattern:
1. LibreChat's Docker image is extended to include Python and the MCP server
2. The server runs inside the same container as LibreChat
3. Configuration is done through `librechat.yaml`
4. No separate containers or complex networking required

## Setup

### 1. Files Required

The integration requires these files in your LibreChat directory:

- `Dockerfile.extended` - Extends LibreChat with Python and MCP server
- `docker-compose.override.yml` - Configures the build and volumes
- `librechat.yaml` - Configures the MCP server for LibreChat
- `mcp-spaced-repetition/` - This directory with the Python code

### 2. Configuration Files

**Dockerfile.extended**:
```dockerfile
FROM ghcr.io/danny-avila/librechat-dev:latest
USER root
RUN apk add --no-cache python3 py3-pip python3-dev
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY mcp-spaced-repetition/requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip && pip install -r /tmp/requirements.txt
RUN mkdir -p /app/tools
COPY mcp-spaced-repetition /app/tools/mcp-spaced-repetition
RUN cd /app/tools/mcp-spaced-repetition && pip install -e .
RUN printf '#!/bin/sh\nexec /opt/venv/bin/python -m mcp_spaced_repetition.server\n' > /app/tools/spaced_repetition_server.sh && \
    chmod +x /app/tools/spaced_repetition_server.sh
USER node
```

**docker-compose.override.yml**:
```yaml
services:
  api:
    build:
      context: .
      dockerfile: Dockerfile.extended
    volumes:
      - ./librechat.yaml:/app/librechat.yaml:ro
      - ./mcp-spaced-repetition:/app/tools/mcp-spaced-repetition:ro
      - ${MCP_DATA_PATH:-./mcp-data}:/data
    environment:
      - SPACED_REPETITION_DATA_PATH=/data/cards.json
```

**librechat.yaml**:
```yaml
version: 1.0.5

# Enable agents in the interface
interface:
  agents: true

# Configure agents endpoint
endpoints:
  agents:
    disableBuilder: false
    capabilities: ["execute_code", "file_search", "actions", "tools", "web_search", "artifacts"]

# MCP Servers Configuration
mcpServers:
  spaced-repetition:
    type: stdio
    command: /app/tools/spaced_repetition_server.sh
    args: []
    description: "Spaced repetition learning system with FSRS algorithm"
    timeout: 60000
    env:
      SPACED_REPETITION_DATA_PATH: /data/cards.json
```

### 3. Enable Agents in .env

Make sure your `.env` file includes agents in the ENDPOINTS:
```
ENDPOINTS=openAI,assistants,azureOpenAI,google,gptPlugins,anthropic,agents
```

### 4. Start LibreChat

```bash
docker compose down
docker compose up -d --build
```

## Available Tools

### `add_card`
Add a new spaced repetition card.

**Parameters**:
- `card_type` (required): "fact" or "concept"
- `question` (required for fact cards): The question text
- `answer` (required for fact cards): The answer text
- `concept` (required for concept cards): Description of the concept
- `tags` (optional): Array of tags for organization

### `remove_card`
Remove a card by ID.

**Parameters**:
- `card_id` (required): ID of the card to remove

### `get_next_due_card`
Get cards that are due for review.

**Parameters**:
- `limit` (optional, default: 1): Maximum number of cards to return

### `update_card`
Update the content of a card without affecting its schedule.

**Parameters**:
- `card_id` (required): ID of the card to update
- `question` (optional): Updated question (fact cards only)
- `answer` (optional): Updated answer (fact cards only)
- `concept` (optional): Updated concept (concept cards only)
- `tags` (optional): Updated tags array

### `review_card`
Review a card and reschedule it based on difficulty rating.

**Parameters**:
- `card_id` (required): ID of the card to review
- `rating` (required): Difficulty rating (1=Again, 2=Hard, 3=Good, 4=Easy)

## Usage Examples

### In LibreChat

1. Create or select an agent
2. Enable the spaced repetition tools
3. Use natural language to interact:

**Adding Cards**:
- "Add a fact card: Q: What is the capital of France? A: Paris"
- "Create a concept card about recursion in programming"

**Reviewing Cards**:
- "Show me the next card to review"
- "I found that question hard" (rating: 2)
- "That was easy" (rating: 4)

**Managing Cards**:
- "Update the wording of the last card"
- "Remove that card"
- "Show me 5 cards that are due"

## Data Persistence

Cards are stored in a configurable location on your host system.

### Configuring Storage Location

By default, cards are stored in `./mcp-data/cards.json` relative to your LibreChat directory. You can change this by setting the `MCP_DATA_PATH` environment variable:

**Option 1: In your .env file**
```
MCP_DATA_PATH=/path/to/your/cards/directory
```

**Option 2: When running docker-compose**
```bash
MCP_DATA_PATH=/home/user/my-cards docker compose up -d
```

**Option 3: Export the variable**
```bash
export MCP_DATA_PATH=/home/user/my-cards
docker compose up -d
```

### Default Location
If `MCP_DATA_PATH` is not set, cards will be stored in:
- `./mcp-data/cards.json` (relative to LibreChat directory)

### Backup and Restore

Since the data is now in a regular directory, you can simply:

**Backup**
```bash
cp ${MCP_DATA_PATH:-./mcp-data}/cards.json cards-backup-$(date +%Y%m%d).json
```

**Restore**
```bash
cp cards-backup-20240620.json ${MCP_DATA_PATH:-./mcp-data}/cards.json
```

## Development

### Project Structure
```
mcp-spaced-repetition/
├── mcp_spaced_repetition/
│   ├── __init__.py
│   ├── server.py      # Main MCP server
│   ├── models.py      # Data models
│   ├── fsrs.py        # FSRS algorithm
│   └── storage.py     # JSON storage
├── requirements.txt
├── pyproject.toml
└── README.md
```

### Hot Reload

The code is mounted as a volume, so you can edit the Python files and restart LibreChat to see changes:
```bash
docker restart LibreChat
```

## FSRS Algorithm

The server uses FSRS-4.5 parameters for scheduling:
- Initial reviews: Cards start with short intervals
- Adaptive scheduling: Intervals adjust based on your performance
- Difficulty tracking: Cards become easier or harder based on your ratings
- Lapse handling: Failed cards get shorter intervals for re-learning

## Troubleshooting

### Check MCP Server Status
```bash
docker logs LibreChat 2>&1 | grep -i mcp
```

### Verify Tools are Available
Look for: `[MCP][spaced-repetition] ✓ Initialized`

### Common Issues

1. **MCP server not showing**: Ensure `agents` is in your ENDPOINTS in `.env`
2. **Tools not available**: Check that `librechat.yaml` is properly mounted
3. **Data not persisting**: Verify the volume is created with `docker volume ls`

## License

MIT