# Weather Alert System

A lightweight desktop notification system that alerts you when weather conditions match your specified criteria. Perfect for monitoring rain, temperature, wind, and other weather conditions in locations you care about.

## Features

- Monitor multiple locations for specific weather conditions
- Receive non-intrusive desktop toast notifications on Windows
- Set custom alert thresholds for various weather parameters
- Store and track historical weather data
- Run as a service or perform one-time checks
- Complete command-line interface

## Screenshots

![Weather Alert System - Notifications](https://i.imgur.com/drfbVRv.jpeg)

![Weather Alert System - Command Line](https://i.imgur.com/cpO362p.png)

## Requirements

- Python 3.6+
- Windows 10/11 (for toast notifications)
- OpenWeatherMap API key

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/kreedyk/weather-alert-system.git
   cd weather-alert-system
   ```

2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

3. Get an API key from [OpenWeatherMap](https://openweathermap.org/api) (free tier is sufficient)

4. Place your API key in a file named `.api_key` in the root directory

## Usage

### Add a Location

```
python weather_alert.py add-location "New York" 40.7128 -74.0060
```

### Add an Alert Condition

```
python weather_alert.py add-alert "New York" temperature above 30 "Heat warning for New York"
```

Available conditions:
- `temperature` - Current temperature
- `feels_like` - Feels-like temperature
- `humidity` - Relative humidity percentage
- `pressure` - Atmospheric pressure
- `wind` - Wind speed
- `clouds` - Cloud coverage percentage
- `precipitation` - Combined rain and snow
- `rain` - Rain amount
- `snow` - Snow amount

Available operators:
- `above` - Greater than threshold
- `below` - Less than threshold
- `equals` - Equal to threshold

### Sample Locations with Ready-to-Trigger Alerts

To test the system with certain preset locations that are more likely to trigger alerts:

1. San Francisco:
   ```
   python weather_alert.py add-location "San Francisco" 37.7749 -122.4194
   python weather_alert.py add-alert "San Francisco" humidity above 60 "High humidity in San Francisco"
   python weather_alert.py add-alert "San Francisco" wind above 4 "Windy conditions in San Francisco"
   ```

2. Rio de Janeiro:
   ```
   python weather_alert.py add-location "Rio de Janeiro" -22.9068 -43.1729
   python weather_alert.py add-alert "Rio de Janeiro" temperature above 25 "Hot weather in Rio"
   ```

3. Moscow:
   ```
   python weather_alert.py add-location "Moscow" 55.7558 37.6173
   python weather_alert.py add-alert "Moscow" temperature below 10 "Cool weather in Moscow"
   ```

The above examples use threshold values that are relatively common in these locations, making it more likely that you'll see a working example when running a check.

### List Configured Locations and Alerts

```
python weather_alert.py list
```

### Perform a Single Weather Check

```
python weather_alert.py check
```

### Run as a Background Service

```
python weather_alert.py service
```

## Configuration

The system creates a configuration file at `config/config.json`. You can edit this file to:

- Change units (metric or imperial)
- Adjust check interval
- Set quiet hours (when no alerts are sent)
- Add or modify locations and alert conditions

Example configuration:
```json
{
  "api": {
    "service": "openweathermap",
    "units": "metric"
  },
  "locations": [
    {
      "name": "New York",
      "latitude": 40.7128,
      "longitude": -74.0060,
      "alerts": [
        {
          "condition": "temperature",
          "operator": "above",
          "value": 30,
          "message": "Heat warning for New York"
        }
      ]
    }
  ],
  "notifications": {
    "desktop": {
      "enabled": true
    }
  },
  "preferences": {
    "check_interval_minutes": 30,
    "quiet_hours": {
      "enabled": true,
      "start": "23:00",
      "end": "07:00"
    },
    "history_days": 30
  }
}
```

## API Key Security

This project uses a separate `.api_key` file to store your OpenWeatherMap API key. For better security, you can alternatively set it as an environment variable:

```
# Windows
set OPENWEATHER_API_KEY=your_api_key_here

# Linux/macOS
export OPENWEATHER_API_KEY=your_api_key_here
```

## Data Storage

Weather data and alerts are stored in an SQLite database in the `data` directory. This enables historical tracking and analysis.

## Notification System

The system uses toast notifications, which appear in the bottom-right corner of your screen. These notifications are:
- Non-intrusive (they don't interrupt your workflow)
- Integrated with the Windows notification center

## Acknowledgements

- Weather data provided by [OpenWeatherMap](https://openweathermap.org/)
- Toast notifications powered by [winotify](https://github.com/versa-syahptr/winotify)
