# twitchio v3
import aiohttp
import aiohttp.client_exceptions
from twitchio.ext import commands
from twitchio.ext import routines
from twitchio import eventsub
import twitchio
from dotenv import load_dotenv
import os
import logging
import asyncio
import ravenpy
from datetime import timedelta, datetime
from typing import Set

from utils import utils

from database import models
from database import utils as dbutils
from database.models import create_all_tables
from database.session import get_async_session
from sqlalchemy import select, update
from sqlalchemy.orm import joinedload

from components.textresponses import RavenTextCommands
from components.characters import RavenCharacterCommands
from components.charactertools import RavenCharacterTools
from components.raveninfo import RavenInfo
from components.items import RavenItemCommands
from components.help import HelpCommands, helptext
from components.marketplace import MarketplaceCommands

from components.reminders import ReminderCommands
from components.alerts import AlertCommands

load_dotenv()

LOGGER: logging.Logger = logging.getLogger("Bot")
TARGET_CHANNEL = os.getenv('TARGET_CHANNEL')
BOT_ID = os.getenv('BOT_ID')

class Bot(commands.Bot):
    def __init__(self):
        super().__init__(
            client_id=os.getenv('CLIENT_ID'),
            client_secret=os.getenv('CLIENT_SECRET'),
            bot_id=os.getenv('BOT_ID'),
            owner_id=os.getenv('OWNER_ID'),
            prefix=self.get_channel_prefixes
        )
        self.channel_prefixes = {}
        self.subscribed_channels: Set[str] = set()

    async def setup_hook(self) -> None:        
        await self.add_component(RavenTextCommands(self))
        await self.add_component(RavenCharacterCommands(self, rfapi))
        await self.add_component(RavenCharacterTools(self, rfapi))
        await self.add_component(RavenInfo(self, rfapi))
        await self.add_component(RavenItemCommands(self, rfapi))
        await self.add_component(MarketplaceCommands(self, rfapi))

        await self.add_component(HelpCommands(self))
        await self.add_component(BotUtilityCommands(self))
        await self.add_component(BotSettingsCommands(self))
        await self.add_component(TestCommands(self))
        await self.add_component(ReminderCommands(self))
        
        await self.add_component(AlertCommands(self))

        async with get_async_session() as session:
            result = await session.execute(
                select(models.BotSettings.channel_id)
                .where(models.BotSettings.bot_joined == True)
            )
            channels = set(result.scalars().all())
        LOGGER.info(f"Joining {len(channels)} channels...")
        channels.add(int(TARGET_CHANNEL))
        channels.add(int(self.owner_id))
        channels.add(int(BOT_ID))
        fail_count = 0
        success_count = 0
        for channel_id in channels:
            try:
                await self.join_channel(channel_id, False)
                success_count += 1
            except twitchio.HTTPException:
                LOGGER.warning(f"Failed to subscribe to {channel_id}")
                fail_count += 1
        LOGGER.info(f"Joined {success_count} channels, failed to join {fail_count} channels.")

        async with get_async_session() as session:
            await session.execute(
                update(models.BotSettings)
                .where(models.BotSettings.channel_id.in_(self.subscribed_channels))
                .values(bot_joined=1)
            )

        self.auto_token_reload.start()
        LOGGER.info("Finished setup hook!")

    async def join_channel(self, channel_id: str, write_db = True):
        payload = eventsub.ChatMessageSubscription(
            broadcaster_user_id=str(channel_id), user_id=self.bot_id)
        await self.subscribe_websocket(payload=payload)
        self.subscribed_channels.add(str(channel_id))
        if write_db:
            async with get_async_session() as session:
                settings = await dbutils.get_channel_settings(session, id=channel_id)
                settings.bot_joined = True

    async def part_channel(self, channel_id: str):
        self.subscribed_channels.remove(str(channel_id))
        async with get_async_session() as session:
            settings = await dbutils.get_channel_settings(session, id=channel_id)
            settings.bot_joined = False
            
    async def event_message(self, payload):
        if not payload.broadcaster.id in self.subscribed_channels:
            return
        
        while self._is_reloading_tokens:
            await asyncio.sleep(0.5)

        payload.text = payload.text.replace("\U000e0000", "").strip()
        return await super().event_message(payload)

    _is_reloading_tokens = False
    async def reload_tokens(self):
        self._is_reloading_tokens = True
        LOGGER.info("Reloading tokens...")
        await self.load_tokens()
        self._is_reloading_tokens = False

    async def event_command_error(self, payload):
        if isinstance(payload.exception, commands.exceptions.CommandNotFound):
            LOGGER.debug(f"[{payload.context.channel.name}] ({payload.context.chatter.name}) Unknown command {payload.context.message.text}")
            return None
        elif isinstance(payload.exception, commands.exceptions.CommandOnCooldown):
            LOGGER.debug(f"[{payload.context.channel.name}] ({payload.context.chatter.name}) {payload.context.message.text} is on cooldown")
            return None
        elif isinstance(payload.exception, commands.exceptions.GuardFailure):
            LOGGER.debug(f"[{payload.context.channel.name}] ({payload.context.chatter.name}) {payload.context.message.text} was guarded")
            return None
        elif isinstance(payload.exception, commands.exceptions.MissingRequiredArgument):
            await payload.context.send(helptext(self, payload.context.invoked_with, payload.context.prefix))
            return None
        elif isinstance(payload.exception, commands.exceptions.CommandInvokeError):
            if isinstance(payload.exception.original, AssertionError):
                await payload.context.send("bruh Error...")
            elif isinstance(payload.exception.original, twitchio.exceptions.HTTPException):
                if payload.exception.original.status == 401:
                    if not self._is_reloading_tokens:
                        await self.reload_tokens()
                    await self.event_message(payload.context.message)
            else:
                await payload.context.send("bruh Error.")
            return await super().event_command_error(payload)
        else:
            # await payload.context.send("bruh Error.")
            return await super().event_command_error(payload)

    async def get_channel_prefixes(self, bot: commands.Bot, message: twitchio.ChatMessage):
        if not message.broadcaster.id in self.channel_prefixes:
            async with get_async_session() as session:
                channel_settings = await dbutils.get_channel_settings(session, channel=message.broadcaster)
                self.channel_prefixes[message.broadcaster.id] = channel_settings.prefix
        return self.channel_prefixes[message.broadcaster.id]


    @routines.routine(delta=timedelta(days=1), wait_first=True, wait_remainder=True)
    async def auto_token_reload(self):
        await self.reload_tokens()

class BotUtilityCommands(commands.Component):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.start_time = datetime.now()

    # @commands.is_owner()
    # @commands.command(aliases=('reloadtokens', 'reload', 'rt'))
    # async def reload_tokens(self, ctx: commands.Context):
    #     """Reloads the bot's tokens."""
    #     await self.bot.reload_tokens()
    #     await ctx.send("Tokens reloaded successfully.")

    @commands.command()
    async def uptime(self, ctx: commands.Context):
        """Shows the bot's uptime."""
        current_time = datetime.now()
        uptime_str = utils.format_timedelta(current_time - self.start_time, utils.TimeSize.LONG)
        await ctx.send(f"/me Bot has been running for {uptime_str}.")
        
    @commands.command(aliases=('ping',))
    async def pong(self, ctx: commands.Context):
        """Pong!"""
        await ctx.send("Pong! 🏓")


class BotSettingsCommands(commands.Component):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.is_elevated()
    @commands.command(aliases=('setprefix','changeprefix','prefixset','modifyprefix'))
    async def prefix(self, ctx: commands.Context, *args: str):
        """Set the bot's prefix for commands."""
        if not args:
            await ctx.send("Include one or more prefixes separated with a space.")
            return
        async with get_async_session() as session:
            channel_settings = await dbutils.get_channel_settings(session, channel=ctx.message.broadcaster)
            channel_settings.prefix = list(args)
        await ctx.send(
            f"Prefix set to {utils.strjoin(', ', *[f'"{x}"' for x in args], before_end=' and ')} "
            f"for channel #{ctx.message.broadcaster.name}"
        )
        self.bot.channel_prefixes[ctx.message.broadcaster.id] = args
    
    @commands.command()
    async def join(self, ctx: commands.Context, user: str=""):
        """Adds the bot to a channel. Can only be used by the bot owner."""
        # """Add the bot to your channel. Can only be used in the bot's channel or abrokecube's channel."""
        # may be uncommented to enable any user to add this bot
        if not ctx.is_owner():
            return
        
        if user and not ctx.is_owner():
            return
        if (not ctx.is_owner()) and (ctx.broadcaster.id not in (self.bot.bot_id, self.bot.owner_id)):
            return
        channel = ctx.author
        if user:
            channel = await utils.get_user_cached(self.bot, user_login=user)
        if channel is None:
            await ctx.send(
                "Not a valid channel..."
            )
        if channel.id in self.bot.subscribed_channels:
            await ctx.send(
                f"Already listening to this channel! "
                f"(You can force rejoin by using {ctx.prefix}part and then {ctx.prefix}{ctx.invoked_with} again)"
            )
            return
        try:
            await self.bot.join_channel(channel.id)
            await ctx.send(
                f"Joined #{channel.display_name}!"
            )
            await channel.send_message(
                sender=self.bot.user,
                token_for=self.bot.user,
                message=f"/me joined #{channel.display_name}!"
            )
        except twitchio.HTTPException:
            await ctx.send(
                "Failed to join channel! :("
            )
            
    @commands.command()
    async def part(self, ctx: commands.Context, user: str=""):
        """Removes the bot from your channel."""
        if user and not ctx.is_owner():
            return
        channel = ctx.broadcaster
        if ctx.broadcaster.id in (self.bot.bot_id, self.bot.owner_id):
            channel = ctx.author
        elif not (ctx.author.broadcaster or ctx.author.moderator or ctx.author.vip):
            return
        if user:
            channel = await utils.get_user_cached(self.bot, user_login=user)
            
        if not channel.id in self.bot.subscribed_channels:
            await ctx.send(
                f"Bot is not in #{channel.name}."
            )
            return
        await self.bot.part_channel(channel.id)
        await ctx.send(
            f"/me left #{channel.name}."
        )

    @commands.is_owner()
    @commands.command()
    async def channels(self, ctx: commands.Context):
        """Prints all joined channels to console."""
        channel_texts = []
        asdf = set()
        async with get_async_session() as session:
            result = await session.execute(
                select(models.BotSettings)
                .where(models.BotSettings.bot_joined == True)
                .options(joinedload(models.BotSettings.channel))
            )
            channels = result.scalars().all()
            for settings_obj in channels:
                channel_id = settings_obj.channel.id
                channel_name = settings_obj.channel.name
                asdf.add(str(channel_id))
                if channel_name:
                    channel_texts.append(channel_name)
                else:
                    user = await utils.get_user_cached(self.bot, user_id=channel_id)
                    channel_texts.append(f"{user.name}")
        await ctx.send(f"/me Currently in {utils.pl(len(channel_texts), 'channel')}.")
        print("--- CHANNELS JOINED ---")
        for channels in [channel_texts[i:i+5] for i in range(0, len(channel_texts), 5)]:
            print(', '.join(channels))

    @commands.is_owner()
    @commands.command()
    async def rf_reauth(self, ctx: commands.Context):
        r = await rfapi._authenticate()
        if r:
            await ctx.send("Successful")
        else:
            await ctx.send("Unsuccessful")
            


class TestCommands(commands.Component):
    def __init__(self, bot: Bot):
        self.bot = bot
    
    @commands.command(aliases=("hi",))
    async def hello(self, ctx: commands.Context, username: str = ""):
        """hi"""
        if not username:
            username = ctx.author.name
        await ctx.send(f'hiii {username}!')

    @commands.command(aliases=("bye",))
    async def goodbye(self, ctx: commands.Context, username: str = ""):
        """bye"""
        if not username:
            username = ctx.author.name
        await ctx.send(f'byeee {username}')
    

rfapi: ravenpy.RavenNest
async def main() -> None:
    global rfapi
    await create_all_tables()
    twitchio.utils.setup_logging(level=int(os.getenv("LOGGING_LEVEL")))
    rfapi = ravenpy.RavenNest(os.getenv("API_USER"), os.getenv("API_PASS"))
    try:
        await rfapi.login()
    except aiohttp.client_exceptions.ClientConnectorError:
        pass

    async def runner() -> None:
        async with Bot() as bot:
            await bot.start()

    try:
        await runner()
    except KeyboardInterrupt:
        LOGGER.warning("Shutting down due to Keyboard Interrupt...")


asyncio.run(main())
