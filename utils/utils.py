from datetime import datetime, timedelta
import string

from twitchio.ext import commands
import os

from enum import Enum

class TimeSize(Enum):
    SMALL = 0
    SMALL_SPACES = 1
    MEDIUM = 2
    MEDIUM_SPACES = 3
    LONG = 4

def strjoin(connecting_char: str, *strings: str):
    return connecting_char.join([str(x) for x in strings if x])

def strenclose(open_char: str, close_char: str, connecting_char: str, *strings: str):
    out = [open_char + str(x) + close_char for x in strings if x]
    if len(out) == 0:
        return None
    return connecting_char.join(out)

def strjoin_len(connecting_char: str, max_chars: int, *strings: str):
    result, current = [], ""

    for s in filter(None, strings):
        if current:
            candidate = current + connecting_char + s
        else:
            candidate = s
        
        if len(candidate) > max_chars:
            result.append(current)
            current = s
        else:
            current = candidate
    
    if current:
        result.append(current)
    
    return result
def strextend(base, max_chars: int, *strings: str):
    if isinstance(base, str):
        result, current = [], base
    elif isinstance(base, list):
        result, current = base[:-1], base[-1] if base else ""
    else:
        raise TypeError("Base must be a string or a list of strings")
    
    for s in filter(None, strings):
        if current:
            candidate = current + s
        else:
            candidate = s
        
        if len(candidate) > max_chars:
            result.append(current)
            current = s
        else:
            current = candidate
    
    if current:
        result.append(current)
    
    return result

def rm_words(string: str, num: int):
    split = string.split(' ')
    if num > 0:
        return " ".join(split[num:])
    elif num < 0:
        return " ".join(split[:num])
    else:
        return string

def parse_time(iso_str: str):
    s = ""
    if iso_str[-1] == "Z":
        s = iso_str[:-1] + '+00:00'
    else:
        s = iso_str + '+00:00'
    return datetime.fromisoformat(s)

def pl(number: int | float, word: str, include_number=True):
    if word[-1].lower() == 's':
        word = word[:-1]
    if include_number:
        if number == 1:
            return f"{number:,} {word}"
        else:
            return f"{number:,} {word}s"
    else:
        if number == 1:
            return f"{word}"
        else:
            return f"{word}s"

def truncate_sentence(in_string: str, char_limit: int):
    if len(in_string) <= char_limit:
        return in_string
    
    excess_chars = len(in_string) - char_limit
    str_split = in_string.split(" ")
    while excess_chars > 0 and len(str_split) > 0:
        excess_chars -= len(str_split.pop()) + 1
    
    if len(str_split) == 0:
        str_split.append(in_string[:char_limit])

    return " ".join(str_split).strip(string.punctuation) + "…"

def format_timedelta(td: timedelta, size=TimeSize.SMALL_SPACES) -> str:  
    return format_seconds(int(td.total_seconds()), size)

_time_str = {
    'day': ('d', 'd', 'day', ' day', ' day'),
    'days': ('d', 'd', 'days', ' days', ' days'),
    'hour': ('h', 'h', 'hr', ' hr', ' hour'),
    'hours': ('h', 'h', 'hrs', ' hrs', ' hours'),
    'minute': ('m', 'm', 'min', ' min', ' minute'),
    'minutes': ('m', 'm', 'mins', ' mins', ' minutes'),
    'second': ('s', 's', 'sec', ' sec', ' second'),
    'seconds': ('s', 's', 'secs', ' secs', ' seconds'),
}


def format_seconds(seconds: int, size=TimeSize.SMALL):
    seconds = int(seconds)
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    
    parts = []
    if days:
        word = _time_str['day'][size.value] if days == 1 else _time_str['days'][size.value]
        parts.append(f"{days}{word}")
    if hours:
        word = _time_str['hour'][size.value] if hours == 1 else _time_str['hours'][size.value]
        parts.append(f"{hours}{word}")
    if minutes:
        word = _time_str['minute'][size.value] if minutes == 1 else _time_str['minutes'][size.value]
        parts.append(f"{minutes}{word}")
    if seconds or not parts:
        word = _time_str['second'][size.value] if seconds == 1 else _time_str['seconds'][size.value]
        parts.append(f"{seconds}{word}")
    if size == TimeSize.LONG and len(parts) > 1:
        # parts[-1] = "and " + parts[-1]
        # bye oxford comma
        last = parts.pop()
        parts[-1] += f" and {last}" 
    if size == TimeSize.LONG:
        return ", ".join(parts).strip()
    elif size in [TimeSize.MEDIUM, TimeSize.MEDIUM_SPACES, TimeSize.SMALL_SPACES]:
        return " ".join(parts).strip()
    else:
        return "".join(parts).strip()

def is_bot_owner():
    def predicate(ctx: commands.Context) -> bool:
        return ctx.chatter.id == os.getenv('OWNER_ID')
    return commands.guard(predicate)