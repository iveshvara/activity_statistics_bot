
import traceback
import datetime

from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from bot_base import bot, base, send_error


async def callback_edit_text(callback: CallbackQuery, text, inline_kb):
    await message_edit_text(callback.message, text, inline_kb)


async def callback_answer(callback: CallbackQuery):
    try:
        await callback.answer()
    except Exception as e:
        pass


async def message_edit_text(message: Message, text, inline_kb):
    if message.md_text == text and message.reply_markup == inline_kb:
        return
    try:
        await message.edit_text(
            text,
            parse_mode='MarkdownV2',
            reply_markup=inline_kb,
            disable_web_page_preview=True)
    except Exception as e:
        await send_error(str(message.chat), str(e), traceback.format_exc())
        await send_error(inline_kb, str(e), traceback.format_exc())


async def message_answer(message: Message, text, incoming_inline_kb=None):
    if incoming_inline_kb is None:
        inline_kb = InlineKeyboardMarkup(row_width=1)
    else:
        inline_kb = incoming_inline_kb

    try:
        new_message = await message.answer(
            text=text,
            parse_mode='MarkdownV2',
            reply_markup=inline_kb,
            disable_web_page_preview=True,
            disable_notification=False,
            protect_content=False)

        if incoming_inline_kb is not None:
            await base.save_menu_message_id(new_message)

    except Exception as e:
        await send_error(text, str(e), traceback.format_exc())
        await send_error(inline_kb, str(e), traceback.format_exc())


async def message_send(id_user, text, incoming_inline_kb=None, disable_notification=False):
    if incoming_inline_kb is None:
        inline_kb = InlineKeyboardMarkup(row_width=1)
    else:
        inline_kb = incoming_inline_kb

    try:
        new_message = await bot.send_message(
            chat_id=id_user,
            text=text,
            parse_mode='MarkdownV2',
            reply_markup=inline_kb,
            disable_web_page_preview=True,
            disable_notification=disable_notification,
            protect_content=False)

        if incoming_inline_kb is not None:
            await base.save_menu_message_id(new_message)

        return new_message

    except Exception as e:
        await send_error(id_user, str(e), traceback.format_exc())


async def message_delete(message: Message):
    try:
        await message.delete()
    except Exception as e:
        # await send_error(str(message.chat), str(e), traceback.format_exc())
        pass


async def message_delete_by_id(id_user, message_id):
    try:
        await bot.delete_message(chat_id=id_user, message_id=message_id)
    except Exception as e:
        # await send_error('id_user: ' + str(id_user) + '\nmessage_id: ' + str(message_id), str(e), traceback.format_exc())
        pass


async def last_menu_message_delete(id_user):
    message_id = await base.get_menu_message_id(id_user)
    if message_id > 0:
        try:
            await bot.delete_message(chat_id=id_user, message_id=message_id)
        except Exception as e:
            pass


async def message_progress_bar(user_id, all_count, count, time_point, message_pb=None):
    if time_point is None:
        time_point = datetime.datetime.now()
    delta = datetime.datetime.now() - time_point

    inline_kb = InlineKeyboardMarkup(row_width=1)
    inline_kb.add(InlineKeyboardButton(text='-', callback_data='-'))

    if message_pb is None:
        message_pb = await message_send(user_id, f'Отправка сообщений {count} из {all_count}', inline_kb)

    if delta.seconds > 1:
        text_report = f'Отправка сообщений {count} из {all_count}'
        await message_edit_text(message_pb, text_report, inline_kb)
        time_point = datetime.datetime.now()

    return message_pb, time_point


async def get_text_homework(project_id, homework_id, id_user, status):
    page_number = status[4:]
    if page_number == '':
        page_number = 0
    else:
        page_number = int(status[4:])

    array_text = await base.get_homeworks_task(project_id, homework_id, id_user)
    number_of_pages = len(array_text)
    page_number = min(number_of_pages - 1, page_number)

    text = array_text[page_number]

    return text, number_of_pages, page_number