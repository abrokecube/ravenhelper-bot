import thefuzz.fuzz
import thefuzz.process
import twitchio
from twitchio.ext import commands
import ravenpy
from ravenpy import ItemTypes, Skills
from cachetools import TTLCache, cached
from utils.utils import is_bot_owner
import random
import thefuzz
from utils.utils import strjoin, strenclose, strextend, strjoin_len, format_seconds, \
    pl, TimeSize, SplitQuery, split_arguments, SplitWildcard

from utils import langstuff
from typing import Iterable

MIN_SEARCH_THRESHOLD = 10
SEARCH_SUCCESS_THRESHOLD = 80
MAX_MSG_LENGTH = 485

@cached(cache=TTLCache(maxsize=1, ttl=15))
def get_wood():
    wood_stuff = [x for x in ravenpy.get_all_items() if x.drop_skill == Skills.Woodcutting]
    wood_stuff.sort(key=lambda x: x.drop_level)
    items_str = [f"{x.name.replace(' Logs', '')} - {x.drop_level}" for x in wood_stuff]
    return ' • '.join(items_str)

@cached(cache=TTLCache(maxsize=1, ttl=15))
def get_fish():
    fish_stuff = [x for x in ravenpy.get_all_items() if x.drop_skill == Skills.Fishing]
    fish_stuff.sort(key=lambda x: x.drop_level)
    items_str = [f"{x.name.replace('Raw ', '')} - {x.drop_level}" for x in fish_stuff]
    return ' • '.join(items_str)

@cached(cache=TTLCache(maxsize=1, ttl=15))
def get_crops():
    farm_stuff = [x for x in ravenpy.get_all_items() if x.drop_skill == Skills.Farming]
    farm_stuff.sort(key=lambda x: x.drop_level)
    items_str = [f"{x.name} - {x.drop_level}" for x in farm_stuff]
    return ' • '.join(items_str)

@cached(cache=TTLCache(maxsize=1, ttl=15))
def get_forage():
    gather_stuff = [x for x in ravenpy.get_all_items() if x.drop_skill == Skills.Gathering]
    gather_stuff.sort(key=lambda x: x.drop_level)
    items_str = [f"{x.name} - {x.drop_level}" for x in gather_stuff]
    return ' • '.join(items_str)

@cached(cache=TTLCache(maxsize=1, ttl=15))
def get_ores():
    mining_stuff = [x for x in ravenpy.get_all_items() if x.drop_skill == Skills.Mining]
    mining_stuff.sort(key=lambda x: x.drop_level)
    items_str = [f"{x.name.replace(' Ore', '')} - {x.drop_level}" for x in mining_stuff]
    return ' • '.join(items_str)

@cached(cache=TTLCache(maxsize=1, ttl=30))
def get_split_query():
    return SplitQuery(ravenpy.get_all_item_names())

class RavenItemCommands(commands.Component):
    def __init__(self, bot: commands.Bot, rf_api: ravenpy.Ravenfall):
        self.bot = bot
        self.rf_api = rf_api

    @commands.command(aliases=("woodcuttingitems",))
    async def wood(self, ctx: commands.Context):
        await ctx.reply(f"/me 🌳 Woodcutting level required to obtain logs: {get_wood()}")
    
    @commands.command(aliases=("fishes","fishingitems"))
    async def fish(self, ctx: commands.Context):
        await ctx.reply(f"/me 🎣 Fishing level required to obtain fish: {get_fish()}")

    @commands.command(aliases=("crop","farmingitems"))
    async def crops(self, ctx: commands.Context):
        await ctx.reply(f"/me 🌾 Farming level required to obtain crops: {get_crops()}")

    @commands.command(aliases=("foraging","gatheringitems"))
    async def forage(self, ctx: commands.Context):
        await ctx.reply(f"/me 🧺 Gathering level required to obtain items: {get_forage()}")

    @commands.command(aliases=("ore","bar","bars","miningitems"))
    async def ores(self, ctx: commands.Context):
        await ctx.reply(f"/me ⛏️ Mining level required to obtain ores: {get_ores()}")

    async def search_item(self, ctx: commands.Context, query: str | Iterable[str]) -> ravenpy.Item | None:
        if isinstance(query, str):
            item_name_full = query
        elif isinstance(query, (list, tuple)):
            item_name_full = ' '.join(query)
        else:
            raise ValueError("item_name was not a valid type!")
        if item_name_full == '':
            await ctx.reply(f"Please include an item name.")
            return None
        search_result = thefuzz.process.extract(item_name_full, ravenpy.get_all_item_names(), limit=7, scorer=thefuzz.fuzz.ratio)
        result, score = search_result[0]
        if score > SEARCH_SUCCESS_THRESHOLD:
            return ravenpy.get_item(result)
        else:
            a = ', '.join([x[0] for x in search_result if x[1] > MIN_SEARCH_THRESHOLD])
            if not a:
                await ctx.reply(f"No results for '{item_name_full}'")
            else:
                await ctx.reply(f"Couldn't find '{item_name_full}', did you mean {a}?")
            return None

    @commands.command(aliases=('info',))
    async def item(self, ctx: commands.Context, *item_name):
        """Get information about an item.
        
        Args:
            item_name (str): Name of an item to query.
        """
        item_name_full = " ".join(item_name)
        if item_name_full.lower() in ['rand', 'random']:
            result = random.choice(ravenpy.get_all_item_names())
            item = ravenpy.get_item(result)
        else:
            item = await self.search_item(ctx, item_name_full)
        if not item:
            return
        
        item_category = item.category.name
        name_desc = strjoin(
            " – ", item.name, item_category, strenclose("\"", "\"", " ", item.description),
        )

        stats_awdf = []
        for thing in item.stats:
            stats_awdf.append(f"{langstuff.stat_names[thing.stat]} {thing.level}")
        stats = ", ".join(stats_awdf)

        effects_asdf = []
        for thing in item.effects:
            stat_name = langstuff.status_effect_names_short[thing.effect]
            stat_duration = ""
            if thing.duration > 0:
                stat_duration = f"for {format_seconds(thing.duration, TimeSize.MEDIUM)}"
            stat_percent = ""
            if thing.percentage > 0:
                stat_percent = f"+{('%.1f' % (thing.percentage*100)).rstrip('0').rstrip('.')}%"
            stat_min = ""
            if thing.min_amount > 0:
                stat_min = f"(Min: {thing.min_amount})"
            effects_asdf.append(strjoin(' ', stat_name, stat_percent, stat_min, stat_duration))
        effects = ", ".join(effects_asdf)

        level_asdf = []
        level = ""
        if item.equip_requirements:
            for thing in item.equip_requirements:
                level_asdf.append(f"{thing.skill.name} {thing.level}")
            level = ", ".join(level_asdf) + " to equip"

        crafting_level = ""
        crafting = ""
        if item.craft_skill:
            crafting_level = f"{item.craft_skill.name} {item.craft_level} to create"
            ingredients = []
            for thing in item.craft_ingredients:
                ingredients.append(f"{thing.item.name} ×{thing.amount:,}")
            crafting = "Ingredients: " + ", ".join(ingredients)

        craft_fail_item = ""
        if item.craft_fail_item:
            craft_fail_item = f"May create {item.craft_fail_item.name} instead"
        
        drop_level = ""
        if item.drop_skill:
            drop_sources = []
            drop_sources.append(f"{item.drop_skill.name} level {item.drop_level}")
            drop_level = f"From {', '.join(drop_sources)}"
        value = f"Sells for {pl(item.sell_price, 'coin')}"

        cooldown_time = ""
        if item.drop_cooldown:
            cooldown_time = f"Can be obtained every {format_seconds(item.drop_cooldown, TimeSize.MEDIUM)}"

        enchants = ""
        if item.enchantments: 
            enchants = f"Up to {pl(item.enchantments, 'enchantment')}"
        
        raid_drop = ""
        if item.raid_min_drop > 0:
            raid_drop = "Can drop in raids/dungeons"
            if item.raid_drop_month_length > 0:
                raid_drop += f" on {langstuff.month_names[item.raid_drop_month_start-1]}"
                if item.raid_drop_month_length > 1:
                    end_month = (item.raid_drop_month_start+item.raid_drop_month_length-1) % 12 + 1
                    raid_drop += f"-{langstuff.month_names[end_month]}"
            if item.drop_slayer_requirement > 1:
                raid_drop += f" with Slayer {item.drop_slayer_requirement}"

        soulbound = ""
        if item.soulbound:
            soulbound = "Cannot be gifted"

        if (len(crafting) + len(effects)) > 250:
            out_strs = strjoin_len(
                ' • ', MAX_MSG_LENGTH, name_desc, stats, effects, level, drop_level,
                enchants, raid_drop, soulbound, value
            )
            out_strs = strextend(out_strs, MAX_MSG_LENGTH, f" | Use ?req to see crafting info")
        else:
            out_strs = strjoin_len(
                ' • ', MAX_MSG_LENGTH, name_desc, stats, effects, level, drop_level, cooldown_time, 
                crafting_level, craft_fail_item, crafting, enchants, raid_drop, soulbound, value
            )
        for out_str in out_strs:
            await ctx.reply(f"/me {out_str}")

    @commands.command(aliases=('requirements','craft','reqs'))
    async def req(self, ctx: commands.Context, *item_name: str):
        """Get requirements to obtain an item.
        
        Args:
            item_name (str): Name of an item to query.
        """
        item_name_full = " ".join(item_name)
        count = 1
        if item_name[-1].isdigit():
            item_name_full = " ".join(item_name[:-1])
            count = int(item_name[-1])
        item = await self.search_item(ctx, item_name_full)
        if not item:
            return
        
        level_asdf = []
        level = ""
        if item.equip_requirements:
            for thing in item.equip_requirements:
                level_asdf.append(f"{thing.skill.name} {thing.level}")
            level = ", ".join(level_asdf) + " to equip"
        
        crafting_level = ""
        crafting = ""
        if item.craft_skill:
            crafting_level = f"{item.craft_skill.name} {item.craft_level} to create"
            ingredients = []
            for thing in item.craft_ingredients:
                ingredients.append(f"{thing.amount*count:,}× {pl(thing.amount*count,thing.item.name, False)}")

            crafting = f"To create {count:,}, you will need " + ", ".join(ingredients[:-1])
            if len(ingredients) > 1:
                crafting += f" and {ingredients[-1]}"
            else:
                crafting += ingredients[-1]
        else:
            crafting = "Uncraftable"

        craft_fail_item = ""
        if item.craft_fail_item:
            craft_fail_item = f"May create {item.craft_fail_item.name} instead"
        
        drop_level = ""
        if item.drop_skill:
            drop_sources = []
            drop_sources.append(f"{item.drop_skill.name} level {item.drop_level}")
            drop_level = f"From {', '.join(drop_sources)}"
        
        value = f"Sells for {pl(item.sell_price, 'coin')}"

        raid_drop = ""
        if item.raid_min_drop > 0:
            raid_drop = "Can drop in raids/dungeons"
            if item.raid_drop_month_length > 0:
                raid_drop += f" on {langstuff.month_names[item.raid_drop_month_start-1]}"
                if item.raid_drop_month_length > 1:
                    end_month = (item.raid_drop_month_start+item.raid_drop_month_length-1) % 12 + 1
                    raid_drop += f"-{langstuff.month_names[end_month]}"
            if item.raid_drop_month_length > 1:
                raid_drop += f" with Slayer {item.drop_slayer_requirement}"
        
        cooldown_time = ""
        if item.drop_cooldown:
            cooldown_time = f"Can be obtained every {format_seconds(item.drop_cooldown, TimeSize.LONG)}"

        out_str = strjoin(
            ' • ', item.name, level, drop_level, cooldown_time, crafting_level,
            crafting, craft_fail_item, raid_drop, value
        )
        await ctx.reply(f"/me {out_str}")

    @commands.command(aliases=("usage","use"))
    async def uses(self, ctx: commands.Context, *item_name: str):
        """Get uses for an item as an ingredient.
        
        Args:
            item_name (str): Name of an item to query.
        """
        item = await self.search_item(ctx, item_name)
        if not item:
            return
        
        if len(item.used_in) == 0:
            await ctx.reply(f"/me {item.name} isn't used in any recipes.")
            return
        item_list = sorted([x.name for x in item.used_in])
        out_str = ', '.join(item_list[:-1])
        if len(item_list) > 1:
            out_str += f" and {item_list[-1]}"
        else:
            out_str += item_list[-1]
        await ctx.reply(f"/me {item.name} is used in creating {out_str}")
    
    @commands.command(aliases=("itemsearch","find"))
    async def search(self, ctx: commands.Context, *item_name: str):
        """A simple item name search command.
        
        Args:
            item_name (str): Name of an item to query.
        """
        item_name_full = " ".join(item_name)
        search_result = thefuzz.process.extract(item_name_full, ravenpy.get_all_item_names(), limit=25, scorer=thefuzz.fuzz.ratio)
        results = ", ".join([x[0] for x in search_result if x[1] > MIN_SEARCH_THRESHOLD])
        if len(results) == 0:
            await ctx.reply(f"No results for '{item_name_full}.'")
            return
        await ctx.reply(f"Search results for '{item_name_full}': {results}")


    @is_bot_owner()
    @commands.command()
    async def fetchitems(self, ctx: commands.Context):
        """Refreshes the internal item database."""
        await ctx.reply(f"Fetching items...", me=True)
        await self.rf_api.refresh_items()
        await ctx.reply(f"Successfully refetched {len(ravenpy.get_all_items())} items", me=True)

    @is_bot_owner()
    @commands.command()
    async def testing(self, ctx: commands.Context, *args: str):
        """aga"""
        username_split = ['mine craft', 'btmc', 'abroke cube gaming']
        asdfasdf = split_arguments(args, SplitWildcard(1), SplitQuery(username_split), get_split_query(), SplitWildcard(1))
        print(asdfasdf)
        ...