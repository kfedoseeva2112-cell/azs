import math
import aiohttp
import logging
import asyncio
import time

logger = logging.getLogger(__name__)

def calculate_distance(lat1, lon1, lat2, lon2):
    """Расчет расстояния по формуле гаверсинусов"""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def get_distance(lat1, lon1, lat2, lon2):
    return calculate_distance(lat1, lon1, lat2, lon2)

async def get_address_from_coords(lat, lon, retries=3, delay=1):
    """Получение адреса через Nominatim в формате: Город, Улица, Дом"""
    url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&addressdetails=1"
    headers = {'User-Agent': 'AZS_Bot/1.0'}
    for i in range(retries):
        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        addr = data.get("address", {})
                        
                        city = addr.get("city") or addr.get("town") or addr.get("village") or addr.get("state")
                        street = addr.get("road") or "Неизвестная улица"
                        house = addr.get("house_number") or ""
                        
                        address_parts = []
                        
                        # Приоритет: Город, Улица, Дом
                        if city:
                            address_parts.append(city)
                        
                        if street and street != "Неизвестная улица":
                            address_parts.append(street)
                        
                        if house:
                            address_parts.append(house)
                        
                        # Если нет города, улицы или дома, пытаемся использовать другие компоненты
                        if not address_parts:
                            if addr.get("suburb"):
                                address_parts.append(addr.get("suburb"))
                            if addr.get("county"):
                                address_parts.append(addr.get("county"))
                            if addr.get("state") and addr.get("state") != city: # Избегаем дублирования
                                address_parts.append(addr.get("state"))
                            if addr.get("country") and addr.get("country") != "Россия":
                                address_parts.append(addr.get("country"))

                        if address_parts:
                            return ", ".join(address_parts)
                        else:
                            return f"{lat}, {lon}" # Крайний случай, если ничего не найдено
                    elif response.status == 429: # Too Many Requests
                        logger.warning(f"Nominatim API rate limit hit for {lat}, {lon}. Retrying in {delay} seconds...")
                        await asyncio.sleep(delay)
                        delay *= 2 # Exponential backoff
                    else:
                        logger.error(f"Nominatim API error: {response.status} for {lat}, {lon}")
                        return f"{lat}, {lon}"
        except aiohttp.ClientError as e:
            logger.error(f"Network error during geocoding for {lat}, {lon}: {e}. Retrying in {delay} seconds...")
            await asyncio.sleep(delay)
            delay *= 2 # Exponential backoff
        except Exception as e:
            logger.error(f"Geocoding error for {lat}, {lon}: {e}")
            return f"{lat}, {lon}"
    logger.error(f"Failed to get address for {lat}, {lon} after {retries} retries.")
    return f"{lat}, {lon}"
