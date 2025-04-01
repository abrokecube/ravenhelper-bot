# twitchio v3
from twitchio.ext import commands
from twitchio.ext import routines
from twitchio import eventsub
import twitchio
from dotenv import load_dotenv
import os
import logging
import asyncio
import ravenpy
from datetime import timedelta

from components.textresponses import RavenTextCommands
from components.characters import RavenCharacterCommands
from components.charactertools import RavenCharacterTools
from components.raveninfo import RavenInfo
from components.items import RavenItemCommands
from components.help import HelpCommands
from components.marketplace import MarketplaceCommands

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
            prefix="?"
        )

    async def setup_hook(self) -> None:
        payload = eventsub.ChatMessageSubscription(broadcaster_user_id=TARGET_CHANNEL, user_id=self.bot_id)
        await self.subscribe_websocket(payload=payload)
        await self.add_component(RavenTextCommands(self))
        await self.add_component(RavenCharacterCommands(self, rfapi))
        await self.add_component(RavenCharacterTools(self, rfapi))
        await self.add_component(RavenInfo(self, rfapi))
        await self.add_component(RavenItemCommands(self, rfapi))
        await self.add_component(MarketplaceCommands(self, rfapi))

        await self.add_component(HelpCommands(self))
        await self.add_component(TestCommands(self))
        
        self.auto_token_reload.start()
        LOGGER.info("Finished setup hook!")

    async def event_message(self, payload):
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
        elif isinstance(payload.exception, commands.exceptions.CommandInvokeError):
            if isinstance(payload.exception.original, AssertionError):
                await payload.context.reply("bruh Error...")
            elif isinstance(payload.exception.original, twitchio.exceptions.HTTPException):
                if payload.exception.original.status == 401:
                    if not self._is_reloading_tokens:
                        await self.reload_tokens()
                    await self.event_message(payload.context.message)
            else:
                await payload.context.reply("bruh Error.")
            return await super().event_command_error(payload)
        else:
            # await payload.context.reply("bruh Error.")
            return await super().event_command_error(payload)
    
    @routines.routine(delta=timedelta(days=1), wait_first=True, wait_remainder=True)
    async def auto_token_reload(self):
        await self.reload_tokens()


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
    
    # @is_bot_owner()
    # @commands.command()
    # async def reload_tokens(self, ctx: commands.Context):
    #     await self.bot.load_tokens()        
    #     await ctx.reply(f'Reloaded tokens', me=True)


rfapi: ravenpy.Ravenfall
async def main() -> None:
    global rfapi
    twitchio.utils.setup_logging(level=int(os.getenv("LOGGING_LEVEL")))
    rfapi = ravenpy.Ravenfall(os.getenv("API_USER"), os.getenv("API_PASS"))
    await rfapi.login()

    async def runner() -> None:
        async with Bot() as bot:
            await bot.start()

    try:
        await runner()
    except KeyboardInterrupt:
        LOGGER.warning("Shutting down due to Keyboard Interrupt...")


asyncio.run(main())
