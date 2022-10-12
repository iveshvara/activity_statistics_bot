
from utils import on_startup, on_shutdown
from bot import dp
from aiogram.utils import executor
import handlers
import logging

logging.basicConfig(level=logging.INFO)


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=False, on_startup=on_startup, on_shutdown=on_shutdown)
