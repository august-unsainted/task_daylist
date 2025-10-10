import asyncio
from aiogram import Bot, Dispatcher

from bot_config import db
from handlers import start, edit_time, view_tasks, new_task

from config import TOKEN
from utils.schedule import scheduler
from utils.time import today

bot = Bot(token=TOKEN)
dp = Dispatcher()


async def main():
    dp.include_routers(start.router, edit_time.router, view_tasks.router, new_task.router)
    scheduler.start()
    query = f'''
        UPDATE tasks SET notification_date = 
        (select case
        when notification_date like '%:%' then 
            strftime('%Y-%m-%d', 'now') || ' ' || strftime('%H:%M:%S', notification_date)
        else
            strftime('%Y-%m-%d', 'now')
        end as formatted_date) 
        where notification_date < ? and end_date is NULL
    '''
    db.execute_query(query, today())
    await dp.start_polling(bot, skip_updates=True)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Бот выключен')
