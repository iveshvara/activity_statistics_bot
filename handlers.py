from bot import bot, dp, cursor, connect
from _settings import LOGS_CHANNEL_ID, THIS_IS_BOT_NAME, YANDEX_API_KEY, GEONAMES_USERNAME, SUPER_ADMIN_ID
from main_functions import get_stat, get_start_menu, \
    registration_process, registration_command, project_admin_process, homework
from utility_functions import process_parameter_continuation, insert_or_update_chats, callback_edit_text, \
    message_answer, setting_up_a_chat
from service import add_buttons_time_selection, its_admin, shielding
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, \
    KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, ChatJoinRequest
from geopy.geocoders import Yandex
import requests


@dp.message_handler(commands=['start'])
async def command_start(message: Message):
    if message.chat.type == 'private':
        id_user = message.chat.id
        text, inline_kb, one_group = await get_start_menu(id_user)

        if one_group is None:
            await message_answer(message, text, inline_kb)
        else:
            text, inline_kb = await setting_up_a_chat(one_group, id_user, False)
            await message_answer(message, text, inline_kb)


@dp.message_handler(commands=['get_stat'])
async def command_get_stat(message: Message):
    if not (message.chat.type == 'group' or message.chat.type == 'supergroup'):
        if message.chat.type == 'private':
            await message.answer('Эта команда работает в группе. Здесь используйте команду /start')
        return

    await message_handler(message)

    id_chat = message.chat.id
    id_user = message.from_user.id

    command = message.text.split('@')[0]
    text = ''
    if command == '/get_stat':
        text = await get_stat(id_chat, id_user)
    elif command == '/test':
        text = ''

    if not text == '':
        try:
            await message_answer(message, text)
        except Exception as e:
            text = f'id_chat: {id_chat}, id_user: {id_user}, text: {text}'
            await bot.send_message(
                text=f'@{THIS_IS_BOT_NAME} error\n\nQuery text:\n{text}\n\nError text:\n{str(e)}',
                chat_id=LOGS_CHANNEL_ID)


@dp.callback_query_handler(lambda x: x.data and x.data.startswith('id_chat '))
async def choosing_a_chat_to_set_up(callback: CallbackQuery):
    id_chat = int(callback.data.replace('id_chat ', ''))
    id_user = callback.from_user.id
    text, inline_kb = await setting_up_a_chat(id_chat, id_user)
    await callback_edit_text(callback, text, inline_kb)


@dp.callback_query_handler(lambda x: x.data and x.data.startswith('settings '))
async def process_parameter(callback: CallbackQuery):
    id_user = callback.from_user.id
    list_str = callback.data.split()
    id_chat = int(list_str[1])
    parameter_name = list_str[2]
    parameter_value = ''
    if len(list_str) > 3:
        parameter_value = list_str[3]

    if parameter_name == 'period_of_activity':
        parameter_value_int = int(parameter_value)
        adding = 0
        if 0 <= parameter_value_int < 7:
            adding = 1
        # elif 7 <= parameter_value_int < 20:
        #     adding = 7
        elif 7 <= parameter_value_int < 21:
            adding = 7
        elif parameter_value_int == 21:
            parameter_value_int = 30
        elif parameter_value_int == 30:
            parameter_value_int = 1
        parameter_value_int += adding
        await process_parameter_continuation(callback, id_chat, id_user, parameter_name, parameter_value_int)

    elif parameter_name == 'project_name':
        text = shielding('Выберете ваш проект:')
        cursor.execute('SELECT project_id, name FROM projects')
        projects_tuple = cursor.fetchall()

        inline_kb = InlineKeyboardMarkup(row_width=1)
        for i in projects_tuple:
            callback_data = 'settings ' + str(id_chat) + ' project_id ' + str(i[0])
            inline_kb.add(InlineKeyboardButton(text=i[1], callback_data=callback_data))

        callback_data = 'settings ' + str(id_chat) + ' project_id 0'
        inline_kb.add(InlineKeyboardButton(text='Нет проекта', callback_data=callback_data))

        await callback_edit_text(callback, text, inline_kb)

    elif parameter_name == 'project_id':
        cursor.execute('UPDATE settings SET project_id = ? WHERE id_chat = ?', (parameter_value, id_chat))
        connect.commit()
        text, inline_kb = await setting_up_a_chat(id_chat, id_user)

        await callback_edit_text(callback, text, inline_kb)
    else:
        # parameter_value = not parameter_value
        if parameter_value == '0':
            parameter_value = 1
        else:
            parameter_value = 0

        await process_parameter_continuation(callback, id_chat, id_user, parameter_name, parameter_value)


@dp.callback_query_handler(text='back')
async def menu_back(callback: CallbackQuery):
    id_user = callback.from_user.id
    text, inline_kb, one_group = await get_start_menu(id_user)

    if one_group is None:
        await callback_edit_text(callback, text, inline_kb)
    else:
        text, inline_kb = await setting_up_a_chat(one_group, id_user, False)
        await callback_edit_text(callback, text, inline_kb)


@dp.callback_query_handler(text='reg')
async def reg_command_callback(callback: CallbackQuery):
    await registration_command(callback)


@dp.message_handler(commands=['reg'])
async def reg_command_message(message: Message):
    await registration_command(message)


@dp.callback_query_handler(lambda x: x.data and x.data.startswith('gender ') or x.data.startswith('projects '))
async def gender_processing(callback: CallbackQuery):
    await callback.answer()

    value = callback.data
    value = value.replace('gender ', '')
    value = value.replace('projects ', '')

    await registration_process(callback.message, value, True)


@dp.callback_query_handler(lambda x: x.data and x.data.startswith('super_admin '))
async def super_admin_functions(callback: CallbackQuery):
    list_str = callback.data.split()
    project_id = ''
    if len(list_str) > 1:
        project_id = int(list_str[1])
    id_chat = ''
    if len(list_str) > 2:
        id_chat = int(list_str[2])

    if project_id == '' and id_chat == '':
        text = shielding('Выберете ваш проект:')
        cursor.execute('SELECT project_id, name FROM projects')
        projects_tuple = cursor.fetchall()

        inline_kb = InlineKeyboardMarkup(row_width=1)
        for i in projects_tuple:
            inline_kb.add(
                InlineKeyboardButton(text=i[1], callback_data='super_admin ' + str(i[0])))

        inline_kb.add(InlineKeyboardButton(text='Нет проекта', callback_data='super_admin 0'))
        inline_kb.add(InlineKeyboardButton(text='Назад', callback_data='back'))

        await callback_edit_text(callback, text, inline_kb)

    elif id_chat == '':
        inline_kb = InlineKeyboardMarkup(row_width=1)
        cursor.execute(
            '''SELECT DISTINCT settings.id_chat, settings.title FROM settings
            LEFT OUTER JOIN chats ON chats.id_chat = settings.id_chat 
            WHERE settings.enable_group AND project_id = ?''', (project_id,))
        meaning = cursor.fetchall()
        for i in meaning:
            title_result = i[1].replace('\\', '')
            inline_kb.add(InlineKeyboardButton(text=title_result, callback_data=f'super_admin {project_id} {i[0]}'))
        inline_kb.add(InlineKeyboardButton(text='Назад', callback_data='super_admin '))

        text = 'Выберете группу для настройки:'
        await callback_edit_text(callback, text, inline_kb)

    else:
        id_user = callback.from_user.id
        text, inline_kb = await setting_up_a_chat(id_chat, id_user, False, True)
        await callback_edit_text(callback, text, inline_kb)


@dp.callback_query_handler(lambda x: x.data and x.data.startswith('project_admin '))
async def project_admin_functions(callback: CallbackQuery):
    id_user = callback.from_user.id
    list_str = callback.data.split()
    project_id = ''
    if len(list_str) > 1:
        project_id = int(list_str[1])
    status = ''
    if len(list_str) > 2:
        status = list_str[2]
    homework_date = ''
    if len(list_str) > 3:
        homework_date = list_str[3]

    text, inline_kb, status = await project_admin_process(project_id, id_user, status, homework_date, callback.message.message_id)

    if status == 'back':
        await menu_back(callback)
    elif status in ('homework', 'sending'):
        # await command_start(callback.message)
        await callback.message.delete()
    else:
        await callback_edit_text(callback, text, inline_kb)


@dp.chat_join_request_handler()
async def join(update: ChatJoinRequest):
    id_user = update.from_user.id
    cursor.execute(
        '''SELECT DISTINCT users.message_id, projects.name, projects.invite_link FROM chats
            INNER JOIN settings ON chats.id_chat = settings.id_chat
            INNER JOIN users ON chats.id_user = users.id_user
            INNER JOIN projects ON settings.project_id = projects.project_id	
            WHERE settings.enable_group AND chats.id_user = ?''', (id_user,))
    meaning = cursor.fetchone()

    inline_kb = InlineKeyboardMarkup(row_width=1)

    if meaning is None:
        await update.decline()
        text = 'Заявка на вступление отклонена. Свяжитесь с вашим куратором для решения этой ситуации.'
    else:
        await update.approve()
        text = 'Все получилось! \nПоздравляем Вас с успешной регистрацией! \n' \
               'Ваша заявка подтверждена на вступление подтверждена, пожалуйста заходите.'
        inline_kb.add(InlineKeyboardButton('Зайти в канал.', url=meaning[2]))
        try:
            await bot.delete_message(chat_id=id_user, message_id=meaning[0])
        except Exception as e:
            pass

    text = shielding(text)
    await bot.send_message(text=text, chat_id=id_user, reply_markup=inline_kb, parse_mode='MarkdownV2')


@dp.message_handler(content_types='any')
async def message_handler(message):
    if message.chat.type == 'private':
        if not message.content_type == 'text':
            return

        id_user = message.from_user.id
        text = message.text

        cursor.execute(
            f'''SELECT 
            IFNULL((SELECT True FROM users WHERE id_user = {id_user} AND NOT registration_field = 'done' ), False),
            IFNULL((SELECT project_id FROM homework_check WHERE id_user = {id_user} AND status = 'wait' ), 0),
            IFNULL((SELECT project_id FROM project_administrators WHERE id_user = {id_user} AND status = 'text' ), 0)''')
        meaning = cursor.fetchone()

        if meaning[0]:
            await registration_process(message, text, False)

        elif meaning[1] > 0:
            text, inline_kb, status = await homework(meaning[1], id_user, text)
            await message_answer(message, text, inline_kb)

        elif meaning[2] > 0:
            await message.delete()

            text, inline_kb, status = await project_admin_process(meaning[2], id_user, 'confirm', '',  text)
            await message_answer(message, text, inline_kb)

        else:
            try:
                await message.delete()
            except Exception as e:
                pass

    else:
        id_chat = message.chat.id
        date_of_the_last_message = message.date

        skip_content_type = ('delete_chat_photo', 'migrate_from_chat_id', 'pinned_message')
        created_title_content_type = ('group_chat_created', 'supergroup_chat_created', 'channel_chat_created')

        if len(message.entities) == 1 and message.entities[0].type == 'bot_command' \
                or message.content_type in skip_content_type \
                or id_chat == 777000:
            pass

        elif message.content_type in created_title_content_type:
            title = shielding(message.chat.title)
            cursor.execute(
                '''INSERT INTO settings (id_chat, title, statistics_for_everyone, include_admins_in_statistics, 
                sort_by_messages, do_not_output_the_number_of_messages, do_not_output_the_number_of_characters, 
                period_of_activity, report_enabled, project_id, curators_group, enable_group, 
                last_notify_date, last_notify_message_id_date, 
                do_not_output_name_from_registration, check_channel_subscription) 
                VALUES (?, ?, False, False, False, False, False, 7, False, 0, False, True, 
                datetime("now"), datetime("now"), False, False)''', (id_chat, title))
            connect.commit()

        elif message.content_type == 'new_chat_title':
            title = shielding(message.chat.title)
            cursor.execute('UPDATE settings SET title = ? WHERE id_chat = ?', (title, id_chat))
            connect.commit()

        elif message.content_type == 'migrate_to_chat_id':
            new_id_chat = message.migrate_to_chat_id
            cursor.execute('UPDATE chats SET id_chat = ? WHERE id_chat = ?', (new_id_chat, id_chat))
            cursor.execute('UPDATE meetings SET id_chat = ? WHERE id_chat = ?', (new_id_chat, id_chat))
            cursor.execute('UPDATE messages SET id_chat = ? WHERE id_chat = ?', (new_id_chat, id_chat))
            cursor.execute('UPDATE settings SET id_chat = ? WHERE id_chat = ?', (new_id_chat, id_chat))
            connect.commit()

        elif message.content_type == 'new_chat_members':
            for i in message.new_chat_members:
                if i.is_bot:
                    if i.username == THIS_IS_BOT_NAME:
                        title = shielding(message.chat.title)

                        cursor.execute('SELECT * FROM settings WHERE id_chat = ?', (id_chat,))
                        meaning = cursor.fetchone()
                        if meaning is None:
                            cursor.execute(
                                '''INSERT INTO settings (id_chat, title, statistics_for_everyone, 
                                include_admins_in_statistics, sort_by_messages, do_not_output_the_number_of_messages, 
                                do_not_output_the_number_of_characters, period_of_activity, report_enabled, project_id, 
                                curators_group, enable_group, last_notify_date, last_notify_message_id_date, 
                                do_not_output_name_from_registration, check_channel_subscription) 
                                VALUES (?, ?, False, False, False, False, False, 7, False, 0, False, True, 
                                datetime("now"), datetime("now"), False, False)''', (id_chat, title))
                        else:
                            cursor.execute('UPDATE settings SET enable_group = True, title = ? WHERE id_chat = ?',
                                           (title, id_chat))
                        connect.commit()

                        text = f'Добавлена новая группа "{message.chat.title}"'
                        await bot.send_message(text=text, chat_id=SUPER_ADMIN_ID)

                else:
                    i_first_name = i.first_name
                    i_last_name = i.last_name
                    i_username = i.username
                    await insert_or_update_chats(id_chat, i.id, i_first_name, i_last_name, i_username, 0,
                                                 date_of_the_last_message)


        elif message.content_type == 'left_chat_member':
            i = message.left_chat_member
            if i.is_bot:
                if i.username == THIS_IS_BOT_NAME:
                    cursor.execute('UPDATE settings SET enable_group = False WHERE id_chat = ?', (id_chat,))
                    connect.commit()
            else:
                id_user = i.id
                cursor.execute(
                    'UPDATE chats SET deleted = True, date_of_the_last_message = ? WHERE id_chat = ? AND id_user = ?',
                    (date_of_the_last_message, id_chat, id_user))
                connect.commit()

                cursor.execute(
                    '''SELECT projects.channel_id FROM settings 
                    INNER JOIN projects ON settings.project_id = projects.project_id
                    AND NOT projects.channel_id = 0  
                    AND settings.id_chat = ?''', (id_chat,))
                meaning = cursor.fetchone()
                if meaning is not None:
                    channel_id = meaning[0]
                    await bot.kick_chat_member(channel_id, id_user)
                    await bot.unban_chat_member(channel_id, id_user)

        else:

            id_user = message.from_user.id
            first_name = message.from_user.first_name
            last_name = message.from_user.last_name
            username = message.from_user.username
            characters = 0

            message_id = 0
            if message.content_type == 'text':
                if message.from_user.is_bot:
                    return
                characters = len(message.text)

            elif message.content_type == 'photo' and message.caption is not None:
                characters = len(message.caption)

            elif message.content_type == 'poll':
                characters = len(message.poll.question)
                for i in message.poll.options:
                    characters += len(i.text)

            if message.from_user.is_bot:
                return

            cursor.execute('INSERT INTO messages (id_chat, id_user, date, characters, message_id) VALUES (?, ?, ?, ?, ?)',
                           (id_chat, id_user, date_of_the_last_message, characters, message_id))
            connect.commit()

            await insert_or_update_chats(id_chat, id_user, first_name, last_name, username, characters,
                                         date_of_the_last_message)


# dont use

@dp.message_handler(commands=['call_meeting'])
async def command_call_meeting(message: Message):
    id_chat = message.chat.id
    id_user = message.from_user.id
    if message.chat.type == 'group' or message.chat.type == 'supergroup':
        try:
            chat_admins = await bot.get_chat_administrators(id_chat)
        except Exception as e:
            chat_admins = ()

        if not its_admin(id_user, chat_admins):
            await message.answer('Эту команду может вызвать только админ группы.')
            return
    else:
        if message.chat.type == 'private':
            await message.answer('Эта команда работает в группе. Здесь используйте команду /start')
        return

    await message_handler(message)

    text = ''
    count_messages = 0

    cursor.execute('SELECT * FROM chats WHERE id_chat = ?', (id_chat,))
    meaning = cursor.fetchall()
    for i in meaning:
        count_messages += 1
        name_user = i[2] + ' ' + i[3]
        name_user = name_user.replace('_', '\_')
        text += f'{count_messages}\. [{name_user}](tg://user?id={i[1]})\. \n'

    inline_kb = add_buttons_time_selection(0)
    await message_answer(message, text, inline_kb)

    inline_kb = add_buttons_time_selection(12)
    await message_answer(message, '/', inline_kb)


@dp.callback_query_handler(lambda x: x.data and x.data.startswith('call_meeting '))
async def call_meeting_process(callback: CallbackQuery):
    id_chat = callback.message.chat.id
    id_user = callback.from_user.id

    week = ['пн', 'вт', 'ср', 'чт', 'пт', 'сб', 'вс']
    list_data = callback.data.split(' ')
    day = list_data[1]
    index_day = week.index(day)
    time = list_data[2]
    index_time = int(time) + 3

    cursor.execute('SELECT * FROM meetings WHERE id_chat = ? AND id_user = ?', (id_chat, id_user))
    meaning = cursor.fetchall()
    if len(meaning) == 0:
        for i in week:
            cursor.execute(
                '''INSERT INTO meetings (id_chat, id_user, day, 
                _00, _01, _02, _03, _04, _05, _06, _07, _08, _09, _10, _11, 
                _12, _13, _14, _15, _16, _17, _18, _19, _20, _21, _22, _23)
                VALUES (?, ?, ?, 
                False, False, False, False, False, False, False, False, False, False, False, False, 
                False, False, False, False, False, False, False, False, False, False, False, False)''',
                (id_chat, id_user, i)
            )
            connect.commit()

            cursor.execute('SELECT * FROM meetings WHERE id_chat = ? AND id_user = ?', (id_chat, id_user))
            meaning = cursor.fetchall()

    new_value_time = meaning[index_day][index_time]
    if new_value_time == 1:
        new_value_time = 0
    else:
        new_value_time = 1
    cursor.execute('UPDATE meetings SET id_user = ?, ? = ? WHERE id_chat = ? AND day = ?',
                   (id_user, '_' + str(time), new_value_time, id_chat, day))
    connect.commit()

    await callback.answer()


@dp.message_handler(content_types=['contact'])
async def handle_contact(message: Message):
    id_user = message.from_user.id
    tel = message.contact.phone_number
    cursor.execute(f'''UPDATE users SET tel = '{tel}' WHERE id_user = {id_user}''')
    connect.commit()

    await message_answer(message, 'ok', ReplyKeyboardRemove())

    text = 'Выберете, в каких проектах вы уже обучались:'
    text = shielding(text)
    inline_kb = InlineKeyboardMarkup(row_width=1)

    await message_answer(message, text, inline_kb)


@dp.message_handler(content_types=['location'])
async def handle_location(message: Message):
    id_user = message.from_user.id
    latitude = message.location.latitude
    longitude = message.location.longitude
    language_code = message.from_user.language_code

    cursor.execute(f'''UPDATE users SET latitude = '{latitude}', longitude = '{longitude}' WHERE id_user = {id_user}''')
    connect.commit()

    # geolocator = Nominatim(user_agent="vaishnava_reminder_bot")
    geolocator = Yandex(api_key=YANDEX_API_KEY)
    location = geolocator.reverse(f'{latitude}, {longitude}')

    address_path = location.raw['metaDataProperty']['GeocoderMetaData']['Address']
    address = address_path['formatted']
    country = ''
    area = ''
    city = ''
    components = address_path['Components']
    for i in components:
        if i['kind'] == 'country':
            country = i['name']
        elif i['kind'] == 'province':
            area = i['name']
        elif i['kind'] == 'area':
            area = i['name']
        elif i['kind'] == 'locality' and city == '':
            city = i['name']

    cursor.execute(
        f'''UPDATE users SET address = '{address}', country = '{country}', area = '{area}', city = '{city}' WHERE id_user = {id_user}''')
    connect.commit()

    if area in ("Севастополь", "Республика Крым"):
        uts = 3
        uts_summer = 3
    else:
        response_text = requests.get(
            f'http://api.geonames.org/timezoneJSON?formatted=true&lat={latitude}&lng={longitude}&username={GEONAMES_USERNAME}')  ## Make a request
        response = response_text.json()
        uts = response['rawOffset']
        uts_summer = response['dstOffset']

    cursor.execute(f'UPDATE users SET uts = "{uts}", uts_summer = "{uts_summer}" WHERE id_user = {id_user}')
    connect.commit()

    uts_text = str(uts)
    if uts == 0:
        pass
    elif uts > 0:
        uts_text = '\+ ' + uts_text
    elif uts < 0:
        uts_text = '\- ' + uts_text
    uts_text += ' UTC'

    text = 'Теперь неодходимо отправить номер телефона.'
    text = shielding(text)
    keyboard = ReplyKeyboardMarkup()
    keyboard.add(KeyboardButton('Отправьте ваш номер телефона.', request_contact=True))

    await message_answer(message, text, keyboard)


@dp.channel_post_handler()
async def join(message: Message):
    pass


@dp.chat_member_handler()
async def join(update):
    pass
