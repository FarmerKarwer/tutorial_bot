import os
import random
import requests
import ydb

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

if __name__=="__main__":
	db = DatabaseClient()
	result = db.execute_query("""SELECT 1 FROM users""")
	print(result)