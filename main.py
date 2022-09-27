
from utils import on_startup
from bot import dp
import handlers

from aiogram.utils import executor


executor.start_polling(dp, skip_updates=False, on_startup=on_startup)
