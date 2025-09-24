from datetime import datetime
from pathlib import Path

from aiogram import Bot
from apscheduler.jobstores.base import JobLookupError
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

from bot_config import db, config
from config import TOKEN
from utils.time import to_str

db_path = Path().cwd() / 'data/bot.db'
jobstores = {'default': SQLAlchemyJobStore(url=f'sqlite:///{db_path}')}
scheduler = AsyncIOScheduler(timezone='Asia/Irkutsk', jobstores=jobstores)


async def send_task(task_id: int):
    tasks = db.execute_query('select * from tasks where id = ?', task_id)
    if not tasks:
        return
    task = tasks[0]
    kb = config.edit_keyboard(task['id'], 'view')
    async with Bot(token=TOKEN) as bot:
        await bot.send_message(chat_id=task['user_id'], text=task['text'], reply_markup=kb)


def schedule_task(task_id: int, date: datetime) -> None:
    scheduler.add_job(send_task, 'date', run_date=date, id=str(task_id), args=[task_id],
                      replace_existing=True, misfire_grace_time=100)


def delete_schedule(task_id: int | str):
    try:
        scheduler.remove_job(str(task_id))
    except JobLookupError:
        print(f'чета нет такого задания: {task_id}')
        pass
