
import datetime
import traceback

from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton as AddInlBtn

from _settings import SUPER_ADMIN_ID
from bot_base import bot, cursor, connect, base, send_error
from service import shielding, get_name_tg, get_today, message_requirements, convert_bool, convert_bool_binary
from utility_functions import message_delete_by_id, callback_edit_text, message_send, message_progress_bar, \
    get_text_homework


async def run_reminder():
    result = await base.get_chats_for_reminder()
    for i in result:
        id_chat = i[0]
        text = await get_stat(id_chat)

        if not text == '':
            await message_send(id_chat, text, disable_notification=True)
            await base.save_last_notify_date_reminder(id_chat)


async def get_stat(id_chat, id_user=None):
    cursor.execute(
        '''SELECT 
            settings.statistics_for_everyone, 
            settings.include_admins_in_statistics, 
            settings.period_of_activity, 
            settings.sort_by, 
            -- settings.do_not_output_the_number_of_messages, 
            -- settings.do_not_output_the_number_of_characters, 
            settings.check_channel_subscription, 
            coalesce(projects.channel_id, 0),
            settings.do_not_output_name_from_registration,
            settings.project_id,
            COUNT(DISTINCT homeworks_task.homework_id) AS homeworks_task
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
            coalesce(projects.channel_id, 0),
            settings.do_not_output_name_from_registration,
            settings.project_id''', (id_chat,))
    meaning = cursor.fetchone()
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
        cursor.execute(
            f'''SELECT 
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
                COUNT(homeworks_status.accepted) AS homeworks
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
                users.first_name''')
        meaning = cursor.fetchall()

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


async def get_start_menu(id_user):
    # Есть уже в base
    cursor.execute(
        """SELECT DISTINCT settings.id_chat, settings.title, settings.project_id FROM settings 
        LEFT OUTER JOIN chats ON chats.id_chat = settings.id_chat 
        WHERE settings.enable_group AND id_user = %s""", (id_user,))
    meaning = cursor.fetchall()
    user_groups = []
    channel_enabled = False
    for i in meaning:
        # get = False
        # try:
        #     # chat_admins = await bot.get_chat_administrators(i[0])
        #     # get = its_admin(i[0], chat_admins)
        #     member = await bot.get_chat_member(i[0], id_user)
        #     get = member.is_chat_admin()
        # except Exception as e:
        #     pass
        #
        # if get:

        if await base.its_admin(id_user):
            title_result = i[1]
            user_groups.append([i[0], title_result])

        if not channel_enabled and i[2] > 0:
            channel_enabled = True

    text = 'Меню:'
    inline_kb = InlineKeyboardMarkup(row_width=1)

    if len(user_groups) == 0:
        if len(meaning) == 0 or not channel_enabled:
            text = 'Это бот для участников проектов https://ipdt.kz/proekty/. Присоединяйтесь!'
            text = shielding(text)
            inline_kb = InlineKeyboardMarkup(row_width=1)
            inline_kb.add(AddInlBtn(text='Перейти на сайт.', url='https://ipdt.kz/proekty/'))

        elif not await base.registration_done(id_user):
            text = 'Добрый день, дорогой друг! \n\n' \
                   'Команда Института рада приветствовать Вас! \n\n' \
                   'Для того, чтобы получить доступ к материалам, необходимо пройти небольшую регистрацию!'
            text = shielding(text)
            inline_kb = InlineKeyboardMarkup(row_width=1)
            inline_kb.add(AddInlBtn(text='Регистрация', callback_data='reg'))

    else:
        text = 'Выберете группу для настройки:'
        for i in user_groups:
            inline_kb.add(AddInlBtn(text=i[1], callback_data=f'id_chat {i[0]}'))

    project_id, project_name = await base.get_project_by_user(id_user)
    text = 'Домашние работы'
    if await base.its_admin(id_user):
        callback_data = f'admin_homework {project_id} choice_group'
    else:
        callback_data = f'homework {project_id} choice'
    inline_kb.add(AddInlBtn(text=text, callback_data=callback_data))

    if await base.registration_done(id_user):
        result = await base.application_for_membership(id_user)
        if result is not None:
            url = result[2]
            if url is not None and len(url) > 0:
                inline_kb.add(AddInlBtn('Канал с лекциями', url=url))

    if await base.its_admin_project(id_user, project_id):
        inline_kb.add(AddInlBtn(text='Рассылка по "' + project_name + '"', callback_data=f'homework {project_id}'))

    if id_user == SUPER_ADMIN_ID:
        inline_kb.add(AddInlBtn(text='God mode', callback_data='super_admin '))

    return text, inline_kb


async def keyboard_homework_all(project_id, id_user, status='text', its_admin=False, id_chat=None):
    inline_kb = InlineKeyboardMarkup(row_width=1)

    part_admin = ''
    if its_admin:
        part_admin = 'admin_'

    part_id_chat = ''
    if id_chat is not None:
        part_id_chat = f' {id_chat}'

    result = await base.get_all_homework(project_id, id_user, its_admin, id_chat)
    for i in result:
        homework_id = str(i[0])
        date = i[1].strftime("%d.%m.%Y")
        homework_status = ''
        homework_counter = ''
        if its_admin:
            if i[2] > 0:
                homework_counter = f' ({i[2]})'
        else:
            if i[2]:
                homework_status = '✅'

        text = f'{homework_status} №{homework_id} от {date}{homework_counter}'
        callback_data = f'{part_admin}homework {project_id} {status}{part_id_chat} {homework_id}'
        inline_kb.add(AddInlBtn(text=text, callback_data=callback_data))

    if its_admin:
        inline_kb.add(AddInlBtn(text='Назад', callback_data=f'{part_admin}homework {project_id} choice_group_back'))
    else:
        inline_kb.add(AddInlBtn(text='Назад', callback_data=f'{part_admin}homework {project_id} back {homework_id}'))

    return inline_kb


async def homework_kb(project_id, homework_id, id_user, number_of_pages=1, page_number=None, id_user_admin=None, id_chat=None):
    inline_kb = InlineKeyboardMarkup(row_width=1)

    if number_of_pages > 1:
        array = []
        if page_number is None:
            page_number = 0

        # array.append(AddInlBtn(text='<<', callback_data=f'homework {project_id} textprev'))
        for i in range(number_of_pages):
            text = str(i + 1)
            if i == page_number:
                if i == 0:
                    text = '1️⃣'
                elif i == 1:
                    text = '2️⃣'
                elif i == 2:
                    text = '3️⃣'
                elif i == 3:
                    text = '4️⃣'
                elif i == 4:
                    text = '5️⃣'
                elif i == 5:
                    text = '6️⃣'
                elif i == 6:
                    text = '7️⃣'
                elif i == 7:
                    text = '8️⃣'
                elif i == 8:
                    text = '9️⃣'
                elif i == 9:
                    text = '🔟'
                elif i == 10:
                    text = '1️⃣1️⃣'
                elif i == 11:
                    text = '1️⃣2️⃣'
                elif i == 12:
                    text = '1️⃣3️⃣'
                elif i == 13:
                    text = '1️⃣4️⃣'
                elif i == 14:
                    text = '1️⃣5️⃣'
                elif i == 15:
                    text = '1️⃣6️⃣'
                elif i == 16:
                    text = '1️⃣7️⃣'
                elif i == 17:
                    text = '1️⃣8️⃣'
                elif i == 18:
                    text = '1️⃣9️⃣'
                elif i == 19:
                    text = '2️⃣0️⃣'
                elif i == 20:
                    text = '2️⃣1️⃣'
                elif i == 21:
                    text = '2️⃣2️⃣'
                elif i == 22:
                    text = '2️⃣3️⃣'
                elif i == 23:
                    text = '2️⃣4️⃣'

            if id_user_admin is not None:
                array.append(AddInlBtn(text=text,
                        callback_data=f'admin_homework {project_id} text{str(i)} {id_chat} {homework_id} {id_user}'))
            else:
                array.append(AddInlBtn(text=text,
                        callback_data=f'homework {project_id} text{str(i)} {homework_id}'))
        # array.append(AddInlBtn(text='>>', callback_data=f'homework {project_id} textnext'))

        len_array = len(array)
        count = -(-len_array // 8)
        part_start = 0
        part_end = 8

        for i in range(count):
            array_part = array[part_start:part_end]
            inline_kb.row(*array_part)
            part_start = part_end
            part_end = part_start + 8

    if id_user_admin is not None:
        if await base.get_status_homework(project_id, homework_id, id_user):
            text = '✅ Принято. Нажмите чтобы <ВЕРНУТЬ>.'
            status = 'return'
        else:
            text = 'Выполняется. Нажмите чтобы <ПРИНЯТЬ>.'
            status = 'accept'
        inline_kb.add(AddInlBtn(text=text,
                                callback_data=f'admin_homework {project_id} {status} {id_chat} {homework_id} {id_user}'))

        # if status:
        #     inline_kb.row(
        #         AddInlBtn(text='Вернуть',
        #                   callback_data=f'admin_homework {project_id} return {id_chat} {homework_id} {id_user}'),
        #         AddInlBtn(text='✅ Принято', callback_data='-'))
        # else:
        #     inline_kb.row(
        #         AddInlBtn(text='В работе', callback_data='-'),
        #         AddInlBtn(text='Принять',
        #                   callback_data=f'admin_homework {project_id} accept {id_chat} {homework_id} {id_user}'))

        inline_kb.add(AddInlBtn(text='Назад', callback_data=f'admin_homework {project_id} choice {id_chat} {homework_id}'))

    else:
        inline_kb.add(AddInlBtn(text='Как выполнить ДЗ?', callback_data=f'homework {project_id} question'))
        inline_kb.add(AddInlBtn(text='Назад', callback_data=f'homework {project_id} choice'))

        await base.update_selected_homeworks(id_user, homework_id, project_id, True)

    return inline_kb


async def admin_homework_process(project_id, id_user_admin, status, id_chat, homework_id, id_user=None):
    # if homework_id in ('', None):
    #     homework_id = await base.get_homework_id_last_homework(project_id)

    text, inline_kb = '', InlineKeyboardMarkup(row_width=1)

    if status[:12] == 'choice_group':
        chats = await base.get_chats_admin_user(project_id, id_user_admin, id_chat)
        number_of_chats = len(chats)
        if number_of_chats == 0:
            await send_error(
                f"Пришло количество чатов 0 из base.get_chats_admin_user, "
                f"где project_id {project_id}, id_user {id_user_admin}", "", str(traceback.format_exc()))
            text = shielding('У вас нет чатов.')

        else:
            if number_of_chats == 1:
                id_chat = chats[0][0]

            if status == 'choice_group_back' and number_of_chats == 1:
                status = 'back_menu_back'
            else:
                status = 'group'

            text, inline_kb, status = \
                await admin_homework_process(project_id, id_user_admin, status, id_chat, homework_id, id_user)

    else:

        if status == 'choice' and homework_id is None:
            text = shielding('Домашние работы')
            inline_kb = await keyboard_homework_all(project_id, id_user, status, True, id_chat)

        elif status == 'choice' and homework_id is not None:
            chats = await base.get_chats_admin_user(project_id, id_user_admin, id_chat)
            current_chat = chats[0]
            title = current_chat[1]
            #
            users = await base.get_users_status_homework_in_chat(project_id, id_chat, homework_id)

            counter = 0
            for i in users:
                counter += 1
                i_id_user = i[0]
                i_name = i[1]
                homework_status = ''
                if i[2]:
                    homework_status = '✅'
                i_counter = ''
                if i[3] > 0:
                    i_counter = f' ({i[3]})'

                inline_kb.add(AddInlBtn(
                    text=f'{homework_status} {counter}. {i_name}{i_counter}',
                    callback_data=f'admin_homework {project_id} text {id_chat} {homework_id} {i_id_user}'))

            inline_kb.add(AddInlBtn(text='Назад', callback_data=f'admin_homework {project_id} group {id_chat}'))

            text = shielding(title + '\n Домашнее задание №' + str(homework_id))

        elif status[:4] == 'text' or status in ('response', 'feedback'):
            if status == 'text':
                status = 'text99'
            text, number_of_pages, page_number = await get_text_homework(project_id, homework_id, id_user, status)
            inline_kb = await homework_kb(project_id, homework_id, id_user, number_of_pages, page_number, id_user_admin, id_chat)

        elif status in ('accept', 'return'):
            accepted = status == 'accept'
            await base.set_status_homework(project_id, homework_id, id_user, id_user_admin, accepted)

            text, inline_kb, status = await admin_homework_process(project_id, id_user_admin, 'text99', id_chat, homework_id, id_user)

            await base.update_counter_homework(project_id, homework_id, id_user, True)

            homework_text = shielding('На ваше домашнее задание получен отклик куратора.')
            homework_inline_kb = InlineKeyboardMarkup(row_width=1)
            homework_inline_kb.add(AddInlBtn(
                text='Посмотреть',
                callback_data=f'homework {project_id} feedback {homework_id}'))
            await message_send(id_user, homework_text, homework_inline_kb)

        # elif status == 'return':
        #     await base.set_status_homework(project_id, homework_id, id_user, "Возвращено", True)
        #
        #     status_meaning, accepted, response_is_filled, user_info = \
        #         await base.get_date_status_meaning_homework("feedback", project_id, homework_id, id_user)
        #
        #     inline_kb = await homework_kb_admin(id_user_admin, project_id, id_chat, homework_id, id_user,
        #                                         "feedback", response_is_filled)
        #
        #     if status_meaning is None:
        #         text = 'Вы вернули домашнее задание на доработку. Оставите отклик?'
        #         text += message_requirements()
        #         text = shielding(text)
        #     else:
        #         text = shielding(status_meaning)

        elif status == 'group':
            if id_chat is None:
                chats = await base.get_chats_admin_user(project_id, id_user_admin, id_chat)
                for i in chats:
                    i_id_chat = i[0]
                    i_title = i[1]
                    inline_kb.add(AddInlBtn(text=i_title, callback_data=f'admin_homework {project_id} group {i_id_chat}'))
                inline_kb.add(AddInlBtn(text='Назад', callback_data=f'admin_homework {project_id} back_menu_back'))

                text = shielding('Домашние задания. \nВыберете группу для проверки домашних заданий:')

            else:
                text, inline_kb, status = await admin_homework_process(project_id, id_user_admin, 'choice', id_chat, homework_id, id_user)

        elif status == 'back_menu_back':
            pass

        elif status == 'back_user':
            text, inline_kb, status = await admin_homework_process(project_id, id_user_admin, 'choice', id_chat, 0, homework_id)

        elif status == 'back':
            chats = await base.get_chats_admin_user(project_id, id_user_admin, 0)
            number_of_chats = len(chats)

            if number_of_chats == 1:
                status = 'back_menu_back'

            elif number_of_chats > 1:
                id_chat = 0
                status = 'group'

                text, inline_kb, status = await admin_homework_process(project_id, id_user_admin, status, 0, id_chat, homework_id)

    return text, inline_kb, status


async def homework_process(project_id, id_user, status, homework_id, message_text=''):
    text = ''
    inline_kb = InlineKeyboardMarkup(row_width=1)

    if status == '':
        cursor.execute(
            'SELECT projects.name, project_administrators.status FROM project_administrators '
            'INNER JOIN projects ON project_administrators.project_id = projects.project_id '
            'WHERE project_administrators.id_user = %s AND project_administrators.project_id = %s',
            (id_user, project_id))
        meaning = cursor.fetchone()

        text = f'Введите текст сообщения, который бот отправит всем студентам всех групп проекта "{meaning[0]}". '
        text += message_requirements()
        text = shielding(text)
        inline_kb.add(AddInlBtn(text='Отмена', callback_data=f'homework {project_id} back'))

        cursor.execute(
            'UPDATE project_administrators SET status = %s, message_id = %s WHERE project_id = %s AND id_user = %s',
            ('text', message_text, project_id, id_user))
        connect.commit()

    elif status == 'confirm':
        message_text = message_text.replace('`', '')
        message_text = message_text.replace('\\', '')
        cursor.execute('UPDATE project_administrators SET status = %s, text = %s WHERE project_id = %s AND id_user = %s',
                       ('confirm', message_text, project_id, id_user))
        connect.commit()

        cursor.execute(
            'SELECT project_administrators.message_id, projects.name FROM projects '
            'INNER JOIN project_administrators ON projects.project_id = project_administrators.project_id '
            'AND project_administrators.id_user = %s '
            'WHERE projects.project_id = %s', (id_user, project_id))
        meaning = cursor.fetchone()
        if meaning is not None:
            text = shielding(message_text)
            inline_kb.add(AddInlBtn(text='Отправить как домашнее задание', callback_data=f'homework {project_id} homework'))
            inline_kb.add(AddInlBtn(text='Отправить как рассылку', callback_data=f'homework {project_id} sending'))
            inline_kb.add(AddInlBtn(text='Отмена', callback_data=f'homework {project_id} back'))

    elif status in ('homework', 'sending'):
        homework_id = await base.get_homework_id_last_homework(project_id)
        homework_id += 1

        cursor.execute('SELECT text FROM project_administrators WHERE id_user = %s AND project_id = %s',
                       (id_user, project_id))
        meaning = cursor.fetchone()
        sending_text = meaning[0]

        if status == 'homework':
            cursor.execute(
                'INSERT INTO homeworks_task (project_id, sender_id, homework_id, text, date) VALUES (%s, %s, %s, %s, NOW())',
                (project_id, id_user, homework_id, sending_text))
            connect.commit()

        sending_text = shielding(sending_text)

        cursor.execute(
            '''SELECT DISTINCT 
                users.id_user,  
                coalesce(users.menu_message_id, 0),
                users.role = 'user'
            FROM settings 
            INNER JOIN chats 
                ON settings.id_chat = chats.id_chat 
                    AND NOT chats.deleted AND settings.enable_group 
                    AND settings.project_id = %s
            INNER JOIN users 
                ON chats.id_user = users.id_user 
            --INNER JOIN project_administrators 
            --    ON users.id_user = project_administrators.id_user''',
            (project_id,)
        )
        meaning = cursor.fetchall()

        # message_progress_bar
        all_count = len(meaning)
        count = 0
        message_pb = None
        time_point = None
        #

        for i in meaning:
            i_id_user = i[0]
            i_message_id = i[1]
            its_homework = i[2] and status == 'homework'

            if its_homework:
                inline_kb = await homework_kb(project_id, homework_id, id_user)
            else:
                inline_kb = InlineKeyboardMarkup(row_width=1)

            if i_message_id > 0:
                await message_delete_by_id(i_id_user, i_message_id)

            await message_send(i_id_user, sending_text, inline_kb)

            # message_progress_bar
            count += 1
            message_pb, time_point = await message_progress_bar(id_user, all_count, count, time_point, message_pb)
            #

            if not its_homework:
                i_text, i_inline_kb = await get_start_menu(i_id_user)
                await message_send(i_id_user, i_text, i_inline_kb)

        cursor.execute(
            'UPDATE project_administrators SET status = NULL, text = NULL, message_id = 0 '
            'WHERE project_id = %s AND id_user = %s', (project_id, id_user))
        connect.commit()

        # message_progress_bar
        await message_pb.delete()
        #

        await message_send(id_user, 'Выполнено')

    elif status == 'choice':
        await base.update_selected_homeworks(id_user)

        text = shielding('Домашние работы')
        inline_kb = await keyboard_homework_all(project_id, id_user)

    elif status[:4] == 'text':
        text, number_of_pages, page_number = await get_text_homework(project_id, homework_id, id_user, status)
        inline_kb = await homework_kb(project_id, homework_id, id_user, number_of_pages, page_number)

    elif status in ('response', 'feedback'):
        status_meaning, accepted, user_info = \
            await base.get_date_status_meaning_homework(status, project_id, homework_id, id_user)
        if status_meaning in ('', None):
            if status == 'response':
                text = 'Для того, чтобы выполнить домашнее задание — пришлите ответ сообщением.'
                text += message_requirements()
            if status == 'feedback':
                if accepted:
                    text = 'Ваше домашнее задание принято.'
                # elif response_is_filled:
                #     text = 'Ваше домашнее задание на проверке у куратора.'
                else:
                    text = 'Для начала выполните домашнее задание.'
        else:
            text = status_meaning

        text = shielding(text)
        inline_kb = await homework_kb(project_id, homework_id, id_user)

    elif status == 'back':
        cursor.execute(
            'UPDATE project_administrators SET status = NULL, text = NULL, message_id = 0 '
            'WHERE project_id = %s AND id_user = %s', (project_id, id_user))
        connect.commit()

    return text, inline_kb, status


async def registration_command(callback_message):
    # id_user = callback_message.from_user.id
    # first_name = callback_message.from_user.first_name
    # last_name = callback_message.from_user.last_name
    # if last_name is None:
    #     last_name = ''
    # username = callback_message.from_user.username
    # if username is None:
    #     username = ''
    # language_code = callback_message.from_user.language_code

    # cursor.execute('SELECT id_user FROM users WHERE id_user = %s', (id_user,))
    # result = cursor.fetchone()
    #
    # if result is None:
    #     today = get_today()
    #     cursor.execute(
    #         """INSERT INTO users (
    #             id_user,
    #             first_name,
    #             last_name,
    #             username,
    #             language_code,
    #             registration_date,
    #             role)
    #         VALUES (%s, %s, %s, %s, %s, %s, 'user')""",
    #         (id_user, first_name, last_name, username, language_code, today))
    # else:
    #     cursor.execute(
    #         "UPDATE users SET first_name = %s, last_name = %s, username = %s, language_code = %s WHERE id_user = %s",
    #         (first_name, last_name, username, language_code, id_user))
    # connect.commit()
    await base.insert_or_update_users(callback_message.from_user)

    if type(callback_message) == CallbackQuery:
        message = callback_message.message
    else:
        message = callback_message

    await registration_process(message, its_callback=False)


async def registration_process(message: Message, meaning='', its_callback=False):
    id_user = message.chat.id

    cursor.execute(
        "SELECT DISTINCT coalesce(users.registration_field, ''), users.menu_message_id, projects.name, projects.invite_link FROM chats "
        "INNER JOIN settings ON chats.id_chat = settings.id_chat "
        "INNER JOIN users ON chats.id_user = users.id_user "
        "INNER JOIN projects ON settings.project_id = projects.project_id "
        "WHERE settings.enable_group AND chats.id_user = %s", (id_user,))
    result_tuple = cursor.fetchone()

    if result_tuple is None:
        return

    registration_field = result_tuple[0]
    message_id = result_tuple[1]
    invite_link = result_tuple[3]

    new_registration_field = ''
    text = ''
    inline_kb = InlineKeyboardMarkup(row_width=1)
    delete_my_message = True

    if registration_field == '':
        new_registration_field = 'gender'
        text = 'Шаг 1 из 7. \nВаш пол:'
        inline_kb.add(AddInlBtn(text='Мужской', callback_data='gender Мужской'))
        inline_kb.add(AddInlBtn(text='Женский', callback_data='gender Женский'))

    elif registration_field == 'gender':
        if its_callback:
            new_registration_field = 'fio'
            text = 'Шаг 2 из 7. \nВведите ваши имя и фамилию:'
        else:
            try:
                await message.delete()
            except Exception as e:
                pass
            return

    elif registration_field == 'fio':
        new_registration_field = 'birthdate'
        text = 'Шаг 3 из 7. \nДата вашего рождения в формате ДД.ММ.ГГГГ или ДДММГГГГ:'

    elif registration_field == 'birthdate':
        fail = False

        format_date = ''
        if len(meaning) == 10 and meaning.count('.') == 2:
            format_date = '%d.%m.%Y'
        elif len(meaning) == 8 and meaning.count('.') == 0:
            format_date = '%d%m%Y'
        else:
            fail = True

        if not fail:
            try:
                meaning = datetime.datetime.strptime(meaning, format_date)
                fail = False
            except Exception as e:
                fail = True

        if fail:
            try:
                await message.delete()
            except Exception as e:
                pass
            return

        new_registration_field = 'address'
        text = 'Шаг 4 из 7. \nВведите ваши страну и город:'

    elif registration_field == 'address':
        new_registration_field = 'tel'
        text = 'Шаг 5 из 7. \nВведите ваш номер телефона:'

    elif registration_field == 'tel':
        new_registration_field = 'mail'
        text = 'Шаг 6 из 7. \nВведите адрес вашей электронной почты:'

    elif registration_field == 'mail':
        # new_registration_field = 'projects'
        # inline_kb = await get_projects_cb('', 'projects')
        # text = 'Шаг 7 из 7. \nЕсли вы обучались ранее в наших проектах, пожалуйста, отметьте их:'

        new_registration_field = 'done'

        inline_kb = InlineKeyboardMarkup(row_width=1)
        inline_kb.add(AddInlBtn('Заявка на вступление', url=invite_link))
        text = 'Шаг 7 из 7. \nУчебные материалы будут выкладываться в канал. Подайте заявку на вступление (будет принята автоматически).'

    # elif registration_field == 'projects':
    #     if its_callback:
    #         if not meaning == 'Готово':
    #             delete_my_message = False
    #             new_registration_field = ''
    #             cursor.execute(f'SELECT projects FROM users WHERE id_user = {id_user}')
    #             projects = cursor.fetchone()[0]
    #             if meaning in projects:
    #                 projects = projects.replace(meaning + ';', '')
    #             else:
    #                 projects += meaning + ';'
    #             meaning = projects
    #
    #             inline_kb = await get_projects_cb(projects, 'projects')
    #             text = message.text
    #             text = shielding(text)
    #
    #             await message.edit_text(text, reply_markup=inline_kb, parse_mode='MarkdownV2')
    #
    #         else:
    #             new_registration_field = 'done'
    #             registration_field = ''
    #
    #         # elif registration_field == 'done':
    #             # inviteToChannel
    #
    #             # 1
    #             invite_link = INVITE_LINK
    #
    #             # 2
    #             # cursor.execute(f'SELECT first_name, last_name, username FROM users WHERE id_user = {id_user}')
    #             # user = cursor.fetchone()
    #             # name = f'{user[0]}, {user[1]}, {user[2]}, {id_user}'
    #             # result = await bot.create_chat_invite_link(chat_id=CHANNEL_ID, name=name, member_limit=1)
    #             # invite_link = result.invite_link
    #
    #             inline_kb = InlineKeyboardMarkup(row_width=1)
    #             inline_kb.add(AddInlBtn('Заявка на вступление', url=invite_link`))
    #
    #             text = 'Шаг 8 из 7. \nУчебные материалы будут выкладываться в канал. Подайте заявку на вступление (будет принята автоматически).'
    #     else:
    #         try:
    #             await message.delete()
    #         except Exception as e:
    #             pass
    #         return

    if not text == '':
        text = shielding(text)

    if delete_my_message:
        if message_id is not None and not message_id == '' and not message_id == message.message_id:
            await message_delete_by_id(id_user, message_id)
        try:
            await message.delete()
        except Exception as e:
            pass

        if not text == '':
            await message_send(id_user, text, inline_kb)

    if registration_field == 'done':
        return

    query_text = ''

    if not registration_field == '':
        query_text = f'''{registration_field} = '{meaning}' '''

    if not new_registration_field == '':
        if not query_text == '':
            query_text += ', '

        query_text += f'''registration_field = '{new_registration_field}' '''

    if not query_text == '':
        query_text += ', '

    query_text += f'menu_message_id = {message.message_id}'
    query_text = f'''UPDATE users SET {query_text} WHERE id_user = {id_user}'''
    try:
        cursor.execute(query_text)
        connect.commit()
    except Exception as e:
        await send_error('', str(e), traceback.format_exc())


async def process_parameter_continuation(callback: CallbackQuery, id_chat, id_user, parameter_name, parameter_value):
    cursor.execute(f'UPDATE settings SET {parameter_name} = %s WHERE id_chat = %s', (parameter_value, id_chat))
    connect.commit()

    text, inline_kb = await setting_up_a_chat(id_chat, id_user)
    await callback_edit_text(callback, text, inline_kb)


async def setting_up_a_chat(id_chat, id_user, back_button=True, super_admin=False):
    cursor.execute(
        '''SELECT 
            settings.statistics_for_everyone,
            settings.include_admins_in_statistics,
            settings.sort_by,
            settings.period_of_activity,
            settings.report_enabled,
            coalesce(projects.name, ''),
            settings.do_not_output_name_from_registration,
            settings.check_channel_subscription,
            settings.title	
        FROM settings 
            LEFT OUTER JOIN projects 
                ON settings.project_id = projects.project_id
        WHERE 
            enable_group 
            AND id_chat = %s''', (id_chat,)
    )
    meaning = cursor.fetchone()

    if meaning is None:
        return '', ''

    statistics_for_everyone = meaning[0]
    include_admins_in_statistics = meaning[1]
    sort_by = meaning[2]
    period_of_activity = meaning[3]
    report_enabled = meaning[4]
    projects_name = meaning[5]
    do_not_output_name_from_registration = meaning[6]
    check_channel_subscription = meaning[7]
    title = meaning[8]

    inline_kb = InlineKeyboardMarkup(row_width=1)
    if statistics_for_everyone:
        text='Статистика доступна всем'
    else:
        text='Статистика доступна только администраторам'
    inline_kb.add(AddInlBtn(
        text=text,
        callback_data=f'settings {id_chat} statistics_for_everyone {convert_bool_binary(statistics_for_everyone)}'))

    inline_kb.add(AddInlBtn(
        text='Включать админов в статистику: ' + convert_bool(include_admins_in_statistics),
        callback_data=
        f'settings {id_chat} include_admins_in_statistics {convert_bool_binary(include_admins_in_statistics)}'))

    if sort_by == 'characters':
        text = 'Сортировка по количеству символов'
    elif sort_by == 'messages':
        text = 'Сортировка по сообщениям'
    else:
        text = 'Сортировка по домашним заданиям'
    inline_kb.add(AddInlBtn(
        text=text,
        callback_data=f'settings {id_chat} sort_by {sort_by}'))

    inline_kb.add(AddInlBtn(
        text='Статистика за период (дней): ' + str(period_of_activity),
        callback_data=f'settings {id_chat} period_of_activity {period_of_activity}'))

    inline_kb.add(AddInlBtn(
        text='Автоматический отчет в чат: ' + convert_bool(report_enabled),
        callback_data=f'settings {id_chat} report_enabled {convert_bool_binary(report_enabled)}'))

    inline_kb.add(AddInlBtn(
        text='Проект: ' + projects_name,
        callback_data=f'settings {id_chat} project_name'))

    if do_not_output_name_from_registration:
        text='Имя и фамилия пользователя'
    else:
        text = 'Имя и фамилия из регистрации'
    inline_kb.add(AddInlBtn(
        text=text,
        callback_data=f'settings {id_chat} do_not_output_name_from_registration '
                      f'{convert_bool_binary(do_not_output_name_from_registration)}'))

    subscription_off = ''
    if check_channel_subscription:
        subscription_off = ' ⚠️'
    inline_kb.add(AddInlBtn(
        text='Проверять подписку на канал : ' + convert_bool(check_channel_subscription) + subscription_off,
        callback_data=
        f'settings {id_chat} check_channel_subscription {convert_bool_binary(check_channel_subscription)}'))

    if back_button:
        inline_kb.add(AddInlBtn(text='Назад', callback_data='back'))

    if super_admin:
        inline_kb.add(AddInlBtn(text='Назад', callback_data='super_admin '))

    text = await get_stat(id_chat, id_user)
    group_name = shielding(title)

    return '*Группа "' + group_name + '"\.*\n\n' + text, inline_kb
