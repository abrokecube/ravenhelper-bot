import ravenpy
import twitchio
from datetime import datetime, timezone
from twitchio.ext import commands
from utils.utils import format_timedelta, TimeSize, is_bot_owner
import time

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

    @is_bot_owner()
    @commands.command(aliases=('ping',))
    async def responsetime(self, ctx: commands.Context):
        """Tests response time of RavenNest"""
        await ctx.reply("Testing for 4 seconds...")
        response_times = []
        master_t1 = time.monotonic()
        for _ in range(10):
            t1 = time.monotonic()
            await self.rf_api._exp_multiplier()
            t2 = time.monotonic()
            response_times.append(t2-t1)
            if t2 - master_t1 > 4:
                break
        t_min = int(min(response_times)*1000)
        t_max = int(max(response_times)*1000)
        t_avg = int((sum(response_times) / len(response_times)) * 1000)
        await ctx.reply(
            f"Sent {len(response_times)} requests to RavenNest. Min = {t_min}ms, Max = {t_max}ms, Avg = {t_avg}ms",
            me=True
        )
        
