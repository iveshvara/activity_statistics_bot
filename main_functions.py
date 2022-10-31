
from bot_base import bot, cursor, connect, base, send_error
from _settings import SUPER_ADMIN_ID
from service import its_admin, shielding, get_name_tg, reduce_large_numbers, get_today, message_requirements
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton as AddInlBtn
# from aiogram.contrib.middlewares.logging import LoggingMiddleware
import datetime
import traceback


async def run_reminder():
    result = await base.get_chats_for_reminder()
    for i in result:
        id_chat = i[0]
        text = await get_stat(id_chat)

        if not text == '':
            try:
                await bot.send_message(text=text, chat_id=id_chat, parse_mode='MarkdownV2', disable_notification=True)
            except Exception as e:
                await send_error(text, str(e), traceback.format_exc())

            await base.save_last_notify_date_reminder(id_chat)

    # text = ''
    #
    # cursor.execute(
    #     '''SELECT DISTINCT
    #         messages_one.id_chat AS id_chat,
    #         messages_two.id_user,
    #         chats.first_name,
    #         chats.last_name,
    #         chats.username
    #     FROM
    #         messages AS messages_one
    #         LEFT JOIN settings ON settings.id_chat = messages_one.id_chat
    #         LEFT JOIN messages AS messages_two ON messages_one.id_chat = messages_two.id_chat
    #                 AND messages_one.message_id = messages_two.message_id
    #                 AND messages_one.message_id > 0
    #         LEFT JOIN chats ON messages_two.id_chat = chats.id_chat
    #                 AND messages_two.id_user = chats.id_user
    #     WHERE
    #         messages_one.message_id > 0
    #         AND settings.enable_group
    #         AND settings.period_of_activity > Round(JulianDay("now") - JulianDay(messages_one.date), 0)
    #         AND Date(settings.last_notify_message_id_date) < Date("now")
    #     GROUP BY
    #         messages_one.id_chat,
    #         messages_two.id_user,
    #         chats.first_name,
    #         chats.last_name,
    #         chats.username,
    #         messages_one.message_id
    #     ORDER BY
    #         id_chat'''
    # )
    # result_tuple = cursor.fetchall()
    # last_id_chat = None
    # id_chat_text_tuple = []
    # for i in result_tuple:
    #     id_chat = i[0]
    #     if not last_id_chat == id_chat:
    #         if last_id_chat is None:
    #             last_id_chat = id_chat
    #         else:
    #             id_chat_text_tuple.append((last_id_chat, text))
    #             text = ''
    #             last_id_chat = id_chat
    #
    #     id_user = i[1]
    #     first_name = i[2]
    #     last_name = i[3]
    #     username = i[4]
    #     text += await get_name_tg(id_user, first_name, last_name, username)
    # else:
    #     if last_id_chat is not None:
    #         id_chat_text_tuple.append([last_id_chat, text])
    #
    # for i in id_chat_text_tuple:
    #     id_chat = i[0]
    #     text = i[1]
    #     text = 'Сегодня не откликнулись на запрос\: \n' + text + '\n \#ВажноеСообщение'
    #     try:
    #         await bot.send_message(text=text, chat_id=id_chat, parse_mode='MarkdownV2', disable_notification=True)
    #     except Exception as e:
    #         pass
    #
    #     cursor.execute('UPDATE settings SET last_notify_message_id_date = datetime("now") WHERE id_chat = %s',
    #                    (id_chat,))
    #     connect.commit()


async def get_stat(id_chat, id_user=None):
    statistics_for_everyone = False
    include_admins_in_statistics = False
    try:
        chat_admins = await bot.get_chat_administrators(id_chat)
    except Exception as e:
        chat_admins = ()
    period_of_activity = 0
    sort_by_messages = False
    do_not_output_the_number_of_messages = False
    do_not_output_the_number_of_characters = False
    check_channel_subscription = False
    channel_id = 0
    do_not_output_name_from_registration = False

    cursor.execute(
        '''SELECT 
            settings.statistics_for_everyone, 
            settings.include_admins_in_statistics, 
            settings.period_of_activity, 
            settings.sort_by_messages, 
            settings.do_not_output_the_number_of_messages, 
            settings.do_not_output_the_number_of_characters, 
            settings.check_channel_subscription, 
            coalesce(projects.channel_id, 0),
            settings.do_not_output_name_from_registration
        FROM settings 
        LEFT OUTER JOIN projects 
                ON settings.project_id = projects.project_id
        WHERE id_chat = %s''', (id_chat,))
    meaning = cursor.fetchone()
    if meaning is not None:
        statistics_for_everyone = meaning[0]
        include_admins_in_statistics = meaning[1]
        period_of_activity = meaning[2]
        sort_by_messages = meaning[3]
        do_not_output_the_number_of_messages = meaning[4]
        do_not_output_the_number_of_characters = meaning[5]
        check_channel_subscription = meaning[6]
        channel_id = meaning[7]
        do_not_output_name_from_registration = meaning[8]

    if statistics_for_everyone or its_admin(id_user, chat_admins) or id_user is None:
        if sort_by_messages:
            sort = 'messages'
        else:
            sort = 'characters'

        today = get_today()
        count_messages = 0
        cursor.execute(
            f'''SELECT 
                users.id_user, 
                users.first_name, 
                coalesce(users.last_name, ''), 
                coalesce(users.username, ''), 
                coalesce(users.fio, ''),
                SUM(coalesce(messages.characters, 0)) AS characters, 
                COUNT(messages.characters) AS messages, 
                chats.deleted, 
                chats.date_of_the_last_message, 
                CASE 
                    WHEN NOT chats.deleted 
                        AND {period_of_activity} > DATE_PART('day', '{today}' - chats.date_of_the_last_message) 
                        THEN 0 
                    ELSE DATE_PART('day', '{today}' - chats.date_of_the_last_message) 
                END AS inactive_days
            FROM chats 
            LEFT JOIN messages 
                ON chats.id_chat = messages.id_chat 
                    AND chats.id_user = messages.id_user 
                    AND {period_of_activity} > DATE_PART('day', '{today}' - messages.date)
            INNER JOIN users 
                ON chats.id_user = users.id_user  
            WHERE 
                chats.id_chat = {id_chat} 
                AND users.id_user IS NOT NULL
            GROUP BY 
                users.id_user, 
                users.first_name, 
                coalesce(users.last_name, ''), 
                coalesce(users.username, ''), 
                coalesce(users.fio, ''),
                chats.deleted, 
                chats.date_of_the_last_message, 
                inactive_days
            ORDER BY deleted ASC, inactive_days ASC, {sort} DESC '''
        )
        meaning = cursor.fetchall()
        # row_count = len(meaning)
        # row_count = int(len(str(row_count)))
        #
        # text = '`' + align_by_number_of_characters('N', row_count) + ' |  ✉ |    🖋️`'
        text = '*N\. Пользователь: `Сообщений/Символов`*\n'

        # requests = None
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
            i_characters = reduce_large_numbers(i[5])
            i_messages = i[6]
            i_deleted = i[7]
            i_date_of_the_last_message = i[8]
            i_inactive_days = i[9]
            # if requests is None:
            #     requests = i[10]
            # i_response = i[11]

            if not include_admins_in_statistics:
                if its_admin(i_id_user, chat_admins):
                    continue

            if i_inactive_days > 0 and not i_deleted and not active_members_inscription_is_shown:
                active_members_inscription_is_shown = True
                text += f'\n\n*Неактивные участники* \(больше {period_of_activity} дней\):'

            if i_deleted and not deleted_members_inscription_is_shown:
                deleted_members_inscription_is_shown = True
                text += f'\n\n*Вышедшие участники:*'
                count_messages = 0

            count_messages += 1

            channel_subscription = ''
            specifics = ''
            characters = ''
            messages = ''
            response = ''

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
                    channel_subscription = '⚠️ '  # 'Не подписан на канал\. \n     — '

            if not do_not_output_the_number_of_characters:
                characters = str(i_characters)  # символов 💬 🖌

            if not do_not_output_the_number_of_messages:
                messages = str(i_messages)  # сообщений 📃

            # if requests > 0:
            #     response = f'откликов: {i_response} из {requests}'

            inactive = ''
            if i_deleted:
                data_str = shielding(i_date_of_the_last_message.strftime("%d.%m.%Y"))  # "%d.%m.%Y %H:%M:%S"
                inactive = f' \(вне чата с {data_str}, дней назад: {int(i_inactive_days)}\)'
            elif i_inactive_days > 0:
                inactive = f' \(неактивен дней: {int(i_inactive_days)}\)'
            else:
                specifics += ': `' + messages + '/' + characters + '`'

            user = await get_name_tg(i_id_user, i_first_name, i_last_name, i_username, i_fio)
            count_messages_text = str(count_messages)
            text += f'\n{count_messages_text}\. {channel_subscription}{user}{specifics}{inactive}'

        if text == '*Активные участники:*\n':
            text = 'Нет статистики для отображения\.'

    else:
        text = 'Статистику могут показать только администраторы группы\.'

    return text


async def get_start_menu(id_user):
    # Есть уже в base
    cursor.execute(
        'SELECT DISTINCT settings.id_chat, settings.title, settings.project_id FROM settings '
        'LEFT OUTER JOIN chats ON chats.id_chat = settings.id_chat '
        'WHERE settings.enable_group AND id_user = %s', (id_user,))
    meaning = cursor.fetchall()
    user_groups = []
    channel_enabled = False
    for i in meaning:
        get = False
        try:
            # chat_admins = await bot.get_chat_administrators(i[0])
            # get = its_admin(i[0], chat_admins)
            member = await bot.get_chat_member(i[0], id_user)
            get = member.is_chat_admin()
        except Exception as e:
            pass

        if get:
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
    homework_date = await base.get_date_last_homework(project_id)
    admin = await base.its_admin(id_user)
    if admin:
        inline_kb.add(AddInlBtn(text='Домашние работы', callback_data=f'admin_homework {project_id} На_проверке'))
    elif homework_date is not None:
        inline_kb.add(AddInlBtn(text='Домашние работы', callback_data=f'homework {project_id} text {homework_date}'))

    if await base.its_admin_project(id_user, project_id):
        inline_kb.add(AddInlBtn(text='[Рассылка по "' + project_name + '"]', callback_data=f'homework {project_id}'))

    if id_user == SUPER_ADMIN_ID:
        inline_kb.add(AddInlBtn(text='[super admin functions]', callback_data='super_admin '))

    return text, inline_kb


async def homework_kb(project_id, id_user, homework_date=None, status='text'):
    text_text = 'Задание'
    text_response = 'Ваш ответ'
    text_feedback = 'Отклик куратора'

    if status == 'text':
        text_text = '⭕ ' + text_text
    elif status == 'response':
        text_response = '⭕ ' + text_response
    elif status == 'feedback':
        text_feedback = '⭕ ' + text_feedback

    homework_date_text = homework_date.strftime("%Y-%m-%d")

    inline_kb = InlineKeyboardMarkup(row_width=1)
    inline_kb.row(
        AddInlBtn(text=text_text, callback_data=f'homework {project_id} text {homework_date_text}'),
        AddInlBtn(text=text_response, callback_data=f'homework {project_id} response {homework_date_text}'),
        AddInlBtn(text=text_feedback, callback_data=f'homework {project_id} feedback {homework_date_text}')
    )

    cursor.execute('UPDATE homework_check SET selected = False WHERE project_id = %s AND id_user = %s',
                   (project_id, id_user))
    cursor.execute('UPDATE homework_check SET selected = True WHERE project_id = %s AND id_user = %s AND date = %s',
                   (project_id, id_user, homework_date))
    connect.commit()

    cursor.execute(
        "SELECT date, status, status = 'Принято' FROM homework_check WHERE project_id = %s AND id_user = %s"
        "ORDER BY date",
                   (project_id, id_user))
    result = cursor.fetchall()
    for i in result:
        date = i[0]
        homework_status = i[1]
        accepted = i[2]

        icon = ''
        homework_accepted = ''
        if homework_date == date:
            icon = '🔴'
        # else:
        #     if accepted:
        #         current = '✅'

        inline_kb.add(AddInlBtn(
            text=icon + ' ' + date.strftime("%d.%m.%Y") + ' — ' + homework_status,
            callback_data=f'homework {project_id} {status} {date}'))

    inline_kb.add(AddInlBtn(text='Назад', callback_data=f'homework {project_id} back'))

    return inline_kb


async def homework_kb_admin(id_user_admin, project_id, id_user, id_chat, homework_date,
                            status, status_number, response_is_filled=True):
    text_text = 'Задание'
    text_response = 'Ответ студента'
    text_feedback = 'Ваш ответ'

    if status == 'text':
        text_text = '⭕ ' + text_text
    elif status == 'response':
        text_response = '⭕ ' + text_response
    elif status in ('feedback', 'accept', 'return'):
        text_feedback = '⭕ ' + text_feedback

    hd_text = homework_date.strftime("%Y-%m-%d")

    inline_kb = InlineKeyboardMarkup(row_width=1)
    inline_kb.row(
        AddInlBtn(text=text_text,
                  callback_data=f'admin_homework {project_id} text {id_user} {id_chat} {hd_text}'),
        AddInlBtn(text=text_response,
                  callback_data=f'admin_homework {project_id} response {id_user} {id_chat} {hd_text}'),
        AddInlBtn(text=text_feedback,
                  callback_data=f'admin_homework {project_id} feedback {id_user} {id_chat} {hd_text}')
    )
    if response_is_filled:
        inline_kb.row(
            AddInlBtn(text='✅ Принять',
                      callback_data=f'admin_homework {project_id} accept {id_user} {id_chat} {hd_text}'),
            AddInlBtn(text='❌ Вернуть',
                      callback_data=f'admin_homework {project_id} return {id_user} {id_chat} {hd_text}')
        )
    else:
        inline_kb.row(
            AddInlBtn(text='-', callback_data='-'),
            AddInlBtn(text='-', callback_data='-')
        )

    await base.set_admin_homework(project_id, homework_date, id_user, id_user_admin)

    cursor.execute(
        """SELECT 
            date, 
            status, 
            status = 'Принято' 
        FROM homework_check 
        WHERE 
            project_id = %s 
                AND id_user = %s
        ORDER BY
            date""", (project_id, id_user))
    result = cursor.fetchall()
    for i in result:
        date = i[0]
        homework_status = i[1]
        accepted = i[2]

        icon = ''
        if homework_date == date:
            icon = '🔴'

        inline_kb.add(AddInlBtn(
            text=icon + ' ' + date.strftime("%d.%m.%Y") + ' — ' + homework_status,
            callback_data=f'admin_homework {project_id} {status} {id_user} {id_chat} {date}'))

    inline_kb.add(AddInlBtn(
        text='Назад',
        callback_data=f'admin_homework {project_id} back_user/{status_number} 0 {id_chat}'))

    return inline_kb


async def admin_homework_process(project_id, id_user_admin, status, id_user, id_chat, homework_date=None):
    if homework_date in ('', None):
        homework_date = await base.get_date_last_homework(project_id)

    text, user_info, inline_kb = '', '', InlineKeyboardMarkup(row_width=1)

    separator = status.find('/')
    if separator == -1:
        status_back = 'На_проверке'
        status_number = '1'
    else:
        status_number = status[separator+1:]
        if status_number == '1':
            status_back = 'На_проверке'
        elif status_number == '2':
            status_back = 'Принято'
        elif status_number == '3':
            status_back = 'Получено'
        elif status_number == '4':
            status_back = 'Возвращено'
        status = status[:separator]

    if status in ('На_проверке', 'Возвращено', 'Получено', 'Принято'):
        chats = await base.get_chats_admin_user(project_id, id_user_admin, id_chat)
        number_of_chats = len(chats)

        if number_of_chats == 0:
            await send_error(
                f"Пришло количество чатов 0 из base.get_chats_admin_user, "
                f"где project_id {project_id}, id_user {id_user_admin}", "", str(traceback.format_exc()))
            text = 'У вас нет чатов.'

        elif number_of_chats > 1:
            text, user_info, inline_kb, status = \
                await admin_homework_process(project_id, id_user_admin, 'group', id_user, id_chat, homework_date)

        else:
            current_chat = chats[0]
            id_chat = current_chat[0]
            title = current_chat[1]
            users = await base.get_users_status_homeworks_in_chats(project_id, id_chat)
            status_text = status.replace('_', ' ')
            counter_status_1 = 0
            counter_status_2 = 0
            counter_status_3 = 0
            counter_status_4 = 0
            users_array = []

            for i in users:
                i_status = i[0]
                i_id_user = i[1]
                i_name = i[2]

                if i_status == 'На проверке':
                    status_number = 1
                    counter_status_1 += 1
                elif i_status == 'Принято':
                    status_number = 2
                    counter_status_2 += 1
                elif i_status == 'Получено':
                    status_number = 3
                    counter_status_3 += 1
                elif i_status == 'Возвращено':
                    status_number = 4
                    counter_status_4 += 1

                if i_status == status_text:
                    # users_array.append(AddInlBtn(
                    inline_kb.add(AddInlBtn(
                        text=i_name,
                        callback_data=f'admin_homework {project_id} response/{status_number} '
                                      f'{i_id_user} {id_chat} {homework_date}'))

            inline_kb.row(
                AddInlBtn(text='На проверке ' + str(counter_status_1),
                          callback_data=f'admin_homework {project_id} На_проверке'),
                AddInlBtn(text='Принято ' + str(counter_status_2),
                          callback_data=f'admin_homework {project_id} Принято'))
            inline_kb.row(
                AddInlBtn(text='Получено ' + str(counter_status_3),
                          callback_data=f'admin_homework {project_id} Получено'),
                AddInlBtn(text='Возвращено ' + str(counter_status_4),
                          callback_data=f'admin_homework {project_id} Возвращено'))

            # inline_kb.add(*users_array)
            inline_kb.add(AddInlBtn(text='Назад', callback_data=f'admin_homework {project_id} back {id_user_admin}'))

            text = title + f': {status_text}'

    elif status in ('text', 'response', 'feedback'):
        status_meaning, accepted, response_is_filled, user_info = \
            await base.get_date_status_meaning_homework(status, project_id, homework_date, id_user)

        inline_kb = await homework_kb_admin(id_user_admin, project_id, id_user, id_chat, homework_date,
                                            status, status_number, response_is_filled)

        if status_meaning in ('', None):
            text = 'Нет данных'
            if status == 'response':
                text = 'Студент еще не выполнил домашнее задание.'
            elif status == 'feedback':
                if accepted:
                    text = 'Вы уже приняли это домашнее задание.'
                elif response_is_filled:
                    text = 'Для того, чтобы оставить отклик на домашнее задание — пришлите сообщение в ответ.'
                    text += message_requirements()
                else:
                    text = 'Пока рано откликаться, студент еще не выполнил домашнее задание.'
        else:
            text = status_meaning

    elif status == 'accept':
        await base.set_status_homework(project_id, homework_date, id_user, "Принято", True)

        status_meaning, accepted, response_is_filled, user_info = \
            await base.get_date_status_meaning_homework("feedback", project_id, homework_date, id_user)

        inline_kb = await homework_kb_admin(id_user_admin, project_id, id_user, id_chat, homework_date,
                                            "feedback", status_number, response_is_filled)

        text = 'Вы приняли домашнее задание.'

    elif status == 'return':
        await base.set_status_homework(project_id, homework_date, id_user, "Возвращено", True)

        status_meaning, accepted, response_is_filled, user_info = \
            await base.get_date_status_meaning_homework("feedback", project_id, homework_date, id_user)

        inline_kb = await homework_kb_admin(id_user_admin, project_id, id_user, id_chat, homework_date,
                                            "feedback", status_number, response_is_filled)

        if status_meaning is None:
            text = 'Вы вернули домашнее задание на доработку. Оставите отклик?'
            text += message_requirements()
        else:
            text = status_meaning

    elif status == 'group':
        if id_chat == 0:
            chats = await base.get_chats_admin_user(project_id, id_user_admin, id_chat)
            for i in chats:
                i_id_chat = i[0]
                i_title = i[1]
                inline_kb.add(AddInlBtn(text=i_title, callback_data=f'admin_homework {project_id} group 0 {i_id_chat}'))
            inline_kb.add(AddInlBtn(text='Назад', callback_data=f'admin_homework {project_id} back_menu_back'))

            text = 'Домашние задания. \nВыберете группу для проверки домашних заданий:'

        else:
            text, user_info, inline_kb, status = \
                await admin_homework_process(project_id, id_user_admin, status_back, id_user, id_chat, homework_date)

    elif status == 'back_menu_back':
        pass

    elif status == 'back_user':
        text, user_info, inline_kb, status = \
            await admin_homework_process(project_id, id_user_admin, status_back, 0, id_chat, homework_date)

    elif status == 'back':
        chats = await base.get_chats_admin_user(project_id, id_user_admin, 0)
        number_of_chats = len(chats)

        if number_of_chats == 1:
            status = 'back_menu_back'

        elif number_of_chats > 1:
            id_chat = 0
            status = 'group'

            text, user_info, inline_kb, status = \
                await admin_homework_process(project_id, id_user_admin, status, 0, id_chat, homework_date)

    return text, user_info, inline_kb, status


async def homework_process(project_id, id_user, status, homework_date, message_text=''):
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
            try:
                await bot.delete_message(id_user, meaning[0])
            except Exception as e:
                pass

            text = shielding(message_text)
            inline_kb.add(AddInlBtn(text='Отправить как домашнее задание', callback_data=f'homework {project_id} homework'))
            inline_kb.add(AddInlBtn(text='Отправить как рассылку', callback_data=f'homework {project_id} sending'))
            inline_kb.add(AddInlBtn(text='Отмена', callback_data=f'homework {project_id} back'))

    elif status in ('homework', 'sending'):
        date = None
        if status == 'homework':
            date = get_today(True)
            cursor.execute('SELECT project_id FROM homework_text WHERE project_id = %s AND date = %s', (project_id, date))
            meaning = cursor.fetchone()
            if meaning is not None:
                text = 'Можно отправить только одно домашнее задание в день\.'
                inline_kb.add(AddInlBtn(text='Ok', callback_data=f'homework {project_id} back'))
                return text, inline_kb, ''

        cursor.execute('SELECT text FROM project_administrators WHERE id_user = %s AND project_id = %s',
                       (id_user, project_id))
        meaning = cursor.fetchone()
        sending_text = meaning[0]

        if status == 'homework':
            cursor.execute(
                'INSERT INTO homework_text (project_id, sender_id, date, text) VALUES (%s, %s, %s, %s)',
                (project_id, id_user, date, sending_text))
            connect.commit()

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

        last_i_id_chat = None
        chat_admins = None
        for i in meaning:
            i_id_user = i[0]
            i_message_id = i[1]
            its_homework = i[2] and status == 'homework'

            if its_homework:
                cursor.execute(
                    "INSERT INTO homework_check (project_id, date, id_user, status, selected) "
                    "VALUES (%s, %s, %s, 'Получено', False)", (project_id, date, i_id_user))
                connect.commit()

                inline_kb = await homework_kb(project_id, i_id_user, date)

            if i_message_id > 0:
                try:
                    await bot.delete_message(chat_id=i_id_user, message_id=i_message_id)
                except Exception as e:
                    pass

            try:
                message = await bot.send_message(text=sending_text, chat_id=i_id_user, reply_markup=inline_kb)
                if its_homework:
                    homework_message_id_text = message.message_id
                    cursor.execute('UPDATE users SET menu_message_id = %s WHERE id_user = %s',
                                   (homework_message_id_text, id_user))
                    connect.commit()
            except Exception as e:
                await send_error('', str(e), traceback.format_exc())

        cursor.execute(
            'UPDATE project_administrators SET status = NULL, text = NULL, message_id = 0 '
            'WHERE project_id = %s AND id_user = %s', (project_id, id_user))
        connect.commit()

    elif status == 'text':
        status_meaning, accepted, response_is_filled, user_info = \
            await base.get_date_status_meaning_homework(status, project_id, homework_date, id_user)
        text = shielding(status_meaning)
        inline_kb = await homework_kb(project_id, id_user, homework_date, status)

    elif status in ('response', 'feedback'):
        status_meaning, accepted, response_is_filled, user_info = \
            await base.get_date_status_meaning_homework(status, project_id, homework_date, id_user)
        if status_meaning in ('', None):
            if status == 'response':
                text = 'Для того, чтобы выполнить домашнее задание — пришлите ответ сообщением.'
                text += message_requirements()
            if status == 'feedback':
                if accepted:
                    text = 'Ваше домашнее задание принято.'
                elif response_is_filled:
                    text = 'Ваше домашнее задание на проверке у куратора.'
                else:
                    text = 'Для начала выполните домашнее задание.'
        else:
            text = status_meaning

        text = shielding(text)
        inline_kb = await homework_kb(project_id, id_user, homework_date, status)

    elif status == 'back':
        cursor.execute(
            'UPDATE project_administrators SET status = NULL, text = NULL, message_id = 0 '
            'WHERE project_id = %s AND id_user = %s', (project_id, id_user))
        connect.commit()

    return text, inline_kb, status


async def homework_response(project_id, homework_date, id_user, text):
    today = get_today()
    cursor.execute("UPDATE homework_check SET response = %s, status = 'На проверке', date_actual = %s "
                   "WHERE project_id = %s AND date = %s AND id_user = %s AND NOT status = 'Принято' ",
                   (text, today, project_id, homework_date, id_user))
    connect.commit()


async def registration_command(callback_message):
    id_user = callback_message.from_user.id
    first_name = callback_message.from_user.first_name
    last_name = callback_message.from_user.last_name
    if last_name is None:
        last_name = ''
    username = callback_message.from_user.username
    if username is None:
        username = ''
    language_code = callback_message.from_user.language_code

    cursor.execute('SELECT id_user FROM users WHERE id_user = %s', (id_user,))
    result = cursor.fetchone()

    if result is None:
        today = get_today()
        cursor.execute(
            "INSERT INTO users (id_user, first_name, last_name, username, language_code, "
            "registration_date, registration_field, fio, address, tel, mail, projects, role) "
            "VALUES (%s, %s, %s, %s, %s, %s, NULL, NULL, NULL, NULL, NULL, NULL, 'user')",
            (id_user, first_name, last_name, username, language_code, today))
    else:
        cursor.execute(
            "UPDATE users SET first_name = %s, last_name = %s, username = %s, language_code = %s WHERE id_user = %s",
            (first_name, last_name, username, language_code, id_user))
    connect.commit()

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
    #             inline_kb.add(AddInlBtn('Заявка на вступление', url=invite_link))
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
            try:
                await bot.delete_message(chat_id=id_user, message_id=message_id)
            except Exception as e:
                pass
        try:
            await message.delete()
        except Exception as e:
            pass

        if not text == '':
            try:
                message = await bot.send_message(text=text, chat_id=id_user, reply_markup=inline_kb, parse_mode='MarkdownV2')
            except Exception as e:
                pass

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
