import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import locale

from humanize import naturalday

locale.setlocale(locale.LC_ALL, 'ru_RU.UTF-8')
TIME_REG = r'(?:[0-1]?[0-9]|2[0-3]):[0-5][0-9]'
DATE_REG = r'(?:0?[1-9]|[1-2]?[0-9]|3[0-1])\.(?:0?[1-9]|1[0-2])(\.\d{2})?'
TASK_REG = rf'(.*?) *(?:\[({DATE_REG}|сегодня|завтра|послезавтра)?,? *(?:({TIME_REG}))? *\]) *(.*)'
print(TASK_REG)


def now_date() -> datetime:
    return datetime.now(tz=ZoneInfo('Asia/Irkutsk'))


def now() -> str:
    return now_date().strftime('%Y-%m-%d %H:%M')


def pad(text: str, sep: str) -> str:
    items = []
    for item in text.split(sep):
        items.append(item.rjust(2, '0'))
    return sep.join(items)


def reset_time(date: datetime) -> datetime:
    return date.replace(hour=0, minute=0, second=0, microsecond=0)


def to_str(date: datetime = None, add_excuse: bool = True) -> str:
    date = date or now_date()
    excuse = 'в ' if add_excuse else ''
    return date.strftime(f'%d.%m.%y {excuse}%H:%M')


def to_db_str(date: datetime = None) -> str:
    date = date or now_date()
    return date.strftime('%Y-%m-%d %H:%M:00')


def from_db_str(date_str: str):
    date_format = '%Y-%m-%d'
    has_time = ':' in date_str
    if has_time:
        date_format += ' %H:%M'
    date = datetime.strptime(date_str, date_format)
    result = to_str(date)
    if not has_time:
        result = result.split()[0]
    return result


def reformat_db_str(date_str: str) -> str:
    date = datetime.strptime(date_str, '%Y-%m-%d %H:%M')
    return format_date(date) + ' в ' + date.strftime('%H:%M')


def replace_date(match) -> str:
    date_format = '%d.%m'
    if match[1]:
        date_format += '.%y'
    if match[2]:
        date_format += ' %H:%M'
    return date_format


def find_year(date: str, has_time: bool = True) -> datetime | None:
    date_format = re.sub(r'\d{2}\.\d{2}(\.\d{2})?( \d{2}:\d{2})?', replace_date, date)
    now = now_date()
    if not has_time:
        now = reset_time(now)
    full_date = datetime.strptime(date, date_format)
    if '%y' not in date_format:
        full_date = full_date.replace(year=now.year)
    full_date = full_date.replace(tzinfo=ZoneInfo('Asia/Irkutsk'))
    if full_date < now:
        return None
    return full_date


def to_date(date: str | None, time: str | None) -> datetime | None:
    if date:
        date = pad(date, '.')
    if time:
        time = pad(time, ':')
    try:
        if date and time:
            return find_year(f'{date} {time}')
        elif time:
            return get_tomorrow(f'_ {time}')
        else:
            return find_year(date, False)
    except ValueError:
        return None


def convert_to_date(date_time_str: str) -> datetime:
    if ', ' not in date_time_str:
        if ':' in date_time_str:
            return get_tomorrow(f'_ {date_time_str}')
        else:
            return datetime.strptime(date_time_str, '%d.%m.%y')
    date_str, time_str = date_time_str.split(', ')
    date = pad(date_str, '.')
    time = pad(time_str, ':')
    full_date = datetime.strptime(f'{date} {time}', '%d.%m.%y %H:%M')
    return full_date


def get_tomorrow(date: str = None) -> datetime:
    tomorrow = now_date() + timedelta(days=1)
    if date and ':' in date:
        time = datetime.strptime(date.split()[-1], '%H:%M:%S').time()
        # date_str = date.strftime('%Y-%m-%d')
        tomorrow = tomorrow.replace(hour=time.hour, minute=time.minute)
    else:
        tomorrow = reset_time(tomorrow)
    return tomorrow


def get_weekday(date: datetime) -> str:
    result = date.strftime('%d %B, %a').lower()
    if result[0] == '0':
        result = result[1:]
    return result


def format_date(date: datetime) -> str:
    natural_day = naturalday(date)
    weekday = get_weekday(date)
    if natural_day == date.strftime('%b %d'):
        return re.sub(r', (\w+)', r' (\1)', weekday)
    return f'{natural_day} ({weekday})'


def get_week(date: datetime) -> tuple[datetime, datetime]:
    days_since_monday = date.weekday()
    days_before_sunday = 6 - date.weekday()
    monday = date - timedelta(days=days_since_monday)
    sunday = date + timedelta(days=days_before_sunday)
    return monday, sunday
