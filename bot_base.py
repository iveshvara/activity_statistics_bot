
import traceback

import psycopg2
from aiogram import Bot
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import Dispatcher
from aiogram.types import Message, User

from _settings import TOKEN, SKIP_ERROR_TEXT, THIS_IS_BOT_NAME, LOGS_CHANNEL_ID
from service import get_today, get_name_tg, shielding, add_text_to_array

bot = Bot(TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

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
            my_files = (
                'bot_base.py',
                'handlers.py',
                'main.py',
                'main_functions.py',
                'service.py',
                'utility_functions.py')
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
            self.cursor.execute("SELECT COALESCE(menu_message_id, 0) FROM users WHERE id_user = %s", (id_user,))
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
        if id_chat is None:
            id_chat = 0

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
                        AND (%s OR chats.id_chat = %s)""",
                (project_id, id_user, id_chat == 0, id_chat))
            result = self.cursor.fetchall()

            return result

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
            answer_text, project_id, homework_id, homework_id_user = '', None, None, None

            self.cursor.execute(
                f"""SELECT 
                --registration
                coalesce((SELECT True FROM users WHERE id_user = {id_user} AND NOT registration_field = 'done'), False), 
                
                --homeworks_task
                coalesce((SELECT project_id FROM project_administrators WHERE id_user = {id_user} AND status = 'text'), 0), 
                
                --homework_feedback
                --coalesce((SELECT project_id FROM homework_check WHERE admin_id = {id_user} AND NOT response IS NULL), 0), 
                --(SELECT homework_id FROM homework_check WHERE admin_id = {id_user} AND NOT response IS NULL), 
                --(SELECT id_user FROM homework_check WHERE admin_id = {id_user} AND NOT response IS NULL), 
                
                --homework_response
                coalesce((SELECT project_id FROM homeworks_status WHERE {id_user} = ANY(selected_id)), 0),
                coalesce((SELECT homework_id FROM homeworks_status WHERE {id_user} = ANY(selected_id)), 0),
                coalesce((SELECT id_user FROM homeworks_status WHERE {id_user} = ANY(selected_id)), 0)""")
            result = self.cursor.fetchone()

            if result[0]:
                answer_text = 'registration'
            elif result[1] > 0:
                answer_text = 'homeworks_task'
                project_id = result[1]
            elif result[2] > 0:
                answer_text = 'homework_response'
                project_id = result[2]
                homework_id = result[3]
                homework_id_user = result[4]

            return answer_text, project_id, homework_id, homework_id_user

        except Exception as e:
            await send_error(self.cursor.query, str(e), traceback.format_exc())

    async def save_last_notify_date_reminder(self, id_chat):
        try:
            today = get_today()
            with self.connect:
                self.cursor.execute('UPDATE settings SET last_notify_date = %s WHERE id_chat = %s', (today, id_chat))

        except Exception as e:
            await send_error(self.cursor.query, str(e), traceback.format_exc())

    async def get_user_info_old(self, project_id, id_user):
        try:
            first_name = None
            last_name = None
            username = None
            fio = None
            title = None

            self.cursor.execute(
                """SELECT 
                    users.first_name, 
                    COALESCE(users.last_name, ''), 
                    COALESCE(users.username, ''), 
                    COALESCE(users.fio, ''), 
                    settings.title 
                FROM users 
                INNER JOIN chats 
                    ON users.id_user = %s 
                    AND users.id_user = chats.id_user 
                INNER JOIN settings 
                    ON chats.id_chat = settings.id_chat 
                    AND settings.enable_group 
                    AND NOT settings.curators_group
                    AND settings.project_id = %s""", (id_user, project_id))
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

    async def get_user_info(self, id_user):
        try:
            user_info = None

            self.cursor.execute(
                """SELECT 
                    first_name, 
                    COALESCE(last_name, ''), 
                    COALESCE(username, ''), 
                    COALESCE(fio, '') 
                FROM users 
                WHERE id_user = %s""", (id_user, ))
            result = self.cursor.fetchone()
            if result is not None:
                first_name = result[0]
                last_name = result[1]
                username = result[2]
                fio = result[3]

                if first_name is not None:
                    user_info = get_name_tg(id_user, first_name, last_name, username, fio)

            return user_info

        except Exception as e:
            await send_error(self.cursor.query, str(e), traceback.format_exc())

    async def get_user_id_chat(self, id_user):
        try:
            self.cursor.execute("SELECT id_chat FROM chats WHERE NOT deleted AND id_user = %s", (id_user, ))
            result = self.cursor.fetchone()

            return result[0]

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
                        text_result += get_name_tg(id_user, first_name, last_name, username) + '\n'

            return text_result

        except Exception as e:
            await send_error(self.cursor.query, str(e), traceback.format_exc())

    async def registration_done(self, id_user):
        try:
            self.cursor.execute("SELECT registration_field = 'done' FROM users WHERE id_user = %s", (id_user,))
            result = self.cursor.fetchone()
            if result is None or result[0] is None:
                return False
            else:
                return result[0]

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

    async def get_stat(self, id_chat, id_user=None):
        self.cursor.execute(
            """SELECT 
                settings.statistics_for_everyone, 
                settings.include_admins_in_statistics, 
                settings.period_of_activity, 
                settings.sort_by, 
                settings.check_channel_subscription, 
                COALESCE(projects.channel_id, 0),
                settings.do_not_output_name_from_registration,
                settings.project_id,
                COUNT(DISTINCT homeworks_task.date) AS homeworks_task
            FROM settings 
            LEFT OUTER JOIN projects 
                    ON settings.project_id = projects.project_id
            LEFT OUTER JOIN homeworks_task 
                    ON settings.project_id = homeworks_task.project_id
            WHERE id_chat = %s
            GROUP BY
                settings.statistics_for_everyone, 
                settings.include_admins_in_statistics, 
                settings.period_of_activity, 
                settings.sort_by,  
                settings.check_channel_subscription, 
                COALESCE(projects.channel_id, 0),
                settings.do_not_output_name_from_registration,
                settings.project_id""", (id_chat,))
        meaning = self.cursor.fetchone()
        if meaning is None:
            await send_error(f'Не найден {id_chat}. Как такое может быть?', '', str(traceback.format_exc()))

        statistics_for_everyone = meaning[0]
        include_admins_in_statistics = meaning[1]
        period_of_activity = meaning[2]
        sort_by = meaning[3]
        check_channel_subscription = meaning[4]
        channel_id = meaning[5]
        do_not_output_name_from_registration = meaning[6]
        project_id = meaning[7]
        homeworks_all = meaning[8]

        if await base.its_admin(id_user) or id_user is None or statistics_for_everyone:
            if sort_by == 'homeworks':
                sort = 'homeworks DESC'
            else:
                sort = f'inactive_days ASC, {sort_by} DESC'
            today = get_today()
            count_messages = 0
            self.cursor.execute(
                f"""SELECT 
                    users.id_user, 
                    users.first_name, 
                    COALESCE(users.last_name, ''), 
                    COALESCE(users.username, ''), 
                    COALESCE(users.fio, ''),
                    SUM(COALESCE(messages.characters, 0)) AS characters, 
                    COUNT(messages.characters) AS messages, 
                    chats.deleted, 
                    chats.date_of_the_last_message, 
                    CASE 
                        WHEN NOT chats.deleted 
                            AND {period_of_activity} > DATE_PART('day', '{today}' - chats.date_of_the_last_message) 
                            THEN 0 
                        ELSE DATE_PART('day', '{today}' - chats.date_of_the_last_message) 
                    END AS inactive_days,
                    NOT role = 'user' AS admin, 
                    COUNT(DISTINCT homeworks_status.homework_id) AS homeworks
                FROM chats 
                LEFT JOIN messages 
                    ON chats.id_chat = messages.id_chat 
                        AND chats.id_user = messages.id_user 
                        AND {period_of_activity} > DATE_PART('day', '{today}' - messages.date)
                LEFT JOIN homeworks_status
                    ON chats.id_user = homeworks_status.id_user
                        AND homeworks_status.project_id = {project_id}
                INNER JOIN users 
                    ON chats.id_user = users.id_user  
                WHERE 
                    chats.id_chat = {id_chat} 
                    AND users.id_user IS NOT NULL
                GROUP BY 
                    users.id_user, 
                    users.first_name, 
                    COALESCE(users.last_name, ''), 
                    COALESCE(users.username, ''), 
                    COALESCE(users.fio, ''),
                    chats.deleted, 
                    chats.date_of_the_last_message, 
                    inactive_days,
                    NOT role = 'user'
                ORDER BY 
                    deleted ASC,  
                    {sort},
                    users.first_name""")
            meaning = self.cursor.fetchall()

            its_homeworks = sort_by == 'homeworks'
            if its_homeworks:
                text = f'*Выполнили все дз:*'
            else:
                text = f'*Активные участники: `Символов/Сообщений/ДЗ из {homeworks_all}`*'
            active_members_inscription_is_shown = False
            deleted_members_inscription_is_shown = False

            for i in meaning:
                i_id_user = i[0]
                i_first_name = i[1]
                i_last_name = i[2]
                i_username = i[3]
                if do_not_output_name_from_registration:
                    i_fio = ''
                else:
                    i_fio = i[4]
                # i_characters = reduce_large_numbers(i[5])
                i_characters = i[5]
                i_messages = i[6]
                i_deleted = i[7]
                i_date_of_the_last_message = i[8]
                i_inactive_days = int(i[9])
                i_admin = i[10]
                i_homeworks = i[11]

                if not include_admins_in_statistics:
                    if i_admin:
                        continue

                if its_homeworks:
                    if i_homeworks < homeworks_all and not i_deleted and not active_members_inscription_is_shown:
                        active_members_inscription_is_shown = True
                        text += f'\n\n*Выполнили не все дз:*'

                    if i_homeworks == 0 and not deleted_members_inscription_is_shown:
                        deleted_members_inscription_is_shown = True
                        text += f'\n\n*Не выполнили ни одно дз:*'
                        count_messages = 0

                    if i_deleted:
                        continue

                else:
                    if i_inactive_days > 0 and not i_deleted and not active_members_inscription_is_shown:
                        active_members_inscription_is_shown = True
                        text += f'\n\n*Неактивные участники:* `неактивен дней/ДЗ из {homeworks_all}`'

                    if i_deleted and not deleted_members_inscription_is_shown:
                        deleted_members_inscription_is_shown = True
                        text += f'\n\n*Вышедшие участники:*'
                        count_messages = 0

                count_messages += 1

                channel_subscription = ''
                if check_channel_subscription and not channel_id == 0 and not i_deleted:
                    member_status = False

                    try:
                        member = await bot.get_chat_member(channel_id, i_id_user)
                        member_status = not member.status == 'left'
                    except Exception as e:
                        pass

                    if member_status:
                        channel_subscription = ''
                    else:
                        channel_subscription = '⚠️ '

                specifics = ''
                if i_deleted:
                    data_str = shielding(i_date_of_the_last_message.strftime("%d.%m.%Y"))
                    specifics = f' \(вне чата с {data_str}, дней назад: {i_inactive_days}\)'
                else:
                    if not its_homeworks:
                        if not sort_by == 'homeworks' and i_inactive_days > 0:
                            specifics = f'{i_inactive_days}/'
                        else:
                            specifics = str(i_characters) + '/' + str(i_messages) + '/'

                    specifics += str(i_homeworks)
                    specifics = ': `' + specifics + '`'

                user = get_name_tg(i_id_user, i_first_name, i_last_name, i_username, i_fio)
                count_messages_text = str(count_messages)
                text += f'\n{count_messages_text}\. {channel_subscription}{user}{specifics}'

            if text == '*Активные участники:*\n':
                text = 'Нет статистики для отображения\.'

        else:
            text = 'Статистику могут показать только администраторы группы\.'

        return text

    async def get_all_homework(self, project_id, id_user, its_admin, id_chat):
        try:
            if its_admin:
                self.cursor.execute(
                    """SELECT 
                        homeworks_task.homework_id, 
                        homeworks_task.date, 
                        SUM(COALESCE(homeworks_answers.counter, 0)) 
                    FROM homeworks_task 
                    LEFT JOIN homeworks_answers 
                         ON homeworks_task.project_id = homeworks_answers.project_id
                            AND homeworks_task.homework_id = homeworks_answers.homework_id
                            AND homeworks_answers.id_user IN (SELECT id_user FROM chats WHERE id_chat = %s)
                            AND homeworks_answers.id_user = homeworks_answers.id_user_response
                    WHERE homeworks_task.project_id = %s
                    GROUP BY
                        homeworks_task.homework_id, 
                        homeworks_task.date 
                    ORDER BY 
                        homeworks_task.homework_id""",
                    (id_chat, project_id))
                result = self.cursor.fetchall()

            else:
                self.cursor.execute(
                    """SELECT 
                        homeworks_task.homework_id, 
                        homeworks_task.date, 
                        COALESCE(homeworks_status.accepted, False) 
                    FROM homeworks_task 
                    LEFT JOIN homeworks_status 
                        ON homeworks_task.project_id = homeworks_status.project_id
                        AND homeworks_task.homework_id = homeworks_status.homework_id
                        AND homeworks_status.id_user = %s
                        AND homeworks_status.accepted
                    WHERE homeworks_task.project_id = %s
                    ORDER BY homeworks_task.homework_id""",
                    (id_user, project_id))
                result = self.cursor.fetchall()

            return result

        except Exception as e:
            await send_error(self.cursor.query, str(e), traceback.format_exc())

    async def get_users_status_homework_in_chat(self, project_id, id_chat, homework_id):
        try:
            self.cursor.execute(
                """SELECT DISTINCT
                    users.id_user, 
                    CASE
                        WHEN users.fio IS NULL
                            THEN concat(users.first_name, ' ', users.last_name) 
                        ELSE users.fio 
                    END AS name,
                    COALESCE(homeworks_status.accepted, False),
					SUM(COALESCE(homeworks_answers.counter, 0))
                FROM users
                    INNER JOIN chats 
                        ON users.id_user = chats.id_user 
                            AND NOT chats.deleted 
                            AND users.role = 'user'
                            AND chats.id_chat = %s 
                LEFT JOIN homeworks_status 
                    ON homeworks_status.project_id = %s 
                        AND homeworks_status.id_user = chats.id_user
                        AND homeworks_status.homework_id = %s
 				LEFT JOIN homeworks_answers 
                     ON homeworks_status.project_id = homeworks_answers.project_id 
                         AND homeworks_status.id_user = homeworks_answers.id_user
                         AND homeworks_status.homework_id = homeworks_answers.homework_id
                         AND homeworks_answers.id_user = homeworks_answers.id_user_response
				GROUP BY
					users.id_user, 
                    CASE
                        WHEN users.fio IS NULL
                            THEN concat(users.first_name, ' ', users.last_name) 
                        ELSE users.fio 
                    END,
                    COALESCE(homeworks_status.accepted, False)
                ORDER BY
                    name""", (id_chat, project_id, homework_id))
            result = self.cursor.fetchall()

            return result

        except Exception as e:
            await send_error(self.cursor.query, str(e), traceback.format_exc())

    async def get_homework_id_last_homework(self, project_id):
        try:
            homework_id = None
            self.cursor.execute("SELECT homework_id FROM homeworks_task WHERE project_id = %s ORDER BY date DESC LIMIT 1",
                                (project_id,))
            result = self.cursor.fetchone()
            if result is not None and not result[0] in ('', None):
                homework_id = result[0]

            return homework_id

        except Exception as e:
            await send_error(self.cursor.query, str(e), traceback.format_exc())

    async def get_date_status_meaning_homework(self, status, project_id, homework_id, id_user=None):
        try:
            status_meaning = 'Нет домашних работ'
            accepted = False
            # status_is_filled = False
            user_info = ''

            if status in ('text', 'response', 'feedback') and id_user is None:
                self.cursor.execute("SELECT text FROM homeworks_task WHERE project_id = %s AND homework_id = %s",
                                    (project_id, homework_id))
                status_meaning = self.cursor.fetchone()[0]

            elif status in ('text', 'response', 'feedback') and id_user is not None:
                self.cursor.execute(
                    """SELECT 
                        homeworks_task.text, 
                        homeworks_status.accepted 
                    FROM homeworks_task 
                    INNER JOIN homeworks_status 
                        ON homeworks_task.project_id = %s   
                            AND homeworks_task.project_id = homeworks_status.project_id
                            AND homeworks_status.id_user = %s
                            AND homeworks_task.homework_id = %s
                            AND homeworks_task.homework_id = homeworks_status.homework_id""",
                    (project_id, id_user, homework_id))
                result = self.cursor.fetchone()
                if result is not None:
                    status_meaning = result[0]
                    accepted = bool(result[1])
                    # status_is_filled = bool(result[2])

            # elif status in ('response', 'feedback'):
            #     self.cursor.execute(
            #         f"""SELECT
            #             {status},
            #             status = 'Принято',
            #             NOT response IS NULL
            #         FROM homeworks_status
            #         WHERE
            #             project_id = %s
            #                 AND homework_id = %s
            #                 AND id_user = %s""", (project_id, homework_id, id_user))
            #     result = self.cursor.fetchone()
            #     if result is not None:
            #         status_meaning = result[0]
            #         accepted = bool(result[1])
            #         # status_is_filled = bool(result[2])
            #
            # if id_user is not None:
            #     first_name, last_name, username, fio, title = await base.get_user_info_old(project_id, id_user)
            #     if first_name is not None:
            #         user_info = shielding(title.replace('\\', '')) + '\n'
            #         user_info += get_name_tg(id_user, first_name, last_name, username, fio)
            #         user_info += '\n\n'

            return status_meaning, accepted, user_info

        except Exception as e:
            await send_error(self.cursor.query, str(e), traceback.format_exc())

    async def get_homeworks_task(self, project_id, homework_id, id_user):
        try:
            self.cursor.execute(
                "SELECT date, text FROM homeworks_task WHERE project_id = %s AND homework_id = %s",
                (project_id, homework_id))
            homeworks_task_date = self.cursor.fetchone()

            date = shielding(homeworks_task_date[0].strftime("%d.%m.%Y"))
            text = shielding(homeworks_task_date[1])
            text = f'__*Задание №{homework_id} от {date}:*__\n\n{text}'

            array_text = ['']
            array_text = add_text_to_array(array_text, text)

            self.cursor.execute(
                """SELECT 
                    id_user_response, 
                    date, 
                    text 
                FROM homeworks_answers 
                WHERE project_id = %s 
                    AND homework_id = %s 
                    AND id_user = %s""",
                (project_id, homework_id, id_user))
            result = self.cursor.fetchall()
            # last_user_info = ''
            for i in result:
                i_id_user = i[0]
                i_date = shielding(i[1].strftime("%d.%m.%Y %H:%M:%S"))
                i_text = i[2]

                i_text = shielding(i_text)

                user_info = await base.get_user_info(i_id_user)
                user_info = user_info.replace(' ', '\xa0')

                heading = f'\n\n\n__*{user_info} от {i_date}:*__'
                heading = heading.replace(' ', '\xa0')

                text = heading + '\n' + i_text
                array_text = add_text_to_array(array_text, text)

            # array_text_len = len(array_text)
            # for i in range(array_text_len):
            #     array_text[i] += f'\n\n\_\_\_\_\_\n\~ {i+1} \~'

            return array_text

        except Exception as e:
            await send_error(self.cursor.query, str(e), traceback.format_exc())

    async def get_status_homework(self, project_id, homework_id, id_user):
        try:
            self.cursor.execute(
                "SELECT accepted FROM homeworks_status WHERE project_id = %s AND homework_id = %s AND id_user = %s",
                (project_id, homework_id, id_user))
            result = self.cursor.fetchone()
            if result is None:
                status = False
            else:
                status = result[0]

            return status

        except Exception as e:
            await send_error(self.cursor.query, str(e), traceback.format_exc())

    async def set_status_homework(self, project_id, homework_id, id_user, id_user_response, status=True):
        try:
            with self.connect:
                self.cursor.execute(
                    """INSERT INTO homeworks_status(
                        project_id,
                        homework_id,
                        id_user,
                        accepted)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (project_id, homework_id, id_user) DO UPDATE SET
                        accepted = %s""",
                    (project_id, homework_id, id_user, status, status))

        except Exception as e:
            await send_error(self.cursor.query, str(e), traceback.format_exc())

        if status:
            text = '# Задание принято.'
        else:
            text = '# Задание возвращено на доработку.'

        await base.insert_homework_response(project_id, homework_id, id_user, id_user_response, text)

    async def insert_homework_response(self, project_id, homework_id, id_user, id_user_response, text=''):
        try:
            with self.connect:
                self.cursor.execute(
                    """INSERT INTO homeworks_answers(
                        project_id,  
                        homework_id, 
                        id_user, 
                        id_user_response, 
                        date, 
                        text,  
                        counter) 
                    VALUES (%s, %s, %s, %s, NOW(), %s, 1)""" , # date_trunc('second', NOW())
                    (project_id, homework_id, id_user, id_user_response, text))

        except Exception as e:
            await send_error(self.cursor.query, str(e), traceback.format_exc())

    async def update_selected_homeworks(self, id_user, homework_id=None, project_id=None, selected_id=None):
        try:
            with self.connect:
                # if project_id is None:
                self.cursor.execute('UPDATE homeworks_status SET selected_id = NULL WHERE %s = ANY(selected_id)', (id_user,))

                if selected_id is not None:
                    self.cursor.execute(
                        """INSERT INTO homeworks_status(
                            project_id,
                            homework_id,
                            id_user,
                            accepted,
                            selected_id)
                        VALUES (%s, %s, %s, False, %s)
                        ON CONFLICT (project_id, homework_id, id_user) DO UPDATE SET
                            selected_id = %s""",
                        (project_id, homework_id, id_user, [selected_id], [selected_id]))

        except Exception as e:
            await send_error(self.cursor.query, str(e), traceback.format_exc())

    async def update_counter_homework(self, project_id, homework_id, id_user, its_admin=False):
        try:
            with self.connect:
                self.cursor.execute(
                    """UPDATE homeworks_answers SET 
                        counter = 0 
                    WHERE 
                        project_id = %s
                            AND homework_id = %s
                            AND id_user = %s
                            AND CASE
                                    WHEN %s = True
                                        THEN id_user = id_user_response
                                    ELSE NOT id_user = id_user_response 
                                END""",
                    (project_id, homework_id, id_user, its_admin))

        except Exception as e:
            await send_error(self.cursor.query, str(e), traceback.format_exc())


base = Database()
