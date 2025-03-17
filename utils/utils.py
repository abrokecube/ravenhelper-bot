from datetime import datetime, timedelta
import string

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

def format_timedelta(td: timedelta, spaces=True) -> str:  
    return format_seconds(int(td.total_seconds()), spaces)

def format_seconds(seconds: int, spaces=True):
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if seconds or not parts:
        parts.append(f"{seconds}s")
    if spaces:
        return " ".join(parts)
    else:
        return "".join(parts)

