from pathlib import Path

from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InputFile, FSInputFile

from bot_config import texts
from config import ADMIN
from utils.schedule import schedule_regular

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.delete()
    await message.answer(texts.get('start'))
    await schedule_regular(message.from_user.id, "08:00")


@router.message(Command('db'), F.chat.id == ADMIN)
async def get_db(message: Message):
    await message.answer_document(document=FSInputFile(Path().cwd() / 'data/bot.db'), caption='✅ База данных успешно загружена!')
