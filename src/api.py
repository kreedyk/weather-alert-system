import requests
import json
import logging
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class WeatherAPI:
    """Interface for fetching weather data from various providers."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the API with configuration."""
        self.config = config
        self.service = config.get('service', 'openweathermap')
        
        # Get API key from environment variable or use the one in .api_key file
        self.api_key = os.environ.get('OPENWEATHER_API_KEY')
        
        # If not in environment, try to read from .api_key file
        if not self.api_key:
            try:
                with open('.api_key', 'r') as f:
                    self.api_key = f.read().strip()
            except FileNotFoundError:
                # Use hardcoded key as fallback (not ideal but for this demo)
                self.api_key = "19724a3a48d488b35b9b9f7ddb46b1f3"
        
        self.units = config.get('units', 'metric')
        
        if not self.api_key:
            logger.error("API key not provided")
            raise ValueError("OpenWeatherMap API key is required")
    
    def get_current_weather(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """Get current weather for a location."""
        if self.service == 'openweathermap':
            return self._get_openweathermap_current(latitude, longitude)
        else:
            raise ValueError(f"Unsupported weather service: {self.service}")
    
    def get_forecast(self, latitude: float, longitude: float, days: int = 5) -> List[Dict[str, Any]]:
        """Get weather forecast for a location."""
        if self.service == 'openweathermap':
            return self._get_openweathermap_forecast(latitude, longitude, days)
        else:
            raise ValueError(f"Unsupported weather service: {self.service}")
    
    def get_alerts(self, latitude: float, longitude: float) -> List[Dict[str, Any]]:
        """Get active weather alerts for a location."""
        if self.service == 'openweathermap':
            return self._get_openweathermap_alerts(latitude, longitude)
        else:
            raise ValueError(f"Unsupported weather service: {self.service}")
    
    def _get_openweathermap_current(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """Get current weather from OpenWeatherMap API."""
        url = f"https://api.openweathermap.org/data/2.5/weather"
        params = {
            'lat': latitude,
            'lon': longitude,
            'appid': self.api_key,
            'units': self.units
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Transform data into a standardized format
            return {
                'timestamp': datetime.now().isoformat(),
                'location': {
                    'name': data.get('name', 'Unknown'),
                    'latitude': latitude,
                    'longitude': longitude,
                },
                'temperature': {
                    'current': data.get('main', {}).get('temp'),
                    'feels_like': data.get('main', {}).get('feels_like'),
                    'min': data.get('main', {}).get('temp_min'),
                    'max': data.get('main', {}).get('temp_max'),
                },
                'humidity': data.get('main', {}).get('humidity'),
                'pressure': data.get('main', {}).get('pressure'),
                'wind': {
                    'speed': data.get('wind', {}).get('speed'),
                    'direction': data.get('wind', {}).get('deg'),
                },
                'clouds': data.get('clouds', {}).get('all'),
                'precipitation': {
                    'rain': data.get('rain', {}).get('1h', 0),
                    'snow': data.get('snow', {}).get('1h', 0),
                },
                'weather': {
                    'condition': data.get('weather', [{}])[0].get('main'),
                    'description': data.get('weather', [{}])[0].get('description'),
                    'icon': data.get('weather', [{}])[0].get('icon'),
                },
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching current weather: {e}")
            raise
    
    def _get_openweathermap_forecast(self, latitude: float, longitude: float, days: int = 5) -> List[Dict[str, Any]]:
        """Get weather forecast from OpenWeatherMap API."""
        url = f"https://api.openweathermap.org/data/2.5/forecast"
        params = {
            'lat': latitude,
            'lon': longitude,
            'appid': self.api_key,
            'units': self.units,
            'cnt': days * 8  # 8 forecasts per day (every 3 hours)
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            forecasts = []
            for item in data.get('list', []):
                forecast = {
                    'timestamp': item.get('dt_txt'),
                    'temperature': {
                        'current': item.get('main', {}).get('temp'),
                        'feels_like': item.get('main', {}).get('feels_like'),
                        'min': item.get('main', {}).get('temp_min'),
                        'max': item.get('main', {}).get('temp_max'),
                    },
                    'humidity': item.get('main', {}).get('humidity'),
                    'pressure': item.get('main', {}).get('pressure'),
                    'wind': {
                        'speed': item.get('wind', {}).get('speed'),
                        'direction': item.get('wind', {}).get('deg'),
                    },
                    'clouds': item.get('clouds', {}).get('all'),
                    'precipitation': {
                        'rain': item.get('rain', {}).get('3h', 0),
                        'snow': item.get('snow', {}).get('3h', 0),
                    },
                    'weather': {
                        'condition': item.get('weather', [{}])[0].get('main'),
                        'description': item.get('weather', [{}])[0].get('description'),
                        'icon': item.get('weather', [{}])[0].get('icon'),
                    },
                }
                forecasts.append(forecast)
            
            return forecasts
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching forecast: {e}")
            raise
    
    def _get_openweathermap_alerts(self, latitude: float, longitude: float) -> List[Dict[str, Any]]:
        """Get weather alerts from OpenWeatherMap API."""
        url = f"https://api.openweathermap.org/data/2.5/onecall"
        params = {
            'lat': latitude,
            'lon': longitude,
            'appid': self.api_key,
            'units': self.units,
            'exclude': 'current,minutely,hourly,daily'  # Only get alerts
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            alerts = []
            for alert in data.get('alerts', []):
                alert_data = {
                    'sender': alert.get('sender_name'),
                    'event': alert.get('event'),
                    'start': datetime.fromtimestamp(alert.get('start')).isoformat(),
                    'end': datetime.fromtimestamp(alert.get('end')).isoformat(),
                    'description': alert.get('description'),
                }
                alerts.append(alert_data)
            
            return alerts
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching alerts: {e}")
            raise
