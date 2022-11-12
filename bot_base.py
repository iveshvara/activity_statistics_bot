
# from aiogram.contrib.middlewares.logging import LoggingMiddleware
import traceback

import psycopg2
from aiogram import Bot
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import Dispatcher
from aiogram.types import Message, User

from _settings import TOKEN, SKIP_ERROR_TEXT, THIS_IS_BOT_NAME, LOGS_CHANNEL_ID
from service import get_today, get_name_tg, shielding

bot = Bot(TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())
# dp.middleware.setup(LoggingMiddleware())

connect = psycopg2.connect(dbname='base', user='postgres', password='postgres', host='localhost')
cursor = connect.cursor()


async def send_error(text: str, error_text: str, traceback_text: str):
    if error_text.find(SKIP_ERROR_TEXT) > -1:
        return

    if not isinstance(text, str):
        text = str(text)

    text_message = f'@{THIS_IS_BOT_NAME} error'
    if text is not None and len(text) > 0:
        text_message += f'\n\nQuery text:\n{text}'
    if error_text is not None and len(error_text) > 0:
        text_message += f'\n\nError text:\n{error_text}'

    traceback_result_text = ''
    if traceback_text is not None:
        if len(traceback_text) < 500:
            traceback_result_text = traceback_text
        else:
            my_files = ('bot_base.py', 'handlers.py', 'main.py', 'main_functions.py', 'service.py', 'utility_functions.py')
            positions_list = []
            traceback_result_text = ''

            for i in my_files:
                positions = traceback_text.find(i)
                if positions > -1:
                    positions_list.append(positions)

            positions_list.sort()
            for i in positions_list:
                part_text = traceback_text[i:]
                position_part_text = part_text.find('\n')
                part_text = part_text[:position_part_text]
                part_text = part_text.replace('py",', 'py,')
                traceback_result_text += '\n' + part_text

            traceback_result_text = '\n\nTraceback:' + traceback_result_text

    text_message += traceback_result_text

    length_message = len(text_message)
    if length_message > 4096:
        crop_characters = length_message - 4096 - 5
        text_message = f'@{THIS_IS_BOT_NAME} error\n\nQuery text:\n{text[crop_characters]} \<\.\.\.\>\n\nError text:\n{error_text}'

    await bot.send_message(text=text_message, chat_id=LOGS_CHANNEL_ID)


def get_names_and_values_of_the_request_details(description, result):
    text_result = ''
    for i in description:
        index = description.index(i)
        text_result += i.name + ': ' + str(result[index]) + '\n'

    return text_result


class Database:
    def __init__(self):
        self.connect = psycopg2.connect(dbname='base', user='postgres', password='postgres', host='localhost')
        self.cursor = self.connect.cursor()

    async def save_chat_project(self, project_id, id_chat):
        try:
            with self.connect:
                self.cursor.execute("UPDATE settings SET project_id = %s WHERE id_chat = %s", (project_id, id_chat))
        except Exception as e:
            await send_error(self.cursor.query, str(e), traceback.format_exc())

    async def save_new_chat(self, id_chat, title):
        try:
            today = get_today()
            with self.connect:
                self.cursor.execute(
                    """INSERT INTO settings (
                        id_chat, 
                        title, 
                        statistics_for_everyone, 
                        include_admins_in_statistics, 
                        sort_by, 
                        do_not_output_the_number_of_messages, 
                        do_not_output_the_number_of_characters, 
                        period_of_activity, 
                        report_enabled, 
                        project_id, 
                        curators_group, 
                        enable_group, 
                        last_notify_date, 
                        last_notify_message_id_date, 
                        do_not_output_name_from_registration, 
                        check_channel_subscription) 
                    VALUES (%s, %s, False, False, 'characters', False, False, 7, False, 0, False, True, 
                    %s, %s, False, False)
                    ON CONFLICT (id_chat) DO 
                    UPDATE SET enable_group = True, title = %s WHERE settings.id_chat = %s""",
                    (id_chat, title, today, today,
                     title, id_chat))
        except Exception as e:
            await send_error(self.cursor.query, str(e), traceback.format_exc())

    async def save_new_title(self, id_chat, title):
        try:
            with self.connect:
                self.cursor.execute("UPDATE settings SET title = %s WHERE id_chat = %s", (title, id_chat))
        except Exception as e:
            await send_error(self.cursor.query, str(e), traceback.format_exc())

    async def migrate_to_chat_id(self, new_id_chat, id_chat):
        try:
            with self.connect:
                self.cursor.execute("UPDATE chats SET id_chat = %s WHERE id_chat = %s", (new_id_chat, id_chat))
                # self.cursor.execute("UPDATE meetings SET id_chat = %s WHERE id_chat = %s", (new_id_chat, id_chat))
                self.cursor.execute("UPDATE messages SET id_chat = %s WHERE id_chat = %s", (new_id_chat, id_chat))
                self.cursor.execute("UPDATE settings SET id_chat = %s WHERE id_chat = %s", (new_id_chat, id_chat))
        except Exception as e:
            await send_error(self.cursor.query, str(e), traceback.format_exc())

    async def save_chat_disable(self, id_chat):
        try:
            with self.connect:
                self.cursor.execute("UPDATE settings SET enable_group = False WHERE id_chat = %s", (id_chat,))
        except Exception as e:
            await send_error(self.cursor.query, str(e), traceback.format_exc())

    async def save_user_disable_in_chat(self, id_chat, id_user, date_of_the_last_message=None):
        if date_of_the_last_message is None:
            date_of_the_last_message = get_today()

        try:
            with self.connect:
                self.cursor.execute(
                    """UPDATE chats SET 
                        deleted = True, 
                        date_of_the_last_message = %s 
                    WHERE 
                        id_chat = %s 
                            AND id_user = %s""",
                    (date_of_the_last_message, id_chat, id_user))

            self.cursor.execute(
                """SELECT 
                    projects.channel_id 
                FROM settings 
                    INNER JOIN projects 
                    ON settings.project_id = projects.project_id 
                        AND NOT projects.channel_id = 0 
                        AND settings.id_chat = %s""", (id_chat,))
            return self.cursor.fetchone()
        except Exception as e:
            await send_error(self.cursor.query, str(e), traceback.format_exc())

    async def save_message_count(self, id_chat, id_user, date_of_the_last_message, characters, message_id):
        try:
            with self.connect:
                self.cursor.execute("""INSERT INTO messages (id_chat, id_user, date, characters, message_id) 
                                    VALUES (%s, %s, %s, %s, %s)""",
                                    (id_chat, id_user, date_of_the_last_message, characters, message_id))
        except Exception as e:
            await send_error(self.cursor.query, str(e), traceback.format_exc())

    async def insert_or_update_users(self, user: User):
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

            with self.connect:
                self.cursor.execute(
                    """INSERT INTO users(
                        id_user, 
                        first_name, 
                        last_name, 
                        username, 
                        language_code, 
                        registration_date, 
                        role) 
                    VALUES (%s, %s, %s, %s, %s, %s, 'user')
                    ON CONFLICT (id_user) DO UPDATE SET 
                        first_name = %s, 
                        last_name = %s, 
                        username = %s, 
                        language_code = %s""",
                    (id_user, first_name, last_name, username, language_code, get_today(),
                     first_name, last_name, username, language_code))

        except Exception as e:
            await send_error(self.cursor.query, str(e), traceback.format_exc())

    async def insert_or_update_chats(self, id_chat, id_user, characters, date_of_the_last_message):
        try:
            with self.connect:
                self.cursor.execute(
                    """INSERT INTO chats (
                        id_chat, 
                        id_user, 
                        messages, 
                        characters, 
                        deleted, 
                        date_of_the_last_message) 
                    VALUES (%s, %s, 1, %s, False, %s)
                    ON CONFLICT (id_chat, id_user) DO UPDATE SET 
                        messages = chats.messages + 1, 
                        characters = chats.characters + %s, 
                        deleted = False, 
                        date_of_the_last_message = %s""",
                    (id_chat, id_user, characters, date_of_the_last_message,
                     characters, date_of_the_last_message))

        except Exception as e:
            await send_error(self.cursor.query, str(e), traceback.format_exc())

    async def save_menu_message_id(self, message: Message):
        try:
            id_user = message.chat.id
            message_id = message.message_id

            with self.connect:
                self.cursor.execute("UPDATE users SET menu_message_id = %s WHERE id_user = %s", (message_id, id_user))

        except Exception as e:
            await send_error(self.cursor.query, str(e), traceback.format_exc())

    async def get_menu_message_id(self, id_user):
        try:
            self.cursor.execute("SELECT coalesce(menu_message_id, 0) FROM users WHERE id_user = %s", (id_user,))
            result = self.cursor.fetchone()
            if result is None:
                return 0
            else:
                return result[0]

        except Exception as e:
            await send_error(self.cursor.query, str(e), traceback.format_exc())

    async def its_admin(self, id_user):
        try:
            self.cursor.execute("SELECT NOT role = 'user' FROM users WHERE id_user = %s", (id_user,))
            result = self.cursor.fetchone()
            if result is None:
                return False
            else:
                return result[0]

        except Exception as e:
            await send_error(self.cursor.query, str(e), traceback.format_exc())

    async def get_chats_admin_user(self, project_id, id_user, id_chat):
        try:
            self.cursor.execute(
                """SELECT 
                    chats.id_chat, 
                    settings.title 
                FROM users 
                    INNER JOIN chats 
                        ON users.id_user = chats.id_user 
                            AND NOT chats.deleted 
                    INNER JOIN settings 
                        ON chats.id_chat = settings.id_chat 
                            AND settings.enable_group 
                            AND NOT settings.curators_group 
                            AND settings.project_id = %s 
                WHERE 
                    users.id_user = %s
                        AND (%s OR chats.id_chat = %s)""", (project_id, id_user, id_chat == 0, id_chat))
            result = self.cursor.fetchall()

            return result

        except Exception as e:
            await send_error(self.cursor.query, str(e), traceback.format_exc())

    async def get_users_in_chats(self, project_id, id_chat):
        try:
            self.cursor.execute(
                """SELECT
                    chats.id_user, 
                    users.first_name, 
                    users.last_name, 
                    users.username, 
                    users.fio, 
                    CASE
                        WHEN users.fio IS NULL
                            THEN concat(users.first_name, ' ', users.last_name) 
                        ELSE users.fio 
                    END AS name, 
                    SUM(CASE 
                        WHEN homework_check.status = 'На проверке' 
                            THEN 1 
                        ELSE 0 
                    END) AS НаПроверке,
                    SUM(CASE 
                        WHEN homework_check.status = 'Принято'
                            THEN 1
                        ELSE 0 
                    END) AS Принято,
                    SUM(CASE 
                        WHEN homework_check.status IN ('Получено', 'Возвращено')
                            THEN 1
                        ELSE 0 
                    END) AS Получено
                FROM users
                    INNER JOIN chats 
                        ON users.id_user = chats.id_user 
                            AND NOT chats.deleted 
                            AND users.role = 'user' 
                LEFT JOIN homework_check 
                    ON homework_check.project_id = %s 
                        AND homework_check.id_user = chats.id_user  
                WHERE 
                    chats.id_chat = %s 
                GROUP BY 
                    chats.id_user, 
                    users.first_name, 
                    users.last_name, 
                    users.username, 
                    users.fio, 
                    CASE 
                        WHEN users.fio IS NULL
                            THEN concat(users.first_name, ' ', users.last_name)
                        ELSE users.fio 
                    END
                ORDER BY
                    НаПроверке DESC, Принято, name""", (project_id, id_chat))
            result = self.cursor.fetchall()

            return result

        except Exception as e:
            await send_error(self.cursor.query, str(e), traceback.format_exc())

    async def get_users_status_homeworks_in_chats(self, project_id, id_chat):
        try:
            self.cursor.execute(
                """SELECT DISTINCT
                    homework_check.status, 
                    users.id_user, 
                    CASE
                        WHEN users.fio IS NULL
                            THEN concat(users.first_name, ' ', users.last_name) 
                        ELSE users.fio 
                    END AS name,
                    CASE
                        WHEN homework_check.status = 'На проверке'
                            THEN 0
                        WHEN homework_check.status = 'Возвращено'
                            THEN 1
                        WHEN homework_check.status = 'Получено'
                            THEN 2
                        ELSE 3 
                    END AS sorting
                FROM users
                    INNER JOIN chats 
                        ON users.id_user = chats.id_user 
                            AND NOT chats.deleted 
                            AND users.role = 'user' 
                LEFT JOIN homework_check 
                    ON homework_check.project_id = %s 
                        AND homework_check.id_user = chats.id_user  
                WHERE 
                    chats.id_chat = %s 
                ORDER BY
                    sorting,
                    name""", (project_id, id_chat))
            result = self.cursor.fetchall()

            return result

        except Exception as e:
            await send_error(self.cursor.query, str(e), traceback.format_exc())

    async def get_date_last_homework(self, project_id):
        try:
            homework_date = None
            self.cursor.execute("SELECT date FROM homework_text WHERE project_id = %s ORDER BY date DESC LIMIT 1",
                                (project_id,))
            result = self.cursor.fetchone()
            if result is not None and not result[0] in ('', None):
                homework_date = result[0]

            return homework_date

        except Exception as e:
            await send_error(self.cursor.query, str(e), traceback.format_exc())

    async def get_date_status_meaning_homework(self, status, project_id, homework_date, id_user=None):
        try:
            status_meaning = 'Нет домашних работ'
            accepted = False
            status_is_filled = False
            user_info = ''

            if status == 'text' and id_user is None:
                self.cursor.execute("SELECT text FROM homework_text WHERE project_id = %s AND date = %s",
                                    (project_id, homework_date))
                status_meaning = self.cursor.fetchone()[0]

            elif status == 'text' and id_user is not None:
                self.cursor.execute(
                    """SELECT 
                        text, 
                        status = 'Принято', 
                        NOT response IS NULL 
                    FROM homework_text 
                    INNER JOIN homework_check 
                        ON homework_text.project_id = %s 
                            AND homework_text.date = %s
                            AND homework_text.project_id = homework_check.project_id
                            AND homework_text.date = homework_check.date
                            AND homework_check.id_user = %s""",
                    (project_id, homework_date, id_user))
                result = self.cursor.fetchone()
                if result is not None:
                    status_meaning = result[0]
                    accepted = bool(result[1])
                    status_is_filled = bool(result[2])

            elif status in ('response', 'feedback'):
                self.cursor.execute(
                    f"""SELECT 
                        {status}, 
                        status = 'Принято', 
                        NOT response IS NULL 
                    FROM homework_check 
                    WHERE 
                        project_id = %s 
                            AND date = %s 
                            AND id_user = %s""", (project_id, homework_date, id_user))
                result = self.cursor.fetchone()
                if result is not None:
                    status_meaning = result[0]
                    accepted = bool(result[1])
                    status_is_filled = bool(result[2])

            if id_user is not None:
                first_name, last_name, username, fio, title = await base.get_user_info(id_user)
                if first_name is not None:
                    user_info = shielding(title.replace('\\', '')) + '\n'
                    user_info += await get_name_tg(id_user, first_name, last_name, username, fio)
                    user_info += '\n\n'

            return status_meaning, accepted, status_is_filled, user_info

        except Exception as e:
            await send_error(self.cursor.query, str(e), traceback.format_exc())

    async def get_all_projects(self):
        try:
            self.cursor.execute("SELECT project_id, name FROM projects")
            result = self.cursor.fetchall()

            return result

        except Exception as e:
            await send_error(self.cursor.query, str(e), traceback.format_exc())

    async def get_chats_in_project(self, project_id):
        try:
            self.cursor.execute(
                """SELECT DISTINCT 
                    settings.id_chat, 
                    settings.title 
                FROM settings
                    LEFT OUTER JOIN chats 
                        ON chats.id_chat = settings.id_chat 
                WHERE 
                    settings.enable_group 
                        AND project_id = %s""", (project_id,))
            result = self.cursor.fetchall()

            return result

        except Exception as e:
            await send_error(self.cursor.query, str(e), traceback.format_exc())

    async def application_for_membership(self, id_user):
        try:
            self.cursor.execute(
                """SELECT DISTINCT 
                    users.menu_message_id, 
                    projects.name, 
                    projects.invite_link 
                FROM chats 
                    INNER JOIN settings 
                        ON chats.id_chat = settings.id_chat 
                    INNER JOIN users 
                        ON chats.id_user = users.id_user 
                    INNER JOIN projects 
                        ON settings.project_id = projects.project_id 
                WHERE 
                    settings.enable_group 
                        AND chats.id_user = %s""", (id_user,))
            result = self.cursor.fetchone()

            return result

        except Exception as e:
            await send_error(self.cursor.query, str(e), traceback.format_exc())

    async def which_menu_to_show(self, id_user):
        try:
            answer_text, project_id, homework_date, homework_id_user = '', None, None, None

            self.cursor.execute(
                f"""SELECT 
                --registration
                coalesce((SELECT True FROM users WHERE id_user = {id_user} AND NOT registration_field = 'done'), False), 
                
                --homework_text
                coalesce((SELECT project_id FROM project_administrators WHERE id_user = {id_user} AND status = 'text'), 0), 
                
                --homework_feedback
                coalesce((SELECT project_id FROM homework_check WHERE admin_id = {id_user} AND NOT response IS NULL), 0), 
                (SELECT date FROM homework_check WHERE admin_id = {id_user} AND NOT response IS NULL), 
                (SELECT id_user FROM homework_check WHERE admin_id = {id_user} AND NOT response IS NULL), 
                
                --homework_response
                coalesce((SELECT project_id FROM homework_check WHERE id_user = {id_user} AND NOT status = 'Принято' AND selected = True), 0), 
                (SELECT date FROM homework_check WHERE id_user = {id_user} AND NOT status = 'Принято' AND selected = True)""")
            result = self.cursor.fetchone()

            if result[0]:
                answer_text = 'registration'
            elif result[1] > 0:
                answer_text = 'homework_text'
                project_id = result[1]
            elif result[2] > 0:
                answer_text = 'homework_feedback'
                project_id = result[2]
                homework_date = result[3]
                homework_id_user = result[4]
            elif result[5] > 0:
                answer_text = 'homework_response'
                project_id = result[5]
                homework_date = result[6]

            return answer_text, project_id, homework_date, homework_id_user

        except Exception as e:
            await send_error(self.cursor.query, str(e), traceback.format_exc())

    async def set_status_homework(self, project_id, date, id_user, status, set_date=False):
        try:
            if set_date:
                date_actual = get_today(True)
            else:
                date_actual = None

            with self.connect:
                self.cursor.execute(
                    """UPDATE homework_check SET status = %s, date_actual = %s 
                    WHERE project_id = %s AND date = %s AND id_user = %s""",
                    (status, date_actual, project_id, date, id_user))

        except Exception as e:
            await send_error(self.cursor.query, str(e), traceback.format_exc())

    async def set_admin_homework(self, project_id, date, id_user, id_user_admin):
        try:
            with self.connect:
                self.cursor.execute(
                    "UPDATE homework_check SET admin_id = NULL WHERE project_id = %s",
                    (project_id,))
                self.cursor.execute(
                    "UPDATE homework_check SET admin_id = %s WHERE project_id = %s AND date = %s AND id_user = %s",
                    (id_user_admin, project_id, date, id_user))

        except Exception as e:
            await send_error(self.cursor.query, str(e), traceback.format_exc())

    async def set_homework_feedback(self, project_id, homework_date, id_user, feedback, feedback_author_id):
        try:
            with self.connect:
                self.cursor.execute(
                    """UPDATE homework_check SET feedback = %s, feedback_author_id = %s 
                    WHERE project_id = %s AND date = %s AND id_user = %s""",
                    (feedback, feedback_author_id, project_id, homework_date, id_user))

        except Exception as e:
            await send_error(self.cursor.query, str(e), traceback.format_exc())

    async def get_user_info(self, id_user):
        try:
            first_name = None
            last_name = None
            username = None
            fio = None
            title = None

            self.cursor.execute(
                """SELECT 
                    users.first_name, 
                    coalesce(users.last_name, ''), 
                    coalesce(users.username, ''), 
                    coalesce(users.fio, ''), 
                    settings.title 
                FROM users 
                INNER JOIN chats 
                    ON users.id_user = %s 
                    AND users.id_user = chats.id_user 
                INNER JOIN settings 
                    ON chats.id_chat = settings.id_chat 
                    AND settings.enable_group 
                    AND NOT settings.curators_group""", (id_user,))
            result = self.cursor.fetchone()
            if result is not None:
                first_name = result[0]
                last_name = result[1]
                username = result[2]
                fio = result[3]
                title = result[4]

            return first_name, last_name, username, fio, title

        except Exception as e:
            await send_error(self.cursor.query, str(e), traceback.format_exc())

    async def get_chats_for_reminder(self):
        try:
            today = get_today()
            self.cursor.execute(
                "SELECT id_chat FROM settings WHERE report_enabled AND enable_group AND %s > last_notify_date",
                (today,))
            return self.cursor.fetchall()

        except Exception as e:
            await send_error(self.cursor.query, str(e), traceback.format_exc())

    async def save_last_notify_date_reminder(self, id_chat):
        try:
            today = get_today()
            with self.connect:
                self.cursor.execute('UPDATE settings SET last_notify_date = %s WHERE id_chat = %s', (today, id_chat))

        except Exception as e:
            await send_error(self.cursor.query, str(e), traceback.format_exc())

    async def get_all_info_about_user(self, id_user):
        try:
            self.cursor.execute("SELECT * FROM users WHERE id_user = %s", (id_user,))
            result = self.cursor.fetchone()
            if result is None:
                text_result = 'None'
            else:
                text_result = 'users:\n' + get_names_and_values_of_the_request_details(self.cursor.description, result)
                text_result = shielding(text_result)
                self.cursor.execute(
                    """SELECT 
                        chats.id_chat, 
                        settings.title as name, 
                        projects.name as project, 
                        enable_group, 
                        curators_group,
                        chats.deleted 
                    FROM chats 
                    INNER JOIN settings 
                        ON chats.id_chat = settings.id_chat 
                            AND chats.id_user = %s
                    LEFT JOIN projects 
                        ON projects.project_id = settings.project_id""", (id_user,))
                result_chats = self.cursor.fetchall()
                text_result += '\n\nchats:\n'
                for i in result_chats:
                    text_result += shielding('\nchat:\n' + get_names_and_values_of_the_request_details(
                        self.cursor.description, i))

                    text_result += '\nadmins:\n'

                    self.cursor.execute(
                        """SELECT 
                            users.id_user, 
                            users.first_name, 
                            users.last_name, 
                            users.username 
                        FROM chats 
                        INNER JOIN users 
                            ON users.id_user = chats.id_user 
                                AND not users.role = 'user' 
                                AND id_chat = %s""", (i[0],))
                    result_admins = self.cursor.fetchall()
                    for ii in result_admins:
                        id_user = ii[0]
                        first_name = ii[1]
                        last_name = ii[2]
                        username = ii[3]
                        text_result += await get_name_tg(id_user, first_name, last_name, username) + '\n'

            return text_result

        except Exception as e:
            await send_error(self.cursor.query, str(e), traceback.format_exc())

    async def registration_done(self, id_user):
        try:
            self.cursor.execute("SELECT NOT registration_field = 'done' FROM users WHERE id_user = %s", (id_user,))
            result = self.cursor.fetchone()
            if result is None or result[0]:
                return False
            else:
                return True

        except Exception as e:
            await send_error(self.cursor.query, str(e), traceback.format_exc())

    async def get_project_by_user(self, id_user):
        try:
            self.cursor.execute(
                """SELECT DISTINCT settings.project_id, projects.name FROM chats 
                INNER JOIN settings ON settings.id_chat = chats.id_chat
                INNER JOIN projects ON projects.project_id = settings.project_id 
                AND NOT settings.project_id = 0 AND chats.id_user = %s """, (id_user,))
            result = self.cursor.fetchone()
            if result is None:
                return 0, ''
            else:
                return result[0], result[1]

        except Exception as e:
            await send_error(self.cursor.query, str(e), traceback.format_exc())

    async def its_admin_project(self, id_user, project_id):
        try:
            self.cursor.execute("SELECT id_user FROM project_administrators WHERE id_user = %s AND project_id = %s",
                                (id_user, project_id))
            result = self.cursor.fetchone()
            if result is None:
                return False
            else:
                return True

        except Exception as e:
            await send_error(self.cursor.query, str(e), traceback.format_exc())


base = Database()
