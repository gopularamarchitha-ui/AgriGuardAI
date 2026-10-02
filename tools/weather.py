import requests

# City coordinate lookup cache / fallbacks
CITY_COORDINATES = {
    "hyderabad": {"lat": 17.3850, "lon": 78.4867, "name": "Hyderabad"},
    "delhi": {"lat": 28.6139, "lon": 77.2090, "name": "Delhi"},
    "mumbai": {"lat": 19.0760, "lon": 72.8777, "name": "Mumbai"},
    "bengaluru": {"lat": 12.9716, "lon": 77.5946, "name": "Bengaluru"},
    "vijayawada": {"lat": 16.5062, "lon": 80.6480, "name": "Vijayawada"},
    "guntur": {"lat": 16.3067, "lon": 80.4365, "name": "Guntur"},
    "warangal": {"lat": 17.9689, "lon": 79.5941, "name": "Warangal"},
    "visakhapatnam": {"lat": 17.6868, "lon": 83.2185, "name": "Visakhapatnam"}
}

def get_weather(city="Hyderabad"):
    """
    Fetches real-time weather metrics using Open-Meteo API.
    Returns: dict containing city, temperature (°C), humidity (%), precipitation (mm), status.
    Uses weather ONLY as contextual background (does not claim weather proves disease existence).
    """
    city_clean = city.strip().lower()

    # Geocoding via Open-Meteo or fallback cache
    lat, lon, city_display = None, None, city
    if city_clean in CITY_COORDINATES:
        lat = CITY_COORDINATES[city_clean]["lat"]
        lon = CITY_COORDINATES[city_clean]["lon"]
        city_display = CITY_COORDINATES[city_clean]["name"]
    else:
        try:
            geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=en&format=json"
            resp = requests.get(geo_url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                if "results" in data and len(data["results"]) > 0:
                    res = data["results"][0]
                    lat = res["latitude"]
                    lon = res["longitude"]
                    city_display = res["name"]
        except Exception as e:
            print(f"[Weather Tool] Geocoding exception for '{city}': {e}")

    if lat is None or lon is None:
        # Default fallback to Hyderabad
        lat, lon = 17.3850, 78.4867
        city_display = city

    try:
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,precipitation&current_weather=true"
        resp = requests.get(weather_url, timeout=5)
        if resp.status_code == 200:
            wdata = resp.json()
            current = wdata.get("current", {})
            curr_weather = wdata.get("current_weather", {})

            temp = current.get("temperature_2m", curr_weather.get("temperature", 28.0))
            humidity = current.get("relative_humidity_2m", 75.0)
            precip = current.get("precipitation", 0.0)

            return {
                "status": "AVAILABLE",
                "city": city_display,
                "temperature_c": round(float(temp), 1),
                "humidity_percent": round(float(humidity), 1),
                "precipitation_mm": round(float(precip), 1),
                "summary": f"{temp}°C, {humidity}% humidity, {precip}mm rainfall"
            }
    except Exception as e:
        print(f"[Weather Tool] Failed to query Open-Meteo weather API: {e}")

    # Soft fallback if API call fails
    return {
        "status": "UNAVAILABLE",
        "city": city_display,
        "temperature_c": 28.0,
        "humidity_percent": 75.0,
        "precipitation_mm": 0.0,
        "summary": "Weather data currently unavailable (using seasonal defaults)."
    }
