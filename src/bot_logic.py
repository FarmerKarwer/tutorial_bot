import tg_api
import json
from database import DatabaseClient
from utils import load_json, unix_to_timestamp

# Constants for file paths
REPLIES_FILEPATH = "./ui/replies.json"
BUTTONS_FILEPATH = "./ui/buttons.json"

# Load JSON data
replies = load_json(REPLIES_FILEPATH)

db = DatabaseClient()

def use_logic(message):
	if button_is_pressed(message):
		handle_callback_query(message)	
	elif text_message_is_entered(message):
		handle_text_message(message)

def handle_callback_query(message):
	# Get the data
	callback_data = message['callback_query']['data']
	chat_id = message['callback_query']['message']['chat']['id']
	message_id = message['callback_query']['message']['message_id']
	user_id = message['callback_query']['from']['id']
	unix_timestamp = message['callback_query']['message']['date']
	timestamp = unix_to_timestamp(unix_timestamp)

	# Use the logic for callback query
	def show_callback_reply(screen_id):
		switch_screen(replies[screen_id], chat_id, message_id, keyboard=get_keyboard(screen_id))

	DEFAULT_CALLBACK_SCREENS = (
		"/start", "menu_2", "menu_2_1", "menu_3",
		"menu_3_1", "menu_3_1_1", "menu_3_1_2", "menu_3_1_new_lev",
		"menu_4", "menu_5", "menu_5_1", "menu_5_1_saved", "menu_5_2", "menu_5_2_saved"
		)

	SPECIAL_CALLBACK_HANDLERS = {
	"menu_1": lambda: show_icebreaker(user_id, chat_id, message_id, screen_id="menu_1")
	}
	SPECIAL_CALLBACK_SCREENS = SPECIAL_CALLBACK_HANDLERS.keys()

	if callback_data in SPECIAL_CALLBACK_SCREENS:
		action = SPECIAL_CALLBACK_HANDLERS.get(callback_data)
		action()
	elif callback_data in DEFAULT_CALLBACK_SCREENS:
		show_callback_reply(callback_data)
	elif callback_data.startswith("topic_"):
		category_dict = {
		"1":"work",
		"2":"romantic",
		"3":"party",
		"4":"study",
		"5":"queue",
		"6":"hobby",
		"7":"gym",
		"8":"transport",
		"9":"walk",
		"10":"cafe"
		}
		category_idx = callback_data.split('_')[-1]
		chosen_category = category_dict[category_idx]
		show_icebreaker(user_id, chat_id, message_id, screen_id="menu_2_1", category=chosen_category, topic_num=category_idx)
	elif callback_data.startswith("menu_3_1_"):
		switch_screen(replies['menu_3_1'], chat_id, message_id, keyboard=get_keyboard('menu_3_1'))
	elif callback_data.startswith("menu_5_2_saved_"):
		switch_screen(replies['menu_5_2_saved'], chat_id, message_id, keyboard=get_keyboard('menu_5_2_saved'))
	else:
		print("ERROR: No callback data")

	db.add_user_action(user_id, action_type="pressed button", completed_at=timestamp)

def handle_text_message(message):
	# Get the data
	text = message['message']['text']
	chat_id = message['message']['chat']['id']
	message_id = message['message']['message_id']
	user_id = message['message']['from']['id']
	unix_timestamp = message['message']['date']
	timestamp = unix_to_timestamp(unix_timestamp)

	# Use the logic for text message
	if text=='/start':
		user = db.select_user(user_id)
		no_user = len(user)==0
		if no_user:
			if "last_name" in message['message']['from'].keys():
				last_name = f"'{message['message']['from']['last_name']}'"
			else:
				last_name = "NULL"
			user_data = {
				"id":user_id,
				"username":message['message']['from']['username'],
				"first_name":message['message']['from']['first_name'],
				"language":message['message']['from']['language_code'],
				"last_name":last_name,
				"created_at":timestamp
			}
			db.add_user(user_data['id'], user_data['username'], user_data['first_name'], user_data['last_name'], user_data['language'], user_data['created_at'])
			switch_screen(replies['/start'], chat_id, message_id, keyboard=get_keyboard('/start'))
		else:
			switch_screen(replies['/start'], chat_id, message_id, keyboard=get_keyboard('/start'))
	
	db.add_user_action(user_id, action_type="sent message", completed_at=timestamp)

def show_icebreaker(user_id, chat_id, message_id, screen_id, category="general", topic_num=None):

	if screen_id=="menu_2_1":
		keyboard = json.loads(get_keyboard(screen_id))
		keyboard["inline_keyboard"][0][0]['callback_data'] = f"topic_{topic_num}"
		keyboard = json.dumps(keyboard)
	else:
		keyboard = get_keyboard(screen_id)

	icebreaker = db.get_icebreaker(user_id, category)
	reply = replies[screen_id].replace("[icebreaker]", icebreaker)
	switch_screen(reply, chat_id, message_id, keyboard=keyboard)

def switch_screen(
    reply,
    chat_id,
    message_id,
    delete_previous = True,
    parse_mode = 'Markdown',
    disable_notification = None,
    protect_content = False,
    reply_parameters = None,
    keyboard = None,
) -> None:
    """Sends a message and optionally deletes the previous one."""
    tg_api.send_text_message(
        reply,
        chat_id,
        parse_mode=parse_mode,
        disable_notification=disable_notification,
        protect_content=protect_content,
        reply_parameters=reply_parameters,
        keyboard=keyboard,
    )
    if delete_previous:
        tg_api.delete_message(message_id, chat_id)

def get_keyboard(screen_name, buttons_filepath=BUTTONS_FILEPATH):
	"""Retrieves the button configuration for a given screen."""
	buttons = load_json(buttons_filepath)
	return json.dumps(buttons[screen_name])

def button_is_pressed(message):
	return 'callback_query' in message.keys()

def text_message_is_entered(message):
	return 'message' in message and 'text' in message['message']
