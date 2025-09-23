from datetime import datetime


def now() -> float:
    return datetime.now().timestamp()


def pad(text: str, sep: str) -> str:
    items = []
    for item in text.split(sep):
        items.append(item.rjust(2, '0'))
    return sep.join(items)


def convert_to_stamp(date_time_str: str) -> float:
    date_str, time_str = date_time_str.split(', ')
    date = pad(date_str, '.')
    time = pad(time_str, ':')
    full_date = datetime.strptime(f'{date} {time}', '%d.%m.%y %H:%M')
    return full_date.timestamp()
