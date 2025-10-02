from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery

from bot_config import texts
from utils.schedule import schedule_regular

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.delete()
    await message.answer(texts.get('start'))
    await schedule_regular(message.from_user.id, "08:00")


