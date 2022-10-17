
from _settings import SKIP_ERROR_TEXT, THIS_IS_BOT_NAME, LOGS_CHANNEL_ID
from bot import bot, cursor, connect, base
from service import shielding, convert_bool
from main_functions import get_stat
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton


async def send_error(text, error_text):
    if error_text == SKIP_ERROR_TEXT:
        return
    text_message = f'@{THIS_IS_BOT_NAME} error\n\nQuery text:\n{text}\n\nError text:\n{error_text}'
    length_message = len(text_message)
    if length_message > 4096:
        crop_characters = length_message - 4096 - 5
        text_message = f'@{THIS_IS_BOT_NAME} error\n\nQuery text:\n{text[crop_characters]} \<\.\.\.\>\n\nError text:\n{error_text}'

    await bot.send_message(text=text_message, chat_id=LOGS_CHANNEL_ID)


async def callback_edit_text(callback: CallbackQuery, text, inline_kb):
    await message_edit_text(callback.message, text, inline_kb)


async def message_edit_text(message: Message, text, inline_kb):
    try:
        await message.edit_text(
            text,
            parse_mode='MarkdownV2',
            reply_markup=inline_kb,
            disable_web_page_preview=True)
    except Exception as e:
        await send_error(text, str(e))


async def message_answer(message: Message, text, inline_kb=None):
    if inline_kb is None:
        inline_kb = InlineKeyboardMarkup(row_width=1)

    try:
        new_message = await message.answer(
            text,
            parse_mode='MarkdownV2',
            reply_markup=inline_kb,
            disable_web_page_preview=True,
            disable_notification=False,
            protect_content=False)

        if inline_kb is not None:
            await base.save_menu_message_id(new_message)

    except Exception as e:
        await send_error(text, str(e))


async def last_menu_message_delete(id_user):
    message_id = await base.get_menu_message_id(id_user)
    if message_id > 0:
        try:
            await bot.delete_message(chat_id=id_user, message_id=message_id)
        except Exception as e:
            pass


async def process_parameter_continuation(callback: CallbackQuery, id_chat, id_user, parameter_name, parameter_value):
    cursor.execute(f'UPDATE settings SET {parameter_name} = ? WHERE id_chat = ?', (parameter_value, id_chat))
    connect.commit()

    text, inline_kb = await setting_up_a_chat(id_chat, id_user)
    await callback_edit_text(callback, text, inline_kb)


async def setting_up_a_chat(id_chat, id_user, back_button=True, super_admin=False):
    cursor.execute(
        '''SELECT 
            settings.statistics_for_everyone,
            settings.include_admins_in_statistics,
            settings.sort_by_messages,
            settings.do_not_output_the_number_of_messages,
            settings.do_not_output_the_number_of_characters,
            settings.period_of_activity,
            settings.report_enabled,
            IFNULL(projects.name, ''),
            settings.do_not_output_name_from_registration,
            settings.check_channel_subscription,
            settings.title	
        FROM settings 
            LEFT OUTER JOIN projects 
                ON settings.project_id = projects.project_id
        WHERE 
            enable_group 
            AND id_chat = ?''', (id_chat,)
    )
    meaning = cursor.fetchone()

    if meaning is None:
        return '', ''

    inline_kb = InlineKeyboardMarkup(row_width=1)
    if meaning[0]:
        inline_kb.add(InlineKeyboardButton(text='Статистика доступна всем', callback_data=f'settings {id_chat} statistics_for_everyone {meaning[0]}'))
    else:
        inline_kb.add(InlineKeyboardButton(text='Статистика доступна только администраторам', callback_data=f'settings {id_chat} statistics_for_everyone {meaning[0]}'))
    inline_kb.add(InlineKeyboardButton(text='Включать админов в статистику: ' + convert_bool(meaning[1]), callback_data=f'settings {id_chat} include_admins_in_statistics {meaning[1]}'))
    if meaning[2]:
        inline_kb.add(InlineKeyboardButton(text='Сортировка по сообщениям', callback_data=f'settings {id_chat} sort_by_messages {meaning[2]}'))
    else:
        inline_kb.add(InlineKeyboardButton(text='Сортировка по количеству символов', callback_data=f'settings {id_chat} sort_by_messages {meaning[2]}'))
    inline_kb.add(InlineKeyboardButton(text='Не выводить количество сообщений: ' + convert_bool(meaning[3]), callback_data=f'settings {id_chat} do_not_output_the_number_of_messages {meaning[3]}'))
    inline_kb.add(InlineKeyboardButton(text='Не выводить количество символов: ' + convert_bool(meaning[4]), callback_data=f'settings {id_chat} do_not_output_the_number_of_characters {meaning[4]}'))
    inline_kb.add(InlineKeyboardButton(text='Статистика за период (дней): ' + str(meaning[5]), callback_data=f'settings {id_chat} period_of_activity {meaning[5]}'))
    inline_kb.add(InlineKeyboardButton(text='Автоматический отчет в чат: ' + convert_bool(meaning[6]), callback_data=f'settings {id_chat} report_enabled {meaning[6]}'))
    inline_kb.add(InlineKeyboardButton(text='Проект: ' + meaning[7], callback_data=f'settings {id_chat} project_name'))
    if meaning[8]:
        inline_kb.add(InlineKeyboardButton(text='Имя и фамилия пользователя', callback_data=f'settings {id_chat} do_not_output_name_from_registration {meaning[8]}'))
    else:
        inline_kb.add(InlineKeyboardButton(text='Имя и фамилия из регистрации', callback_data=f'settings {id_chat} do_not_output_name_from_registration {meaning[8]}'))

    check_channel_subscription = meaning[9]
    check_channel_subscription_on = ''
    if check_channel_subscription:
        check_channel_subscription_on = ' ⚠️'
    inline_kb.add(InlineKeyboardButton(
        text='Проверять подписку на канал️: ' + convert_bool(meaning[9]) + check_channel_subscription_on,
        callback_data=f'settings {id_chat} check_channel_subscription {meaning[9]}'))

    if back_button:
        inline_kb.add(InlineKeyboardButton(text='Назад', callback_data='back'))

    if super_admin:
        inline_kb.add(InlineKeyboardButton(text='Назад', callback_data='super_admin '))

    text = await get_stat(id_chat, id_user)

    group_name = meaning[10]
    return '*Группа "' + group_name + '"\.*\n\n' + text, inline_kb


# dont use

async def process_parameter_input(callback: CallbackQuery, parameter_name, parameter_value):
    inline_kb = InlineKeyboardMarkup(row_width=1)
    inline_kb.add(InlineKeyboardButton(text='Назад', callback_data='back'))

    text = f'Текущее значение параметра {parameter_name} = "{parameter_value}". Введите новое значение:'
    text = shielding(text)
    await callback_edit_text(callback, text, inline_kb)


async def insert_or_update_chats(id_chat, id_user, first_name, last_name, username, characters,
                                 date_of_the_last_message):
    if last_name is None:
        last_name = ''

    if username is None:
        username = ''

    cursor.execute('SELECT * FROM chats WHERE id_chat = ? AND id_user = ?', (id_chat, id_user))
    meaning = cursor.fetchone()
    if meaning is None:
        text = '''INSERT INTO chats (id_chat, id_user, first_name, last_name, username, messages, characters, 
            deleted, date_of_the_last_message) VALUES (?, ?, ?, ?, ?, 1, ?, False, ?)'''
        values = (id_chat, id_user, first_name, last_name, username, characters, date_of_the_last_message)
    else:
        text = f'''UPDATE chats SET messages = messages + 1, characters = characters + ?, first_name = ?, 
            last_name = ?, username = ?, deleted = False, date_of_the_last_message = ? 
            WHERE id_chat = ? AND id_user = ?'''
        values = (characters, first_name, last_name, username, date_of_the_last_message, id_chat, id_user)

    try:
        cursor.execute(text, values)
        connect.commit()
    except Exception as e:
        await bot.send_message(text=f'@{THIS_IS_BOT_NAME} error\n\nQuery text:\n{text}\n\nError text:\n{str(e)}',
                               chat_id=LOGS_CHANNEL_ID)

