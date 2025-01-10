import json
from bot_logic import use_logic
from tg_api import get_updates
import time
import logging

# Configure logging
logging.basicConfig(
    filename='logs.txt',      # Name of the log file
    filemode='a',             # Append mode; use 'w' to overwrite existing file
    level=logging.INFO,        # Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def handler():
	message = get_updates()['result'][-1] 
	use_logic(message)	
	return {
	'statusCode':200,
	'message':message
	}

def handler_long():
	print("Long polling has started...")
	logging.info("Long polling has started...")
	print("Press Ctrl + C to exit")

	last_update_id = None
	offset = None
	running = True

	try:
		while running:
			if last_update_id:
				offset = last_update_id+1

			updates = get_updates(offset = offset, timeout=30)

			if updates["ok"] and updates["result"]:
				logging.debug(f"Received updates: {updates}")
				update = updates['result'][-1]
				if (last_update_id is None) or (update["update_id"] == last_update_id + 1):
					last_update_id = update["update_id"]
					logging.info(f"Received update ID: {last_update_id}")
					use_logic(update)

			time.sleep(1)
	except KeyboardInterrupt:
		print("Bot has been stopped. Exiting gracefully...")
		logging.info("Bot has been stopped by user.")
	return {
	'statusCode':200
	}
