
from bot_base import bot, base, send_error
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup
import traceback


async def callback_edit_text(callback: CallbackQuery, text, inline_kb):
    await message_edit_text(callback.message, text, inline_kb)


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
        await send_error(str(message.from_user), str(e), traceback.format_exc())


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
        await send_error('', str(e), traceback.format_exc())


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
