from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import locale

locale.setlocale(locale.LC_ALL, 'ru_RU')


def now_date() -> datetime:
    return datetime.now(tz=ZoneInfo('Asia/Irkutsk'))


def now() -> float:
    return now_date().timestamp()


def pad(text: str, sep: str) -> str:
    items = []
    for item in text.split(sep):
        items.append(item.rjust(2, '0'))
    return sep.join(items)


def to_str(date: datetime = None, add_excuse: bool = True) -> str:
    date = date or now_date()
    excuse = 'в ' if add_excuse else ''
    return date.strftime(f'%d.%m.%y {excuse}%H:%M')


def convert_to_date(date_time_str: str) -> datetime:
    date_str, time_str = date_time_str.split(', ')
    date = pad(date_str, '.')
    time = pad(time_str, ':')
    full_date = datetime.strptime(f'{date} {time}', '%d.%m.%y %H:%M')
    return full_date


def get_tomorrow(date: str) -> datetime:
    time = datetime.strptime(date.split()[-1], '%H:%M').time()
    tomorrow = now_date() + timedelta(days=1)
    tomorrow = tomorrow.replace(hour=time.hour, minute=time.minute)
    return tomorrow


def weekday_date(date: datetime) -> str:
    return date.strftime('%d.%m, %a').lower()

