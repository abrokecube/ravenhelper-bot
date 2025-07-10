from twitchio.ext import commands
import ravenpy

from utils import charutils
from utils import utils

class RavenCharacterTools(commands.Component):
    def __init__(self, bot: commands.Bot, rf_api: ravenpy.RavenNest):
        self.bot = bot
        self.rf_api = rf_api
    
    @commands.command()
    async def giftall(self, ctx: commands.Context, *args):
        """Generates a list of commands to gift a user all of a character's items
        
        Args:
            user (str): Twitch username.
            character (str): Character index or name.
            recipient (str): User to gift items to.
        """
        result = await charutils.search_user_characters(
            self.rf_api, ctx, *args, single_char_only=True
        )
        if result is None:
            return
        user_chars = result.chars
        if len(result.leftover_args) == 0:
            await ctx.send("uuh Missing recipient argument.")
            return
        
        character = user_chars[0]
        target_user = utils.filter_username(result.leftover_args[0])
        
        if not utils.is_twitch_username(target_user):
            await ctx.send("uuh Recipient is not a valid Twitch username.")
            return
        
        out_commands = []
        for item in character.items:
            if item.soulbound or item.equipped:
                continue
            out_commands.append(
                f"!gift {target_user} {item.item.name} {item.amount}"
            )

        if len(out_commands) == 0:
            await ctx.send("uuh This character has no items!")
            return
        
        out_str = "\n".join(out_commands)
        text_url = await utils.upload_to_pastes(out_str)
        if not text_url:
            await ctx.send("bruh Failed to upload text to pastes.")
        else:
            await ctx.send(
                f"Gift commands for {utils.get_char_identifier(character)} to {utils.unping(target_user)}: {text_url}"
            )

    @commands.command()
    async def sellall(self, ctx: commands.Context, character_name: str, sell_percent: float, add_value_percent: float):
        """Generates a list of commands to sell all items of a character
        
        Args:
            character_name (str): Character index or name.
            sell_percent (float): Percentage of item amount to sell (0.0 = 0%, 1.0 = 100%).
            add_value_percent (float): Percentage of item value to add to the sale (0.0 = 0%, 1.0 = 100%).
        """
        result = await charutils.search_user_characters(
            self.rf_api, ctx, character_name, single_char_only=True
        )
        if result is None:
            return
        user_chars = result.chars
        if len(user_chars) == 0:
            await ctx.send("uuh No characters found.")
            return
        
        character = user_chars[0]
        out_commands = []
        for item in character.items:
            if item.soulbound or item.equipped:
                continue
            item_amount = int(item.amount*(sell_percent/100))
            sell_value = item.item.sell_price
            sell_value += sell_value * (add_value_percent/100)
            sell_value = int(round(sell_value))
            if item_amount == 0:
                continue

            out_commands.append(
                f"!sell {item.item.name} {item_amount} {sell_value}"
            )

        if len(out_commands) == 0:
            await ctx.send("uuh This character has no items!")
            return
        
        out_str = "\n".join(out_commands)
        text_url = await utils.upload_to_pastes(out_str)
        if not text_url:
            await ctx.send("bruh Failed to upload text to pastes.")
        else:
            await ctx.send(
                f"Sell commands for {utils.get_char_identifier(character)}: {text_url}"
            )
        