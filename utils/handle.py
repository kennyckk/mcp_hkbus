"""
Shared helper implementations for KMB MCP server.

These functions are pure implementations and depend on injected
callables and values so that callers (e.g., kmb_mcp.py) can control
HTTP clients, caching, constants, and allow easy test patching.
"""

from typing import Any, Awaitable, Callable, Dict, List, Optional

import httpx


async def fetch_api(url: str, http_client: httpx.AsyncClient) -> Dict:
    """
    Fetch data from an API endpoint using the provided http_client.
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


async def get_cached_data(
    cache_key: str,
    url: str,
    fetch_api_func: Callable[[str], Awaitable[Dict]],
    cache: Dict[str, Any],
) -> Dict:
    """
    Get data from cache or fetch it if not available using the provided
    fetch function and cache store.
    """
    if cache.get(cache_key) is None:
        data = await fetch_api_func(url)
        cache[cache_key] = data
    return cache[cache_key]


async def get_route_list(
    get_cached_data_func: Callable[[str, str], Awaitable[Dict]],
    route_list_url: str,
) -> List:
    data = await get_cached_data_func("route_list", route_list_url)
    if "data" in data:
        return data["data"]
    return []


async def get_stop_list(
    get_cached_data_func: Callable[[str, str], Awaitable[Dict]],
    stop_list_url: str,
) -> List:
    data = await get_cached_data_func("stop_list", stop_list_url)
    if "data" in data:
        return data["data"]
    return []


async def get_route_stop_list(
    get_cached_data_func: Callable[[str, str], Awaitable[Dict]],
    route_stop_list_url: str,
) -> List:
    data = await get_cached_data_func("route_stop_list", route_stop_list_url)
    if "data" in data:
        return data["data"]
    return []


async def get_route_details(
    route: str,
    direction: Optional[str],
    service_type: str,
    *,
    get_route_list_func: Callable[[], Awaitable[List]],
    fetch_api_func: Callable[[str], Awaitable[Dict]],
    route_url: str,
) -> Any:
    if direction is None:
        routes = await get_route_list_func()
        route_data = [r for r in routes if r["route"] == route]
        return route_data

    url = f"{route_url}/{route}/{direction}/{service_type}"
    return await fetch_api_func(url)


async def get_stop_details(
    stop_id: str,
    *,
    fetch_api_func: Callable[[str], Awaitable[Dict]],
    stop_url: str,
) -> Dict:
    url = f"{stop_url}/{stop_id}"
    return await fetch_api_func(url)


async def get_route_stops(
    route: str,
    direction: str,
    service_type: str,
    *,
    fetch_api_func: Callable[[str], Awaitable[Dict]],
    route_stop_url: str,
) -> List:
    direction_full = "inbound" if direction == "I" else "outbound"
    url = f"{route_stop_url}/{route}/{direction_full}/{service_type}"
    response = await fetch_api_func(url)
    if "data" in response:
        return response["data"]
    return []


async def get_eta(
    stop_id: str,
    route: Optional[str],
    service_type: str,
    *,
    fetch_api_func: Callable[[str], Awaitable[Dict]],
    eta_url: str,
    stop_eta_url: str,
) -> List:
    if route:
        url = f"{eta_url}/{stop_id}/{route}/{service_type}"
    else:
        url = f"{stop_eta_url}/{stop_id}"

    response = await fetch_api_func(url)
    if "data" in response:
        return response["data"]
    return []


async def find_stops_by_name(
    name: str,
    *,
    get_stop_list_func: Callable[[], Awaitable[List]],
) -> List:
    stops = await get_stop_list_func()
    matching_stops: List[Dict[str, Any]] = []

    for stop in stops:
        if (
            name.lower() in stop["name_en"].lower()
            or (stop.get("name_tc") and name.lower() in stop["name_tc"].lower())
        ):
            matching_stops.append(stop)

    return matching_stops


async def find_routes_by_destination(
    destination: str,
    *,
    get_route_list_func: Callable[[], Awaitable[List]],
) -> List:
    routes = await get_route_list_func()
    matching_routes: List[Dict[str, Any]] = []

    for route in routes:
        if (
            destination.lower() in route["dest_en"].lower()
            or (
                route.get("dest_tc")
                and destination.lower() in route["dest_tc"].lower()
            )
        ):
            matching_routes.append(route)

    return matching_routes

