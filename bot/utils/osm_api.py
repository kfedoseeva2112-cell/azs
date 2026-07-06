import aiohttp
import asyncio
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"
_address_cache = {}

async def search_stations_nearby(lat: float, lon: float, radius_km: float = 3.0, limit: int = 20) -> List[Dict[str, Any]]:
    radius_m = radius_km * 1000
    query = f"""
    [out:json];
    node(around:{radius_m},{lat},{lon})[amenity=fuel];
    out body;
    """
    params = {'data': query}
    headers = {'User-Agent': 'AZS_Bot/1.0'}

    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(OVERPASS_URL, params=params, timeout=30) as response:
                if response.status == 200:
                    data = await response.json()
                    elements = data.get('elements', [])
                    stations = []
                    for node in elements[:limit]:
                        lat_node = node.get('lat')
                        lon_node = node.get('lon')
                        if lat_node is None or lon_node is None:
                            continue
                        tags = node.get('tags', {})
                        name = tags.get('name', 'АЗС без названия')
                        address = await get_address_from_coords(lat_node, lon_node)
                        stations.append({
                            'lat': lat_node,
                            'lon': lon_node,
                            'name': name,
                            'address': address,
                            'tags': tags
                        })
                        await asyncio.sleep(1)  # задержка для Nominatim
                    return stations
                else:
                    logger.error(f"Overpass API error: {response.status}")
                    return []
    except Exception as e:
        logger.error(f"Error in search_stations_nearby: {e}")
        return []

async def get_address_from_coords(lat: float, lon: float) -> str:
    cache_key = f"{lat:.5f},{lon:.5f}"
    if cache_key in _address_cache:
        return _address_cache[cache_key]

    params = {'format': 'json', 'lat': lat, 'lon': lon, 'addressdetails': 1}
    headers = {'User-Agent': 'AZS_Bot/1.0'}

    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(NOMINATIM_URL, params=params, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    addr = data.get('address', {})
                    city = addr.get('city') or addr.get('town') or addr.get('village') or addr.get('state')
                    street = addr.get('road') or ''
                    house = addr.get('house_number') or ''
                    parts = [p for p in [city, street, house] if p]
                    address = ', '.join(parts) if parts else f"{lat}, {lon}"
                    _address_cache[cache_key] = address
                    return address
                else:
                    return f"{lat}, {lon}"
    except Exception:
        return f"{lat}, {lon}"
