from datetime import datetime
from typing import Dict
import requests


def weather(**kwargs) -> Dict:
    try:
        url = f'https://api.open-meteo.com/v1/forecast' \
              f'?latitude={kwargs["latitude"]}' \
              f'&longitude={kwargs["longitude"]}' \
              f'&temperature_unit={kwargs["unit"]}'
        if kwargs['function_name'] == 'get_current_weather':
            url += '&current_weather=true'
            return requests.get(url).json()

        elif kwargs['function_name'] == 'get_forecast_weather':
            url += '&daily=weathercode,temperature_2m_max,temperature_2m_min,precipitation_probability_mean,'
            url += f'&forecast_days={kwargs["forecast_days"]}'
            url += '&timezone=auto'
            response = requests.get(url).json()
            results = {}
            for i, time in enumerate(response["daily"]["time"]):
                results[datetime.strptime(time, "%Y-%m-%d").strftime("%A, %B %d, %Y")] = {
                    "weathercode": response["daily"]["weathercode"][i],
                    "temperature_2m_max": response["daily"]["temperature_2m_max"][i],
                    "temperature_2m_min": response["daily"]["temperature_2m_min"][i],
                    "precipitation_probability_mean": response["daily"]["precipitation_probability_mean"][i]
                }
            return {"today": datetime.today().strftime("%A, %B %d, %Y"), "forecast": results}
    except Exception as e:
        print(f"\n ERROR: {e}")
        return {"weather": "По какой-то причине не удалось получить данные на запрос. Попробуйте позже."}

weather_json = {
    "type": "function",
    "function": {
        "name": "weather",
        "description": "Fetches current weather or forecast based on function name and parameters",
        "strict": True,
        "parameters": {
            "type": "object",
            "required": [
                "plugin",
                "function_name",
                "latitude",
                "longitude",
                "unit",
                "forecast_days"
            ],
            "properties": {
                "plugin": {
                    "type": "string",
                    "description": "name of the plugin is 'weather'"
                },
                "function_name": {
                    "type": "string",
                    "description": "Specify either 'get_current_weather' or 'get_forecast_weather'"
                },
                "latitude": {
                    "type": "number",
                    "description": "Latitude of the location for weather data"
                },
                "longitude": {
                    "type": "number",
                    "description": "Longitude of the location for weather data"
                },
                "unit": {
                    "type": "string",
                    "description": "Temperature unit, e.g., 'celsius' or 'fahrenheit'"
                },
                "forecast_days": {
                    "type": "number",
                    "description": "Number of days to forecast (required for 'get_forecast_weather')"
                }
            },
            "additionalProperties": False
        }
    }
}
