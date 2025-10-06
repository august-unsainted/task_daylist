import re
from datetime import timedelta
from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from bot_config import *
from handlers.view_tasks import get_id
from utils.keyboards import get_back_kb, markup, btn
from utils.schedule import schedule_task, delete_schedule
from utils.time import now, to_str, get_tomorrow, now_date, to_date, TASK_REG, format_date, reformat_db_str, from_db_str

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
    date_info = date.strftime(date_format)
    task_id = db.execute_query(query, task, now(), date_info, _id)
    task_id = task_id or _id
    if has_time:
        schedule_task(task_id, date)
        answer_text += '\n\n' + texts.get('notification_time').format(date.strftime('%H:%M'))
    kb = config.edit_keyboard(task_id, 'new')
    return {'text': answer_text, 'parse_mode': 'HTML', 'reply_markup': kb}


@router.callback_query(F.data.startswith('delete'))
async def delete_task(callback: CallbackQuery):
    task_id = get_id(callback)
    task = db.execute_query('delete from tasks where id = ? returning *', task_id)[0]
    delete_schedule(task_id)
    button = btn('Понятно 👍', f'list_{task['notification_date']}')
    await callback.message.edit_text(texts.get('delete'), reply_markup=markup([[button]]))


@router.callback_query(F.data.startswith('edit'))
async def set_edit_task(callback: CallbackQuery, state: FSMContext):
    task_id = get_id(callback)
    task = db.execute_query('select text, notification_date from tasks where id = ?', task_id)[0]
    date = from_db_str(task['notification_date'])
    text = f"{task['text']} [{date}]"
    await callback.message.edit_text(config.texts.get('edit').format(text), parse_mode='HTML',
                                     reply_markup=config.keyboards.get('cancel'))
    await state.update_data(message=callback.message.message_id, task=task_id)
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
    task = db.execute_query('update tasks set end_date = ? where id = ? returning *', now(), task_id)[0]
    mess_text = callback.message.text
    mess_text += '\n' if '🕓 Создано:' in mess_text else '\n\n'
    text = f'{mess_text}✅ Выполнено: {format_date(now_date())}'
    delete_schedule(task_id)
    await callback.message.edit_text(text=text, reply_markup=get_back_kb(task))


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
    full_date = f'{date} ({time})' if time != '00:00' else date
    answer_text = texts.get('move').format(full_date, task['text'])
    kb = config.edit_keyboard(task_id, 'completed')
    schedule_task(task_id, new_date)
    await callback.message.edit_text(text=answer_text, parse_mode='HTML', reply_markup=kb)


@router.callback_query(F.data.startswith('message_delete'))
async def delete_message(callback: CallbackQuery):
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass
