
from _settings import TOKEN, SKIP_ERROR_TEXT, THIS_IS_BOT_NAME, LOGS_CHANNEL_ID
from aiogram import Bot
from aiogram.dispatcher import Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import Message, User
# from aiogram.contrib.middlewares.logging import LoggingMiddleware
import psycopg2
import datetime

bot = Bot(TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())
# dp.middleware.setup(LoggingMiddleware())

connect = psycopg2.connect(dbname='base', user='postgres', password='postgres', host='localhost')
cursor = connect.cursor()


async def send_error(text, error_text):
    if error_text == SKIP_ERROR_TEXT:
        return
    text_message = f'@{THIS_IS_BOT_NAME} error\n\nQuery text:\n{text}\n\nError text:\n{error_text}'
    length_message = len(text_message)
    if length_message > 4096:
        crop_characters = length_message - 4096 - 5
        text_message = f'@{THIS_IS_BOT_NAME} error\n\nQuery text:\n{text[crop_characters]} \<\.\.\.\>\n\nError text:\n{error_text}'

    await bot.send_message(text=text_message, chat_id=LOGS_CHANNEL_ID)


class Database:
    def __init__(self):
        self.connect = psycopg2.connect(dbname='base', user='postgres', password='postgres', host='localhost')
        self.cursor = self.connect.cursor()

    async def save_chat_project(self, project_id, id_chat):
        try:
            with self.connect:
                self.cursor.execute('UPDATE settings SET project_id = %s WHERE id_chat = %s', (project_id, id_chat))
        except Exception as e:
            await send_error('', str(e))

    async def save_new_chat(self, id_chat, title):
        try:
            with self.connect:
                self.cursor.execute(
                    '''INSERT INTO settings (id_chat, title, statistics_for_everyone, include_admins_in_statistics, 
                    sort_by_messages, do_not_output_the_number_of_messages, do_not_output_the_number_of_characters, 
                    period_of_activity, report_enabled, project_id, curators_group, enable_group, 
                    last_notify_date, last_notify_message_id_date, 
                    do_not_output_name_from_registration, check_channel_subscription) 
                    VALUES (%s, %s, False, False, False, False, False, 7, False, 0, False, True, 
                    datetime("now"), datetime("now"), False, False)''', (id_chat, title))
        except Exception as e:
            await send_error('', str(e))

    async def save_new_title(self, id_chat, title):
        try:
            with self.connect:
                self.cursor.execute('UPDATE settings SET title = %s WHERE id_chat = %s', (title, id_chat))
        except Exception as e:
            await send_error('', str(e))

    async def migrate_to_chat_id(self, new_id_chat, id_chat):
        try:
            with self.connect:
                self.cursor.execute('UPDATE chats SET id_chat = %s WHERE id_chat = %s', (new_id_chat, id_chat))
                self.cursor.execute('UPDATE meetings SET id_chat = %s WHERE id_chat = %s', (new_id_chat, id_chat))
                self.cursor.execute('UPDATE messages SET id_chat = %s WHERE id_chat = %s', (new_id_chat, id_chat))
                self.cursor.execute('UPDATE settings SET id_chat = %s WHERE id_chat = %s', (new_id_chat, id_chat))
        except Exception as e:
            await send_error('', str(e))

    async def save_or_update_new_title(self, id_chat, title):
        try:
            with self.connect:
                self.cursor.execute('SELECT id_chat FROM settings WHERE id_chat = %s', (id_chat,))
                result = cursor.fetchone()
                if result is None:
                    await base.save_new_chat(id_chat, title)
                else:
                    self.cursor.execute('UPDATE settings SET enable_group = True, title = %s WHERE id_chat = %s',
                                        (title, id_chat))
        except Exception as e:
            await send_error('', str(e))

    async def save_chat_disable(self, id_chat):
        try:
            with self.connect:
                self.cursor.execute('UPDATE settings SET enable_group = False WHERE id_chat = %s', (id_chat,))
        except Exception as e:
            await send_error('', str(e))

    async def save_user_disable_in_chat(self, id_chat, id_user, date_of_the_last_message):
        try:
            with self.connect:
                self.cursor.execute(
                    'UPDATE chats SET deleted = True, date_of_the_last_message = %s WHERE id_chat = %s AND id_user = %s',
                    (date_of_the_last_message, id_chat, id_user))

                self.cursor.execute(
                    'SELECT projects.channel_id FROM settings '
                    'INNER JOIN projects ON settings.project_id = projects.project_id '
                    'AND NOT projects.channel_id = 0 '
                    'AND settings.id_chat = %s', (id_chat,))
                return self.cursor.fetchone()
        except Exception as e:
            await send_error('', str(e))

    async def save_message_count(self, id_chat, id_user, date_of_the_last_message, characters, message_id):
        try:
            with self.connect:
                self.cursor.execute('INSERT INTO messages (id_chat, id_user, date, characters, message_id) '
                                    'VALUES (%s, %s, %s, %s, %s)',
                                    (id_chat, id_user, date_of_the_last_message, characters, message_id))
        except Exception as e:
            await send_error('', str(e))

    async def insert_or_update_chats_and_users(self, id_chat, user: User, characters, date_of_the_last_message):
        try:
            id_user = user.id
            first_name = user.first_name
            last_name = user.last_name
            username = user.username
            language_code = user.language_code

            if last_name is None:
                last_name = ''

            if username is None:
                username = ''

            # id_user
            self.cursor.execute('SELECT id_user FROM users WHERE id_user = %s', (id_user,))
            result = self.cursor.fetchone()

            if result is None:
                today = datetime.datetime.now()
                text = 'INSERT INTO users (id_user, first_name, last_name, username, language_code, ' \
                       'registration_date, registration_field, fio, address, tel, mail, projects) ' \
                       'VALUES (%s, %s, %s, %s, %s, %s, NULL, NULL, NULL, NULL, NULL, NULL)'
                values = (id_user, first_name, last_name, username, language_code, today)
            else:
                text = 'UPDATE users SET first_name = %s, last_name = %s, username = %s, language_code = %s, ' \
                       'registration_field = NULL, projects = NULL ' \
                       'WHERE id_user = %s'
                values = (first_name, last_name, username, language_code, id_user)
            self.cursor.execute(text, values)

            # chats
            self.cursor.execute('SELECT id_chat FROM chats WHERE id_chat = %s AND id_user = %s', (id_chat, id_user))
            result = self.cursor.fetchone()

            if result is None:
                text = 'INSERT INTO chats (id_chat, id_user, messages, characters, ' \
                       'deleted, date_of_the_last_message) VALUES (%s, %s, 1, %s, False, %s)'
                values = (id_chat, id_user, characters, date_of_the_last_message)
            else:
                text = 'UPDATE chats SET messages = messages + 1, characters = characters + %s, deleted = False, ' \
                       'date_of_the_last_message = %s ' \
                       'WHERE id_chat = %s AND id_user = %s'
                values = (characters, date_of_the_last_message, id_chat, id_user)

            self.cursor.execute(text, values)

        except Exception as e:
            await send_error('', str(e))

    async def save_menu_message_id(self, message: Message):
        try:
            user_id = message.chat.id
            message_id = message.message_id

            with self.connect:
                self.cursor.execute('UPDATE users SET menu_message_id = %s WHERE id_user = %s', (message_id, user_id))

        except Exception as e:
            await send_error('', str(e))

    async def get_menu_message_id(self, user_id):
        try:
            self.cursor.execute('SELECT coalesce(menu_message_id, 0) FROM users WHERE id_user = %s', (user_id,))
            result = self.cursor.fetchone()

            return result[0]
        
        except Exception as e:
            await send_error('', str(e))


base = Database()
