from datetime import datetime, timedelta
from pathlib import Path

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup
from apscheduler.jobstores.base import JobLookupError
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

from bot_config import db, config
from config import TOKEN
from handlers.view_tasks import get_today_tasks
from utils.time import now_date, reset_time, to_db_str

db_path = Path().cwd() / 'data/bot.db'
jobstores = {'default': SQLAlchemyJobStore(url=f'sqlite:///{db_path}')}
scheduler = AsyncIOScheduler(timezone='Asia/Irkutsk', jobstores=jobstores)


async def send_mess(user_id: int, text: str, kb: InlineKeyboardMarkup):
    async with Bot(token=TOKEN) as bot:
        await bot.send_message(chat_id=user_id, text=text, reply_markup=kb, parse_mode='HTML')


async def send_task(task_id: int):
    tasks = db.execute_query('select * from tasks where id = ?', task_id)
    if not tasks:
        return
    task = tasks[0]
    kb = config.edit_keyboard(task['id'], 'view')
    await send_mess(task['user_id'], task['text'], kb)


async def send_today(user_id: int):
    yesterday = reset_time(now_date() - timedelta(days=1))
    query = (f"UPDATE tasks SET notification_date = datetime(notification_date, '+1 day') "
             f"where notification_date like '{to_db_str(yesterday)}%' and user_id = ?")
    db.execute_query(query, user_id)
    text, kb = await get_today_tasks(user_id)
    await send_mess(user_id, text, kb)


def schedule_task(task_id: int | str, date: datetime) -> None:
    scheduler.add_job(send_task, 'date', run_date=date, id=str(task_id), args=[task_id],
                      replace_existing=True, misfire_grace_time=100)


async def schedule_regular(user_id: int, time: str) -> None:
    scheduler.add_job(send_today, 'cron', hour=time[:2], minute=time[3:], id=str(user_id),
                      args=[user_id], replace_existing=True, misfire_grace_time=100)


def delete_schedule(task_id: int | str):
    try:
        scheduler.remove_job(str(task_id))
    except JobLookupError:
        pass
