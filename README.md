# KMB Bus MCP Server

A Model Context Protocol (MCP) server that provides real-time access to Hong Kong's KMB (九龍巴士) and Long Win Bus (龍運巴士) route information and arrival times. This server enables Language Models to query Hong Kong bus service information to answer user questions about bus routes, stops, and estimated arrival times.

## Features

- Real-time bus arrival information (ETA)
- Comprehensive bus route queries
- Bus stop information and searches
- Route-stop mapping
- Caching system to optimize API calls
- Bilingual support (English and Traditional Chinese)

## Data Source

This project utilizes the official KMB/LWB Open Data API:

- Base URL: https://data.etabus.gov.hk/v1/transport/kmb
- [KMB Open Data API Documentation](https://data.etabus.gov.hk/documentation/overview)

## Prerequisites

- Python 3.10 or higher
- uv package manager

## Installation

1. First, install uv if you haven't already:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Clone the repository:

```bash
git clone https://github.com/yourusername/kmb-mcp-server.git
cd kmb-mcp-server
```

3. Use uv to handle the python package:

```bash
uv sync #using uv.lock
```

## Usage

1. Edit the Config in your MCP Client (e.g. Claude Desktop):

```json
{
  "mcpServers": {
    "bus_service": {
      "command": "path/to/uv.exe",
      "args": ["--directory", "path/to/kmb_bus", "run", "kmb_mcp.py"],
      "background": true
    }
  }
}
```

2. The server provides several tools that can be used by Language Models to query bus information:

- `get_route_list()`: Get a list of all bus routes
- `get_stop_list()`: Get a list of all bus stops
- `get_route_stops()`: Get stops for a specific route
- `find_stops_by_name()`: Search for bus stops by name
- `get_all_routes_at_stop()`: Get all routes serving a specific stop
- `get_eta()`: Get estimated arrival times

## Testing

Run the test suite using pytest:

```bash
pytest test/kmb-mcp-tests.py
```

## Dependencies

- `httpx`: For async HTTP requests
- `fastmcp`: For MCP server implementation
- `pytest`: For testing (development only)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Acknowledgments

- KMB/LWB for providing the open data API
- The MCP protocol developers

## Note

This service relies on the KMB/LWB Open Data API. Please be mindful of API rate limits and implement appropriate error handling in production environments.
