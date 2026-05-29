# twitchio v3
from twitchio.ext import commands
from twitchio.ext import routines
import twitchio
from dotenv import load_dotenv
import os
import logging
import asyncio
import ravenpy
from datetime import timedelta



_ = load_dotenv()

LOGGER: logging.Logger = logging.getLogger("Bot")
TARGET_CHANNEL = os.getenv('TARGET_CHANNEL')
BOT_ID = os.getenv('BOT_ID')

class Bot(commands.Bot):
    def __init__(self):
        super().__init__(
            client_id=os.getenv('TWITCH_APP_ID'),
            client_secret=os.getenv('TWITCH_APP_SECRET'),
            bot_id=os.getenv('BOT_ID'),
            owner_id=os.getenv('OWNER_ID'),
            prefix="?"
        )

    async def setup_hook(self) -> None:
        if not BOT_ID:
            LOGGER.error("BOT_ID is not configued. Please configure your .env file.")
        LOGGER.info("Login with http://localhost:4343/oauth?scopes=user:read:chat%20user:write:chat%20user:bot")

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

    async def add_token(self, token, refresh):
        resp: twitchio.authentication.ValidateTokenPayload = await super().add_token(token, refresh)
        LOGGER.info(f"Added token for {resp.user_id}")
        if resp.user_id != BOT_ID:
            LOGGER.error("The authenticated user does not match BOT_ID")
        else:
            LOGGER.info("Success. You can now exit this script")
        

    @routines.routine(delta=timedelta(days=1), wait_first=True, wait_remainder=True)
    async def auto_token_reload(self):
        await self.reload_tokens()



rfapi: ravenpy.RavenNest
async def main() -> None:
    twitchio.utils.setup_logging(level=int(os.getenv("LOGGING_LEVEL")))

    async def runner() -> None:
        async with Bot() as bot:
            await bot.start()

    try:
        await runner()
    except KeyboardInterrupt:
        LOGGER.warning("Shutting down due to Keyboard Interrupt...")


asyncio.run(main())
