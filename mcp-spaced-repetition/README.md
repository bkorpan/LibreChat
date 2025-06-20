# MCP Spaced Repetition Server

An MCP (Model Context Protocol) server that implements a spaced repetition learning system for LibreChat. It uses the FSRS (Free Spaced Repetition Scheduler) algorithm to optimize learning intervals.

## Features

- **Two Card Types**:
  - **Fact Cards**: Simple question-answer pairs
  - **Concept Cards**: AI generates varied questions to test understanding
  
- **FSRS Scheduling**: Advanced spaced repetition algorithm for optimal learning intervals
- **JSON Storage**: Persistent storage with configurable location
- **Docker Integration**: Seamlessly integrates with LibreChat's Docker setup

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
Update a card after review or modify its content.

**Parameters**:
- `card_id` (required): ID of the card to update
- `rating` (optional): Difficulty rating (1=Again, 2=Hard, 3=Good, 4=Easy)
- `question` (optional): Updated question (fact cards only)
- `answer` (optional): Updated answer (fact cards only)
- `concept` (optional): Updated concept (concept cards only)

## Installation

### Option 1: Docker (Recommended for LibreChat)

1. Clone or copy the `mcp-spaced-repetition` directory
2. Build and run with Docker Compose:
   ```bash
   cd mcp-spaced-repetition
   docker-compose up -d
   ```

3. Add to your `librechat.yaml`:
   ```yaml
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
       description: "Spaced repetition learning system"
   ```

### Option 2: Local Installation

1. Install the package:
   ```bash
   cd mcp-spaced-repetition
   pip install -e .
   ```

2. Add to your `librechat.yaml`:
   ```yaml
   mcpServers:
     spaced-repetition:
       type: stdio
       command: python
       args:
         - -m
         - mcp_spaced_repetition.server
       env:
         SPACED_REPETITION_DATA_PATH: /path/to/cards.json
   ```

## Configuration

### Environment Variables

- `SPACED_REPETITION_DATA_PATH`: Path to the JSON file for storing cards (default: `~/.mcp-spaced-repetition/cards.json`)

### Docker Volumes

The Docker setup uses a named volume `mcp-spaced-repetition-data` to persist cards between container restarts.

## Usage Examples

### Adding Cards

**Fact Card**:
```
"Please add a fact card: 
Q: What is the capital of France? 
A: Paris"
```

**Concept Card**:
```
"Add a concept card about the principle of recursion in programming"
```

### Reviewing Cards

```
"Show me the next card to review"
"I found that question hard" (rating: 2)
"That was easy" (rating: 4)
```

### Managing Cards

```
"Update the wording of the last card"
"Remove that card"
"Show me 5 cards that are due"
```

## FSRS Algorithm

The server uses FSRS-4.5 parameters for scheduling:
- Initial reviews: Cards start with short intervals
- Adaptive scheduling: Intervals adjust based on your performance
- Difficulty tracking: Cards become easier or harder based on your ratings
- Lapse handling: Failed cards get shorter intervals for re-learning

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
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── pyproject.toml
└── README.md
```

### Running Tests
```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest
```

## License

MIT