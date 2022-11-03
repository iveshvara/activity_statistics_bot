
from bot_base import dp
from aiogram.utils import executor
import logging
import asyncio
import aioschedule
from main_functions import run_reminder
import handlers

logging.basicConfig(level=logging.INFO)


async def on_startup(_):
    # dp.middleware.setup(LoggingMiddleware())
    asyncio.create_task(scheduler())


async def scheduler():
    aioschedule.every().monday.at("00:00").do(run_reminder)
    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(1)


async def on_shutdown(_):
    pass


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=False, on_startup=on_startup, on_shutdown=on_shutdown)
