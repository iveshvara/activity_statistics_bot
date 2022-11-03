
from _settings import THIS_IS_BOT_NAME, YANDEX_API_KEY, GEONAMES_USERNAME, SUPER_ADMIN_ID
from bot_base import bot, dp, base, cursor, connect
from main_functions import get_stat, get_start_menu, registration_process, registration_command, \
    admin_homework_process, homework_process, homework_response, homework_kb, \
    process_parameter_continuation, setting_up_a_chat
from utility_functions import callback_edit_text, message_answer, message_delete, last_menu_message_delete, message_send
from service import add_buttons_time_selection, its_admin, shielding
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, \
    KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, ChatJoinRequest
from geopy.geocoders import Yandex
import requests
import datetime


@dp.message_handler(commands=['start', 'menu'])
async def command_start(message: Message):
    if message.chat.type == 'private':
        id_user = message.chat.id
        await last_menu_message_delete(id_user)

        text, inline_kb = await get_start_menu(id_user)
        await message_answer(message, text, inline_kb)

    else:
        await message_delete(message)


@dp.message_handler(commands=['test'])
async def command_start(message: Message):
    await message_send(message.from_user.id, 'Start')
    # Перенести пользователей из chats в users
    # cursor.execute('''SELECT DISTINCT chats.id_user, chats.first_name, chats.last_name, chats.username FROM chats
    #                 LEFT JOIN users ON chats.id_user = users.id_user
    #                 WHERE users.id_user IS NULL''')
    # meaning = cursor.fetchall()
    # for i in meaning:
    #     cursor.execute(
    #         'INSERT INTO users (id_user, first_name, last_name, username, language_code, registration_date, registration_field, message_idmessage_id, gender, fio, birthdate, address, tel, mail, projects) '
    #         'VALUES (%s, %s, %s, %s, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL)',
    #         (i[0], i[1], i[2], i[3]))
    #     connect.commit()

    # Заполнить админов групп
    # cursor.execute(
    #     '''SELECT DISTINCT chats.id_chat, settings.title, settings.project_id FROM chats
    #     INNER JOIN settings ON settings.id_chat =  chats.id_chat
    #     WHERE NOT chats.deleted AND NOT settings.curators_group AND settings.enable_group ''')
    # meaning = cursor.fetchall()
    # for i in meaning:
    #     try:
    #         chat_admins = await bot.get_chat_administrators(i[0])
    #         qwe = 1
    #     except Exception as e:
    #         chat_admins = ()
    #
    #     for ii in chat_admins:
    #         id_user = ii.user.id
    #         cursor.execute("UPDATE users SET role = 'admin' WHERE id_user = %s", (id_user,))
    #         connect.commit()

    # Очистить домашки
    # cursor.execute('''DELETE FROM homework_check; DELETE FROM homework_text;''')
    # connect.commit()

    # Актуализация удаленных
    # # chat_member = await bot.get_chat_member(-1001531919077, 5751545336)
    # # member = chat_member.status == 'member'
    # cursor.execute('''SELECT * FROM chats WHERE NOT deleted''')
    # result = cursor.fetchall()
    # for i in result:
    #     id_chat = i[0]
    #     id_user = i[1]
    #     member = False
    #     try:
    #         chat_member = await bot.get_chat_member(id_chat, id_user)
    #         member = not chat_member.status == 'left'
    #     except Exception as e:
    #         pass
    #
    #     if not member:
    #         cursor.execute("UPDATE chats SET deleted = True WHERE id_chat = %s AND id_user = %s", (id_chat, id_user))
    #         connect.commit()

    # Очистить 777000
    # cursor.execute('''DELETE FROM chats WHERE id_user = 777000''')
    # connect.commit()

    # cursor.execute('''SELECT id_user, registration_field, mail FROM users''')
    # result = cursor.fetchall()
    # q = len(result)
    # for i in result:
    #     id_user = i[0]
    #     registration_field = i[1]
    #     mail = i[2]
    #     if registration_field is None and mail is not None:
    #         cursor.execute('''UPDATE users SET registration_field = 'done' WHERE id_user = %s''', (id_user,))
    #         connect.commit()
    #         print(id_user, q, result.index(i))

    await message_send(message.from_user.id, 'Done')


@dp.message_handler(commands=['get_stat'])
async def command_get_stat(message: Message):
    if message.chat.type == 'private':
        await message.answer('Эта команда работает в группе. Здесь используйте команду /start')

    else:
        await message_handler(message)

        id_chat = message.chat.id
        id_user = message.from_user.id

        text = await get_stat(id_chat, id_user)

        if not text == '':
            await message_answer(message, text)


@dp.callback_query_handler(lambda x: x.data and x.data.startswith('id_chat '))
async def choosing_a_chat_to_set_up(callback: CallbackQuery):
    id_chat = int(callback.data.replace('id_chat ', ''))
    id_user = callback.from_user.id
    text, inline_kb = await setting_up_a_chat(id_chat, id_user)
    await callback_edit_text(callback, text, inline_kb)

    await callback.answer()


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
        projects_tuple = await base.get_all_projects()

        inline_kb = InlineKeyboardMarkup(row_width=1)
        for i in projects_tuple:
            callback_data = 'settings ' + str(id_chat) + ' project_id ' + str(i[0])
            inline_kb.add(InlineKeyboardButton(text=i[1], callback_data=callback_data))

        callback_data = 'settings ' + str(id_chat) + ' project_id 0'
        inline_kb.add(InlineKeyboardButton(text='Нет проекта', callback_data=callback_data))

        await callback_edit_text(callback, text, inline_kb)

    elif parameter_name == 'project_id':
        await base.save_chat_project(parameter_value, id_chat)
        text, inline_kb = await setting_up_a_chat(id_chat, id_user)

        await callback_edit_text(callback, text, inline_kb)
    else:
        if parameter_value in ('False', False, '0'):
            parameter_value = True
        else:
            parameter_value = False

        await process_parameter_continuation(callback, id_chat, id_user, parameter_name, parameter_value)

    await callback.answer()


@dp.callback_query_handler(text='back')
async def menu_back(callback: CallbackQuery):
    id_user = callback.from_user.id
    text, inline_kb = await get_start_menu(id_user)
    await callback_edit_text(callback, text, inline_kb)

    await callback.answer()


@dp.callback_query_handler(text='reg')
async def reg_command_callback(callback: CallbackQuery):
    await registration_command(callback)

    await callback.answer()


@dp.message_handler(commands=['reg'])
async def reg_command_message(message: Message):
    await registration_command(message)


@dp.callback_query_handler(text='-')
async def skip_action(callback: CallbackQuery):
    await callback.answer()


@dp.callback_query_handler(lambda x: x.data and x.data.startswith('gender ') or x.data.startswith('projects '))
async def gender_processing(callback: CallbackQuery):
    value = callback.data
    value = value.replace('gender ', '')
    value = value.replace('projects ', '')

    await registration_process(callback.message, value, True)

    await callback.answer()


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
        projects_tuple = await base.get_all_projects()

        inline_kb = InlineKeyboardMarkup(row_width=1)
        for i in projects_tuple:
            inline_kb.add(
                InlineKeyboardButton(text=i[1], callback_data='super_admin ' + str(i[0])))

        inline_kb.add(InlineKeyboardButton(text='Нет проекта', callback_data='super_admin 0'))
        inline_kb.add(InlineKeyboardButton(text='Назад', callback_data='back'))

        await callback_edit_text(callback, text, inline_kb)

    elif id_chat == '':
        inline_kb = InlineKeyboardMarkup(row_width=1)
        result = await base.get_chats_in_project(project_id)
        for i in result:
            title_result = i[1].replace('\\', '')
            inline_kb.add(InlineKeyboardButton(text=title_result, callback_data=f'super_admin {project_id} {i[0]}'))
        inline_kb.add(InlineKeyboardButton(text='Назад', callback_data='super_admin '))

        text = 'Выберете группу для настройки:'
        await callback_edit_text(callback, text, inline_kb)

    else:
        id_user = callback.from_user.id
        text, inline_kb = await setting_up_a_chat(id_chat, id_user, False, True)
        await callback_edit_text(callback, text, inline_kb)

    await callback.answer()


@dp.callback_query_handler(lambda x: x.data and x.data.startswith('homework '))
async def homework_functions(callback: CallbackQuery):
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
        homework_date = datetime.datetime.strptime(list_str[3], "%Y-%m-%d").date()
    message_id = callback.message.message_id

    text, inline_kb, status = await homework_process(project_id, id_user, status, homework_date, message_id)

    if status == 'back':
        await menu_back(callback)
    elif status in ('homework', 'sending'):
        pass
    else:
        await callback_edit_text(callback, text, inline_kb)

    await callback.answer()


@dp.callback_query_handler(lambda x: x.data and x.data.startswith('admin_homework '))
async def admin_homework_functions(callback: CallbackQuery):
    id_user_admin = callback.from_user.id
    list_str = callback.data.split()
    project_id = ''
    if len(list_str) > 1:
        project_id = int(list_str[1])
    status = ''
    if len(list_str) > 2:
        status = list_str[2]
    id_user = 0
    if len(list_str) > 3:
        id_user = int(list_str[3])
    id_chat = 0
    if len(list_str) > 4:
        id_chat = int(list_str[4])
    homework_date = ''
    if len(list_str) > 5:
        homework_date = datetime.datetime.strptime(list_str[5], "%Y-%m-%d").date()

    text, user_info, inline_kb, status = \
        await admin_homework_process(project_id, id_user_admin, status, id_user, id_chat, homework_date)
    text = user_info + shielding(text)

    if status == 'back_menu_back':
        await menu_back(callback)
    else:
        await callback_edit_text(callback, text, inline_kb)

    await callback.answer()


@dp.chat_join_request_handler()
async def join(update: ChatJoinRequest):
    id_user = update.from_user.id
    result = await base.application_for_membership(id_user)

    inline_kb = InlineKeyboardMarkup(row_width=1)

    if result is None:
        await update.decline()
        text = 'Заявка на вступление отклонена. Свяжитесь с вашим куратором для решения этой ситуации.'
    else:
        await update.approve()
        text = 'Все получилось! \nПоздравляем Вас с успешной регистрацией! \n' \
               'Ваша заявка подтверждена на вступление подтверждена, пожалуйста заходите.'
        inline_kb.add(InlineKeyboardButton('Зайти в канал.', url=result[2]))
        try:
            await bot.delete_message(chat_id=id_user, message_id=result[0])
        except Exception as e:
            pass

    text = shielding(text)
    await message_send(id_user, text, inline_kb)


@dp.message_handler(content_types='any')
async def message_handler(message):
    id_user = message.from_user.id

    if message.chat.type == 'private':
        if message.forward_from is not None:
            if id_user == SUPER_ADMIN_ID:
                forward_id = message.forward_from.id
                text_result = await base.get_all_info_about_user(forward_id)
                await message_answer(message, text_result)
            else:
                await message_delete(message)

        elif message.content_type == 'text':
            text = message.text
            answer_text, project_id, homework_date, homework_id_user = await base.which_menu_to_show(id_user)

            if answer_text == 'registration':
                await registration_process(message, text, False)

            elif answer_text == 'homework_text':
                await message_delete(message)

                text, inline_kb, status = await homework_process(project_id, id_user, 'confirm', '', text)
                await message_answer(message, text, inline_kb)

            elif answer_text == 'homework_feedback':
                await message_delete(message)

                await base.set_homework_feedback(project_id, homework_date, homework_id_user, text, id_user)

                text, user_info, inline_kb, status = \
                    await admin_homework_process(project_id, id_user, 'feedback', homework_id_user, 0, homework_date)

                text = user_info + shielding(text)
                message_id = await base.get_menu_message_id(id_user)
                if message_id > 0:
                    try:
                        await bot.edit_message_text(
                            chat_id=id_user,
                            message_id=message_id,
                            text=text,
                            reply_markup=inline_kb,
                            parse_mode='MarkdownV2')
                    except Exception as e:
                        pass

                homework_text = shielding('На ваше домашнее задание получен отклик куратора.')
                homework_inline_kb = InlineKeyboardMarkup(row_width=1)
                homework_inline_kb.add(InlineKeyboardButton(
                    text='Посмотреть',
                    callback_data=f'homework {project_id} feedback {homework_date}'))
                await message_send(homework_id_user, homework_text, homework_inline_kb)

            elif answer_text == 'homework_response':
                await last_menu_message_delete(id_user)

                await homework_response(project_id, homework_date, id_user, text)

                inline_kb = await homework_kb(project_id, id_user, homework_date, 'response')
                text = shielding(text)
                await message_answer(message, text, inline_kb)

            else:
                await message_delete(message)

        else:
            await message_delete(message)

    else:
        id_chat = message.chat.id
        date_of_the_last_message = message.date

        skip_content_type = ('delete_chat_photo', 'migrate_from_chat_id', 'pinned_message')
        created_title_content_type = ('group_chat_created', 'supergroup_chat_created', 'channel_chat_created')

        if message.content_type in skip_content_type:
            pass

        elif len(message.entities) == 1 and message.entities[0].type == 'bot_command':
            await message_delete(message)

        elif id_user == 777000:
            # TODO
            # await send_error(message.content_type, 'id_user = 777000', traceback.format_exc())
            pass

        elif message.content_type in created_title_content_type:
            await base.save_new_chat(id_chat, message.chat.title)

        elif message.content_type == 'new_chat_title':
            await base.save_new_title(id_chat, message.chat.title)

        elif message.content_type == 'migrate_to_chat_id':
            new_id_chat = message.migrate_to_chat_id
            await base.migrate_to_chat_id(new_id_chat, id_chat)

        elif message.content_type == 'new_chat_members':
            for i in message.new_chat_members:
                if i.is_bot:
                    if i.username == THIS_IS_BOT_NAME:
                        await base.save_or_update_new_title(id_chat, message.chat.title)

                        text = f'Добавлена новая группа "{message.chat.title}"'
                        await message_send(SUPER_ADMIN_ID, text)

                else:

                    await base.insert_or_update_chats_and_users(id_chat, i, 0, date_of_the_last_message)

        elif message.content_type == 'left_chat_member':
            i = message.left_chat_member
            if i.is_bot:
                if i.username == THIS_IS_BOT_NAME:
                    await base.save_chat_disable(id_chat)

            else:
                i_id_user = i.id
                result = await base.save_user_disable_in_chat(id_chat, i_id_user, date_of_the_last_message)
                if result is not None:
                    channel_id = result[0]
                    await bot.kick_chat_member(channel_id, i_id_user)
                    await bot.unban_chat_member(channel_id, i_id_user)

        else:
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

            await base.save_message_count(id_chat, id_user, date_of_the_last_message, characters, message_id)

            await base.insert_or_update_chats_and_users(id_chat, message.from_user, characters, date_of_the_last_message)


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

    cursor.execute('SELECT * FROM chats WHERE id_chat = %s', (id_chat,))
    meaning = cursor.fetchall()
    for i in meaning:
        count_messages += 1
        name_user = i[2] + ' ' + i[3]
        name_user = name_user.replace('_', '\_')
        text += f'{count_messages}\. [{name_user}](tg://user%sid={i[1]})\. \n'

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

    cursor.execute('SELECT * FROM meetings WHERE id_chat = %s AND id_user = %s', (id_chat, id_user))
    meaning = cursor.fetchall()
    if len(meaning) == 0:
        for i in week:
            cursor.execute(
                '''INSERT INTO meetings (id_chat, id_user, day, 
                _00, _01, _02, _03, _04, _05, _06, _07, _08, _09, _10, _11, 
                _12, _13, _14, _15, _16, _17, _18, _19, _20, _21, _22, _23)
                VALUES (%s, %s, %s, 
                False, False, False, False, False, False, False, False, False, False, False, False, 
                False, False, False, False, False, False, False, False, False, False, False, False)''',
                (id_chat, id_user, i)
            )
            connect.commit()

            cursor.execute('SELECT * FROM meetings WHERE id_chat = %s AND id_user = %s', (id_chat, id_user))
            meaning = cursor.fetchall()

    new_value_time = meaning[index_day][index_time]
    if new_value_time == 1:
        new_value_time = 0
    else:
        new_value_time = 1
    cursor.execute('UPDATE meetings SET id_user = %s, %s = %s WHERE id_chat = %s AND day = %s',
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
            f'http://api.geonames.org/timezoneJSON%sformatted=true&lat={latitude}&lng={longitude}&username={GEONAMES_USERNAME}')  ## Make a request
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

    text = 'Теперь необходимо отправить номер телефона.'
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
