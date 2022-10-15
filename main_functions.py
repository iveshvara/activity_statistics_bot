
from bot import bot, cursor, connect
from _settings import LOGS_CHANNEL_ID, THIS_IS_BOT_NAME, SUPER_ADMIN_ID
from service import its_admin, shielding, get_name_tg, reduce_large_numbers
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
# from aiogram.contrib.middlewares.logging import LoggingMiddleware
import datetime


async def run_reminder():
    cursor.execute(
        'SELECT * FROM settings WHERE strftime("%w", date("now")) = "1" '
        'AND date("now") > date(last_notify_date) AND report_enabled AND enable_group')
    result_tuple = cursor.fetchall()
    for i in result_tuple:
        id_chat = i[0]
        text = await get_stat(id_chat)
        # if not text == '' and not text == 'Нет статистики для отображения\.':
        if not text == '':
            await bot.send_message(text=text, chat_id=id_chat, parse_mode='MarkdownV2', disable_notification=True)
            cursor.execute('UPDATE settings SET last_notify_date = datetime("now") WHERE id_chat = ?', (id_chat,))
            connect.commit()

    text = ''

    cursor.execute(
        '''SELECT DISTINCT
            messages_one.id_chat AS id_chat,
            messages_two.id_user,
            chats.first_name,
            chats.last_name,
            chats.username 
        FROM
            messages AS messages_one
            LEFT JOIN settings ON settings.id_chat = messages_one.id_chat
            LEFT JOIN messages AS messages_two ON messages_one.id_chat = messages_two.id_chat
                    AND messages_one.message_id = messages_two.message_id
                    AND messages_one.message_id > 0
            LEFT JOIN chats ON messages_two.id_chat = chats.id_chat
                    AND messages_two.id_user = chats.id_user
        WHERE
            messages_one.message_id > 0
            AND settings.enable_group
            AND settings.period_of_activity > Round(JulianDay("now") - JulianDay(messages_one.date), 0)
            AND Date(settings.last_notify_message_id_date) < Date("now")
        GROUP BY
            messages_one.id_chat,
            messages_two.id_user,
            chats.first_name,
            chats.last_name,
            chats.username,
            messages_one.message_id
        ORDER BY
            id_chat'''
    )
    result_tuple = cursor.fetchall()
    last_id_chat = None
    id_chat_text_tuple = []
    for i in result_tuple:
        id_chat = i[0]
        if not last_id_chat == id_chat:
            if last_id_chat is None:
                last_id_chat = id_chat
            else:
                id_chat_text_tuple.append((last_id_chat, text))
                text = ''
                last_id_chat = id_chat

        id_user = i[1]
        first_name = i[2]
        last_name = i[3]
        username = i[4]
        text += await get_name_tg(id_user, first_name, last_name, username)
    else:
        if last_id_chat is not None:
            id_chat_text_tuple.append([last_id_chat, text])

    for i in id_chat_text_tuple:
        id_chat = i[0]
        text = i[1]
        text = 'Сегодня не откликнулись на запрос\: \n' + text + '\n \#ВажноеСообщение'
        try:
            await bot.send_message(text=text, chat_id=id_chat, parse_mode='MarkdownV2', disable_notification=True)
        except Exception as e:
            pass

        cursor.execute('UPDATE settings SET last_notify_message_id_date = datetime("now") WHERE id_chat = ?',
                       (id_chat,))
        connect.commit()


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
            IFNULL(projects.channel_id, 0),
            settings.do_not_output_name_from_registration
        FROM settings 
        LEFT OUTER JOIN projects 
                ON settings.project_id = projects.project_id
        WHERE id_chat = ?''', (id_chat,))
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

        count_messages = 0
        cursor.execute(
            f'''SELECT chats.id_user, chats.first_name, chats.last_name, chats.username, users.FIO,
            SUM(IFNULL(messages.characters, 0)) AS characters, COUNT(messages.characters) AS messages, 
            chats.deleted, chats.date_of_the_last_message, 
                CASE WHEN NOT chats.deleted AND ? > ROUND(julianday("now") - julianday(chats.date_of_the_last_message), 0) THEN 0 
                ELSE ROUND(julianday("now") - julianday(chats.date_of_the_last_message), 0) END AS inactive_days
                -- ,(SELECT COUNT(DISTINCT message_id) FROM messages 
                --    WHERE chats.id_chat = messages.id_chat 
                --        AND messages.message_id IS NOT NULL 
                --        AND NOT messages.message_id = 0 
                --        AND 7 > ROUND(julianday("now") - julianday(date), 0)
                --) AS requests,
                --(SELECT COUNT(DISTINCT messages_two.message_id) FROM messages AS messages_one 
                --    INNER JOIN messages AS messages_two 
                --    ON messages_one.id_chat = messages_two.id_chat 
                --        AND messages_one.message_id = messages_two.message_id 
                --        AND chats.id_user = messages_two.id_user
                --    WHERE chats.id_chat = messages_one.id_chat 
                --        AND messages_one.message_id IS NOT NULL 
                --        AND NOT messages_one.message_id = 0 
                --        AND 7 > ROUND(julianday("now") - julianday(messages_one.date), 0)
                --) AS response 
            FROM chats 
            LEFT JOIN messages 
                ON chats.id_chat = messages.id_chat 
                    AND chats.id_user = messages.id_user 
                    AND ? > ROUND(julianday("now") - julianday(messages.date), 0)
            LEFT JOIN users 
                ON chats.id_user = users.id_user  
            WHERE chats.id_chat = ? 
            GROUP BY chats.id_chat, chats.id_user, chats.first_name, chats.last_name, chats.username, chats.date_of_the_last_message, chats.deleted 
            ORDER BY deleted ASC, inactive_days ASC, {sort} DESC ''', (period_of_activity, period_of_activity, id_chat)
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
                data_str = shielding(
                    datetime.datetime.strptime(i_date_of_the_last_message, '%Y-%m-%d %H:%M:%S').strftime(
                        "%d.%m.%Y"))  # "%d.%m.%Y %H:%M:%S"
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
    cursor.execute(
        'SELECT DISTINCT settings.id_chat, settings.title, settings.project_id FROM settings '
        'LEFT OUTER JOIN chats ON chats.id_chat = settings.id_chat '
        'WHERE settings.enable_group AND id_user = ?', (id_user,))
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
            title_result = i[1].replace('\\', '')
            user_groups.append([i[0], title_result])

        if not channel_enabled and i[2] > 0:
            channel_enabled = True

    text = ''
    inline_kb = InlineKeyboardMarkup(row_width=1)
    one_group = None

    if len(user_groups) == 0:
        if len(meaning) == 0 or not channel_enabled:
            text = 'Это бот для участников проектов https://ipdt.kz/proekty/. Присоединяйтесь!'
            text = shielding(text)
            inline_kb = InlineKeyboardMarkup(row_width=1)
            inline_kb.add(InlineKeyboardButton(text='Перейти на сайт.', url='https://ipdt.kz/proekty/'))

        else:
            text = 'Добрый день, дорогой друг! \n\n' \
                   'Команда Института рада приветствовать Вас! \n\n' \
                   'Для того, чтобы получить доступ к материалам, необходимо пройти небольшую регистрацию!'
            text = shielding(text)
            inline_kb = InlineKeyboardMarkup(row_width=1)
            inline_kb.add(InlineKeyboardButton(text='Регистрация', callback_data='reg'))

    elif len(user_groups) == 1:
        one_group = user_groups[0][0]

    else:
        text = 'Выберете группу для настройки:'
        for i in user_groups:
            inline_kb.add(InlineKeyboardButton(text=i[1], callback_data=f'id_chat {i[0]}'))

    cursor.execute(
        'SELECT projects.project_id, projects.name FROM project_administrators '
        'INNER JOIN projects ON project_administrators.project_id = projects.project_id '
        'WHERE project_administrators.id_user = ?', (id_user,))
    meaning = cursor.fetchone()
    if meaning is not None:
        inline_kb.add(InlineKeyboardButton(text='[Рассылка по "' + meaning[1] + '"]',
                                           callback_data='project_admin ' + str(meaning[0])))

    if id_user == SUPER_ADMIN_ID:
        inline_kb.add(InlineKeyboardButton(text='[super admin functions]', callback_data='super_admin '))

    return text, inline_kb, one_group


async def project_admin_process(project_id, id_user, status, message_text=''):
    text = ''
    inline_kb = InlineKeyboardMarkup(row_width=1)
    message_requirements = \
        shielding('\nТребования к сообщению:\n'
                  '— Можно использовать эмодзи и ссылки в открытом виде.\n'
                  '— Нельзя использовать форматирование. Введенное форматирование будет утеряно.\n'
                  '— Текст должен помещаться в одно сообщение Telegram (не больше 4096 символов).')

    if status == '':
        cursor.execute(
            'SELECT projects.name, project_administrators.status FROM project_administrators '
            'INNER JOIN projects ON project_administrators.project_id = projects.project_id '
            'WHERE project_administrators.id_user = ? AND project_administrators.project_id = ?',
            (id_user, project_id))
        meaning = cursor.fetchone()

        text = shielding(f'Введите текст сообщения, который бот отправит всем студентам всех групп проекта "{meaning[0]}". ')
        text += message_requirements
        inline_kb.add(InlineKeyboardButton(text='Отмена', callback_data=f'project_admin {project_id} back'))

        cursor.execute(
            'UPDATE project_administrators SET status = ?, message_id = ? WHERE project_id = ? AND id_user = ?',
            ('text', message_text, project_id, id_user))
        connect.commit()

    elif status == 'confirm':
        message_text = message_text.replace('`', '')
        message_text = message_text.replace('\\', '')
        cursor.execute('UPDATE project_administrators SET status = ?, text = ? WHERE project_id = ? AND id_user = ?',
                       ('confirm', message_text, project_id, id_user))
        connect.commit()

        cursor.execute(
            'SELECT project_administrators.message_id, projects.name FROM projects '
            'INNER JOIN project_administrators ON projects.project_id = project_administrators.project_id '
            'AND project_administrators.id_user = ? '
            'WHERE projects.project_id = ?', (id_user, project_id))
        meaning = cursor.fetchone()
        if meaning is not None:
            await bot.delete_message(id_user, meaning[0])
            text = shielding(message_text)
            inline_kb.add(InlineKeyboardButton(text='Отправить как домашнее задание', callback_data=f'project_admin {project_id} homework'))
            inline_kb.add(InlineKeyboardButton(text='Отправить как рассылку', callback_data=f'project_admin {project_id} sending'))
            inline_kb.add(InlineKeyboardButton(text='Отмена', callback_data=f'project_admin {project_id} back'))

    elif status in ('homework', 'sending'):
        date = None
        if status == 'homework':
            date = datetime.date.today()
            # TODO
            # cursor.execute('SELECT project_id FROM homework_text WHERE project_id = ? AND date = ?', (project_id, date))
            # meaning = cursor.fetchone()
            # if meaning is not None:
            #     text = 'Можно отправить только одно домашнее задание в день\.'
            #     inline_kb.add(InlineKeyboardButton(text='Ok', callback_data=f'project_admin {project_id} back'))
            #     return text, inline_kb, ''

        cursor.execute('SELECT text FROM project_administrators WHERE id_user = ? AND project_id = ?',
                       (id_user, project_id))
        meaning = cursor.fetchone()

        if meaning is not None:
            sending_text = meaning[0]

            if status == 'homework':
                cursor.execute(
                    'INSERT INTO homework_text (project_id, sender_id, date, text) VALUES (?, ?, ?, ?)',
                    (project_id, id_user, date, sending_text))
                connect.commit()

            cursor.execute(
                'SELECT DISTINCT chats.id_user, chats.id_chat FROM settings '
                'INNER JOIN chats ON settings.id_chat = chats.id_chat AND NOT chats.deleted '
                'WHERE project_id = ?', (project_id,))
            meaning = cursor.fetchall()

            if meaning is not None:

                last_i_id_chat = None
                chat_admins = None

                for i in meaning:
                    i_id_user = i[0]

                    await bot.send_message(text=sending_text, chat_id=i_id_user)

                    if status == 'homework':
                        i_id_chat = i[1]
                        if not last_i_id_chat == i_id_chat:
                            last_i_id_chat = i_id_chat
                            try:
                                chat_admins = await bot.get_chat_administrators(i_id_chat)
                            except Exception as e:
                                chat_admins = ()
                        # TODO
                        # if not its_admin(i_id_user, chat_admins):
                            cursor.execute(
                                'INSERT INTO homework_check (project_id, date, id_chat, id_user, date_actual, '
                                'status, text, accepted, feedback) VALUES (?, ?, ?, ?, "", "sent", "", False, "")',
                                (project_id, date, i_id_chat, i_id_user))
                            connect.commit()

                        text = shielding('Это домашнее задание. Для его выполнения, вам необходимо написать сообщение. ')
                        text += message_requirements
                        await bot.send_message(text=text, chat_id=i_id_user, parse_mode='MarkdownV2')

                    if i_id_user == SUPER_ADMIN_ID:
                        break

                cursor.execute(
                    'UPDATE project_administrators SET status = "", text = "", message_id = 0 '
                    'WHERE project_id = ? AND id_user = ?', (project_id, id_user))
                connect.commit()

    elif status == 'back':
        cursor.execute(
            'UPDATE project_administrators SET status = "", text = "", message_id = 0 '
            'WHERE project_id = ? AND id_user = ?', (project_id, id_user))
        connect.commit()

    return text, inline_kb, status


async def homework(project_id, id_user, text):
    cursor.execute('UPDATE homework_check SET text = ?, status = "check", date_actual = date("now") '
                   'WHERE status = "sent" AND project_id = ? AND id_user = ? ', (text, project_id, id_user))
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

    cursor.execute('SELECT id_user FROM users WHERE id_user = ?', (id_user,))
    result = cursor.fetchone()

    if result is None:
        cursor.execute(
            'INSERT INTO users (id_user, first_name, last_name, username, language_code, '
            'registration_date, registration_field, FIO, address, tel, mail, projects) '
            'VALUES (?, ?, ?, ?, ?, datetime("now"), "", "", "", "", "", "")',
            (id_user, first_name, last_name, username, language_code))
    else:
        cursor.execute(
            'UPDATE users SET first_name = ?, last_name = ?, username = ?, language_code = ?, '
            'registration_field = "", projects = "" '
            'WHERE id_user = ?', (first_name, last_name, username, language_code, id_user))
    connect.commit()

    if type(callback_message) == CallbackQuery:
        message = callback_message.message
    else:
        message = callback_message

    await registration_process(message, its_callback=False)


async def registration_process(message: Message, meaning='', its_callback=False):
    id_user = message.chat.id

    cursor.execute(
        'SELECT DISTINCT users.registration_field, users.message_id, projects.name, projects.invite_link FROM chats '
        'INNER JOIN settings ON chats.id_chat = settings.id_chat '
        'INNER JOIN users ON chats.id_user = users.id_user '
        'INNER JOIN projects ON settings.project_id = projects.project_id '
        'WHERE settings.enable_group AND chats.id_user = ?', (id_user,))
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
        inline_kb.add(InlineKeyboardButton(text='Мужской', callback_data='gender Мужской'))
        inline_kb.add(InlineKeyboardButton(text='Женский', callback_data='gender Женский'))

    elif registration_field == 'gender':
        if its_callback:
            new_registration_field = 'FIO'
            text = 'Шаг 2 из 7. \nВведите ваши имя и фамилию:'
        else:
            try:
                await message.delete()
            except Exception as e:
                pass
            return

    elif registration_field == 'FIO':
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
        inline_kb.add(InlineKeyboardButton('Заявка на вступление', url=invite_link))
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
    #             inline_kb.add(InlineKeyboardButton('Заявка на вступление', url=invite_link))
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
            message = await bot.send_message(text=text, chat_id=id_user, reply_markup=inline_kb, parse_mode='MarkdownV2')

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

    query_text += f'message_id = {message.message_id}'
    query_text = f'''UPDATE users SET {query_text} WHERE id_user = {id_user}'''
    try:
        cursor.execute(query_text)
        connect.commit()
    except Exception as e:
        await bot.send_message(text=f'@{THIS_IS_BOT_NAME} error\n\nQuery text:\n{query_text}\n\nError text:\n{str(e)}',
                               chat_id=LOGS_CHANNEL_ID)
