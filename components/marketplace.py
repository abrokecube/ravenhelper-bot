import twitchio
from twitchio.ext import commands
import ravenpy
import math
from datetime import datetime, timedelta, timezone
from utils.utils import format_timedelta, strjoin, pl
import thefuzz
import thefuzz.process
from typing import Iterable

SEARCH_SUCCESS_THRESHOLD = 80
MIN_SEARCH_THRESHOLD = 10

class MarketplaceCommands(commands.Component):
    def __init__(self, bot: commands.Bot, rf_api: ravenpy.Ravenfall):
        self.bot = bot
        self.rf_api = rf_api

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

    @commands.group(aliases=('marketplace', 'buy'), invoke_fallback=True)
    async def market(self, ctx: commands.Context, *item_name: str):
        """Get information about marketplace listings. Use the "list" subcommand
        to get the lastest item listings.
        
        Args:
            item_name (str, optional): Item name to query.
        """
        item_name_full = " ".join(item_name)
        item = await self.search_item(ctx, item_name_full)
        if not item:
            return
        market_items = await self.rf_api.get_marketplace()
        item_results = list(filter(lambda x: x.item == item, market_items))
        if len(item_results) == 0:
            await ctx.reply(f"{item.name} was not found in the marketplace.", me=True)
            return
        items_sorted = sorted(item_results, key=lambda x: x.amount, reverse=True)
        items_sorted = sorted(items_sorted, key=lambda x: x.price_per_item)
        now = datetime.now(timezone.utc)
        items_str_list = []
        for market_item in items_sorted:
            age_formatted = format_timedelta(now - market_item.created,max_terms=2)
            items_str_list.append(
                f'{market_item.price_per_item:,}c ({market_item.amount:,}, {age_formatted} ago)'
            )
        await ctx.reply(
            f"{pl(len(items_sorted), 'listing')} of {item.name} found: " \
            f"{strjoin(', ', *items_str_list)}",
            me=True
        )
        
        
    @market.command(aliases=(
        'time', 'newest', 'new', 'recent', 'latest',
        'time_reverse', 'oldest', 'old',
        'price','cheapest', 'cheap',
        'price_reverse', 'expensive',
    ))
    async def list(self, ctx: commands.Context, page: int = 1):
        """Get a list of marketplace items. Set the sorting method using one of 
        this command's aliases. Avalable sorting methods are: newest, oldest, cheapest,
        and expensive.
        
        Args:
            page (int, optional): Page number to navigate to.
        """
        market_items = await self.rf_api.get_marketplace()
        invoked_with = ctx.invoked_with.split()[-1]
        if invoked_with in ("newest", "new", 'time', 'recent', 'latest', 'list'):
            title = "Newest listings"
            sorted_items = sorted(market_items, key=lambda x: x.created, reverse=True)
        elif invoked_with in ("oldest", "old", 'time_reverse'):
            title = "Oldest listings"
            sorted_items = sorted(market_items, key=lambda x: x.created)
        elif invoked_with in ("price", "cheapest", 'cheap'):
            title = "Cheapest listings"
            sorted_items = sorted(market_items, key=lambda x: x.price_per_item)
        elif invoked_with in ("price_reverse", "expensive"):
            title = "Most expensive listings"
            sorted_items = sorted(market_items, key=lambda x: x.price_per_item, reverse=True)
        else:
            raise ValueError("you forgot something aga")

        items_per_page = 5
        max_pages = math.ceil(len(market_items)/items_per_page)
        if page < 1:
            await ctx.reply("uuh Page number starts at 1")
            return
        elif page > max_pages:
            await ctx.reply(f"uuh There are only {max_pages} pages")
            return
        items_str = []
        for item in sorted_items[(page-1)*items_per_page:page*items_per_page]:
            time_delta = format_timedelta(datetime.now(timezone.utc) - item.created, max_terms=2)
            item_str = f"{item.item.name}: {item.price_per_item:,}c ("
            if item.amount > 1:
                item_str += f"{item.amount:,} available, "
            item_str += f"{time_delta} ago)"
            items_str.append(item_str)
        out_str = f"{title} ✦ Page {page}/{max_pages} ✦ {' • '.join(items_str)}"
        await ctx.reply(out_str, me=True)
