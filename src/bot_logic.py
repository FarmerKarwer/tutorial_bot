import json
from utils import load_json

# Constants for file paths
REPLIES_FILEPATH = "./ui/replies.json"
BUTTONS_FILEPATH = "./ui/buttons.json"

# Load JSON data
replies = load_json(REPLIES_FILEPATH)

def use_logic(message):
	print(f"It works!")
	print(message)
