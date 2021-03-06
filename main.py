from aiogram import Bot
from aiogram.dispatcher import Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from settings import TOKEN, SUPER_ADMIN_ID
import sqlite3
from datetime import datetime

bot = Bot(TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

connect = sqlite3.connect('base.db')
cursor = connect.cursor()


async def on_startup(_):
    connect.execute(
        'CREATE TABLE IF NOT EXISTS chats(id_chat INTEGER, id_user INTEGER, first_name TEXT, last_name TEXT, '
        'username TEXT, characters INTEGER, messages INTEGER, date_of_the_last_message TEXT, deleted BLOB)')
    connect.execute(
        'CREATE TABLE IF NOT EXISTS messages(id_chat INTEGER, id_user INTEGER, date TEXT, characters INTEGER)')
    connect.execute(
        'CREATE TABLE IF NOT EXISTS settings(id_chat INTEGER, title TEXT, statistics_for_everyone BLOB, '
        'include_admins_in_statistics BLOB, sort_by_messages BLOB, do_not_output_the_number_of_messages BLOB, '
        'do_not_output_the_number_of_characters BLOB, period_of_activity INTEGER, report_enabled BLOB, '
        'report_every_week BLOB, report_time TEXT)')
    connect.execute(
        'CREATE TABLE IF NOT EXISTS meetings(id_chat INTEGER, id_user INTEGER, day TEXT,'
        '_00 BLOB, _01 BLOB, _02 BLOB, _03 BLOB, _04 BLOB, _05 BLOB, _06 BLOB, _07 BLOB, _08 BLOB, _09 BLOB, _10 BLOB, _11 BLOB, '
        '_12 BLOB, _13 BLOB, _14 BLOB, _15 BLOB, _16 BLOB, _17 BLOB, _18 BLOB, _19 BLOB, _20 BLOB, _21 BLOB, _22 BLOB, _23 BLOB)')
    connect.commit()


def its_admin(id_user, chat_admins):
    if id_user == SUPER_ADMIN_ID:
        return True

    for ii in chat_admins:
        if ii.user.id == id_user:
            return True

    return False


async def get_stat(id_chat, id_user, use_username):
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

    if statistics_for_everyone or its_admin(id_user, chat_admins):
        text = '*???????????????? ??????????????????:*\n'
        # text = ''
        # messages = ''
        # characters = ''
        # if not do_not_output_the_number_of_messages:
        #     messages = '??????????????????'
        # if not do_not_output_the_number_of_characters:
        #     characters = '????????????????'
        #
        if sort_by_messages:
            sort = 'messages'
        #     text += messages
        #     if not characters == '' and not text == '':
        #         text += ', '
        #     text += characters
        else:
            sort = 'characters'
        #     text += characters
        #     if not messages == '' and not text == '':
        #         text += ', '
        #     text += messages
        #
        # text = '???????????????? ?????????????????? \(' + text + '\):\n'

        count_messages = 0
        cursor.execute(
            # f'SELECT *, CASE '
            # f'WHEN NOT chats.deleted AND {period_of_activity} > ROUND(julianday("now") - julianday(chats.date_of_the_last_message), 0) '
            # 'THEN 0 '
            # 'ELSE ROUND(julianday("now") - julianday(chats.date_of_the_last_message), 0) '
            # 'END AS inactive_days '
            # f'FROM chats WHERE id_chat = {id_chat} AND {period_of_activity} ORDER BY deleted ASC, inactive_days ASC, {sort} DESC'
            'SELECT chats.id_user, chats.first_name, chats.last_name, chats.username, '
            'SUM(IFNULL(messages.characters, 0)) AS characters, SUM(1) AS messages, '
            'chats.deleted, chats.date_of_the_last_message, '
                f'CASE WHEN NOT chats.deleted AND {period_of_activity} > ROUND(julianday("now") - julianday(chats.date_of_the_last_message), 0) THEN 0 '
                'ELSE ROUND(julianday("now") - julianday(chats.date_of_the_last_message), 0) END AS inactive_days '
            'FROM chats '
            'LEFT JOIN messages ON chats.id_chat = messages.id_chat AND chats.id_user = messages.id_user '
            f'WHERE chats.id_chat = {id_chat} AND {period_of_activity} > ROUND(julianday("now") - julianday(messages.date), 0) '
            'GROUP BY chats.id_chat, chats.id_user, chats.first_name, chats.last_name, chats.username, chats.date_of_the_last_message, chats.deleted '
            f'ORDER BY deleted ASC, inactive_days ASC, {sort} DESC '
        )
        meaning = cursor.fetchall()

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

            if not include_admins_in_statistics:
                if its_admin(i_id_user, chat_admins):
                    continue

            if i_inactive_days > 0 and i_deleted == 0 and not active_members_inscription_is_shown:
                active_members_inscription_is_shown = True
                text += f'\n\n*???????????????????? ??????????????????* \(???????????? {period_of_activity} ????????\):\n'

            if i_deleted == 1 and not deleted_members_inscription_is_shown:
                deleted_members_inscription_is_shown = True
                text += f'\n\n*???????????????? ??????????????????:*\n'

            count_messages += 1

            specifics = ''
            characters = ''
            messages = ''
            if not do_not_output_the_number_of_messages:
                messages = f'??????????????????: {i_messages}'
            if not do_not_output_the_number_of_characters:
                characters = f'????????????????: {i_characters}'

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
                specifics += '\.'
                specifics = ':\n' + specifics

            inactive = ''
            if i_deleted == 1:
                data_str = shielding(datetime.strptime(i_date_of_the_last_message, '%Y-%m-%d %H:%M:%S').strftime("%d.%m.%Y"))#"%d.%m.%Y %H:%M:%S"
                inactive = f' \(?????? ???????? ?? {data_str}, ???????? ??????????: {int(i_inactive_days)}\)\n'
            elif i_inactive_days > 0:
                inactive = f' \(?????????????????? ????????: {int(i_inactive_days)}\)\n'

            name_user = shielding(i_first_name + ' ' + i_last_name).strip()
            # if use_username and not i_username == '':
            #     # user = '@' + i_username
            #     user = f'[{name_user}](http://t.me/{i_username})'
            # else:
            #     user = f'[{name_user}](tg://user?id={i_id_user})'
            # ???????? ???????????? ????????????????????, ???? ?????????? ?????????????????????? ???????? ????????????????
            user = f'[{name_user}](tg://user?id={i_id_user})'
            if not i_username == '':
                user += f' \(@{shielding(i_username)}\)'
            text += f'\n{count_messages}\. {user}{inactive}{specifics}\n'

        if text == '*???????????????? ??????????????????:*\n':
            text = '?????? ???????????????????? ?????? ??????????????????????\.'

    else:
        text = '???????????????????? ?????????? ???????????????? ???????????? ???????????????????????????? ????????????.'

    return text


async def get_start_menu(id_user):
    this_is_super_admin = id_user == SUPER_ADMIN_ID
    if this_is_super_admin:
        piece = ''
    else:
        piece = f' WHERE id_user = {id_user}'
    cursor.execute('SELECT DISTINCT chats.id_chat, settings.title FROM chats '
                   'LEFT OUTER JOIN settings ON chats.id_chat = settings.id_chat' + piece)
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
        text = '?????? ???????????? ????????????, ???????????????????? ???????????????? ???????? ?? ????????????, ?????? ???? ?????????????????? ??????????????????????????????\.'
    elif len(user_groups) == 1:
        one_group = user_groups[0][0]
    else:
        text = '???????????????? ???????????? ?????? ??????????????????:'
        for i in user_groups:
            inline_kb.add(InlineKeyboardButton(text=i[1], callback_data=f'id_chat {i[0]}'))

    return text, inline_kb, one_group


async def setting_up_a_chat(id_chat, id_user, back_button=True):
    cursor.execute(f'SELECT * FROM settings WHERE id_chat = {id_chat}')
    meaning = cursor.fetchone()

    if meaning is None:
        return

    inline_kb = InlineKeyboardMarkup(row_width=1)
    if meaning[2]:
        inline_kb.add(InlineKeyboardButton(text='???????????????????? ???????????????? ????????', callback_data=f'settings {id_chat} statistics_for_everyone {meaning[2]}'))
    else:
        inline_kb.add(InlineKeyboardButton(text='???????????????????? ???????????????? ???????????? ??????????????????????????????', callback_data=f'settings {id_chat} statistics_for_everyone {meaning[2]}'))
    inline_kb.add(InlineKeyboardButton(text='???????????????? ?????????????? ?? ????????????????????: ' + convert_bool(meaning[3]), callback_data=f'settings {id_chat} include_admins_in_statistics {meaning[3]}'))
    if meaning[4]:
        inline_kb.add(InlineKeyboardButton(text='???????????????????? ???? ????????????????????', callback_data=f'settings {id_chat} sort_by_messages {meaning[4]}'))
    else:
        inline_kb.add(InlineKeyboardButton(text='???????????????????? ???? ???????????????????? ????????????????', callback_data=f'settings {id_chat} sort_by_messages {meaning[4]}'))
    inline_kb.add(InlineKeyboardButton(text='???? ???????????????? ???????????????????? ??????????????????: ' + convert_bool(meaning[5]), callback_data=f'settings {id_chat} do_not_output_the_number_of_messages {meaning[5]}'))
    inline_kb.add(InlineKeyboardButton(text='???? ???????????????? ???????????????????? ????????????????: ' + convert_bool(meaning[6]), callback_data=f'settings {id_chat} do_not_output_the_number_of_characters {meaning[6]}'))
    inline_kb.add(InlineKeyboardButton(text='???????????????????? ???? ???????????? (????????): ' + str(meaning[7]), callback_data=f'settings {id_chat} period_of_activity {meaning[7]}'))
    # inline_kb.add(InlineKeyboardButton(text='???????????????????????????? ?????????? ?? ??????: ' + convert_bool(meaning[7]), callback_data=f'settings {id_chat} report_enabled {meaning[8]}'))
    # if meaning[9]:
    #     inline_kb.add(InlineKeyboardButton(text='?????????? ???????????? ????????????', callback_data=f'settings {id_chat} report_every_week {meaning[9]}'))
    # else:
    #     inline_kb.add(InlineKeyboardButton(text='?????????? ???????????? ????????', callback_data=f'settings {id_chat} report_every_week {meaning[9]}'))
    # inline_kb.add(InlineKeyboardButton(text='?????????? ???????????????? ????????????: ' + meaning[9], callback_data=f'settings {id_chat} report_time {meaning[10]}'))

    if back_button:
        inline_kb.add(InlineKeyboardButton(text='??????????', callback_data='back'))

    text = await get_stat(id_chat, id_user, True)
    #group_name = shielding(meaning[1])
    group_name = meaning[1]
    return '*???????????? "' + group_name + '"\.*\n\n' + text, inline_kb


async def process_parameter_input(callback: CallbackQuery, id_chat, parameter_name, parameter_value):
    inline_kb = InlineKeyboardMarkup(row_width=1)
    inline_kb.add(InlineKeyboardButton(text='??????????', callback_data='back'))

    await callback.message.edit_text(
        f'?????????????? ???????????????? ?????????????????? {parameter_name} = "{parameter_value}". ?????????????? ?????????? ????????????????:',
        parse_mode='MarkdownV2',
        reply_markup=inline_kb)


async def process_parameter_continuation(callback: CallbackQuery, id_chat, id_user, parameter_name, parameter_value):
    cursor.execute(f'UPDATE settings SET {parameter_name} = {parameter_value} WHERE id_chat = {id_chat}')
    connect.commit()

    text, inline_kb = await setting_up_a_chat(id_chat, id_user)
    await callback.message.edit_text(text, parse_mode='MarkdownV2', reply_markup=inline_kb)


def convert_bool(value):
    if value == True or value == 1:
        return '????'
    else:
        return '??????'


def shielding(text):
    text_result = ''
    # allowed_simbols = ' ,:;???'
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
            await message.answer('?????? ?????????????? ???????????????? ?? ????????????. ?????????? ?????????????????????? ?????????????? /start')
        return

    await message_handler(message)

    id_chat = message.chat.id
    id_user = message.from_user.id
    text = await get_stat(id_chat, id_user, False)

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
            await message.answer('?????? ?????????????? ?????????? ?????????????? ???????????? ?????????? ????????????.')
            return
    else:
        if message.chat.type == 'private':
            await message.answer('?????? ?????????????? ???????????????? ?? ????????????. ?????????? ?????????????????????? ?????????????? /start')
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
        for ii in ['????', '????', '????', '????', '????', '????', '????']:
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

    week = ['????', '????', '????', '????', '????', '????', '????']
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
    title = "'" + shielding(message.chat.title) + "'"

    id_user = message.from_user.id
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    if last_name is None:
        last_name = ''
    username = message.from_user.username
    if username is None:
        username = ''
    characters = 0
    date_of_the_last_message = message.date

    if len(message.entities) == 1 and message.entities[0].type == 'bot_command':
        pass
    elif message.content_type == 'text':
        if message.from_user.is_bot:
            return
        characters = len(message.text)
    elif message.content_type == 'photo' and message.caption is not None:
        characters = len(message.caption)
    elif message.content_type == 'poll':
        characters = len(message.poll.question)
        for i in message.poll.options:
            characters += len(i.text)

    if message.content_type == 'new_chat_members':
        for i in message.new_chat_members:
            if i.is_bot:
                continue

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
    elif message.content_type == 'left_chat_member':
        i = message.left_chat_member
        if not i.is_bot:
            cursor.execute(f'SELECT * FROM chats WHERE id_chat = {id_chat} AND id_user = {i.id}')
            meaning = cursor.fetchone()
            if meaning is not None:
                cursor.execute(f'UPDATE chats SET deleted = True, date_of_the_last_message = "{date_of_the_last_message}" '
                               f'WHERE id_chat = {id_chat} AND id_user = {i.id}')
            connect.commit()

    if message.from_user.is_bot:
        return

    cursor.execute('INSERT INTO messages (id_chat, id_user, date, characters) '
                   f'VALUES ({id_chat}, {id_user}, "{date_of_the_last_message}", {characters})')
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

    cursor.execute(f'SELECT * FROM settings WHERE id_chat = {id_chat}')
    meaning = cursor.fetchone()

    if meaning is None:
        cursor.execute(
            'INSERT INTO settings (id_chat, title, statistics_for_everyone, include_admins_in_statistics, '
            'sort_by_messages, do_not_output_the_number_of_messages, do_not_output_the_number_of_characters, '
            'period_of_activity, report_enabled, report_every_week, report_time) ' 
            f'VALUES ({id_chat}, {title}, False, False, False, False, False, 7, False, False, "00:00")')
        connect.commit()
    else:
        cursor.execute(f'UPDATE settings SET title = {title} WHERE id_chat = {id_chat}')
    connect.commit()


executor.start_polling(dp, skip_updates=False, on_startup=on_startup)
