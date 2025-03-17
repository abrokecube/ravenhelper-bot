from typing import List
from twitchio.ext import commands
import ravenpy
import asyncio
DEBUG = True

def match_identifier(chars: List[ravenpy.Character], target: str):
    for idx, char in enumerate(chars):
        char_id = set()   
        char_id.add(str(idx+1))
        if idx == 0:
            char_id.add(str(0))
        char_id.add(char.identifier.lower())
        
        if target.lower() in char_id:
            return char
    return None

async def _get_characters(bot: commands.Bot, rfapi: ravenpy.Ravenfall, *, user_id: str=None, user_name=None):
    uid = user_id
    if uid is None:
        if user_name:
            user_query = await bot.fetch_users(logins=[user_name.strip('@'),])
            if user_query:
                user_id = user_query[0].id
            else:
                return None
        else:
            return None
    tasks = [
        rfapi.get_character(user_id,'1'),
        rfapi.get_character(user_id,'2'),
        rfapi.get_character(user_id,'3')
    ]
    user_chars = await asyncio.gather(*tasks, return_exceptions=not DEBUG)
    user_chars = [x for x in user_chars if isinstance(x, ravenpy.Character)]
    return user_chars

async def search_user_characters(rfapi: ravenpy.Ravenfall, ctx: commands.Context, arg1, arg2, single_char_only=False) -> List[ravenpy.Character] | None:
    author_chars = None
    user_chars = None
    mode = ""
    if (not arg1) and (not arg2):
        mode = "author"
        if single_char_only:
            await ctx.reply("uuh Please specify a character.")
    elif arg1 and not arg2 and len(arg1) < 4:
        mode = "author_select"
    elif arg1 and not arg2:
        mode = "user_or_author_select"
    elif arg1 and arg2:
        mode = "user_select"
    
    if mode == "author":
        author_chars = await _get_characters(ctx.bot, rfapi, user_id=ctx.author.id)
    elif mode == "author_select":
        author_chars = await _get_characters(ctx.bot, rfapi, user_id=ctx.author.id)
    elif mode == "user_or_author_select":
        tasks = [
            _get_characters(ctx.bot, rfapi, user_id=ctx.author.id),
            _get_characters(ctx.bot, rfapi, user_name=arg1)
        ]
        author_chars, user_chars = await asyncio.gather(*tasks, return_exceptions=not DEBUG)
    elif mode == "user_select":
        user_chars = await _get_characters(ctx.bot, rfapi, user_name=arg1)

    is_targeting_user = mode == "user_or_author_select" or mode == "user_select"
    if is_targeting_user and user_chars == None:
        await ctx.reply(f"YEP User '{arg1}' not found.")
        return None

    if is_targeting_user and len(user_chars) == 0:
        await ctx.reply(f"YEP User '{arg1}' has no characters.")
        return None

    out_chars = None
    if mode == "author":
        out_chars = author_chars
    elif mode == "author_select":
        match = match_identifier(author_chars, arg1)
        if match:
            out_chars = [match]
        else:
            await ctx.reply(f"YEP Character '{arg1}' not found.")
            return None
    elif mode == "user_or_author_select":
        match = match_identifier(author_chars, arg1)
        if not match:
            out_chars = user_chars
        else:
            out_chars = [match]
    elif mode == "user_select":
        match = match_identifier(user_chars, arg2)
        if match:
            out_chars = [match]
        else:
            await ctx.reply(f"YEP Character '{arg2}' not found.")
            return None
    if len(out_chars) == 0:
        await ctx.reply("uuh Ravenfall servers may not be responding.")
        return 
    return out_chars
