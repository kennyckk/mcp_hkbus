#!/usr/bin/env python
"""
Unit tests for the KMB Bus MCP Server
"""
from pathlib import Path
from unittest.mock import patch, MagicMock

import asyncio
import json
import unittest
import httpx
import pytest

# Import the MCP server module - assuming it's saved as kmb_mcp.py
import sys
sys.path.append(Path("__file__").parent.parent.as_posix())
import kmb_mcp

# Mock data for testing
MOCK_ROUTE_LIST = {
    "type": "RouteList",
    "version": "1.0",
    "generated_timestamp": "2023-04-01T12:00:00+08:00",
    "data": [
        {
            "co": "KMB",
            "route": "1A",
            "bound": "O",
            "service_type": "1",
            "orig_en": "JORDAN",
            "orig_tc": "佐敦",
            "dest_en": "CENTRAL (HONG KONG STATION)",
            "dest_tc": "中環 (香港站)",
            "data_timestamp": "2023-04-01T12:00:00+08:00"
        },
        {
            "co": "KMB",
            "route": "1A",
            "bound": "I",
            "service_type": "1",
            "orig_en": "CENTRAL (HONG KONG STATION)",
            "orig_tc": "中環 (香港站)",
            "dest_en": "JORDAN",
            "dest_tc": "佐敦",
            "data_timestamp": "2023-04-01T12:00:00+08:00"
        },
        {
            "co": "KMB",
            "route": "960",
            "bound": "O",
            "service_type": "1",
            "orig_en": "TUEN MUN (TOWN CENTRE)",
            "orig_tc": "屯門 (市中心)",
            "dest_en": "AIRPORT (GROUND TRANSPORTATION CENTRE)",
            "dest_tc": "機場 (地面運輸中心)",
            "data_timestamp": "2023-04-01T12:00:00+08:00"
        }
    ]
}

MOCK_STOP_LIST = {
    "type": "StopList",
    "version": "1.0",
    "generated_timestamp": "2023-04-01T12:00:00+08:00",
    "data": [
        {
            "stop": "A3ADFCDF8487ADB9",
            "name_tc": "佐敦站",
            "name_en": "JORDAN STATION",
            "name_sc": "佐敦站",
            "lat": 22.304893,
            "long": 114.171997,
            "data_timestamp": "2023-04-01T12:00:00+08:00"
        },
        {
            "stop": "B7C80A855DF5F56E",
            "name_tc": "中環站",
            "name_en": "CENTRAL STATION",
            "name_sc": "中環站",
            "lat": 22.282039,
            "long": 114.158119,
            "data_timestamp": "2023-04-01T12:00:00+08:00"
        },
        {
            "stop": "HJ29876HWEF234XX",
            "name_tc": "旺角站",
            "name_en": "MONG KOK STATION",
            "name_sc": "旺角站",
            "lat": 22.319359,
            "long": 114.168815,
            "data_timestamp": "2023-04-01T12:00:00+08:00"
        }
    ]
}

MOCK_ROUTE_STOP_LIST = {
    "type": "RouteStopList",
    "version": "1.0",
    "generated_timestamp": "2023-04-01T12:00:00+08:00",
    "data": [
        {
            "co": "KMB",
            "route": "1A",
            "bound": "O",
            "service_type": "1",
            "seq": 1,
            "stop": "A3ADFCDF8487ADB9",
            "data_timestamp": "2023-04-01T12:00:00+08:00"
        },
        {
            "co": "KMB",
            "route": "1A",
            "bound": "O",
            "service_type": "1",
            "seq": 2,
            "stop": "B7C80A855DF5F56E",
            "data_timestamp": "2023-04-01T12:00:00+08:00"
        },
        {
            "co": "KMB",
            "route": "960",
            "bound": "O",
            "service_type": "1",
            "seq": 1,
            "stop": "HJ29876HWEF234XX",
            "data_timestamp": "2023-04-01T12:00:00+08:00"
        }
    ]
}

MOCK_STOP_DETAILS = {
    "type": "Stop",
    "version": "1.0",
    "generated_timestamp": "2023-04-01T12:00:00+08:00",
    "data": {
        "stop": "A3ADFCDF8487ADB9",
        "name_tc": "佐敦站",
        "name_en": "JORDAN STATION",
        "name_sc": "佐敦站",
        "lat": 22.304893,
        "long": 114.171997,
        "data_timestamp": "2023-04-01T12:00:00+08:00"
    }
}

MOCK_ROUTE_DETAILS = {
    "type": "Route",
    "version": "1.0",
    "generated_timestamp": "2023-04-01T12:00:00+08:00",
    "data": {
        "co": "KMB",
        "route": "1A",
        "bound": "O",
        "service_type": "1",
        "orig_en": "JORDAN",
        "orig_tc": "佐敦",
        "dest_en": "CENTRAL (HONG KONG STATION)",
        "dest_tc": "中環 (香港站)",
        "data_timestamp": "2023-04-01T12:00:00+08:00"
    }
}

MOCK_ROUTE_STOPS = {
    "type": "RouteStop",
    "version": "1.0",
    "generated_timestamp": "2023-04-01T12:00:00+08:00",
    "data": [
        {
            "co": "KMB",
            "route": "1A",
            "bound": "O",
            "service_type": "1",
            "seq": 1,
            "stop": "A3ADFCDF8487ADB9",
            "data_timestamp": "2023-04-01T12:00:00+08:00"
        },
        {
            "co": "KMB",
            "route": "1A",
            "bound": "O",
            "service_type": "1",
            "seq": 2,
            "stop": "B7C80A855DF5F56E",
            "data_timestamp": "2023-04-01T12:00:00+08:00"
        }
    ]
}

MOCK_ETA_DATA = {
    "type": "ETA",
    "version": "1.0",
    "generated_timestamp": "2023-04-01T12:00:00+08:00",
    "data": [
        {
            "co": "KMB",
            "route": "1A",
            "dir": "O",
            "service_type": "1",
            "seq": 1,
            "stop": "A3ADFCDF8487ADB9",
            "dest_tc": "中環 (香港站)",
            "dest_en": "CENTRAL (HONG KONG STATION)",
            "eta_seq": 1,
            "eta": "2023-04-01T12:10:00+08:00",
            "rmk_tc": "",
            "rmk_en": "",
            "data_timestamp": "2023-04-01T12:00:00+08:00"
        },
        {
            "co": "KMB",
            "route": "1A",
            "dir": "O",
            "service_type": "1",
            "seq": 1,
            "stop": "A3ADFCDF8487ADB9",
            "dest_tc": "中環 (香港站)",
            "dest_en": "CENTRAL (HONG KONG STATION)",
            "eta_seq": 2,
            "eta": "2023-04-01T12:25:00+08:00",
            "rmk_tc": "",
            "rmk_en": "",
            "data_timestamp": "2023-04-01T12:00:00+08:00"
        }
    ]
}

@pytest.mark.asyncio
async def test_fetch_api():
    """Test the fetch_api function"""
    with patch('httpx.AsyncClient.get') as mock_get:
        # Set up the mock
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = MOCK_ROUTE_LIST
        mock_get.return_value = mock_response
        
        # Call the function
        result = await kmb_mcp.fetch_api("https://example.com/api")
        
        # Verify the result
        assert result == MOCK_ROUTE_LIST
        mock_get.assert_called_once_with("https://example.com/api")

@pytest.mark.asyncio
async def test_get_route_list():
    """Test the get_route_list function"""
    with patch('kmb_mcp.get_cached_data') as mock_get_cached:
        # Set up the mock
        mock_get_cached.return_value = MOCK_ROUTE_LIST
        
        # Call the function
        result = await kmb_mcp.get_route_list()
        
        # Verify the result
        assert result == MOCK_ROUTE_LIST["data"]
        mock_get_cached.assert_called_once_with("route_list", kmb_mcp.ROUTE_LIST_URL)

@pytest.mark.asyncio
async def test_get_stop_list():
    """Test the get_stop_list function"""
    with patch('kmb_mcp.get_cached_data') as mock_get_cached:
        # Set up the mock
        mock_get_cached.return_value = MOCK_STOP_LIST
        
        # Call the function
        result = await kmb_mcp.get_stop_list()
        
        # Verify the result
        assert result == MOCK_STOP_LIST["data"]
        mock_get_cached.assert_called_once_with("stop_list", kmb_mcp.STOP_LIST_URL)

@pytest.mark.asyncio
async def test_get_route_stops():
    """Test the get_route_stops function"""
    with patch('kmb_mcp.fetch_api') as mock_fetch:
        # Set up the mock
        mock_fetch.return_value = MOCK_ROUTE_STOPS
        
        # Call the function
        result = await kmb_mcp.get_route_stops("1A", "O", "1")
        
        # Verify the result
        assert result == MOCK_ROUTE_STOPS["data"]
        mock_fetch.assert_called_once_with(f"{kmb_mcp.ROUTE_STOP_URL}/1A/outbound/1")

@pytest.mark.asyncio
async def test_get_stop_details():
    """Test the get_stop_details function"""
    with patch('kmb_mcp.fetch_api') as mock_fetch:
        # Set up the mock
        mock_fetch.return_value = MOCK_STOP_DETAILS
        
        # Call the function
        result = await kmb_mcp.get_stop_details("A3ADFCDF8487ADB9")
        
        # Verify the result
        assert result == MOCK_STOP_DETAILS
        mock_fetch.assert_called_once_with(f"{kmb_mcp.STOP_URL}/A3ADFCDF8487ADB9")

@pytest.mark.asyncio
async def test_get_eta():
    """Test the get_eta function"""
    with patch('kmb_mcp.fetch_api') as mock_fetch:
        # Set up the mock
        mock_fetch.return_value = MOCK_ETA_DATA
        
        # Call the function
        result = await kmb_mcp.get_eta("A3ADFCDF8487ADB9", "1A", "1")
        
        # Verify the result
        assert result == MOCK_ETA_DATA["data"]
        mock_fetch.assert_called_once_with(f"{kmb_mcp.ETA_URL}/A3ADFCDF8487ADB9/1A/1")

@pytest.mark.asyncio
async def test_find_stops_by_name():
    """Test the find_stops_by_name function"""
    with patch('kmb_mcp.get_stop_list') as mock_get_stops:
        # Set up the mock
        mock_get_stops.return_value = MOCK_STOP_LIST["data"]
        
        # Call the function
        result = await kmb_mcp.find_stops_by_name("JORDAN")
        
        # Verify the result
        assert len(result) == 1
        assert result[0]["name_en"] == "JORDAN STATION"
        
        # Test case insensitivity
        result_case_insensitive = await kmb_mcp.find_stops_by_name("jordan")
        assert len(result_case_insensitive) == 1
        assert result_case_insensitive[0]["name_en"] == "JORDAN STATION"
        
        # Test partial matching
        result_partial = await kmb_mcp.find_stops_by_name("station")
        assert len(result_partial) == 3  # All mock stops have "STATION" in their name

@pytest.mark.asyncio
async def test_find_routes_by_destination():
    """Test the find_routes_by_destination function"""
    with patch('kmb_mcp.get_route_list') as mock_get_routes:
        # Set up the mock
        mock_get_routes.return_value = MOCK_ROUTE_LIST["data"]
        
        # Call the function
        result = await kmb_mcp.find_routes_by_destination("CENTRAL")
        
        # Verify the result
        assert len(result) == 1
        assert result[0]["route"] == "1A"
        assert result[0]["bound"] == "O"
        
        # Test case insensitivity
        result_case_insensitive = await kmb_mcp.find_routes_by_destination("central")
        assert len(result_case_insensitive) == 1
        
        # Test partial matching
        result_partial = await kmb_mcp.find_routes_by_destination("AIRPORT")
        assert len(result_partial) == 1
        assert result_partial[0]["route"] == "960"

@pytest.mark.asyncio
async def test_get_next_bus():
    """Test the get_next_bus tool"""
    with patch('kmb_mcp.find_stops_by_name') as mock_find_stops, \
         patch('kmb_mcp.get_eta') as mock_get_eta:
        # Set up the mocks
        mock_find_stops.return_value = [MOCK_STOP_LIST["data"][0]]  # Jordan Station
        mock_get_eta.return_value = MOCK_ETA_DATA["data"]
        
        # Call the function
        result = await kmb_mcp.get_next_bus("1A", "JORDAN")
        
        # Verify the result
        assert "Arrivals for route 1A at 'JORDAN STATION'" in result
        assert "12:10:00" in result  # First ETA time
        assert "12:25:00" in result  # Second ETA time

@pytest.mark.asyncio
async def test_find_buses_to_destination():
    """Test the find_buses_to_destination tool"""
    with patch('kmb_mcp.find_routes_by_destination') as mock_find_routes:
        # Set up the mock
        mock_find_routes.return_value = [MOCK_ROUTE_LIST["data"][0]]  # 1A to Central
        
        # Call the function
        result = await kmb_mcp.find_buses_to_destination("CENTRAL")
        
        # Verify the result
        assert "Bus routes going to 'CENTRAL'" in result
        assert "Route 1A" in result
        assert "JORDAN" in result  # Origin

@pytest.mark.asyncio
async def test_get_route_stops_info():
    """Test the get_route_stops_info tool"""
    with patch('kmb_mcp.get_route_details') as mock_get_route_details, \
         patch('kmb_mcp.get_route_stops') as mock_get_route_stops, \
         patch('kmb_mcp.get_stop_details') as mock_get_stop_details:
        # Set up the mocks
        mock_get_route_details.return_value = [MOCK_ROUTE_LIST["data"][0]]  # 1A outbound
        mock_get_route_stops.return_value = MOCK_ROUTE_STOPS["data"]
        mock_get_stop_details.side_effect = [
            {"data": MOCK_STOP_LIST["data"][0]},  # Jordan for first stop
            {"data": MOCK_STOP_LIST["data"][1]}   # Central for second stop
        ]
        
        # Call the function
        result = await kmb_mcp.get_route_stops_info("1A")
        
        # Verify the result
        assert "Route 1A Outbound from JORDAN to CENTRAL" in result
        assert "JORDAN STATION" in result
        assert "CENTRAL STATION" in result

@pytest.mark.asyncio
async def test_find_stop_by_name():
    """Test the find_stop_by_name tool"""
    with patch('kmb_mcp.find_stops_by_name') as mock_find_stops:
        # Set up the mock
        mock_find_stops.return_value = [MOCK_STOP_LIST["data"][0]]  # Jordan Station
        
        # Call the function
        result = await kmb_mcp.find_stop_by_name("JORDAN")
        
        # Verify the result
        assert "Found 1 stops matching 'JORDAN'" in result
        assert "JORDAN STATION" in result
        assert "A3ADFCDF8487ADB9" in result  # Stop ID

@pytest.mark.asyncio
async def test_get_all_routes_at_stop():
    """Test the get_all_routes_at_stop tool"""
    with patch('kmb_mcp.find_stops_by_name') as mock_find_stops, \
         patch('kmb_mcp.get_route_stop_list') as mock_get_route_stop_list, \
         patch('kmb_mcp.get_route_details') as mock_get_route_details:
        # Set up the mocks
        mock_find_stops.return_value = [MOCK_STOP_LIST["data"][0]]  # Jordan Station
        mock_get_route_stop_list.return_value = [MOCK_ROUTE_STOP_LIST["data"][0]]  # 1A at Jordan
        mock_get_route_details.return_value = [MOCK_ROUTE_LIST["data"][0]]  # 1A outbound
        
        # Call the function
        result = await kmb_mcp.get_all_routes_at_stop("JORDAN")
        
        # Verify the result
        assert "Routes serving 'JORDAN STATION'" in result
        assert "Route 1A: JORDAN → CENTRAL" in result

# Integration test - requires actual API access
@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_api_access():
    """Test access to the real KMB API - only runs when explicitly requested"""
    # Reset any cache
    kmb_mcp.cache = {
        "route_list": None,
        "stop_list": None, 
        "route_stop_list": None,
        "last_update": None
    }
    
    # Test basic API access
    routes = await kmb_mcp.get_route_list()
    assert isinstance(routes, list)
    assert len(routes) > 0
    assert "route" in routes[0]
    
    # Test stop list API
    stops = await kmb_mcp.get_stop_list()
    assert isinstance(stops, list)
    assert len(stops) > 0
    assert "stop" in stops[0]
    
    # Pick a route and test route-specific functions
    test_route = routes[0]["route"]
    route_details = await kmb_mcp.get_route_details(test_route)
    assert isinstance(route_details, list)
    
    # Pick a stop and test ETA
    test_stop = stops[0]["stop"]
    eta_data = await kmb_mcp.get_eta(test_stop)
    assert isinstance(eta_data, list)
    
    # The ETA might be empty if there are no buses scheduled
    # so we don't assert on its contents

if __name__ == '__main__':
    pytest.main(['-xvs'])