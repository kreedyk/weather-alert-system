import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, time
import json

logger = logging.getLogger(__name__)

class AlertChecker:
    """
    Checks if weather data meets alert conditions.
    """
    
    def __init__(self, config_path: str):
        """Initialize with configuration file path."""
        self.config_path = config_path
        self.config = self._load_config()
        self.alert_history = {}  # Keep track of already triggered alerts
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
                # Debug: log location names
                location_names = [loc.get('name') for loc in config.get('locations', [])]
                logger.debug(f"Loaded locations: {location_names}")
                
                return config
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.error(f"Error loading configuration: {e}")
            raise
    
    def refresh_config(self):
        """Reload configuration from file."""
        self.config = self._load_config()
    
    def is_quiet_hours(self) -> bool:
        """Check if current time is within quiet hours."""
        quiet_hours = self.config.get('preferences', {}).get('quiet_hours', {})
        
        if not quiet_hours.get('enabled', False):
            return False
        
        now = datetime.now().time()
        start_str = quiet_hours.get('start', '22:00')
        end_str = quiet_hours.get('end', '07:00')
        
        try:
            start = datetime.strptime(start_str, '%H:%M').time()
            end = datetime.strptime(end_str, '%H:%M').time()
            
            # Handle overnight quiet hours
            if start > end:
                return now >= start or now <= end
            else:
                return start <= now <= end
        except ValueError:
            logger.error(f"Invalid quiet hours format: {start_str} - {end_str}")
            return False
    
    def check_location_alerts(self, location_name: str, weather_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Check if weather data for a location triggers any alerts.
        Returns a list of triggered alerts.
        """
        if self.is_quiet_hours():
            logger.debug("Skipping alert check during quiet hours")
            return []
        
        triggered_alerts = []
        
        # Debug: print the location name being checked
        logger.debug(f"Looking for location in config: '{location_name}'")
        
        # Find the location in config
        location = None
        for loc in self.config.get('locations', []):
            config_name = loc.get('name', '')
            logger.debug(f"Comparing with config location: '{config_name}'")
            
            if config_name.strip() == location_name.strip():
                logger.debug(f"Found location match: {config_name}")
                location = loc
                break
        
        if not location:
            logger.warning(f"Location not found in config: {location_name}")
            return []
        
        # Check each alert condition for the location
        for alert in location.get('alerts', []):
            condition = alert.get('condition')
            operator = alert.get('operator')
            threshold = alert.get('value')
            message = alert.get('message', f"Weather alert for {location_name}")
            
            if self._check_condition(weather_data, condition, operator, threshold):
                # Create a unique ID for this alert to avoid duplicates
                alert_id = f"{location_name}_{condition}_{operator}_{threshold}"
                
                # Check if this alert was already triggered recently
                last_trigger = self.alert_history.get(alert_id)
                current_time = datetime.now()
                
                # Only trigger if it's been at least 6 hours since last alert
                if not last_trigger or (current_time - last_trigger).total_seconds() > 21600:
                    self.alert_history[alert_id] = current_time
                    
                    triggered_alert = {
                        'location': location_name,
                        'condition': condition,
                        'threshold': threshold,
                        'current_value': self._get_condition_value(weather_data, condition),
                        'message': message,
                        'timestamp': current_time.isoformat()
                    }
                    triggered_alerts.append(triggered_alert)
                    
                    logger.info(f"Alert triggered: {triggered_alert}")
        
        return triggered_alerts
    
    def _check_condition(self, weather_data: Dict[str, Any], condition: str, operator: str, threshold: float) -> bool:
        """Check if a weather condition meets the alert criteria."""
        current_value = self._get_condition_value(weather_data, condition)
        
        if current_value is None:
            return False
        
        if operator == 'above':
            return current_value > threshold
        elif operator == 'below':
            return current_value < threshold
        elif operator == 'equals':
            return current_value == threshold
        else:
            logger.warning(f"Unknown operator: {operator}")
            return False
    
    def _get_condition_value(self, weather_data: Dict[str, Any], condition: str) -> Optional[float]:
        """Extract the value for a condition from weather data."""
        try:
            if condition == 'temperature':
                return weather_data.get('temperature', {}).get('current')
            elif condition == 'feels_like':
                return weather_data.get('temperature', {}).get('feels_like')
            elif condition == 'humidity':
                return weather_data.get('humidity')
            elif condition == 'pressure':
                return weather_data.get('pressure')
            elif condition == 'wind':
                return weather_data.get('wind', {}).get('speed')
            elif condition == 'clouds':
                return weather_data.get('clouds')
            elif condition == 'precipitation':
                rain = weather_data.get('precipitation', {}).get('rain', 0)
                snow = weather_data.get('precipitation', {}).get('snow', 0)
                return rain + snow
            elif condition == 'rain':
                return weather_data.get('precipitation', {}).get('rain', 0)
            elif condition == 'snow':
                return weather_data.get('precipitation', {}).get('snow', 0)
            else:
                logger.warning(f"Unknown condition: {condition}")
                return None
        except (TypeError, KeyError) as e:
            logger.error(f"Error extracting condition {condition}: {e}")
            return None