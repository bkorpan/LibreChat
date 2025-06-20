FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application
COPY . .

# Install the package
RUN pip install --no-cache-dir -e .

# Create data directory
RUN mkdir -p /data

# Set environment variable for data path
ENV SPACED_REPETITION_DATA_PATH=/data/cards.json

# Run the MCP server
CMD ["python", "-m", "mcp_spaced_repetition.server"]