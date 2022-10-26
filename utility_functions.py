
from bot_base import bot, cursor, connect, base, send_error
from service import convert_bool, convert_bool_binary, shielding
from main_functions import get_stat
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
import traceback


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
        await send_error(str(message.from_user), str(e), traceback.format_exc())


async def message_answer(message: Message, text, incoming_inline_kb=None):
    if incoming_inline_kb is None:
        inline_kb = InlineKeyboardMarkup(row_width=1)
    else:
        inline_kb = incoming_inline_kb

    try:
        new_message = await message.answer(
            text,
            parse_mode='MarkdownV2',
            reply_markup=inline_kb,
            disable_web_page_preview=True,
            disable_notification=False,
            protect_content=False)

        if incoming_inline_kb is not None:
            await base.save_menu_message_id(new_message)

    except Exception as e:
        await send_error('', str(e), traceback.format_exc())


async def message_delete(message: Message):
    try:
        await message.delete()
    except Exception as e:
        await send_error('', str(e), traceback.format_exc())


async def last_menu_message_delete(id_user):
    message_id = await base.get_menu_message_id(id_user)
    if message_id > 0:
        try:
            await bot.delete_message(chat_id=id_user, message_id=message_id)
        except Exception as e:
            pass


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
            settings.sort_by_messages,
            settings.do_not_output_the_number_of_messages,
            settings.do_not_output_the_number_of_characters,
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

    inline_kb = InlineKeyboardMarkup(row_width=1)
    if meaning[0]:
        text='Статистика доступна всем'
    else:
        text='Статистика доступна только администраторам'
    inline_kb.add(InlineKeyboardButton(
        text=text,
        callback_data=f'settings {id_chat} statistics_for_everyone {convert_bool_binary(meaning[0])}'))

    inline_kb.add(InlineKeyboardButton(
        text='Включать админов в статистику: ' + convert_bool(meaning[1]),
        callback_data=f'settings {id_chat} include_admins_in_statistics {convert_bool_binary(meaning[1])}'))

    if meaning[2]:
        text='Сортировка по сообщениям'
    else:
        text = 'Сортировка по количеству символов'
    inline_kb.add(InlineKeyboardButton(
        text=text,
        callback_data=f'settings {id_chat} sort_by_messages {convert_bool_binary(meaning[2])}'))

    inline_kb.add(InlineKeyboardButton(
        text='Не выводить количество сообщений: ' + convert_bool(meaning[3]),
        callback_data=f'settings {id_chat} do_not_output_the_number_of_messages {convert_bool_binary(meaning[3])}'))

    inline_kb.add(InlineKeyboardButton(
        text='Не выводить количество символов: ' + convert_bool(meaning[4]),
        callback_data=f'settings {id_chat} do_not_output_the_number_of_characters {convert_bool_binary(meaning[4])}'))

    inline_kb.add(InlineKeyboardButton(
        text='Статистика за период (дней): ' + str(meaning[5]),
        callback_data=f'settings {id_chat} period_of_activity {meaning[5]}'))

    inline_kb.add(InlineKeyboardButton(
        text='Автоматический отчет в чат: ' + convert_bool(meaning[6]),
        callback_data=f'settings {id_chat} report_enabled {convert_bool_binary(meaning[6])}'))

    inline_kb.add(InlineKeyboardButton(
        text='Проект: ' + meaning[7],
        callback_data=f'settings {id_chat} project_name'))

    if meaning[8]:
        text='Имя и фамилия пользователя'
    else:
        text = 'Имя и фамилия из регистрации'
    inline_kb.add(InlineKeyboardButton(
        text=text,
        callback_data=f'settings {id_chat} do_not_output_name_from_registration {convert_bool_binary(meaning[8])}'))

    check_channel_subscription = meaning[9]
    check_channel_subscription_on = ''
    if check_channel_subscription:
        check_channel_subscription_on = ' ⚠️'
    inline_kb.add(InlineKeyboardButton(
        text='Проверять подписку на канал️: ' + convert_bool(meaning[9]) + check_channel_subscription_on,
        callback_data=f'settings {id_chat} check_channel_subscription {convert_bool_binary(meaning[9])}'))

    if back_button:
        inline_kb.add(InlineKeyboardButton(text='Назад', callback_data='back'))

    if super_admin:
        inline_kb.add(InlineKeyboardButton(text='Назад', callback_data='super_admin '))

    text = await get_stat(id_chat, id_user)

    group_name = shielding(meaning[10])
    return '*Группа "' + group_name + '"\.*\n\n' + text, inline_kb
