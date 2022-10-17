
from _settings import TOKEN
from aiogram import Bot
from aiogram.dispatcher import Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import Message, User
# from aiogram.contrib.middlewares.logging import LoggingMiddleware

import sqlite3


bot = Bot(TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())
# dp.middleware.setup(LoggingMiddleware())

connect = sqlite3.connect('base.db')
cursor = connect.cursor()


class Database:
    def __init__(self):
        self.connect = sqlite3.connect('base.db')
        self.cursor = self.connect.cursor()

    async def save_chat_project(self, project_id, id_chat):
        with self.connect:
            self.cursor.execute('UPDATE settings SET project_id = ? WHERE id_chat = ?', (project_id, id_chat))

    async def save_new_chat(self, id_chat, title):
        with self.connect:
            self.cursor.execute(
                '''INSERT INTO settings (id_chat, title, statistics_for_everyone, include_admins_in_statistics, 
                sort_by_messages, do_not_output_the_number_of_messages, do_not_output_the_number_of_characters, 
                period_of_activity, report_enabled, project_id, curators_group, enable_group, 
                last_notify_date, last_notify_message_id_date, 
                do_not_output_name_from_registration, check_channel_subscription) 
                VALUES (?, ?, False, False, False, False, False, 7, False, 0, False, True, 
                datetime("now"), datetime("now"), False, False)''', (id_chat, title))

    async def save_new_title(self, id_chat, title):
        with self.connect:
            self.cursor.execute('UPDATE settings SET title = ? WHERE id_chat = ?', (title, id_chat))

    async def migrate_to_chat_id(self, new_id_chat, id_chat):
        with self.connect:
            self.cursor.execute('UPDATE chats SET id_chat = ? WHERE id_chat = ?', (new_id_chat, id_chat))
            self.cursor.execute('UPDATE meetings SET id_chat = ? WHERE id_chat = ?', (new_id_chat, id_chat))
            self.cursor.execute('UPDATE messages SET id_chat = ? WHERE id_chat = ?', (new_id_chat, id_chat))
            self.cursor.execute('UPDATE settings SET id_chat = ? WHERE id_chat = ?', (new_id_chat, id_chat))

    async def save_or_update_new_title(self, id_chat, title):
        with self.connect:
            self.cursor.execute('SELECT id_chat FROM settings WHERE id_chat = ?', (id_chat,))
            result = cursor.fetchone()
            if result is None:
                await base.save_new_chat(id_chat, title)
            else:
                self.cursor.execute('UPDATE settings SET enable_group = True, title = ? WHERE id_chat = ?',
                                    (title, id_chat))

    async def save_chat_disable(self, id_chat):
        with self.connect:
            self.cursor.execute('UPDATE settings SET enable_group = False WHERE id_chat = ?', (id_chat,))

    async def save_user_disable_in_chat(self, id_chat, id_user, date_of_the_last_message):
        with self.connect:
            self.cursor.execute(
                'UPDATE chats SET deleted = True, date_of_the_last_message = ? WHERE id_chat = ? AND id_user = ?',
                (date_of_the_last_message, id_chat, id_user))

            self.cursor.execute(
                'SELECT projects.channel_id FROM settings '
                'INNER JOIN projects ON settings.project_id = projects.project_id '
                'AND NOT projects.channel_id = 0 '
                'AND settings.id_chat = ?', (id_chat,))
            return self.cursor.fetchone()

    async def save_message_count(self, id_chat, id_user, date_of_the_last_message, characters, message_id):
        with self.connect:
            self.cursor.execute('INSERT INTO messages (id_chat, id_user, date, characters, message_id) '
                                'VALUES (?, ?, ?, ?, ?)',
                                (id_chat, id_user, date_of_the_last_message, characters, message_id))

    async def insert_or_update_chats_and_users(self, id_chat, user: User, characters, date_of_the_last_message):
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
        self.cursor.execute('SELECT id_user FROM users WHERE id_user = ?', (id_user,))
        result = self.cursor.fetchone()

        if result is None:
            text = 'INSERT INTO users (id_user, first_name, last_name, username, language_code, ' \
                   'registration_date, registration_field, FIO, address, tel, mail, projects) ' \
                   'VALUES (?, ?, ?, ?, ?, datetime("now"), "", "", "", "", "", "")'
            values = (id_user, first_name, last_name, username, language_code)
        else:
            text = 'UPDATE users SET first_name = ?, last_name = ?, username = ?, language_code = ?, ' \
                   'registration_field = "", projects = "" ' \
                   'WHERE id_user = ?'
            values = (first_name, last_name, username, language_code, id_user)
        self.cursor.execute(text, values)

        # chats
        self.cursor.execute('SELECT id_chat FROM chats WHERE id_chat = ? AND id_user = ?', (id_chat, id_user))
        result = self.cursor.fetchone()

        if result is None:
            text = 'INSERT INTO chats (id_chat, id_user, first_name, last_name, username, messages, characters, ' \
                   'deleted, date_of_the_last_message) VALUES (?, ?, ?, ?, ?, 1, ?, False, ?)'
            values = (id_chat, id_user, first_name, last_name, username, characters, date_of_the_last_message)
        else:
            text = 'UPDATE chats SET messages = messages + 1, characters = characters + ?, first_name = ?, ' \
                   'last_name = ?, username = ?, deleted = False, date_of_the_last_message = ? ' \
                   'WHERE id_chat = ? AND id_user = ?'
            values = (characters, first_name, last_name, username, date_of_the_last_message, id_chat, id_user)

        self.cursor.execute(text, values)

    async def save_menu_message_id(self, message: Message):
        user_id = message.chat.id
        message_id = message.message_id

        with self.connect:
            self.cursor.execute('UPDATE users SET menu_message_id = ? WHERE id_user = ?', (message_id, user_id))

    async def get_menu_message_id(self, user_id):
        self.cursor.execute('SELECT IFNULL(menu_message_id, 0) FROM users WHERE id_user = ?', (user_id,))
        result = self.cursor.fetchone()

        return result[0]


base = Database()
