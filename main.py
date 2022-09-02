from aiogram import Bot
from aiogram.dispatcher import Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from settings import TOKEN, SUPER_ADMIN_ID, THIS_IS_BOT_NAME
import sqlite3
from datetime import datetime
import asyncio
import aioschedule

bot = Bot(TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

connect = sqlite3.connect('base.db')
cursor = connect.cursor()


async def on_startup(_):
    connect.execute(
        'CREATE TABLE IF NOT EXISTS chats(id_chat INTEGER, id_user INTEGER, first_name TEXT, last_name TEXT, '
        'username TEXT, characters INTEGER, messages INTEGER, date_of_the_last_message TEXT, deleted BLOB)')
    connect.execute(
        'CREATE TABLE IF NOT EXISTS messages(id_chat INTEGER, id_user INTEGER, date TEXT, characters INTEGER, message_id INTEGER)')
    connect.execute(
        'CREATE TABLE IF NOT EXISTS settings(id_chat INTEGER, title TEXT, statistics_for_everyone BLOB, '
        'include_admins_in_statistics BLOB, sort_by_messages BLOB, do_not_output_the_number_of_messages BLOB, '
        'do_not_output_the_number_of_characters BLOB, period_of_activity INTEGER, report_enabled BLOB, '
        'report_every_week BLOB, report_time TEXT, enable_group BLOB, last_notify_date TEXT)')
    connect.execute(
        'CREATE TABLE IF NOT EXISTS meetings(id_chat INTEGER, id_user INTEGER, day TEXT,'
        '_00 BLOB, _01 BLOB, _02 BLOB, _03 BLOB, _04 BLOB, _05 BLOB, _06 BLOB, _07 BLOB, _08 BLOB, _09 BLOB, _10 BLOB, _11 BLOB, '
        '_12 BLOB, _13 BLOB, _14 BLOB, _15 BLOB, _16 BLOB, _17 BLOB, _18 BLOB, _19 BLOB, _20 BLOB, _21 BLOB, _22 BLOB, _23 BLOB)')
    connect.commit()

    asyncio.create_task(scheduler())


async def scheduler():
    aioschedule.every().hour.do(run_reminder)
    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(1)


def its_admin(id_user, chat_admins):
    if id_user == SUPER_ADMIN_ID:
        return True

    for ii in chat_admins:
        if ii.user.id == id_user:
            return True

    return False


async def get_stat(id_chat, id_user=None):
    statistics_for_everyone = False
    include_admins_in_statistics = False
    try:
        chat_admins = await bot.get_chat_administrators(id_chat)
    except Exception:
        chat_admins = ()
    period_of_activity = 0
    sort_by_messages = False
    do_not_output_the_number_of_messages = False
    do_not_output_the_number_of_characters = False

    cursor.execute(f'SELECT * FROM settings WHERE id_chat = {id_chat}')
    meaning = cursor.fetchone()
    if meaning is not None:
        statistics_for_everyone = meaning[2]
        include_admins_in_statistics = meaning[3]
        period_of_activity = meaning[7]
        sort_by_messages = meaning[4]
        do_not_output_the_number_of_messages = meaning[5]
        do_not_output_the_number_of_characters = meaning[6]

    if statistics_for_everyone or its_admin(id_user, chat_admins) or id_user == None:
        text = '*Активные участники:*\n'

        if sort_by_messages:
            sort = 'messages'
        else:
            sort = 'characters'

        count_messages = 0
        cursor.execute(
            f'''SELECT chats.id_user, chats.first_name, chats.last_name, chats.username, 
            SUM(IFNULL(messages.characters, 0)) AS characters, COUNT(messages.characters) AS messages, 
            chats.deleted, chats.date_of_the_last_message, 
                CASE WHEN NOT chats.deleted AND {period_of_activity} > ROUND(julianday("now") - julianday(chats.date_of_the_last_message), 0) THEN 0 
                ELSE ROUND(julianday("now") - julianday(chats.date_of_the_last_message), 0) END AS inactive_days,
                (SELECT COUNT(DISTINCT message_id) FROM messages 
                WHERE chats.id_chat = messages.id_chat AND messages.message_id IS NOT NULL AND NOT messages.message_id = 0 AND 7 > ROUND(julianday("now") - julianday(date), 0)) AS requests,
                (SELECT COUNT(DISTINCT messages_two.message_id) FROM messages AS messages_one 
                INNER JOIN messages AS messages_two ON messages_one.id_chat = messages_two.id_chat AND messages_one.message_id = messages_two.message_id AND chats.id_user = messages_two.id_user
                WHERE chats.id_chat = messages_one.id_chat AND messages_one.message_id IS NOT NULL AND NOT messages_one.message_id = 0 AND 7 > ROUND(julianday("now") - julianday(messages_one.date), 0)) AS response 
            FROM chats 
            LEFT JOIN messages ON chats.id_chat = messages.id_chat AND chats.id_user = messages.id_user 
                AND {period_of_activity} > ROUND(julianday("now") - julianday(messages.date), 0) 
            WHERE chats.id_chat = {id_chat} 
            GROUP BY chats.id_chat, chats.id_user, chats.first_name, chats.last_name, chats.username, chats.date_of_the_last_message, chats.deleted 
            ORDER BY deleted ASC, inactive_days ASC, {sort} DESC '''
        )
        meaning = cursor.fetchall()

        requests = None
        active_members_inscription_is_shown = False
        deleted_members_inscription_is_shown = False
        for i in meaning:
            i_id_user = i[0]
            i_first_name = i[1]
            i_last_name = i[2]
            i_username = i[3]
            i_characters = i[4]
            i_messages = i[5]
            i_deleted = i[6]
            i_date_of_the_last_message = i[7]
            i_inactive_days = i[8]
            if requests is None:
                requests = i[9]
            i_response = i[10]

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

            specifics = ''
            characters = ''
            messages = ''
            response = ''

            if not do_not_output_the_number_of_messages:
                messages = f'сообщений: {i_messages}'
            if not do_not_output_the_number_of_characters:
                characters = f'символов: {i_characters}'
            if requests > 0:
                response = f'откликов: {i_response} из {requests}'

            inactive = ''
            if i_deleted:
                data_str = shielding(datetime.strptime(i_date_of_the_last_message, '%Y-%m-%d %H:%M:%S').strftime("%d.%m.%Y"))#"%d.%m.%Y %H:%M:%S"
                inactive = f' \(вне чата с {data_str}, дней назад: {int(i_inactive_days)}\)'
            elif i_inactive_days > 0:
                inactive = f' \(неактивен дней: {int(i_inactive_days)}\)'
            else:
                if sort_by_messages:
                    specifics = messages
                    if not characters == '' and not specifics == '':
                        specifics += ', '
                    specifics += characters
                else:
                    specifics = characters
                    if not messages == '' and not specifics == '':
                        specifics += ', '
                    specifics += messages

                if not specifics == '':
                    if response == '':
                        specifics += '\.'
                    else:
                        specifics += ', ' + response + '\.'
                    specifics = ':\n     — ' + specifics + ''

                specifics += '\n'

            user = await get_name_tg(id_user, i_first_name, i_last_name, i_username)
            text += f'\n*{count_messages}*\. {user}{inactive}{specifics}'

        if text == '*Активные участники:*\n':
            text = 'Нет статистики для отображения\.'

    else:
        text = 'Статистику могут показать только администраторы группы.'

    return text


async def get_start_menu(id_user):
    this_is_super_admin = id_user == SUPER_ADMIN_ID
    if this_is_super_admin:
        piece = ''
    else:
        piece = f' AND id_user = {id_user}'
    cursor.execute('SELECT DISTINCT chats.id_chat, settings.title FROM chats '
                   'LEFT OUTER JOIN settings ON chats.id_chat = settings.id_chat WHERE settings.enable_group' + piece)
    meaning = cursor.fetchall()
    user_groups = []
    for i in meaning:
        get = False
        if this_is_super_admin:
            get = True
        else:
            try:
                member = await bot.get_chat_member(i[0], id_user)
                get = member.is_chat_admin()
            except Exception:
                pass

        if get:
            title_result = i[1].replace('\\', '')
            user_groups.append([i[0], title_result])

    text = ''
    inline_kb = InlineKeyboardMarkup(row_width=1)
    one_group = None

    if len(user_groups) == 0:
        text = 'Для начала работы, необходимо добавить бота в группу, где вы являетесь администратором\.'
    elif len(user_groups) == 1:
        one_group = user_groups[0][0]
    else:
        text = 'Выберете группу для настройки:'
        for i in user_groups:
            inline_kb.add(InlineKeyboardButton(text=i[1], callback_data=f'id_chat {i[0]}'))

    return text, inline_kb, one_group


async def setting_up_a_chat(id_chat, id_user, back_button=True):
    cursor.execute(f'SELECT * FROM settings WHERE enable_group AND id_chat = {id_chat}')
    meaning = cursor.fetchone()

    if meaning is None:
        return '', ''

    inline_kb = InlineKeyboardMarkup(row_width=1)
    if meaning[2]:
        inline_kb.add(InlineKeyboardButton(text='Статистика доступна всем', callback_data=f'settings {id_chat} statistics_for_everyone {meaning[2]}'))
    else:
        inline_kb.add(InlineKeyboardButton(text='Статистика доступна только администраторам', callback_data=f'settings {id_chat} statistics_for_everyone {meaning[2]}'))
    inline_kb.add(InlineKeyboardButton(text='Включать админов в статистику: ' + convert_bool(meaning[3]), callback_data=f'settings {id_chat} include_admins_in_statistics {meaning[3]}'))
    if meaning[4]:
        inline_kb.add(InlineKeyboardButton(text='Сортировка по сообщениям', callback_data=f'settings {id_chat} sort_by_messages {meaning[4]}'))
    else:
        inline_kb.add(InlineKeyboardButton(text='Сортировка по количеству символов', callback_data=f'settings {id_chat} sort_by_messages {meaning[4]}'))
    inline_kb.add(InlineKeyboardButton(text='Не выводить количество сообщений: ' + convert_bool(meaning[5]), callback_data=f'settings {id_chat} do_not_output_the_number_of_messages {meaning[5]}'))
    inline_kb.add(InlineKeyboardButton(text='Не выводить количество символов: ' + convert_bool(meaning[6]), callback_data=f'settings {id_chat} do_not_output_the_number_of_characters {meaning[6]}'))
    inline_kb.add(InlineKeyboardButton(text='Статистика за период (дней): ' + str(meaning[7]), callback_data=f'settings {id_chat} period_of_activity {meaning[7]}'))
    inline_kb.add(InlineKeyboardButton(text='Автоматический отчет в чат: ' + convert_bool(meaning[8]), callback_data=f'settings {id_chat} report_enabled {meaning[8]}'))
    # if meaning[9]:
    #     inline_kb.add(InlineKeyboardButton(text='Отчет каждую неделю', callback_data=f'settings {id_chat} report_every_week {meaning[9]}'))
    # else:
    #     inline_kb.add(InlineKeyboardButton(text='Отчет каждый день', callback_data=f'settings {id_chat} report_every_week {meaning[9]}'))
    # inline_kb.add(InlineKeyboardButton(text='Время отправки отчета: ' + meaning[9], callback_data=f'settings {id_chat} report_time {meaning[10]}'))

    if back_button:
        inline_kb.add(InlineKeyboardButton(text='Назад', callback_data='back'))

    text = await get_stat(id_chat, id_user)
    #group_name = shielding(meaning[1])
    group_name = meaning[1]
    return '*Группа "' + group_name + '"\.*\n\n' + text, inline_kb


async def process_parameter_input(callback: CallbackQuery, id_chat, parameter_name, parameter_value):
    inline_kb = InlineKeyboardMarkup(row_width=1)
    inline_kb.add(InlineKeyboardButton(text='Назад', callback_data='back'))

    await callback.message.edit_text(
        f'Текущее значение параметра {parameter_name} = "{parameter_value}". Введите новое значение:',
        parse_mode='MarkdownV2',
        reply_markup=inline_kb)


async def process_parameter_continuation(callback: CallbackQuery, id_chat, id_user, parameter_name, parameter_value):
    cursor.execute(f'UPDATE settings SET {parameter_name} = {parameter_value} WHERE id_chat = {id_chat}')
    connect.commit()

    text, inline_kb = await setting_up_a_chat(id_chat, id_user)
    await callback.message.edit_text(text, parse_mode='MarkdownV2', reply_markup=inline_kb)


def convert_bool(value):
    if value == True or value == 1:
        return 'Да'
    else:
        return 'Нет'


def shielding(text):
    text_result = ''
    # allowed_simbols = ' ,:;—'
    forbidden_characters = '_*[]()~">#+-=|{}.!' # '.-_[]()"'
    for i in text:
        # if i.isalnum() or i in allowed_simbols:
        #     text_result += i
        # elif i in forbidden_characters:
        #     text_result += '\\' + i
        # else:
        #     pass
        if i in forbidden_characters:
            text_result += '\\' + i
        else:
            text_result += i

    # if text_result[-1] == ':':
    #     text_result = text_result[:-1]

    return text_result


async def get_name_tg(id_user, first_name, last_name, username):
    name_user = shielding(first_name + ' ' + last_name).strip()
    # if use_username and not i_username == '':
    #     # user = '@' + i_username
    #     user = f'[{name_user}](http://t.me/{i_username})'
    # else:
    #     user = f'[{name_user}](tg://user?id={i_id_user})'
    # если ошибка сохранится, то нужно попробовать хтмл разметку
    user = f'[{name_user}](tg://user?id={id_user})'
    if not username == '':
        user += f' \(@{shielding(username)}\)'

    return user


async def run_reminder():
    cursor.execute('SELECT * FROM settings WHERE strftime("%w", date("now")) = "1" AND date("now") > date(last_notify_date) AND report_enabled AND enable_group')
    result_tuple = cursor.fetchall()
    for i in result_tuple:
        id_chat = i[0]
        text = await get_stat(id_chat)
        if not text == '' and not text == 'Нет статистики для отображения.':
            await bot.send_message(text=text, chat_id=id_chat, parse_mode='MarkdownV2', disable_notification=True)
            cursor.execute(f'UPDATE settings SET last_notify_date = datetime("now") WHERE id_chat = {id_chat}')
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
    tuple = []
    for i in result_tuple:
        id_chat = i[0]
        if not last_id_chat == id_chat:
            if last_id_chat is None:
                last_id_chat = id_chat
            else:
                tuple.append((last_id_chat, text))
                text = ''
                last_id_chat = id_chat

        id_user = i[1]
        first_name = i[2]
        last_name = i[3]
        username = i[4]
        text += await get_name_tg(id_user, first_name, last_name, username)
    else:
        if last_id_chat is not None:
            tuple.append([last_id_chat, text])

    for i in tuple:
        id_chat = i[0]
        text = i[1]
        text = 'Сегодня не откликнулись на запрос\: \n' + text + '\n #ВажноеСообщение'
        await bot.send_message(text=text, chat_id=id_chat, parse_mode='MarkdownV2', disable_notification=True)
        cursor.execute(f'UPDATE settings SET last_notify_message_id_date = datetime("now") WHERE id_chat = {id_chat}')
        connect.commit()


@dp.message_handler(commands=['start'])
async def command_start(message: Message):
    if not message.chat.type == 'private':
        return
    id_user = message.from_user.id
    text, inline_kb, one_group = await get_start_menu(id_user)

    if one_group is None:
        await message.answer(text, parse_mode='MarkdownV2', reply_markup=inline_kb)
    else:
        text, inline_kb = await setting_up_a_chat(one_group, id_user, False)
        await message.answer(text, parse_mode='MarkdownV2', reply_markup=inline_kb)


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
        await message.answer(text, parse_mode='MarkdownV2', disable_notification=True)


@dp.message_handler(commands=['call_meeting'])
async def command_call_meeting(message: Message):
    id_chat = message.chat.id
    id_user = message.from_user.id
    if message.chat.type == 'group' or message.chat.type == 'supergroup':
        chat_admins = await bot.get_chat_administrators(id_chat)
        its_admin = False
        for i in chat_admins:
            if i.user.id == id_user:
                its_admin = True
                break

        if not its_admin:
            await message.answer('Эту команду может вызвать только админ группы.')
            return
    else:
        if message.chat.type == 'private':
            await message.answer('Эта команда работает в группе. Здесь используйте команду /start')
        return

    await message_handler(message)

    text = ''
    count_messages = 0

    cursor.execute(f'SELECT * FROM chats WHERE id_chat = {id_chat}')
    meaning = cursor.fetchall()
    for i in meaning:
        count_messages += 1
        name_user = i[2] + ' ' + i[3]
        name_user = name_user.replace('_', '\_')
        text += f'{count_messages}\. [{name_user}](tg://user?id={i[1]})\. \n'

    inline_kb = add_buttons_time_selection(0)
    await message.answer(text, parse_mode='MarkdownV2', reply_markup=inline_kb)

    inline_kb = add_buttons_time_selection(12)
    await message.answer('/', parse_mode='MarkdownV2', reply_markup=inline_kb)


def add_buttons_time_selection(shift):
    inline_kb = InlineKeyboardMarkup(row_width=7)
    massive = []
    massive_line = []
    first_pass = True
    for i in range(12):
        if shift > 0:
            first_pass = False
        value = i + shift
        # if value < 3 or value > 22:
        #     continue
        for ii in ['пн', 'вт', 'ср', 'чт', 'пт', 'сб', 'вс']:
            i_zero = ''
            if first_pass:
                i_text = ii
                callback_data = 'no'
            else:
                if value < 10:
                    i_zero = '0'
                i_text = i_zero + str(value)# + ':00'
                callback_data = 'call_meeting ' + ii + ' ' + i_zero + str(value)
            massive_line.append(InlineKeyboardButton(text=i_text, callback_data=callback_data))

        first_pass = False
        massive.append(massive_line)
        massive_line = []

    for massive_line in massive:
        inline_kb.row(*massive_line)

    return inline_kb


@dp.callback_query_handler(lambda x: x.data and x.data.startswith('call_meeting '))
async def menu_back(callback: CallbackQuery):
    id_chat = callback.message.chat.id
    id_user = callback.from_user.id

    week = ['пн', 'вт', 'ср', 'чт', 'пт', 'сб', 'вс']
    list_data = callback.data.split(' ')
    day = list_data[1]
    index_day = week.index(day)
    time = list_data[2]
    index_time = int(time) + 3

    cursor.execute(f'SELECT * FROM meetings WHERE id_chat = {id_chat} AND id_user = {id_user}')
    meaning = cursor.fetchall()
    if len(meaning) == 0:
        for i in week:
            cursor.execute(
                'INSERT INTO meetings (id_chat, id_user, day, '
                '_00, _01, _02, _03, _04, _05, _06, _07, _08, _09, _10, _11, '
                '_12, _13, _14, _15, _16, _17, _18, _19, _20, _21, _22, _23)'
                f'VALUES ({id_chat}, {id_user}, "{i}", '
                'False, False, False, False, False, False, False, False, False, False, False, False, '
                'False, False, False, False, False, False, False, False, False, False, False, False)')
            connect.commit()

            cursor.execute(f'SELECT * FROM meetings WHERE id_chat = {id_chat} AND id_user = {id_user}')
            meaning = cursor.fetchall()

    new_value_time = meaning[index_day][index_time]
    if new_value_time == 1:
        new_value_time = 0
    else:
        new_value_time = 1
    cursor.execute(f'UPDATE meetings SET id_user = {id_user}, _{time} = {new_value_time} WHERE id_chat = {id_chat} AND day = "{day}"')
    connect.commit()

    await callback.answer()


@dp.callback_query_handler(text='back')
async def menu_back(callback: CallbackQuery):
    id_user = callback.from_user.id
    text, inline_kb, one_group = await get_start_menu(id_user)

    if one_group is None:
        await callback.message.edit_text(text, parse_mode='MarkdownV2', reply_markup=inline_kb)
    else:
        text, inline_kb = await setting_up_a_chat(one_group, id_user, False)
        await callback.message.edit_text(text, parse_mode='MarkdownV2', reply_markup=inline_kb)


@dp.callback_query_handler(lambda x: x.data and x.data.startswith('id_chat '))
async def choosing_a_chat_to_set_up(callback: CallbackQuery):
    id_chat = int(callback.data.replace('id_chat ', ''))
    id_user = callback.from_user.id
    text, inline_kb = await setting_up_a_chat(id_chat, id_user)
    await callback.message.edit_text(text, parse_mode='MarkdownV2', reply_markup=inline_kb)


@dp.callback_query_handler(lambda x: x.data and x.data.startswith('settings '))
async def process_parameter(callback: CallbackQuery):
    id_user = callback.from_user.id
    list_str = callback.data.split()
    id_chat = int(list_str[1])
    parameter_name = list_str[2]
    parameter_value = list_str[3]

    # no_blob_parameters = ['period_of_activity', 'report_time']
    # if parameter_name in no_blob_parameters:
    #     await process_parameter_input(callback, id_chat, parameter_name, parameter_value)
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
    else:
        if parameter_value == '0':
            parameter_value = '1'
        else:
            parameter_value = '0'
        await process_parameter_continuation(callback, id_chat, id_user, parameter_name, parameter_value)


@dp.message_handler(content_types='any')
async def message_handler(message):
    id_chat = message.chat.id
    date_of_the_last_message = message.date

    skip_content_type = ('delete_chat_photo', 'migrate_from_chat_id', 'pinned_message')
    created_title_content_type = ('group_chat_created', 'supergroup_chat_created', 'channel_chat_created')

    if len(message.entities) == 1 and message.entities[0].type == 'bot_command':
        return

    elif message.content_type in skip_content_type:
        return

    elif message.content_type in created_title_content_type:
        title = shielding(message.chat.title)
        cursor.execute(
            f'''INSERT INTO settings (id_chat, title, statistics_for_everyone, include_admins_in_statistics, 
            sort_by_messages, do_not_output_the_number_of_messages, do_not_output_the_number_of_characters, 
            period_of_activity, report_enabled, report_every_week, report_time, enable_group, 
            last_notify_date, last_notify_message_id_date) 
            VALUES ({id_chat}, "{title}", False, False, False, False, False, 7, False, False, "00:00", True, 
            datetime("now"), datetime("now"))''')
        connect.commit()

        return

    elif message.content_type == 'new_chat_title':
        title = shielding(message.chat.title)
        cursor.execute(f'UPDATE settings SET title = "{title}" WHERE id_chat = {id_chat}')
        connect.commit()

        return

    elif message.content_type == 'migrate_to_chat_id':
        new_id_chat = message.migrate_to_chat_id
        cursor.execute(f'UPDATE chats SET id_chat = {new_id_chat} WHERE id_chat = {id_chat}')
        cursor.execute(f'UPDATE meetings SET id_chat = {new_id_chat} WHERE id_chat = {id_chat}')
        cursor.execute(f'UPDATE messages SET id_chat = {new_id_chat} WHERE id_chat = {id_chat}')
        cursor.execute(f'UPDATE settings SET id_chat = {new_id_chat} WHERE id_chat = {id_chat}')
        connect.commit()

        return

    elif message.content_type == 'new_chat_members':
        for i in message.new_chat_members:
            if i.is_bot:
                if i.username == THIS_IS_BOT_NAME:
                    title = shielding(message.chat.title)

                    cursor.execute(f'SELECT * FROM settings WHERE id_chat = {id_chat}')
                    meaning = cursor.fetchone()
                    if meaning is None:
                        cursor.execute(
                            f'''INSERT INTO settings (id_chat, title, statistics_for_everyone, include_admins_in_statistics, 
                            sort_by_messages, do_not_output_the_number_of_messages, do_not_output_the_number_of_characters, 
                            period_of_activity, report_enabled, report_every_week, report_time, enable_group, 
                            last_notify_date, last_notify_message_id_date) 
                            VALUES ({id_chat}, "{title}", False, False, False, False, False, 7, False, False, "00:00", True, 
                            datetime("now"), datetime("now"))''')
                    else:
                        cursor.execute(f'UPDATE settings SET enable_group = True, title = "{title}" WHERE id_chat = {id_chat}')
                    connect.commit()

            else:
                i_last_name = i.last_name
                if i_last_name is None:
                    i_last_name = ''

                i_username = i.username
                if i_username is None:
                    i_username = ''

                cursor.execute(f'SELECT * FROM chats WHERE id_chat = {id_chat} AND id_user = {i.id}')
                meaning = cursor.fetchone()
                if meaning is None:
                    cursor.execute(
                        'INSERT INTO chats (id_chat, id_user, first_name, last_name, username, '
                        'messages, characters, deleted, date_of_the_last_message) '
                        f'VALUES ({id_chat}, {i.id}, "{i.first_name}", "{i_last_name}", '
                        f'"{i_username}", 0, 0, False, "{date_of_the_last_message}")')
                else:
                    cursor.execute(
                        f'UPDATE chats SET deleted = False WHERE id_chat = {id_chat} AND id_user = {i.id}')

                connect.commit()

        return

    elif message.content_type == 'left_chat_member':
        i = message.left_chat_member
        if i.is_bot:
            if i.username == THIS_IS_BOT_NAME:
                cursor.execute(f'UPDATE settings SET enable_group = False WHERE id_chat = {id_chat}')
        else:
            cursor.execute(f'UPDATE chats SET deleted = True, date_of_the_last_message = "{date_of_the_last_message}" '
                           f'WHERE id_chat = {id_chat} AND id_user = {i.id}')

        connect.commit()

        return

    id_user = message.from_user.id
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    if last_name is None:
        last_name = ''
    username = message.from_user.username
    if username is None:
        username = ''
    characters = 0

    message_id = 0
    if message.content_type == 'text':
        if message.from_user.is_bot:
            return
        characters = len(message.text)
        if message.text.find('@' + THIS_IS_BOT_NAME) > 0:
            try:
                chat_admins = await bot.get_chat_administrators(id_chat)
                if its_admin(id_user, chat_admins):
                    message_id = message.message_id
                    cursor.execute(f'SELECT id_user, first_name, last_name, username FROM chats WHERE id_chat = {id_chat} AND deleted = 0')
                    result = cursor.fetchall()
                    text = 'Внимание\! Общий опрос\: \n'
                    for i in result:
                        i_id_user = i[0]
                        i_first_name = i[1]
                        i_last_name = i[2]
                        i_username = i[3]
                        name_user = shielding(i_first_name + ' ' + i_last_name).strip()
                        user = f'[{name_user}](tg://user?id={i_id_user})'
                        if not i_username == '':
                            user += f' \(@{shielding(i_username)}\)'
                        text += user + '\n'
                    text += 'Чтобы ваш ответ был учтен, необходимо ответить на сообщение куратора, т\.е\. нажать на сообщение куратора и выбрать \"Ответить\"\.'
                    text += '\n \#ВажноеСообщение'
                    await message.reply(text, parse_mode='MarkdownV2', disable_notification=True)
                    cursor.execute(f'UPDATE settings SET last_notify_message_id_date = datetime("now") WHERE id_chat = {id_chat}')
                    connect.commit()
            except Exception:
                pass
        if message.reply_to_message is not None:
            autor_id_user = message.from_user.id
            autor_message_id = message.reply_to_message.message_id
            cursor.execute(f'SELECT * FROM messages WHERE id_chat = {id_chat} AND id_user = {autor_id_user} AND message_id = {autor_message_id}')
            meaning = cursor.fetchone()
            if meaning is not None:
                message_id = autor_message_id
    elif message.content_type == 'photo' and message.caption is not None:
        characters = len(message.caption)
    elif message.content_type == 'poll':
        characters = len(message.poll.question)
        for i in message.poll.options:
            characters += len(i.text)

    if message.from_user.is_bot:
        return

    cursor.execute('INSERT INTO messages (id_chat, id_user, date, characters, message_id) '
                   f'VALUES ({id_chat}, {id_user}, "{date_of_the_last_message}", {characters}, {message_id})')
    connect.commit()

    cursor.execute(f'SELECT * FROM chats WHERE id_chat = {id_chat} AND id_user = {id_user}')
    meaning = cursor.fetchone()

    if meaning is None:
        cursor.execute(
            f'INSERT INTO chats (id_chat, id_user, first_name, last_name, '
            f'username, messages, characters, deleted, date_of_the_last_message) '
            f'VALUES ({id_chat}, {id_user}, "{first_name}", "{last_name}", '
            f'"{username}", 1, {characters}, False, "{date_of_the_last_message}")')
    else:
        cursor.execute('UPDATE chats SET '
                       'messages = messages + 1, '
                       f'characters = characters + {characters}, '
                       f'first_name = "{first_name}", '
                       f'last_name = "{last_name}", '
                       f'username = "{username}", '
                       f'deleted = False, '
                       f'date_of_the_last_message = "{date_of_the_last_message}" '
                       f'WHERE id_chat = {id_chat} AND id_user = {id_user}')
    connect.commit()


executor.start_polling(dp, skip_updates=False, on_startup=on_startup)
