import asyncio
from aiogram import Bot, Dispatcher

from handlers import view_tasks, new_task

from config import TOKEN
from utils.schedule import scheduler

bot = Bot(token=TOKEN)
dp = Dispatcher()


async def main():
    dp.include_routers(view_tasks.router, new_task.router)
    scheduler.start()
    await dp.start_polling(bot, skip_updates=True)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Бот выключен')
