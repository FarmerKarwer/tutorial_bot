from datetime import datetime, timezone
import json

def load_json(filepath):
    with open(filepath, "r", encoding="utf-8") as file:
        return json.load(file)

def unix_to_timestamp(unix_time):
    # Convert the Unix timestamp to a datetime object
    dt = datetime.fromtimestamp(unix_time, tz=timezone.utc)
    
    # Format the datetime object in ISO 8601 format with milliseconds
    formatted_time = dt.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
    
    return formatted_time
