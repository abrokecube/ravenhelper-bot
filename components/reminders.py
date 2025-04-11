import asyncio
import twitchio
from twitchio.ext import commands
from typing import NamedTuple, List, Dict
from datetime import datetime, timedelta
import heapq
from functools import total_ordering
from utils.parse_time import parse_time
from utils.utils import format_seconds, format_timedelta, TimeSize, truncate_sentence, pl, strjoin
from dataclasses import dataclass

# from database.session import get_async_session
from database import models, utils
from database.session import get_async_session
from sqlalchemy import select
from sqlalchemy.orm import joinedload

@dataclass
class Reminder:
    user_name: str
    user_id: str
    channel_name: str
    channel_id: str
    description: str
    start_time: datetime
    end_time: datetime
    id: int = None

    def to_modal_obj(self):
        return models.Reminder(
            description = self.description,
            start_time = self.start_time,
            end_time = self.end_time,
            user_id = self.user_id,
            channel_id = self.channel_id
        )
    
    @staticmethod
    def from_modal_obj(obj: models.Reminder):
        return Reminder(
            user_name=obj.user.name,
            user_id=obj.user_id,
            channel_name=obj.channel.name,
            channel_id=obj.channel_id,
            description = obj.description,
            start_time = obj.start_time,
            end_time = obj.end_time,
            id = obj.id
        )
    
    def __lt__(self, value: 'Reminder'):
        return self.end_time < value.end_time
    

class ReminderCommands(commands.Component):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_reminders: List[Reminder] = []
        
        self.active_reminders_user: Dict[str, List[Reminder]] = {}
        heapq.heapify(self.active_reminders)
        
        asyncio.create_task(self.load_reminders_from_db())
        asyncio.create_task(self.timer_task())

    def get_active_rem_user_key(self, ctx: commands.Context):
        return f"{ctx.broadcaster.name}_{ctx.author.id}"

    async def load_reminders_from_db(self):
        async with get_async_session() as session:
            result = await session.execute(
                select(models.Reminder)
                .options(
                    joinedload(models.Reminder.user),
                    joinedload(models.Reminder.channel),
                )
            )
            reminders = result.scalars().all()
            for reminder_obj in reminders:
                reminder = Reminder.from_modal_obj(reminder_obj)
                key = f"{reminder.channel_name}_{reminder.user_id}"
                if not key in self.active_reminders_user:
                    self.active_reminders_user[key] = []
                self.active_reminders_user[key].append(reminder)
                heapq.heappush(self.active_reminders, reminder)
                
    @commands.group(aliases=('rem','r'), invoke_fallback=True)
    @commands.cooldown(rate=2, per=3)
    async def remind(self, ctx: commands.Context, *args: str):
        """Sets a reminder for yourself. You will be notified in the chat you
        set the reminder in.
        
        Arguments:
            time (str): Time in minutes. Supports specifying h:m:s (ex: 1h2m, 1:04, 55 seconds)
            description (str, optional): An optional description to go with the reminder (up to 50 chars).
        """
        time = ""
        description = ""
        if not args:
            await ctx.reply(
                "/me Enter a duration."
            )
            return
        time = args[0]
        description = truncate_sentence(' '.join(args[1:]), 50)
        
        seconds = parse_time(time)
        if seconds <= 0:
            await ctx.reply(
                "/me uuh Invalid duration."
            )
            return
        if seconds < 10:
            await ctx.reply(
                "/me uuh Duration must be 10 seconds or longer."
            )
            return
        now = datetime.now()
        reminder = Reminder(
            user_name=ctx.author.name,
            user_id=ctx.author.id,
            channel_name=ctx.broadcaster.name,
            channel_id=ctx.broadcaster.id,
            description=description,
            start_time=now,
            end_time=now+timedelta(seconds=seconds)
        )
        
        await self.save_reminder_to_db(reminder)
        heapq.heappush(self.active_reminders, reminder)
        key = self.get_active_rem_user_key(ctx)
        if not key in self.active_reminders_user:
            self.active_reminders_user[key] = []
        self.active_reminders_user[key].append(reminder)
        
        if description:
            await ctx.reply(
                f"/me Will remind you about \"{description}\" in {format_seconds(seconds, TimeSize.LONG)}."
            )
        else:
            await ctx.reply(
                f"/me Will remind you in {format_seconds(seconds, TimeSize.LONG, include_zero=False)}."
            )
            
    @remind.command(aliases=('list',))
    async def status(self, ctx: commands.Context):
        key = f"{ctx.broadcaster.name}_{ctx.author.id}"
        user_reminders = self.active_reminders_user.get(key)
        if not user_reminders:
            await ctx.reply(
                f"You have no reminders in this channel.",
                me=True
            )
        else:
            reminders = []
            now = datetime.now()
            for reminder in user_reminders:
                time_left = format_timedelta(reminder.end_time - now)
                name = reminder.description or "reminder"
                reminders.append(
                    f"{name} in {time_left}"
                )
            await ctx.reply(
                f"You have {pl(len(user_reminders), 'active reminder')} in this channel: "
                f"{strjoin(', ', *reminders, before_end=' and ')}.",
                me=True
            )
            
    async def save_reminder_to_db(self, reminder: Reminder):
        async with get_async_session() as session:
            reminder_obj = models.Reminder(
                description = reminder.description,
                start_time = reminder.start_time,
                end_time = reminder.end_time,
                user_id = reminder.user_id,
                channel_id = reminder.channel_id
            )
            session.add(reminder_obj)
            # make sure user and channel are in the database
            await utils.get_user(session, id=reminder.user_id, name=reminder.user_name)
            await utils.get_channel(session, id=reminder.channel_id, name=reminder.channel_name)
            await session.flush()
            reminder.id = reminder_obj.id
    
    async def delete_reminder_from_db(self, reminder: Reminder):
        if reminder.id is None:
            return
        async with get_async_session() as session:
            result = await session.execute(
                select(models.Reminder).where(models.Reminder.id == reminder.id)
            )
            reminder_obj = result.scalar_one_or_none()
            if reminder_obj:
                await session.delete(reminder_obj)
    
                        
    async def timer_task(self):
        while True:
            now = datetime.now()
            for reminder in self.active_reminders[:]:
                if now > reminder.end_time:
                    heapq.heappop(self.active_reminders)
                    await self.delete_reminder_from_db(reminder)
                    key = f"{reminder.channel_name}_{reminder.user_id}"
                    self.active_reminders_user[key].remove(reminder)
                    desc = reminder.description or "Reminder!"
                    dur = format_seconds((reminder.end_time - reminder.start_time).total_seconds(), include_zero=False)
                    channel = self.bot.create_partialuser(reminder.channel_id)
                    await channel.send_message(
                        sender=self.bot.user, token_for=self.bot.user,
                        message=f"/me @{reminder.user_name} dinkDonk {desc} (from {dur} ago)"
                    )
                else:
                    break
            await asyncio.sleep(0.25)
    