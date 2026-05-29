import asyncio
import twitchio
from twitchio.ext import commands
import ravenpy
import math
from datetime import datetime, timedelta, timezone
from utils.utils import format_timedelta, strjoin, pl, truncate_sentence
from utils import utils
import thefuzz
import thefuzz.process
from typing import Iterable, Tuple

SEARCH_SUCCESS_THRESHOLD = 80
MIN_SEARCH_THRESHOLD = 10

class MarketplaceCommands(commands.Component):
    def __init__(self, bot: commands.Bot, rf_api: ravenpy.RavenNest):
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
            await ctx.send(f"Please include an item name.")
            return None
        search_result = thefuzz.process.extract(item_name_full, ravenpy.get_all_item_names(), limit=7, scorer=thefuzz.fuzz.ratio)
        result, score = search_result[0]
        if score > SEARCH_SUCCESS_THRESHOLD:
            return ravenpy.get_item(result)
        else:
            a = ', '.join([x[0] for x in search_result if x[1] > MIN_SEARCH_THRESHOLD])
            if not a:
                await ctx.send(f"No results for '{item_name_full}'")
            else:
                await ctx.send(f"Couldn't find '{item_name_full}', did you mean {a}?")
            return None

    @commands.group(aliases=('marketplace', 'buy'), invoke_fallback=True)
    async def market(self, ctx: commands.Context, *item_name: str):
        """Get information about marketplace listings. Use the "list" subcommand
        to get the lastest item listings.
        
        Args:
            arg (str, optional): Write "inspect" to see item seller info.
            item_name (str, optional): Item name to query.
        """
        item_name_args = list(item_name)
        inspect_items = False
        if item_name_args and item_name_args[0] == "inspect":
            item_name_args.pop(0)
            inspect_items = True
            
        item_name_full = " ".join(item_name_args)
        item = await self.search_item(ctx, item_name_full)
        if not item:
            return
        market_items = await self.rf_api.get_marketplace()
        item_results = list(filter(lambda x: x.item == item, market_items))
        if len(item_results) == 0:
            await ctx.send(f"{item.name} was not found in the marketplace.", me=True)
            return
        
        items_sorted = sorted(item_results, key=lambda x: x.amount, reverse=True)
        items_sorted = sorted(items_sorted, key=lambda x: x.price_per_item)
        
        item_owners = [''] * len(items_sorted)
        if inspect_items:
            item_owners = await self.get_item_owners(items_sorted)
        
        now = datetime.now(timezone.utc)
        items_str_list = []
        for owner, market_item in zip(item_owners, items_sorted):
            age_formatted = format_timedelta(now - market_item.created,max_terms=2)
            item_by = ""
            if inspect_items:
                item_by = f" by {owner.user_name}: {truncate_sentence(owner.identifier, 20)}"
            items_str_list.append(
                f'{market_item.price_per_item:,}c ({market_item.amount:,}, {age_formatted} ago{item_by})'
            )
        await ctx.send(
            f"{pl(len(items_sorted), 'listing')} of {item.name} found: " \
            f"{strjoin(', ', *items_str_list)}",
            me=True
        )

    async def get_item_owners(
        self, items_sorted: Iterable[ravenpy.MarketplaceItem]
    ) -> tuple[ravenpy.Character]:
        item_owners = []
        char_ids = {}
        for market_item in items_sorted:
            char_ids[market_item.seller_char_id] = ''
        char_tasks = [self.rf_api.get_character_from_id(x) for x in char_ids.keys()]
        task_results = await asyncio.gather(*char_tasks)
        for result in task_results:
            result: ravenpy.Character
            char_ids[result.char_id] = result
        for idx, market_item in enumerate(items_sorted):
            owner_char: ravenpy.Character = char_ids[market_item.seller_char_id]
            item_owners.append(owner_char)
        return tuple(item_owners)
        
        
    @market.command(aliases=(
        'time', 'newest', 'new', 'recent', 'latest',
        'time_reverse', 'oldest', 'old',
        'price','cheapest', 'cheap',
        'price_reverse', 'expensive',
    ))
    async def list(self, ctx: commands.Context, *args):
        """Get a list of marketplace items. Set the sorting method using one of 
        this command's aliases. Avalable sorting methods are: newest, oldest, cheapest,
        and expensive.
        
        Args:
            arg (str, optional): Write "inspect" to see item seller info.
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
    
        items_str = []
        arg_result = utils.split_arguments(
            args,
            utils.SplitQuery(['inspect'], optional=True),
            utils.SplitWildcard(),
        )
        inspect_q, page_q = [x.text or '' for x in arg_result]
        page = 1
        if page_q:
            page = int(page_q)
        inspect_items = bool(inspect_q)
        
        items_per_page = 5
        max_pages = math.ceil(len(market_items)/items_per_page)
        if page < 1:
            await ctx.send("uuh Page number starts at 1")
            return
        elif page > max_pages:
            await ctx.send(f"uuh There are only {max_pages} pages")
            return
        
        sorted_sliced = sorted_items[(page-1)*items_per_page:page*items_per_page]
        
        item_owners = [''] * len(sorted_sliced)
        if inspect_items:
            item_owners = await self.get_item_owners(sorted_sliced)

        for owner, item in zip(item_owners, sorted_sliced):
            time_delta = format_timedelta(datetime.now(timezone.utc) - item.created, max_terms=2)
            item_by = ""
            if inspect_items:
                item_by = f" by {owner.user_name}: {truncate_sentence(owner.identifier, 20)}"

            item_str = f"{item.item.name}: {item.price_per_item:,}c ("
            if item.amount > 1:
                item_str += f"{item.amount:,} available, "
            item_str += f"{time_delta} ago{item_by})"
            items_str.append(item_str)
        out_str = f"{title} ✦ Page {page}/{max_pages} ✦ {' • '.join(items_str)}"
        await ctx.send(out_str, me=True)
