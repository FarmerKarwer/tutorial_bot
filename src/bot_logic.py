import tg_api
import json
from cache_manager import CacheManager
from database import DatabaseClient
from utils import load_json, unix_to_timestamp

# Constants for file paths
REPLIES_RUS_FILEPATH = "./ui/replies.json"
BUTTONS_RUS_FILEPATH = "./ui/buttons.json"
REPLIES_ENG_FILEPATH = "./ui/replies_en.json"
BUTTONS_ENG_FILEPATH = "./ui/buttons_en.json"

db = DatabaseClient()
cache = CacheManager('cache')

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
	global replies
	replies = get_replies_for_user_language(user_id)

	data_to_save = {"chat_id":chat_id, "message_id":message_id, "callback_data":callback_data, "text":None}

	# Use the logic for callback query
	def show_callback_reply(screen_id, user_id):
		switch_screen(replies[screen_id], chat_id, message_id, keyboard=get_keyboard(screen_id, user_id))

	DEFAULT_CALLBACK_SCREENS = (
		"/start", "menu_2", "menu_2_1", "menu_3",
		 "menu_5", "menu_5_2", "menu_5_3"
		)

	SPECIAL_CALLBACK_HANDLERS = {
	"menu_1": lambda: show_icebreaker(user_id, chat_id, message_id, screen_id="menu_1"),
	"menu_3_1_1": lambda: show_challenge_confirmation(user_id, chat_id, message_id),
	"menu_3_1_new_lev": lambda: show_new_level_reached(user_id, chat_id, message_id),
	"menu_4": lambda: show_stats(user_id, chat_id, message_id),
	"menu_5_1": lambda: show_current_notif_settings(user_id, chat_id, message_id),
	"menu_5_1_saved": lambda: show_notif_settings_updated(user_id, chat_id, message_id),
	"menu_5_3_sent": lambda: show_review_sent(user_id, chat_id, message_id, timestamp)
	}
	SPECIAL_CALLBACK_SCREENS = SPECIAL_CALLBACK_HANDLERS.keys()

	if callback_data in SPECIAL_CALLBACK_SCREENS:
		action = SPECIAL_CALLBACK_HANDLERS.get(callback_data)
		action()
	elif callback_data in DEFAULT_CALLBACK_SCREENS:
		show_callback_reply(callback_data, user_id)
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
	elif callback_data.startswith("menu_3_1_2"):
		show_challenge_completed(user_id, chat_id, message_id, callback_data, timestamp)
	elif callback_data.startswith("menu_3_1_"):
		data_to_save = show_challenge(user_id, chat_id, message_id, callback_data, cache_data=data_to_save)
	elif callback_data.startswith("menu_5_2_saved_"):
		show_lang_settings_updated(user_id, chat_id, message_id, callback_data)
	else:
		print("ERROR: No callback data")

	db.add_user_action(user_id, action_type="pressed button", completed_at=timestamp)
	cache.save(user_id, json.dumps(data_to_save))

def handle_text_message(message):
	# Get the data
	text = message['message']['text']
	chat_id = message['message']['chat']['id']
	message_id = message['message']['message_id']
	user_id = message['message']['from']['id']
	unix_timestamp = message['message']['date']
	timestamp = unix_to_timestamp(unix_timestamp)
	previous_screen = json.loads(cache.get(user_id)['data'])['callback_data']
	global replies
	replies = get_replies_for_user_language(user_id)

	data_to_save = {"chat_id":chat_id, "message_id":message_id, "callback_data":None, "text":text}

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
		replies = get_replies_for_user_language(user_id)
		switch_screen(replies['/start'], chat_id, message_id, keyboard=get_keyboard('/start', user_id))
	elif previous_screen=='menu_5_3':
		show_review_confirmation(user_id, chat_id, message_id, text)
	
	db.add_user_action(user_id, action_type="sent message", completed_at=timestamp)
	cache.save(user_id, json.dumps(data_to_save))

def show_icebreaker(user_id, chat_id, message_id, screen_id, category="general", topic_num=None):

	if screen_id=="menu_2_1":
		keyboard = json.loads(get_keyboard(screen_id, user_id))
		keyboard["inline_keyboard"][0][0]['callback_data'] = f"topic_{topic_num}"
		keyboard = json.dumps(keyboard)
	else:
		keyboard = get_keyboard(screen_id, user_id)

	icebreaker = db.get_icebreaker(user_id, category)
	reply = replies[screen_id].replace("[icebreaker]", icebreaker)
	switch_screen(reply, chat_id, message_id, keyboard=keyboard)

def show_challenge(user_id, chat_id, message_id, callback_data, cache_data):
	difficulty_dict = {
		"novice":["Beginner", 1, "Новичок", "Novice"],
		"beginner":["Beginner+", 1, "Начинающий", "Beginner"],
		"mid":["Intermediate", 2, "Средний", "Intermediate"],
		"uppermid":["Advanced", 4, "Продвинутый", "Advanced"],
		"adv":["Expert", 6, "Ветеран", "Veteran"],
		"cringe":["Cringe", 10, "Кринж-грандмастер", "Cringe Grandmaster"]
		}
	difficulty_idx = callback_data.split('_')[-1]
	chosen_difficulty_list = difficulty_dict[difficulty_idx]

	user_language = db.get_user_property(user_id, "language")
	if user_language =="ru":
		lang_idx = 2
	elif user_language =="en":
		lang_idx = 3

	user_level = db.get_user_property(user_id, "level_id")
	if user_level < chosen_difficulty_list[1]:
		reply = replies['menu_3_1_closed'].replace('[level]', str(chosen_difficulty_list[1]))
		reply = reply.replace('[difficulty]', chosen_difficulty_list[lang_idx])
		switch_screen(reply, chat_id, message_id, keyboard=get_keyboard('menu_3_1_closed', user_id))
	else:
		chosen_difficulty = chosen_difficulty_list[0]
		try:
			if callback_data.startswith("menu_3_1_random")==False:
				challenge = db.get_challenge(user_id, chosen_difficulty)
			else:
				challenge=db.get_random_challenge(user_id, chosen_difficulty)
		except IndexError:
			keyboard = json.loads(get_keyboard('menu_3_1_no_challenges', user_id))
			keyboard['inline_keyboard'][1][0]['callback_data'] = 'menu_3_1_random'+f"_{difficulty_idx}"
			keyboard = json.dumps(keyboard)
			switch_screen(replies['menu_3_1_no_challenges'], chat_id, message_id, keyboard=keyboard)
			cache_data['challenge_category'] = callback_data
			return cache_data
		challenge_text = challenge[1]
		challenge_id = challenge[0]
		reply = replies['menu_3_1'].replace('[level]', chosen_difficulty_list[lang_idx])
		reply = reply.replace('[challenge]', challenge_text)
		switch_screen(reply, chat_id, message_id, keyboard=get_keyboard('menu_3_1', user_id))
		cache_data['challenge_id'] = challenge_id
		cache_data['challenge_category'] = callback_data
		return cache_data

def show_challenge_confirmation(user_id, chat_id, message_id):
	cache_data = json.loads(cache.get(user_id)['data'])
	challenge_id = cache_data['challenge_id']
	challenge_category = cache_data['challenge_category']
	keyboard = json.loads(get_keyboard('menu_3_1_1', user_id))
	keyboard['inline_keyboard'][0][0]['callback_data'] = "menu_3_1_2"+f"_{challenge_id}"
	keyboard['inline_keyboard'][0][1]['callback_data'] = challenge_category
	keyboard = json.dumps(keyboard)
	switch_screen(replies['menu_3_1_1'], chat_id, message_id, keyboard=keyboard)

def show_challenge_completed(user_id, chat_id, message_id, callback_data, timestamp):
	challenge_id = callback_data.split('_')[-1]
	challenge_info = db.add_challenge_log(user_id, challenge_id, timestamp)
	xp_given = challenge_info['challenge_xp']
	user_xp_updated = challenge_info['user_xp']

	user_level = db.get_user_property(user_id, 'level_id')
	user_level_number = db.get_level_info(user_id, user_level)['level_num']

	upper_level = user_level_number+1
	upper_level_required_xp = db.get_level_info(user_id, upper_level)['xp_required']

	if user_xp_updated<upper_level_required_xp:
		keyboard = json.loads(get_keyboard('menu_3_1_2', user_id))
		keyboard['inline_keyboard'][0][0]['callback_data'] = "/start"
		keyboard = json.dumps(keyboard)
	else:
		db.update_user_level(user_id, upper_level)
		keyboard = get_keyboard('menu_3_1_2', user_id)

	reply = replies['menu_3_1_2'].replace('[xp]', str(xp_given))
	switch_screen(reply, chat_id, message_id, keyboard=keyboard)

def show_new_level_reached(user_id, chat_id, message_id):
	user_level = db.get_user_property(user_id, 'level_id')
	user_level_info = db.get_level_info(user_id, user_level)
	level_number = user_level_info['level_num']
	level_description = user_level_info[1]

	reply = replies['menu_3_1_new_lev']['main_message']
	reply = reply.replace('[level_num]', str(level_number))
	reply = reply.replace('[level_desc]', level_description)

	if level_number in (2,4,6,10):
		reply = reply+replies['menu_3_1_new_lev']['bonus_message']

	switch_screen(reply, chat_id, message_id, keyboard=get_keyboard('menu_3_1_new_lev', user_id))

def show_stats(user_id, chat_id, message_id):
	user_info = db.select_user(user_id)[0]
	level_num = user_info['level_id']
	level_desc = db.get_level_info(user_id, level_num)[1]
	xp = user_info['xp']
	challenge_cnt = user_info['challenges_completed']
	upper_level_xp_required = db.get_level_info(user_id, level_num+1)['xp_required']
	xp_diff = upper_level_xp_required - xp

	reply = replies['menu_4']
	to_update = {"[level_num]":str(level_num), 
				"[level_desc]":level_desc, 
				"[xp]": str(xp), "[xp_diff]": str(xp_diff), "[challenge_cnt]":str(challenge_cnt)}
	for key, value in to_update.items():
		reply = reply.replace(key, value)

	switch_screen(reply, chat_id, message_id, keyboard=get_keyboard('menu_4', user_id))

def show_current_notif_settings(user_id, chat_id, message_id):
	current_settings = db.get_user_property(user_id, "notification_settings")
	if current_settings==True:
		reply = replies['menu_5_1'].replace('[status]', "включены")
		keyboard = get_keyboard('menu_5_1', user_id)
	else:
		reply = replies['menu_5_1'].replace('[status]', "отключены")
		keyboard = json.loads(get_keyboard('menu_5_1', user_id))
		keyboard["inline_keyboard"][0][0]['text'] = "Включить"
		keyboard = json.dumps(keyboard)
	switch_screen(reply, chat_id, message_id, keyboard=keyboard)

def show_notif_settings_updated(user_id, chat_id, message_id):
	current_settings = db.get_user_property(user_id, "notification_settings")
	if current_settings==True:
		db.update_notification_settings(user_id, False)
		reply = replies['menu_5_1_saved'].replace('[status]', "отключены")
	else:
		db.update_notification_settings(user_id, True)
		reply = replies['menu_5_1_saved'].replace('[status]', "включены")
	switch_screen(reply, chat_id, message_id, keyboard=get_keyboard('menu_5_1_saved', user_id))

def show_lang_settings_updated(user_id, chat_id, message_id, callback_data):
	current_settings = db.get_user_property(user_id, "language")
	language = callback_data.split('_')[-1]
	if language == current_settings:
		switch_screen(replies['menu_5_2_closed'], chat_id, message_id, keyboard=get_keyboard('menu_5_2_closed', user_id))
	else:
		db.update_language_settings(user_id, language)
		switch_screen(replies['menu_5_2_saved'], chat_id, message_id, keyboard=get_keyboard('menu_5_2_saved', user_id))

def show_review_confirmation(user_id, chat_id, message_id, text):
	reply = replies['menu_5_3_1'].replace('[review]', text)
	switch_screen(reply, chat_id, message_id, keyboard=get_keyboard('menu_5_3_1', user_id))

def show_review_sent(user_id, chat_id, message_id, timestamp):
	review = json.loads(cache.get(user_id)['data'])['text']
	db.send_review(user_id, review, timestamp)
	switch_screen(replies['menu_5_3_sent'], chat_id, message_id, keyboard=get_keyboard('menu_5_3_sent', user_id))


def get_replies_for_user_language(user_id):
	try:
		language_settings = db.get_user_property(user_id, 'language')
	except IndexError:
		return None

	if language_settings and language_settings=="ru":
		replies = load_json(REPLIES_RUS_FILEPATH)
	else:
		replies = load_json(REPLIES_ENG_FILEPATH)
	return replies

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

def get_keyboard(screen_name, user_id):
	"""Retrieves the button configuration for a given screen."""
	language_settings = db.get_user_property(user_id, 'language')

	if language_settings and language_settings=="ru":
		buttons = load_json(BUTTONS_RUS_FILEPATH)
	else:
		buttons = load_json(BUTTONS_ENG_FILEPATH)

	return json.dumps(buttons[screen_name])

def button_is_pressed(message):
	return 'callback_query' in message.keys()

def text_message_is_entered(message):
	return 'message' in message and 'text' in message['message']
