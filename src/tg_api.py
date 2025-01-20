from dotenv import load_dotenv
import os
import requests
import json

"""
There will be all the methods necessary for Telegram Bot
"""

load_dotenv(override=True)
TG_TOKEN=os.getenv('BOT_TOKEN')
URL = f"https://api.telegram.org/bot{TG_TOKEN}/"

# Sending Messages
def send_text_message(reply, chat_id, parse_mode='Markdown', disable_notification=None, 
    protect_content=None, reply_parameters=None, keyboard=None):
	data = {
		'text':reply,
		'chat_id':chat_id,
		'parse_mode':parse_mode,
		'disable_notification':disable_notification,
		'protect_content':protect_content,
		'reply_parameters':reply_parameters,
		'reply_markup': keyboard
	}
	url = URL+"sendMessage"
	response = requests.post(url, data=data)

def delete_message(message_id, chat_id):
	data = {
	'chat_id':chat_id,
	'message_id':message_id
	}
	url = URL+"deleteMessage"
	requests.post(url, data=data)

def answer_callback_query(callback_query_id):
	data = {"callback_query_id": callback_query_id}
	url = URL+"answerCallbackQuery"
	requests.post(url, data=data)

def edit_message_reply_markup(chat_id, message_id, reply_markup):
	"""
	Edits the inline keyboard of a specific message.
	"""
	url = URL+"editMessageReplyMarkup"

	# Payload for the API request
	payload = {
		"chat_id": chat_id,
		"message_id": message_id,
		"reply_markup": json.dumps(reply_markup)
	}

	# Send the request
	response = requests.post(url, data=payload)

def get_updates(offset=None, timeout=None):
	url = URL+"getUpdates"
	params = {"offset": offset, "timeout": timeout}
	update = requests.get(url, params=params)
	return update.json()

if __name__ == "__main__":
    print(get_updates())
