from dotenv import load_dotenv
import os
import random
import requests
import ydb

load_dotenv(override=True)
class DatabaseClient:
	def __init__(self):
		self.YANDEX_TOKEN = os.getenv('YANDEX_TOKEN')
		self.IAM = requests.post('https://iam.api.cloud.yandex.net/iam/v1/tokens', 
			json={'yandexPassportOauthToken': self.YANDEX_TOKEN}).json()

		driver_config = ydb.DriverConfig(
			'grpcs://ydb.serverless.yandexcloud.net:2135', 
			'/ru-central1/b1gg2cdr6pv9ip92ua8l/etnj0tqt4gq80vrmrv7h',
			credentials=ydb.credentials.AccessTokenCredentials(f'Bearer {self.IAM['iamToken']}')
			)

		driver = ydb.Driver(driver_config)
		driver.wait(fail_fast=True, timeout=5)
		self.pool = ydb.SessionPool(driver)

	def execute_query(self, query):
		# create the transaction and execute query.
		return self.pool.retry_operation_sync(lambda s: s.transaction().execute(
			query,
			commit_tx=True,
			settings=ydb.BaseRequestSettings().with_timeout(3).with_operation_timeout(2)
			))

	def add_user(self, user_id, username, first_name, last_name, language, created_at):
		query = f"""
		INSERT INTO users (id, username, first_name, last_name, created_at, level_id, xp, challenges_completed, notification_settings, language)
		VALUES ({user_id}, '{username}', '{first_name}', '{last_name}', TIMESTAMP('{created_at}'), 1, 0, 0, TRUE, '{language}');
		"""
		self.execute_query(query)

	def add_user_action(self, user_id, action_type, completed_at):
		query = f"""
		INSERT INTO user_actions (user_id, action_type, completed_at)
		VALUES ({user_id}, '{action_type}', TIMESTAMP('{completed_at}'))
		"""
		self.execute_query(query)

	def select_user(self, user_id):
		query = f"SELECT * FROM users WHERE id={user_id}"
		result = self.execute_query(query)[0].rows
		return result

	def get_user_property(self, user_id, user_property):
		query = f"SELECT {user_property} FROM users WHERE id={user_id}"
		result = self.execute_query(query)[0].rows[0][user_property]
		return result

	def get_icebreaker(self, user_id, category="general"):
		user_language = self.get_user_property(user_id, "language")
		icebreakers_cnt_query = f"""
		SELECT COUNT(*) AS total_rows FROM icebreakers 
		WHERE category='{category}';
		"""
		total_rows = self.execute_query(icebreakers_cnt_query)[0].rows[0]['total_rows']
		random_offset = random.randint(0, total_rows - 1)

		if user_language=="en":
			column = "desc_en"
		elif user_language=="ru":
			column = "desc_ru"

		query = f"""SELECT {column} FROM icebreakers
		WHERE category='{category}' 
		LIMIT 1 OFFSET {random_offset};"""
		result = self.execute_query(query)[0].rows[0][column]
		return result

	def get_challenge(self, user_id, category):
		user_language = self.get_user_property(user_id, "language")
		user_level = self.get_user_property(user_id, "level_id")
		if user_language=="en":
			column = "desc_en"
		elif user_language=="ru":
			column = "desc_ru"

		query = f"""
		SELECT challenge_id FROM challenge_logs 
		WHERE user_id={user_id}
		"""
		completed_challenges = self.execute_query(query)[0].rows
		if len(completed_challenges)==0:
			query = f"""
			SELECT id, {column} FROM challenges 
			WHERE category='{category}' AND level_required <= {user_level};
			"""
		else:
			completed_challenges = tuple(item['challenge_id'] for item in completed_challenges)
			query = f"""
			SELECT id, {column} FROM challenges 
			WHERE id NOT IN {completed_challenges} AND category='{category}' AND level_required <= {user_level};
			"""
		result = self.execute_query(query)[0].rows[0]
		return result

	def get_random_challenge(self, user_id, category):
		user_language = self.get_user_property(user_id, "language")
		challenges_cnt_query = f"""
		SELECT COUNT(*) AS total_rows FROM challenges 
		WHERE category='{category}';
		"""
		total_rows = self.execute_query(challenges_cnt_query)[0].rows[0]['total_rows']
		random_offset = random.randint(0, total_rows - 1)

		if user_language=="en":
			column = "desc_en"
		elif user_language=="ru":
			column = "desc_ru"

		query = f"""SELECT id, {column} FROM challenges
		WHERE category='{category}' 
		LIMIT 1 OFFSET {random_offset};"""
		result = self.execute_query(query)[0].rows[0]
		return result

	def add_challenge_log(self, user_id, challenge_id, timestamp):
		query = f"""
		SELECT xp FROM challenges 
		WHERE id={challenge_id}
		"""
		xp = self.execute_query(query)[0].rows[0]['xp']

		query = f"""
		SELECT xp, challenges_completed FROM users 
		WHERE id={user_id}
		"""
		user_info = self.execute_query(query)[0].rows[0]
		user_challenges_cnt = user_info['challenges_completed']
		user_xp = user_info['xp']

		new_challenges_cnt = user_challenges_cnt+1
		new_xp = user_xp+xp

		query = f"""
		INSERT INTO challenge_logs (user_id, challenge_id, completed_at)
		VALUES ({user_id}, {challenge_id}, TIMESTAMP('{timestamp}'));
		"""
		self.execute_query(query)
		query = f"""
		UPDATE users
		SET xp = {new_xp}, challenges_completed = {new_challenges_cnt}
		WHERE id={user_id};
		"""
		self.execute_query(query)
		return {"challenge_xp":xp, "user_xp":new_xp}

	def get_level_info(self, user_id, level_id):
		user_language = self.get_user_property(user_id, "language")
		if user_language=="en":
			column = "level_desc_en"
		elif user_language=="ru":
			column = "level_desc_ru"
		query = f"""
		SELECT level_num, {column}, xp_required FROM levels 
		WHERE id={level_id}
		"""
		result = self.execute_query(query)[0].rows[0]
		return result

	def update_user_level(self, user_id, level_id):
		query = f"""
		UPDATE users
		SET level_id = {level_id}
		WHERE id={user_id};
		"""
		self.execute_query(query)

	def update_notification_settings(self, user_id, new_setting):
		query = f"""
		UPDATE users
		SET notification_settings = {new_setting}
		WHERE id={user_id};
		"""
		self.execute_query(query)

	def update_language_settings(self, user_id, new_setting):
		query = f"""
		UPDATE users
		SET language = '{new_setting}'
		WHERE id={user_id};
		"""
		self.execute_query(query)

	def send_review(self, user_id, review_text, timestamp):
		query = f"""
		INSERT INTO user_reviews (user_id, text, completed_at)
		VALUES ({user_id}, '{review_text}', TIMESTAMP('{timestamp}'))
		"""
		self.execute_query(query)

if __name__=="__main__":
	db = DatabaseClient()
	result = db.execute_query("""SELECT 1 FROM users""")
	print(result)