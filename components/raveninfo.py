import ravenpy
import twitchio
from datetime import datetime, timezone
from twitchio.ext import commands
from utils.utils import format_timedelta, TimeSize

class RavenInfo(commands.Component):
    def __init__(self, bot: commands.Bot, rf_api: ravenpy.Ravenfall):
        self.bot = bot
        self.rf_api = rf_api

    @commands.command(aliases=('mult',))
    async def multiplier(self, ctx: commands.Context):
        mult = await self.rf_api.get_global_mult()
        start_time = mult.start_time
        end_time = mult.end_time
        now = datetime.now(timezone.utc)
        time_left = end_time - now
        if now > end_time:
            out_text = "Current global exp multiplier is 1×."
        else:
            out_text = f"Current global exp multiplier is {mult.multiplier}×, ending in {format_timedelta(time_left, TimeSize.LONG)}, thanks to {mult.event_name}!"

        await ctx.reply(f"/me {out_text}")
