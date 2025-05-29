#!/usr/bin/env python
"""
KMB Bus MCP Server

This server provides tools to query KMB bus information through MCP.
"""

import asyncio
import json
from typing import Dict, List, Optional, Any, Union
import httpx
from mcp.server.fastmcp import FastMCP

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
    """
    Fetch data from an API endpoint
    """
    try:
        response = await http_client.get(url)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        return {"error": f"HTTP error: {e}"}
    except httpx.RequestError as e:
        return {"error": f"Request error: {e}"}
    except Exception as e:
        return {"error": f"Unexpected error: {e}"}

async def get_cached_data(cache_key: str, url: str) -> Dict:
    """
    Get data from cache or fetch it if not available
    """
    if cache.get(cache_key) is None:
        data = await fetch_api(url)
        cache[cache_key] = data
    return cache[cache_key]

async def get_route_list() -> List:
    """
    Get list of all KMB bus routes
    """
    data = await get_cached_data("route_list", ROUTE_LIST_URL)
    if "data" in data:
        return data["data"]
    return []

async def get_stop_list() -> List:
    """
    Get list of all KMB bus stops
    """
    data = await get_cached_data("stop_list", STOP_LIST_URL)
    if "data" in data:
        return data["data"]
    return []

async def get_route_stop_list() -> List:
    """
    Get list of all route-stop combinations
    """
    data = await get_cached_data("route_stop_list", ROUTE_STOP_LIST_URL)
    if "data" in data:
        return data["data"]
    return []

async def get_route_details(route: str, direction: str = None, service_type: str = "1") -> Dict:
    """
    Get details for a specific route
    """
    if direction is None:
        # If direction is not specified, get all directions for this route
        routes = await get_route_list()
        route_data = [r for r in routes if r["route"] == route]
        return route_data
    
    url = f"{ROUTE_URL}/{route}/{direction}/{service_type}"
    return await fetch_api(url)

async def get_stop_details(stop_id: str) -> Dict:
    """
    Get details for a specific stop
    """
    url = f"{STOP_URL}/{stop_id}"
    return await fetch_api(url)

async def get_route_stops(route: str, direction: str, service_type: str = "1") -> List:
    """
    Get stops for a specific route
    """
    # Convert direction code to full form
    direction_full = "inbound" if direction == "I" else "outbound"
    url = f"{ROUTE_STOP_URL}/{route}/{direction_full}/{service_type}"
    response = await fetch_api(url)
    if "data" in response:
        return response["data"]
    return []

async def get_eta(stop_id: str, route: str = None, service_type: str = "1") -> List:
    """
    Get ETA for a stop and optionally a specific route
    """
    if route:
        url = f"{ETA_URL}/{stop_id}/{route}/{service_type}"
    else:
        url = f"{STOP_ETA_URL}/{stop_id}"
    
    response = await fetch_api(url)
    if "data" in response:
        return response["data"]
    return []

async def find_stops_by_name(name: str) -> List:
    """
    Find stops by name (partial match)
    """
    stops = await get_stop_list()
    matching_stops = []
    
    for stop in stops:
        if (name.lower() in stop["name_en"].lower() or 
            (stop.get("name_tc") and name.lower() in stop["name_tc"].lower())):
            matching_stops.append(stop)
    
    return matching_stops

async def find_routes_by_destination(destination: str) -> List:
    """
    Find routes that go to a specific destination
    """
    routes = await get_route_list()
    matching_routes = []
    
    for route in routes:
        if (destination.lower() in route["dest_en"].lower() or 
            (route.get("dest_tc") and destination.lower() in route["dest_tc"].lower())):
            matching_routes.append(route)
    
    return matching_routes

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

if __name__ == "__main__":
    mcp.run(transport='stdio')