#!/usr/bin/env python
"""
KMB Bus MCP Server

This server provides tools to query KMB bus information through MCP.
"""
import httpx
import os
import logging
import uvicorn

from typing import Dict, List, Optional, Any, Union
from mcp.server.fastmcp import FastMCP
from starlette.middleware.cors import CORSMiddleware
from utils import handle as handle_utils


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize MCP server
mcp = FastMCP("kmb-bus")

# API endpoints
BASE_URL = "https://data.etabus.gov.hk/v1/transport/kmb"
ROUTE_LIST_URL = f"{BASE_URL}/route/"
ROUTE_URL = f"{BASE_URL}/route"
STOP_LIST_URL = f"{BASE_URL}/stop"
STOP_URL = f"{BASE_URL}/stop"
ROUTE_STOP_LIST_URL = f"{BASE_URL}/route-stop"
ROUTE_STOP_URL = f"{BASE_URL}/route-stop"
ETA_URL = f"{BASE_URL}/eta"
STOP_ETA_URL = f"{BASE_URL}/stop-eta"
ROUTE_ETA_URL = f"{BASE_URL}/route-eta"

# HTTP client
http_client = httpx.AsyncClient(timeout=30.0)

# Cache for API responses to avoid redundant calls
cache = {
    "route_list": None,
    "stop_list": None,
    "route_stop_list": None,
    "last_update": None
}

async def fetch_api(url: str) -> Dict:
    """Delegate to shared implementation with injected http_client."""
    return await handle_utils.fetch_api(url, http_client)

async def get_cached_data(cache_key: str, url: str) -> Dict:
    """Delegate to shared implementation with injected fetch and cache."""
    return await handle_utils.get_cached_data(
        cache_key,
        url,
        fetch_api_func=fetch_api,
        cache=cache,
    )

async def get_route_list() -> List:
    """Delegate to shared implementation; keep signature for tests."""
    return await handle_utils.get_route_list(
        get_cached_data_func=get_cached_data,
        route_list_url=ROUTE_LIST_URL,
    )

async def get_stop_list() -> List:
    """Delegate to shared implementation; keep signature for tests."""
    return await handle_utils.get_stop_list(
        get_cached_data_func=get_cached_data,
        stop_list_url=STOP_LIST_URL,
    )

async def get_route_stop_list() -> List:
    """Delegate to shared implementation; keep signature for tests."""
    return await handle_utils.get_route_stop_list(
        get_cached_data_func=get_cached_data,
        route_stop_list_url=ROUTE_STOP_LIST_URL,
    )

async def get_route_details(route: str, direction: str = None, service_type: str = "1") -> Dict:
    """Delegate to shared implementation; keep signature for tests."""
    return await handle_utils.get_route_details(
        route,
        direction,
        service_type,
        get_route_list_func=get_route_list,
        fetch_api_func=fetch_api,
        route_url=ROUTE_URL,
    )

async def get_stop_details(stop_id: str) -> Dict:
    """Delegate to shared implementation; keep signature for tests."""
    return await handle_utils.get_stop_details(
        stop_id,
        fetch_api_func=fetch_api,
        stop_url=STOP_URL,
    )

async def get_route_stops(route: str, direction: str, service_type: str = "1") -> List:
    """Delegate to shared implementation; keep signature for tests."""
    return await handle_utils.get_route_stops(
        route,
        direction,
        service_type,
        fetch_api_func=fetch_api,
        route_stop_url=ROUTE_STOP_URL,
    )

async def get_eta(stop_id: str, route: str = None, service_type: str = "1") -> List:
    """Delegate to shared implementation; keep signature for tests."""
    return await handle_utils.get_eta(
        stop_id,
        route,
        service_type,
        fetch_api_func=fetch_api,
        eta_url=ETA_URL,
        stop_eta_url=STOP_ETA_URL,
    )

async def find_stops_by_name(name: str) -> List:
    """Delegate to shared implementation; keep signature for tests."""
    return await handle_utils.find_stops_by_name(
        name,
        get_stop_list_func=get_stop_list,
    )

async def find_routes_by_destination(destination: str) -> List:
    """Delegate to shared implementation; keep signature for tests."""
    return await handle_utils.find_routes_by_destination(
        destination,
        get_route_list_func=get_route_list,
    )

@mcp.tool()
async def get_next_bus(route: str, stop_name: str) -> str:
    """Get the next arrival time for a specified bus route at a stop.
    
    Args:
        route: The bus route number (e.g., "1A", "6", "960")
        stop_name: The name of the bus stop
    """
    # Find the stop ID by name
    stops = await find_stops_by_name(stop_name)
    
    if not stops:
        return f"Could not find any stops matching '{stop_name}'"
    
    results = []
    for stop in stops:
        stop_id = stop["stop"]
        stop_name_en = stop["name_en"]
        
        # Get ETA data
        eta_data = await get_eta(stop_id, route)

        
        if not eta_data:
            results.append(f"No arrival data available for route {route} at stop '{stop_name_en}' ({stop_id})")
            continue
        
        # Filter ETAs for the specified route
        route_etas = [eta for eta in eta_data if eta["route"] == route]
        
        if not route_etas:
            results.append(f"No scheduled arrivals for route {route} at stop '{stop_name_en}' ({stop_id})")
            continue
        
        # Format ETA information
        stop_results = [f"Arrivals for route {route} at '{stop_name_en}' ({stop_id}):"]
        
        for eta in route_etas:
            eta_time = eta.get("eta", None)
            if eta_time :
                eta_time = eta_time.split("+")[0].replace("T", " ")  # Format the timestamp
            
            dest = eta.get("dest_tc", "") or eta.get("dest_en", "Unknown destination")
            remark = eta.get("rmk_tc", "") or eta.get("rmk_en", "")
            
            if remark:
                stop_results.append(f"- {eta_time} to {dest} ({remark})")
            else:
                stop_results.append(f"- {eta_time} to {dest}")
        
        results.append("\n".join(stop_results))
    
    return "\n\n".join(results)

@mcp.tool()
async def find_buses_to_destination(destination: str) -> str:
    """Find bus routes that go to a specified destination.
    
    Args:
        destination: The destination to search for (e.g., "Central", "Mong Kok", "Airport")
    """
    matching_routes = await find_routes_by_destination(destination)
    
    if not matching_routes:
        return f"Could not find any routes going to '{destination}'"
    
    # Group routes by origin for better readability
    routes_by_origin = {}
    
    for route in matching_routes:
        origin = route.get("orig_en", "Unknown")
        if origin not in routes_by_origin:
            routes_by_origin[origin] = []
        
        routes_by_origin[origin].append({
            "route": route["route"],
            "destination": route.get("dest_en", "Unknown"),
            "bound": "Inbound" if route["bound"] == "I" else "Outbound"
        })
    
    # Format the results
    results = [f"Bus routes going to '{destination}':"]
    
    for origin, routes in routes_by_origin.items():
        results.append(f"\nFrom {origin}:")
        for route_info in routes:
            results.append(f"- Route {route_info['route']} to {route_info['destination']} ({route_info['bound']})")
    
    return "\n".join(results)

@mcp.tool()
async def get_route_stops_info(route: str) -> str:
    """Get all stops along a specified bus route.
    
    Args:
        route: The bus route number (e.g., "1A", "6", "960")
    """
    # Get all directions for this route
    route_details = await get_route_details(route)
    
    if not route_details:
        return f"Could not find information for route {route}"
    
    results = []
    
    for direction_info in route_details:
        direction = direction_info["bound"]
        service_type = direction_info["service_type"]
        origin = direction_info.get("orig_en", "Unknown")
        destination = direction_info.get("dest_en", "Unknown")
        
        direction_text = "Inbound" if direction == "I" else "Outbound"
        results.append(f"Route {route} {direction_text} from {origin} to {destination}:")
        
        # Get stops for this direction
        stops_data = await get_route_stops(route, direction, service_type)
        
        if not stops_data:
            results.append("  No stop information available")
            continue
        
        # Sort stops by sequence
        stops_data.sort(key=lambda x: x.get("seq", 0))
        
        # Get full stop details for each stop
        stop_details = []
        for stop_data in stops_data:
            stop_id = stop_data["stop"]
            stop_info = await get_stop_details(stop_id)
            
            if "data" in stop_info:
                stop_details.append({
                    "seq": stop_data.get("seq", 0),
                    "stop_id": stop_id,
                    "name": stop_info["data"].get("name_en", "Unknown"),
                    "lat": stop_info["data"].get("lat", 0),
                    "long": stop_info["data"].get("long", 0)
                })
        
        # Add stop information to results
        for i, stop in enumerate(stop_details, 1):
            results.append(f"  {i}. {stop['name']} (ID: {stop['stop_id']})")
    
    return "\n\n".join(results)

@mcp.tool()
async def find_stop_by_name(stop_name: str) -> str:
    """Find bus stops matching a name or partial name.
    
    Args:
        stop_name: Full or partial name of the bus stop to search for
    """
    stops = await find_stops_by_name(stop_name)
    
    if not stops:
        return f"Could not find any stops matching '{stop_name}'"
    
    results = [f"Found {len(stops)} stops matching '{stop_name}':"]
    
    for i, stop in enumerate(stops, 1):
        stop_id = stop["stop"]
        name_en = stop["name_en"]
        name_tc = stop.get("name_tc", "")
        lat = stop.get("lat", 0)
        lng = stop.get("long", 0)
        
        if name_tc:
            results.append(f"{i}. {name_en} ({name_tc})")
        else:
            results.append(f"{i}. {name_en}")
        results.append(f"   ID: {stop_id}")
        results.append(f"   Location: {lat}, {lng}")
    
    return "\n".join(results)

@mcp.tool()
async def get_all_routes_at_stop(stop_name: str) -> str:
    """Get all bus routes that pass through a specified bus stop.
    
    Args:
        stop_name: Name of the bus stop
    """
    # Find stops matching the name
    stops = await find_stops_by_name(stop_name)
    
    if not stops:
        return f"Could not find any stops matching '{stop_name}'"
    
    results = []
    
    for stop in stops:
        stop_id = stop["stop"]
        stop_name_en = stop["name_en"]
        
        # Get all route-stop combinations
        route_stops = await get_route_stop_list()
        
        # Filter for this stop
        stop_routes = [rs for rs in route_stops if rs["stop"] == stop_id]
        
        if not stop_routes:
            results.append(f"No routes found for stop '{stop_name_en}' ({stop_id})")
            continue
        
        # Group by route for better readability
        routes_info = {}
        for rs in stop_routes:
            route = rs["route"]
            bound = rs["bound"]
            service_type = rs["service_type"]
            
            key = f"{route}:{service_type}"
            if key not in routes_info:
                routes_info[key] = []
            routes_info[key].append(bound)
        
        # Format results
        stop_results = [f"Routes serving '{stop_name_en}' ({stop_id}):"]
        
        # Get full route information for each route
        for key, bounds in routes_info.items():
            route, service_type = key.split(":")
            route_data = await get_route_details(route)
            
            for r in route_data:
                if r["service_type"] == service_type and r["bound"] in bounds:
                    origin = r.get("orig_en", "Unknown")
                    dest = r.get("dest_en", "Unknown")
                    direction = "→" if r["bound"] == "O" else "←"
                    
                    stop_results.append(f"- Route {route}: {origin} {direction} {dest}")
        
        results.append("\n".join(stop_results))
    
    return "\n\n".join(results)

def main():
    transport_mode = os.getenv("TRANSPORT", "stdio")
    
    if transport_mode == "http":
        # HTTP mode with config extraction from URL parameters
        logger.info("Starting HKBUS MCP server in HTTP mode...")
        # Setup Starlette app with CORS for cross-origin requests
        app = mcp.streamable_http_app()
        
        # IMPORTANT: add CORS middleware for browser based clients
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["*"],
            expose_headers=["mcp-session-id", "mcp-protocol-version"],
            max_age=86400,
        )

        # Use Smithery-required PORT environment variable
        port = int(os.environ.get("PORT", 8011))
        print(f"Listening on port {port}")

        uvicorn.run(app, host="0.0.0.0", port=port, log_level="debug")
    
    else:
        # Optional: add stdio transport for backwards compatibility
        # You can publish this to uv for users to run locally
        logger.info("Starting HKBUS MCP server in STDIO mode...")
        # Run with stdio transport (default)
        mcp.run(transport='stdio')

if __name__ == "__main__":
    main()