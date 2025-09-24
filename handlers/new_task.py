from datetime import timedelta
from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from bot_config import *
from utils.schedule import schedule_task, delete_schedule
from utils.time import now, convert_to_date, to_str, get_tomorrow, now_date

router = Router()


class EditStates(StatesGroup):
    text = State()


def get_add_args(text: str, _id: int, query: str) -> dict:
    if ' [' not in text:
        return {'text': 'Неправильный формат'}
    task, date = text.strip().split(' [')
    date = date[:-1]
    day, time = date.split(', ')
    answer_text = texts.get('new').format(day, task, time)
    full_date = convert_to_date(date)
    task_id = db.execute_query(query, task, now(), full_date.timestamp(), date, _id)
    schedule_task(task_id, full_date)
    kb = config.edit_keyboard(task_id, 'new')
    return {'text': answer_text, 'parse_mode': 'HTML', 'reply_markup': kb}


@router.callback_query(F.data.startswith('delete'))
async def delete_task(callback: CallbackQuery):
    task_id = callback.data.split('_')[-1]
    db.execute_query('delete from tasks where id = ?', task_id)
    delete_schedule(task_id)
    await callback.message.edit_text(texts.get('delete'), reply_markup=kbs.get('okay'))


@router.callback_query(F.data.startswith('edit'))
async def set_edit_task(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text('Введите текст')
    task_id = callback.data.split('_')[-1]
    await state.update_data(message=callback.message.message_id, task=task_id)
    await state.set_state(EditStates.text)


@router.message(EditStates.text)
async def edit_task(message: Message, state: FSMContext):
    data = await state.get_data()
    query = ('update tasks set text = ?, creation_date = ?, notification_stamp = ?, notification_date = ? '
             'where id = ?')
    args = get_add_args(message.text, data['task'], query)
    await message.delete()
    await message.bot.edit_message_text(message_id=data.get('message'), chat_id=message.chat.id,
                                        **args)
    await state.clear()


@router.message()
async def add_task(message: Message):
    query = ('insert into tasks (text, creation_date, notification_stamp, notification_date, user_id) '
             'values (?, ?, ?, ?, ?)')
    if message.text == 'тест':
        next_min_date = now_date() + timedelta(minutes=1)
        date = next_min_date.strftime('%d.%m.%y, %H:%M')
        args = get_add_args(f'новое задание [{date}]', message.from_user.id, query)
    else:
        args = get_add_args(message.text, message.from_user.id, query)
    await message.delete()
    await message.answer(**args)


@router.callback_query(F.data.startswith('done'))
async def done_task(callback: CallbackQuery):
    task_id = callback.data.split('_')[-1]
    db.execute_query('update tasks set end_date = ? where id = ?', now(), task_id)
    text = f'{callback.message.text}\n\n✅ Выполнено: {to_str()}'
    kb = config.edit_keyboard(task_id, 'view_checked')
    await callback.message.edit_text(text=text, reply_markup=kb)


@router.callback_query(F.data.startswith('move'))
async def move_task(callback: CallbackQuery):
    task_id = callback.data.split('_')[-1]
    tasks = db.execute_query('select * from tasks where id = ?', task_id)
    if not tasks:
        return
    task = tasks[0]
    query = 'update tasks set notification_stamp = ?, notification_date = ? where id = ?'
    new_date = get_tomorrow(task['notification_date'])
    new_date_str = to_str(new_date, False)
    db.execute_query(query, new_date.timestamp(), new_date_str, task_id)
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

