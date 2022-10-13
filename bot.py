
from _settings import TOKEN

from aiogram import Bot
from aiogram.dispatcher import Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
# from aiogram.contrib.middlewares.logging import LoggingMiddleware

import sqlite3


bot = Bot(TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())
# dp.middleware.setup(LoggingMiddleware())

connect = sqlite3.connect('base.db')
cursor = connect.cursor()
