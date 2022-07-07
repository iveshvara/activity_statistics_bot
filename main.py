from aiogram import Bot
from aiogram.dispatcher import Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
from aiogram import types
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from settings import TOKEN
import sqlite3
import datetime
# import asyncio
# import aioschedule

bot = Bot(TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

connect = sqlite3.connect('base.db')
cursor = connect.cursor()


async def on_startup(_):
    connect.execute('CREATE TABLE IF NOT EXISTS chats('
                    'id_chat INTEGER, '
                    'id_user INTEGER, '
                    'first_name TEXT, '
                    'username TEXT, '
                    'characters INTEGER, '
                    'messages INTEGER, '
                    'date_of_the_last_message TEXT, '
                    'deleted BLOB)')
    connect.execute('CREATE TABLE IF NOT EXISTS settings('
                    'id_chat INTEGER, '
                    'title TEXT, '
                    'include_admins_in_statistics BLOB, '
                    'sort_by_messages BLOB, '
                    'do_not_output_the_number_of_messages BLOB, '
                    'do_not_output_the_number_of_characters BLOB, '
                    'days_without_activity_is_bad INTEGER, '
                    'report_enabled BLOB, '
                    'report_every_week BLOB, '
                    'report_time TEXT)')
    connect.commit()


@dp.message_handler(commands=['start'])
async def command_start(message: Message):
    text, inline_kb, one_group = await get_start_menu(message.from_user.id)

    if one_group is None:
        await message.answer(text, parse_mode='MarkdownV2', reply_markup=inline_kb)
    else:
        await setting_up_a_chat(message, one_group)


async def get_start_menu(id_user):
    cursor.execute('SELECT DISTINCT chats.id_chat, settings.title FROM chats '
                   'LEFT OUTER JOIN settings ON chats.id_chat = settings.id_chat '
                   f'WHERE id_user = {id_user}')
    meaning = cursor.fetchall()
    user_groups = []
    for i in meaning:
        try:
            member = await bot.get_chat_member(i[0],  id_user)
            if member.is_chat_admin():
                user_groups.append([i[0], i[1]])
        except Exception:
            pass

    text = ''
    inline_kb = InlineKeyboardMarkup(row_width=1)
    one_group = None

    if len(user_groups) == 0:
        text = 'Для начала работы, необходимо добавить бота в группу, где вы являетесь основателем.'
    elif len(user_groups) == 1:
        one_group = user_groups[0]
    else:
        text = 'Выберете группу для настройки:'
        for i in user_groups:
            inline_kb.add(InlineKeyboardButton(text=i[1], callback_data=f'id_chat {i[0]}'))

    return text, inline_kb, one_group


@dp.callback_query_handler(text='back')
async def choosing_a_chat_to_set_up(callback: CallbackQuery):
    text, inline_kb, one_group = await get_start_menu(callback.from_user.id)

    if one_group is None:
        await callback.message.edit_text(text, parse_mode='MarkdownV2', reply_markup=inline_kb)
    else:
        await setting_up_a_chat(callback.message, one_group)


@dp.callback_query_handler(lambda x: x.data and x.data.startswith('id_chat '))
async def choosing_a_chat_to_set_up(callback: CallbackQuery):
    id_chat = int(callback.data.replace('id_chat ', ''))
    await setting_up_a_chat(callback.message, id_chat)


async def setting_up_a_chat(message: Message, id_chat):
    cursor.execute(f'SELECT * FROM settings WHERE id_chat = {id_chat}')
    meaning = cursor.fetchone()

    if meaning is None:
        return

    inline_kb = InlineKeyboardMarkup(row_width=1)
    inline_kb.add(InlineKeyboardButton(text='Включать админов в статистику: ' + convert_bool(meaning[2]), callback_data=f'settings {id_chat} include_admins_in_statistics {meaning[2]}'))
    if meaning[3]:
        inline_kb.add(InlineKeyboardButton(text='Сортировка по сообщениям', callback_data=f'settings {id_chat} sort_by_messages {meaning[3]}'))
    else:
        inline_kb.add(InlineKeyboardButton(text='Сортировка по количеству символов', callback_data=f'settings {id_chat} sort_by_messages {meaning[3]}'))
    inline_kb.add(InlineKeyboardButton(text='Не выводить количество сообщений: ' + convert_bool(meaning[4]), callback_data=f'settings {id_chat} do_not_output_the_number_of_messages {meaning[4]}'))
    inline_kb.add(InlineKeyboardButton(text='Не выводить количество символов: ' + convert_bool(meaning[5]), callback_data=f'settings {id_chat} do_not_output_the_number_of_characters {meaning[5]}'))
    # inline_kb.add(InlineKeyboardButton(text='Отмечать после количества дней без активности: ' + str(meaning[6]), callback_data=f'settings {id_chat} days_without_activity_is_bad {meaning[6]}'))
    # inline_kb.add(InlineKeyboardButton(text='Автоматический отчет в чат: ' + convert_bool(meaning[7]), callback_data=f'settings {id_chat} report_enabled {meaning[7]}'))
    # if meaning[8]:
    #     inline_kb.add(InlineKeyboardButton(text='Отчет каждую неделю', callback_data=f'settings {id_chat} report_every_week {meaning[8]}'))
    # else:
    #     inline_kb.add(InlineKeyboardButton(text='Отчет каждый день', callback_data=f'settings {id_chat} report_every_week {meaning[8]}'))
    # inline_kb.add(InlineKeyboardButton(text='Время отправки отчета: ' + meaning[9], callback_data=f'settings {id_chat} report_time {meaning[9]}'))

    inline_kb.add(InlineKeyboardButton(text='Назад', callback_data='back'))

    await message.edit_text('Параметры "' + meaning[1] + '":', reply_markup=inline_kb)


def convert_bool(value):
    if value == True or value == 1:
        return 'Да'
    else:
        return 'Нет'


@dp.callback_query_handler(lambda x: x.data and x.data.startswith('settings '))
async def process_parameter(callback: CallbackQuery):
    list_str = callback.data.split()
    id_chat = int(list_str[1])
    parameter_name = list_str[2]
    parameter_value = list_str[3]

    no_blob_parameters = ['days_without_activity_is_bad', 'report_time']
    if parameter_name in no_blob_parameters:
        await process_parameter_input(callback, id_chat, parameter_name, parameter_value)
    else:
        if parameter_value == '0':
            parameter_value = '1'
        else:
            parameter_value = '0'
        await process_parameter_continuation(callback, id_chat, parameter_name, parameter_value)


async def process_parameter_input(callback: CallbackQuery, id_chat, parameter_name, parameter_value):
    inline_kb = InlineKeyboardMarkup(row_width=1)
    inline_kb.add(InlineKeyboardButton(text='Назад', callback_data='back'))

    await callback.message.edit_text(f'Текущее значение параметра {parameter_name} = "{parameter_value}". Введите новое значение:', reply_markup=inline_kb)


async def process_parameter_continuation(callback: CallbackQuery, id_chat, parameter_name, parameter_value):
    cursor.execute(f'UPDATE settings SET {parameter_name} = {parameter_value} WHERE id_chat = {id_chat}')
    connect.commit()

    await setting_up_a_chat(callback.message, id_chat)


@dp.message_handler(commands=['get_stat'])
async def command_start(message: Message):
    await get_stat(message)


async def get_stat(message: Message):
    id_chat = message.chat.id

    include_admins_in_statistics = False
    chat_admins = await bot.get_chat_administrators(id_chat)
    days_without_activity_is_bad = 0
    sort_by_messages = False
    do_not_output_the_number_of_messages = False
    do_not_output_the_number_of_characters = False

    cursor.execute(f'SELECT * FROM settings WHERE id_chat = {id_chat}')
    meaning = cursor.fetchone()
    if meaning is not None:
        if meaning[2]:
            include_admins_in_statistics = True
        days_without_activity_is_bad = meaning[6]
        sort_by_messages = meaning[3]
        do_not_output_the_number_of_messages = meaning[4]
        do_not_output_the_number_of_characters = meaning[5]

    text = ''
    count_messages = 0
    # cursor.execute(f'SELECT * FROM chats WHERE id_chat = {id_chat} ORDER BY characters DESC')
    cursor.execute(f'SELECT *, CASE '
                   f'WHEN {days_without_activity_is_bad} > ROUND(julianday("now") - julianday(chats.date_of_the_last_message), 0) ' 
                   'THEN 0 ' 
                   'ELSE ROUND(julianday("now") - julianday(chats.date_of_the_last_message), 0) '
                   'END AS inactive_days '
                   f'FROM chats WHERE id_chat = {id_chat} ORDER BY inactive_days ASC, characters DESC')
    meaning = cursor.fetchall()

    inscription_is_shown = False
    for i in meaning:
        if not include_admins_in_statistics:
            its_admin = False
            for ii in chat_admins:
                if ii.user.id == i[1]:
                    its_admin = True
                    break
            if its_admin:
                continue

        if i[8] > 0 and not inscription_is_shown:
            inscription_is_shown = True
            text = 'Активные участники:\n' + text
            text += f'\nНеактивные участники \(больше {days_without_activity_is_bad} дней\):\n'  # 😴

        count_messages += 1

        specifics = ''
        characters = ''
        messages = ''
        if not do_not_output_the_number_of_messages:
            messages = f'сообщений: {i[5]}'
        if not do_not_output_the_number_of_characters:
            characters = f'символов: {i[4]}'

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
            specifics = ': ' + specifics

        inactive = ''
        if i[8] > 0:
            inactive = f' \(неактивен: {int(i[8])} дней\)'

        text += f'{count_messages}\. [{i[3]}](tg://user?id={i[2]}){inactive}{specifics}\. \n'

    if text == '':
        text = 'Нет статистики для отображения\.'

    await message.answer(text, parse_mode='MarkdownV2', disable_notification=True)


@dp.message_handler(content_types=['any'])
async def message_handler(message):
    id_chat = message.chat.id
    title = message.chat.title
    id_user = message.from_user.id
    first_name = message.from_user.first_name
    characters = 0
    username = message.from_user.username
    if username is None:
        username = ''
    date_of_the_last_message = message.date # .strftime("%d.%m.%Y %H:%M:%S")
    if message.content_type == 'text':
        if message.from_user.is_bot:
            return
        characters = len(message.text)
    elif message.content_type == 'photo':
        characters = len(message.caption)
    elif message.content_type == 'poll':
        characters = len(message.poll.question)
        for i in message.poll.options:
            characters += len(i.text)

    if message.content_type == 'new_chat_members':
        for i in message.new_chat_members:
            cursor.execute('INSERT INTO chats (id_chat, id_user, first_name, username, messages, characters, deleted, date_of_the_last_message) '
                           f'VALUES ({id_chat}, {i.id}, "{i.first_name}", "{i.username}", 0, 0, False, "{date_of_the_last_message}")')

    cursor.execute(f'SELECT * FROM chats WHERE id_chat = {id_chat} AND id_user = {id_user}')
    meaning = cursor.fetchone()

    if meaning is None:
        cursor.execute(
            f'INSERT INTO chats (id_chat, id_user, first_name, username, messages, characters, deleted, date_of_the_last_message) '
            f'VALUES ({id_chat}, {id_user}, "{first_name}", "{username}", 1, {characters}, False, "{date_of_the_last_message}")')
    else:
        cursor.execute('UPDATE chats SET '
                       'messages = messages + 1, '
                       f'characters = characters + {characters}, '
                       f'first_name = "{first_name}", '
                       f'username = "{username}", '
                       f'deleted = False, '
                       f'date_of_the_last_message = "{date_of_the_last_message}" '
                       f'WHERE id_chat = {id_chat} AND id_user = {id_user}')
    connect.commit()

    cursor.execute(f'SELECT * FROM settings WHERE id_chat = {id_chat}')
    meaning = cursor.fetchone()

    if meaning is None:
        cursor.execute(
            'INSERT INTO settings ('
            'id_chat, '
            'title, '
            'include_admins_in_statistics, '
            'sort_by_messages, '
            'do_not_output_the_number_of_messages, '
            'do_not_output_the_number_of_characters, '
            'days_without_activity_is_bad, '
            'report_enabled, '
            'report_every_week, '
            'report_time) '
            f'VALUES ({id_chat}, "{title}", False, False, False, False, 7, False, False, "00:00")')
        connect.commit()
    else:
        cursor.execute(f'UPDATE chats SET title = "{title}" WHERE id_chat = {id_chat}')
    connect.commit()


executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
