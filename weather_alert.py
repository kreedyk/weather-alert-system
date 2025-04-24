#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List

# Fix encoding for Windows
if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# Import project modules
from src.api import WeatherAPI
from src.alerts import AlertChecker
from src.notifier import Notifier
from src.storage import WeatherDatabase

# Set up logging
def setup_logging(log_level: str, log_file: str = None):
    """Configure logging."""
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        numeric_level = logging.INFO
    
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    if log_file:
        logging.basicConfig(
            level=numeric_level,
            format=log_format,
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
    else:
        logging.basicConfig(
            level=numeric_level,
            format=log_format
        )

def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration from file, creating default if it doesn't exist."""
    config_file = Path(config_path)
    
    if not config_file.exists():
        # Create default configuration
        default_config = {
            "api": {
                "service": "openweathermap",
                "units": "metric"
            },
            "locations": [],
            "notifications": {
                "desktop": {
                    "enabled": True
                }
            },
            "preferences": {
                "check_interval_minutes": 30,
                "quiet_hours": {
                    "enabled": True,
                    "start": "22:00",
                    "end": "07:00"
                },
                "history_days": 30
            }
        }
        
        # Ensure parent directory exists
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Write default config
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=2, ensure_ascii=False)
        
        print(f"Created default configuration at {config_file}")
        print("Please edit the configuration with your API key and settings.")
        return default_config
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"Error: {config_file} is not valid JSON")
        sys.exit(1)

def add_location(config_path: str, name: str, latitude: float, longitude: float):
    """Add a new location to the configuration."""
    config = load_config(config_path)
    
    # Check if location already exists
    for location in config.get('locations', []):
        if location.get('name') == name:
            print(f"Location '{name}' already exists")
            return
    
    # Add new location
    new_location = {
        "name": name,
        "latitude": latitude,
        "longitude": longitude,
        "alerts": []
    }
    
    config.setdefault('locations', []).append(new_location)
    
    # Save updated config
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    print(f"Added location '{name}' at {latitude}, {longitude}")

def add_alert(config_path: str, location: str, condition: str, operator: str, value: float, message: str):
    """Add a new alert condition to a location."""
    config = load_config(config_path)
    
    # Find the location
    location_found = False
    for loc in config.get('locations', []):
        if loc.get('name') == location:
            location_found = True
            
            # Create new alert
            new_alert = {
                "condition": condition,
                "operator": operator,
                "value": value,
                "message": message
            }
            
            # Add alert if it doesn't already exist
            alerts = loc.setdefault('alerts', [])
            for alert in alerts:
                if (alert.get('condition') == condition and 
                    alert.get('operator') == operator and 
                    alert.get('value') == value):
                    print(f"Alert already exists for {location}")
                    return
            
            alerts.append(new_alert)
            break
    
    if not location_found:
        print(f"Location '{location}' not found in configuration")
        return
    
    # Save updated config
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    print(f"Added alert for {condition} {operator} {value} to '{location}'")

def list_locations(config_path: str):
    """List all configured locations with their alerts."""
    config = load_config(config_path)
    
    locations = config.get('locations', [])
    if not locations:
        print("No locations configured")
        return
    
    print(f"Configured locations ({len(locations)}):")
    for i, location in enumerate(locations, 1):
        name = location.get('name', 'Unnamed')
        lat = location.get('latitude', 'N/A')
        lon = location.get('longitude', 'N/A')
        alerts = location.get('alerts', [])
        
        print(f"{i}. {name} ({lat}, {lon}) - {len(alerts)} alerts")
        
        for j, alert in enumerate(alerts, 1):
            condition = alert.get('condition', 'Unknown')
            operator = alert.get('operator', '==')
            value = alert.get('value', 'N/A')
            message = alert.get('message', 'No message')
            
            print(f"   {j}. {condition} {operator} {value} - {message}")

def check_now(config_path: str, db_path: str, log_file: str):
    """Run a single check of all locations and send alerts if needed."""
    setup_logging("INFO", log_file)
    logger = logging.getLogger("weather_alert")
    
    config = load_config(config_path)
    
    # Initialize components
    try:
        api = WeatherAPI(config.get('api', {}))
        alert_checker = AlertChecker(config_path)
        notifier = Notifier(config_path)
        db = WeatherDatabase(db_path)
    except Exception as e:
        logger.error(f"Initialization error: {e}")
        return
    
    # Check each location
    for location in config.get('locations', []):
        name = location.get('name')
        lat = location.get('latitude')
        lon = location.get('longitude')
        
        if not all([name, lat, lon]):
            logger.warning(f"Skipping location with incomplete data: {location}")
            continue
        
        try:
            # Get current weather
            logger.info(f"Checking weather for {name}")
            weather_data = api.get_current_weather(lat, lon)
            
            # Store in database
            db.store_weather_data(name, weather_data)
            
            # Check for alerts
            triggered_alerts = alert_checker.check_location_alerts(name, weather_data)
            
            # Send notifications for triggered alerts
            for alert in triggered_alerts:
                notifier.send_alert(alert)
                db.store_alert(alert)
            
            if triggered_alerts:
                logger.info(f"Sent {len(triggered_alerts)} alerts for {name}")
            else:
                logger.info(f"No alerts triggered for {name}")
                
        except Exception as e:
            logger.error(f"Error checking {name}: {e}")

def run_service(config_path: str, db_path: str, log_file: str):
    """Run as a continuous service, checking periodically."""
    setup_logging("INFO", log_file)
    logger = logging.getLogger("weather_alert")
    
    config = load_config(config_path)
    check_interval = config.get('preferences', {}).get('check_interval_minutes', 30)
    
    logger.info(f"Starting Weather Alert service, checking every {check_interval} minutes")
    
    try:
        while True:
            check_now(config_path, db_path, log_file)
            
            # Sleep until next check
            logger.info(f"Next check in {check_interval} minutes")
            time.sleep(check_interval * 60)
    except KeyboardInterrupt:
        logger.info("Service stopped by user")
    except Exception as e:
        logger.error(f"Service error: {e}")

def main():
    """Main entry point with argument parsing."""
    # Set default paths
    default_config_path = os.path.join("config", "config.json")
    default_db_path = os.path.join("data", "weather_history.db")
    default_log_path = os.path.join("logs", "alerts.log")
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Weather Alert System")
    subparsers = parser.add_subparsers(dest="command", help="Command")
    
    # Add location command
    add_loc_parser = subparsers.add_parser("add-location", help="Add a new location")
    add_loc_parser.add_argument("name", help="Location name")
    add_loc_parser.add_argument("latitude", type=float, help="Latitude")
    add_loc_parser.add_argument("longitude", type=float, help="Longitude")
    
    # Add alert command
    add_alert_parser = subparsers.add_parser("add-alert", help="Add a new alert")
    add_alert_parser.add_argument("location", help="Location name")
    add_alert_parser.add_argument("condition", choices=[
        "temperature", "feels_like", "humidity", "pressure", 
        "wind", "clouds", "precipitation", "rain", "snow"
    ], help="Weather condition")
    add_alert_parser.add_argument("operator", choices=["above", "below", "equals"], 
                               help="Comparison operator")
    add_alert_parser.add_argument("value", type=float, help="Threshold value")
    add_alert_parser.add_argument("message", help="Alert message")
    
    # List locations command
    subparsers.add_parser("list", help="List configured locations and alerts")
    
    # Check now command
    check_parser = subparsers.add_parser("check", help="Run a single weather check")
    
    # Run service command
    service_parser = subparsers.add_parser("service", help="Run as a continuous service")
    
    # Common options
    for p in [parser, check_parser, service_parser]:
        p.add_argument("-c", "--config", default=default_config_path,
                      help=f"Path to config file (default: {default_config_path})")
        p.add_argument("-d", "--database", default=default_db_path,
                      help=f"Path to database file (default: {default_db_path})")
        p.add_argument("-l", "--log", default=default_log_path,
                      help=f"Path to log file (default: {default_log_path})")
    
    args = parser.parse_args()
    
    # Create directories if they don't exist
    for path in [os.path.dirname(args.config), 
                os.path.dirname(args.database), 
                os.path.dirname(args.log)]:
        if path and not os.path.exists(path):
            os.makedirs(path)
    
    # Execute appropriate command
    if args.command == "add-location":
        add_location(args.config, args.name, args.latitude, args.longitude)
    elif args.command == "add-alert":
        add_alert(args.config, args.location, args.condition, 
                 args.operator, args.value, args.message)
    elif args.command == "list":
        list_locations(args.config)
    elif args.command == "check":
        check_now(args.config, args.database, args.log)
    elif args.command == "service":
        run_service(args.config, args.database, args.log)
    else:
        # If no command specified, just load/create config
        load_config(args.config)
        parser.print_help()

if __name__ == "__main__":
    main()