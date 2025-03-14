# twitchio v3
from twitchio.ext import commands
from twitchio import eventsub
import twitchio
from dotenv import load_dotenv
import os
import logging
import asyncio
import ravenpy

from components.textresponses import RavenTextResponses

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
        await self.add_component(RavenTextResponses(self))
        await self.add_component(RavenHelperAPI(self))

        await self.add_component(TestCommands(self))
        LOGGER.info("Finished setup hook!")

    # async def event_command_error(self, error):
    #     if isinstance(error, commands.exceptions.CommandNotFound):
    #         return False



class TestCommands(commands.Component):
    def __init__(self, bot: Bot):
        self.bot = bot
    
    @commands.command(aliases=("hi",))
    async def hello(self, ctx: commands.Context):
        await ctx.send(f'hiii {ctx.author.name}! (eventsub)')

    @commands.command(aliases=("bye",))
    async def goodbye(self, ctx: commands.Context):
        await ctx.send(f'byeee {ctx.author.name}')





class RavenHelperAPI(commands.Component):
    def __init__(self, bot: Bot):
        self.bot = bot



rfapi: ravenpy.Ravenfall
async def main() -> None:
    # Setup logging, this is optional, however a nice to have...
    twitchio.utils.setup_logging(level=logging.INFO)
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
