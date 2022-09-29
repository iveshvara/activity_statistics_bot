
from utils import on_startup, on_shutdown
from bot import dp
import handlers

from aiogram.utils import executor


executor.start_polling(dp, skip_updates=False, on_startup=on_startup, on_shutdown=on_shutdown)
