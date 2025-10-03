import re
from datetime import timedelta
from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from bot_config import *
from handlers.view_tasks import get_id
from utils.schedule import schedule_task, delete_schedule
from utils.time import now, convert_to_date, to_str, get_tomorrow, now_date, to_date, TASK_REG, format_date

router = Router()


class EditStates(StatesGroup):
    text = State()


def get_add_args(text: str, _id: int, query: str) -> dict:
    match = re.fullmatch(TASK_REG, text)
    date = time = task = ''
    if '[' not in text:
        task = text
        date = get_tomorrow()
    elif match:
        groups = match.groups()
        task = groups[0] or groups[-1]
        date, year, time = groups[1:4]
        if not date or not date.replace('.', '').isdigit():
            if date == 'сегодня':
                date = now_date()
            elif date == 'послезавтра':
                date = now_date() + timedelta(days=2)
            else:
                date = get_tomorrow()
            date = date.strftime('%d.%m')
        date = to_date(date, time)
    if not date:
        return {'text': texts.get('error').format('текст [ДД.ММ ЧЧ:ММ]', text), 'parse_mode': 'HTML'}
    answer_text = texts.get('new').format(format_date(date), task)
    date_format = '%Y-%m-%d'
    has_time = '0:0' in str(time) or date.hour or date.minute
    if has_time:
        date_format += ' %H:%M:00'
    task_id = db.execute_query(query, task, now(), date.strftime(date_format), _id)
    if has_time:
        schedule_task(task_id, date)
        answer_text += '\n\n' + texts.get('notification_time').format(date.strftime('%H:%M'))
    kb = config.edit_keyboard(task_id, 'new')
    return {'text': answer_text, 'parse_mode': 'HTML', 'reply_markup': kb}


@router.callback_query(F.data.startswith('delete'))
async def delete_task(callback: CallbackQuery):
    task_id = get_id(callback)
    db.execute_query('delete from tasks where id = ?', task_id)
    delete_schedule(task_id)
    await callback.message.edit_text(texts.get('delete'), reply_markup=kbs.get('okay'))


@router.callback_query(F.data.startswith('edit'))
async def set_edit_task(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text('Введите текст')
    await state.update_data(message=callback.message.message_id, task=get_id(callback))
    await state.set_state(EditStates.text)


@router.message(EditStates.text)
async def edit_task(message: Message, state: FSMContext):
    data = await state.get_data()
    query = 'update tasks set text = ?, creation_date = ?, notification_date = ? where id = ?'
    args = get_add_args(message.text, data.get('task'), query)
    await message.delete()
    await message.bot.edit_message_text(message_id=data.get('message'), chat_id=message.chat.id, **args)
    await state.clear()


@router.message()
async def add_task(message: Message):
    query = 'insert into tasks (text, creation_date, notification_date, user_id) values (?, ?, ?, ?)'
    if message.text == 'тест':
        next_min_date = now_date() + timedelta(minutes=1)
        date = next_min_date.strftime('%d.%m %H:%M')
        args = get_add_args(f'новое задание [{date}]', message.from_user.id, query)
    else:
        args = get_add_args(message.text, message.from_user.id, query)
    await message.delete()
    await message.answer(**args)


@router.callback_query(F.data.startswith('done'))
async def done_task(callback: CallbackQuery):
    task_id = get_id(callback)
    db.execute_query('update tasks set end_date = ? where id = ?', now(), task_id)
    mess_text = callback.message.text
    mess_text += '\n' if '🕓 Создано:' in mess_text else '\n\n'
    text = f'{mess_text}✅ Выполнено: {to_str()}'
    kb = config.edit_keyboard(task_id, 'view_checked')
    await callback.message.edit_text(text=text, reply_markup=kb)


@router.callback_query(F.data.startswith('move'))
async def move_task(callback: CallbackQuery):
    task_id = get_id(callback)
    tasks = db.execute_query('select * from tasks where id = ?', task_id)
    if not tasks:
        return
    task = tasks[0]
    query = 'update tasks set notification_date = ? where id = ?'
    new_date = get_tomorrow(task['notification_date'])
    new_date_str = to_str(new_date, False)
    db.execute_query(query, new_date_str, task_id)
    date, time = new_date_str.split(' ')
    answer_text = texts.get('move').format(date, time, task['text'])
    kb = config.edit_keyboard(task_id, 'view_checked')
    await callback.message.edit_text(text=answer_text, parse_mode='HTML', reply_markup=kb)


@router.callback_query(F.data.startswith('message_delete'))
async def delete_message(callback: CallbackQuery):
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        print('чет не удаляется')
        pass
