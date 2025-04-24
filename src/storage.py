import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import os

logger = logging.getLogger(__name__)

class WeatherDatabase:
    """
    Handles storage and retrieval of weather data and alerts.
    """
    
    def __init__(self, db_path: str):
        """Initialize database, creating it if it doesn't exist."""
        self.db_path = db_path
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Initialize database
        self._init_db()
    
    def _init_db(self):
        """Create database tables if they don't exist."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create weather data table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS weather_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    location TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    data TEXT NOT NULL
                )
            ''')
            
            # Create alerts table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    location TEXT NOT NULL,
                    condition TEXT NOT NULL,
                    threshold REAL NOT NULL,
                    current_value REAL NOT NULL,
                    message TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            ''')
            
            # Create indexes for faster queries
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_weather_location_time
                ON weather_data (location, timestamp)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_alerts_location_time
                ON alerts (location, timestamp)
            ''')
            
            conn.commit()
            conn.close()
            
            logger.info(f"Database initialized at {self.db_path}")
        except sqlite3.Error as e:
            logger.error(f"Database initialization error: {e}")
            raise
    
    def store_weather_data(self, location: str, data: Dict[str, Any]):
        """Store weather data for a location."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Convert data to JSON for storage
            data_json = json.dumps(data)
            timestamp = data.get('timestamp', datetime.now().isoformat())
            
            cursor.execute(
                'INSERT INTO weather_data (location, timestamp, data) VALUES (?, ?, ?)',
                (location, timestamp, data_json)
            )
            
            conn.commit()
            conn.close()
            
            logger.debug(f"Stored weather data for {location} at {timestamp}")
            
            # Clean up old data
            self._cleanup_old_data()
        except sqlite3.Error as e:
            logger.error(f"Error storing weather data: {e}")
    
    def get_weather_data(self, location: str, days: int = 1) -> List[Dict[str, Any]]:
        """
        Retrieve weather data for a location from the last N days.
        Returns a list of weather data entries.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Calculate cutoff date
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            cursor.execute(
                'SELECT timestamp, data FROM weather_data WHERE location = ? AND timestamp > ? ORDER BY timestamp DESC',
                (location, cutoff_date)
            )
            
            results = []
            for row in cursor.fetchall():
                timestamp, data_json = row
                try:
                    data = json.loads(data_json)
                    results.append(data)
                except json.JSONDecodeError:
                    logger.warning(f"Error decoding weather data JSON for {location} at {timestamp}")
            
            conn.close()
            
            logger.debug(f"Retrieved {len(results)} weather records for {location}")
            return results
        except sqlite3.Error as e:
            logger.error(f"Error retrieving weather data: {e}")
            return []
    
    def store_alert(self, alert: Dict[str, Any]):
        """Store an alert that was triggered."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            location = alert.get('location', 'Unknown')
            condition = alert.get('condition', 'Unknown')
            threshold = alert.get('threshold', 0)
            current_value = alert.get('current_value', 0)
            message = alert.get('message', '')
            timestamp = alert.get('timestamp', datetime.now().isoformat())
            
            cursor.execute(
                'INSERT INTO alerts (location, condition, threshold, current_value, message, timestamp) VALUES (?, ?, ?, ?, ?, ?)',
                (location, condition, threshold, current_value, message, timestamp)
            )
            
            conn.commit()
            conn.close()
            
            logger.debug(f"Stored alert for {location} at {timestamp}")
        except sqlite3.Error as e:
            logger.error(f"Error storing alert: {e}")
    
    def get_alerts(self, location: Optional[str] = None, days: int = 7) -> List[Dict[str, Any]]:
        """
        Retrieve alerts from the last N days.
        If location is specified, filter by location.
        Returns a list of alert entries.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Calculate cutoff date
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            if location:
                cursor.execute(
                    'SELECT location, condition, threshold, current_value, message, timestamp FROM alerts WHERE location = ? AND timestamp > ? ORDER BY timestamp DESC',
                    (location, cutoff_date)
                )
            else:
                cursor.execute(
                    'SELECT location, condition, threshold, current_value, message, timestamp FROM alerts WHERE timestamp > ? ORDER BY timestamp DESC',
                    (cutoff_date,)
                )
            
            results = []
            for row in cursor.fetchall():
                loc, cond, thresh, current, msg, ts = row
                alert = {
                    'location': loc,
                    'condition': cond,
                    'threshold': thresh,
                    'current_value': current,
                    'message': msg,
                    'timestamp': ts
                }
                results.append(alert)
            
            conn.close()
            
            logger.debug(f"Retrieved {len(results)} alerts")
            return results
        except sqlite3.Error as e:
            logger.error(f"Error retrieving alerts: {e}")
            return []
    
    def _cleanup_old_data(self, days: int = 30):
        """Delete weather data older than N days."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Calculate cutoff date
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            # Delete old weather data
            cursor.execute(
                'DELETE FROM weather_data WHERE timestamp < ?',
                (cutoff_date,)
            )
            
            # Delete old alerts
            cursor.execute(
                'DELETE FROM alerts WHERE timestamp < ?',
                (cutoff_date,)
            )
            
            conn.commit()
            
            if cursor.rowcount > 0:
                logger.info(f"Cleaned up {cursor.rowcount} old records")
            
            conn.close()
        except sqlite3.Error as e:
            logger.error(f"Error cleaning up old data: {e}")
    
    def get_statistics(self, location: str, condition: str, days: int = 7) -> Dict[str, Any]:
        """
        Calculate statistics for a specific condition at a location.
        Returns a dictionary with min, max, avg values over the period.
        """
        weather_data = self.get_weather_data(location, days)
        
        if not weather_data:
            return {
                'min': None,
                'max': None,
                'avg': None,
                'count': 0
            }
        
        values = []
        for entry in weather_data:
            # Extract the condition value based on the condition type
            if condition == 'temperature':
                value = entry.get('temperature', {}).get('current')
            elif condition == 'feels_like':
                value = entry.get('temperature', {}).get('feels_like')
            elif condition == 'humidity':
                value = entry.get('humidity')
            elif condition == 'pressure':
                value = entry.get('pressure')
            elif condition == 'wind':
                value = entry.get('wind', {}).get('speed')
            elif condition == 'precipitation':
                rain = entry.get('precipitation', {}).get('rain', 0)
                snow = entry.get('precipitation', {}).get('snow', 0)
                value = rain + snow
            else:
                value = None
            
            if value is not None:
                values.append(value)
        
        if not values:
            return {
                'min': None,
                'max': None,
                'avg': None,
                'count': 0
            }
        
        return {
            'min': min(values),
            'max': max(values),
            'avg': sum(values) / len(values),
            'count': len(values)
        }
