from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import locale

locale.setlocale(locale.LC_ALL, 'ru_RU')


def now_date() -> datetime:
    return datetime.now(tz=ZoneInfo('Asia/Irkutsk'))


def now() -> str:
    return now_date().strftime('%Y-%m-%d %H:%M')


def pad(text: str, sep: str) -> str:
    items = []
    for item in text.split(sep):
        items.append(item.rjust(2, '0'))
    return sep.join(items)


def to_str(date: datetime = None, add_excuse: bool = True) -> str:
    date = date or now_date()
    excuse = 'в ' if add_excuse else ''
    return date.strftime(f'%d.%m.%y {excuse}%H:%M')


def to_db_str(date: datetime = None) -> str:
    date = date or now_date()
    return date.strftime('%Y-%m-%d %H:%M')


def reformat_db_str(date_str: str = None) -> str:
    date = datetime.strptime(date_str, '%Y-%m-%d %H:%M')
    return to_str(date)


def find_year(date: str, has_time: bool = True) -> datetime | None:
    has_year = date.count('.') == 2
    format = '%d.%m.%y %H:%M' if has_year else '%d.%m %H:%M'
    if not has_time:
        format = format.split()[0]
    full_date = datetime.strptime(date, format)
    now = now_date()
    if not has_year:
        full_date = full_date.replace(year=now.year)
    full_date = full_date.replace(tzinfo=ZoneInfo('Asia/Irkutsk'))
    if full_date < now:
        return None
    return full_date


def to_date(date_str: str) -> datetime | None:
    date, time = None, None
    if ':' in date_str and '.' in date_str:
        date, time = date_str.split()
    elif '.' in date_str:
        date = pad(date_str.strip(), '.')
    else:
        time = pad(date_str.strip(), ':')

    try:
        if date and time:
            return find_year(f'{date} {time}')
        elif time:
            return get_tomorrow(time)
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
    if date:
        time = datetime.strptime(date.split()[-1], '%H:%M').time()
        # date_str = date.strftime('%Y-%m-%d')
        hour, minute = time.hour, time.minute
    else:
        hour, minute = 0, 0
    tomorrow = tomorrow.replace(hour=hour, minute=minute)
    return tomorrow


def weekday_date(date: datetime) -> str:
    return date.strftime('%d.%m, %a').lower()
