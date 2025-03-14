import asyncio
import aiohttp
from async_lru import alru_cache
import base64
import json
from enum import Enum
from typing import List, Dict, Any, Callable
import math
from datetime import datetime, timedelta
import os

import thefuzz
import thefuzz.fuzz
import thefuzz.process
from . import itemdefs
from .enums import *
from .itemdata import get_item_data


class ItemEffect:
    def __init__(self, **kwargs):
        self.effect: Effects = kwargs.get('effect')
        self.duration: float = kwargs.get('duration')
        self.percentage: float = kwargs.get('percentage')
        self.min_amount: float = kwargs.get('min_amount')

class ItemRequirement:
    def __init__(self, **kwargs):
        self.skill: Skills = kwargs.get('skill')
        self.level: int = kwargs.get('level')

class ItemStat:
    def __init__(self, **kwargs):
        self.stat: Stat = kwargs.get('stat')
        self.level: int = kwargs.get('level')

class Ingredient:
    def __init__(self, **kwargs):
        self.item: Item = kwargs.get('item')
        self.amount: int = kwargs.get('amount')

class Item:
    def __init__(self, data):
        self.id = data.get('id')
        self.name = data.get('name')
        self.description = data.get('description')
        self.level = data.get('level')
        self.type: ItemType | None = ItemType(data.get("type")) if data.get('type') else None
        self.category: ItemCategory | None = ItemCategory(data.get("category")) if data.get('category') else None
        self.material: ItemMaterials | None = ItemMaterials(data.get("material")) if data.get('material') else None
        self.sell_price = data.get("sell_price")
        self.buy_price = data.get("buy_price")
        self.enchantments = data.get("enchantments")
        self.soulbound = data.get("soulbound")
        self.craft_skill = data.get("craft_skill")
        self.craft_level = data.get("craft_level")
        self.min_success_rate = data.get("min_success_rate")
        self.max_success_rate = data.get("max_success_rate")
        self.preperation_time = data.get("preperation_time")
        self.is_fixed_success_rate = data.get("is_fixed_success_rate")
        self.drop_skill = data.get("drop_skill")
        self.drop_level = data.get("drop_level")
        self.drop_chance = data.get("drop_chance")
        self.drop_cooldown = data.get("drop_cooldown")
        self.raid_drop_month_start = data.get("raid_drop_month_start")
        self.raid_drop_month_length = data.get("raid_drop_month_length")
        self.raid_min_drop = data.get("raid_min_drop")
        self.raid_max_drop = data.get("raid_max_drop")
        self.raid_drop_tier = data.get("raid_drop_tier")
        self.drop_slayer_requirement = data.get("drop_slayer_requirement")

        self._craft_fail_item = data.get("craft_fail_item")
        self._craft_ingredients = data.get("craft_ingredients")
        self._used_in = data.get("used_in")
        self._modified = data.get("modified")

        self.craft_fail_item: Item = None
        self.craft_ingredients: List[Item] = []
        self.used_in = []

        self.effects = []
        for effect in data.get("effects"):
            self.effects.append(ItemEffect(**{
                "effect": Effects(effect['id']),
                "duration": effect["duration"],
                "percentage": effect["percentage"],
                "min_amount": effect["min_amount"],
            }))

        self.equip_requirements = []
        for req in data.get('equip_requirements'):
            self.equip_requirements.append(ItemRequirement(**{
                "skill": Skills(req['skill']),
                "level": req['level']
            }))

        self.stats = []
        for stat in data.get('stats'):
            self.stats.append(ItemStat(**{
                "stat": Stat(stat['stat']),
                "level": stat['level']
            }))

class CharacterStat:
    def __init__(self, skill: Skills, exp: float, level: int):
        self.skill = skill
        self.level = level
        self.level_exp = exp
        self.total_exp_for_level = experience_for_level(level+1)

class ClanStat:
    def __init__(self, **kwargs):
        self.skill = ClanSkill[kwargs.get('name').capitalize()]
        self.level = kwargs.get('level')
        self.experience = kwargs.get('experience')
        self.max_level = kwargs.get('maxLevel')

class CharacterClanRole:
    def __init__(self, **kwargs):
        self.role = ClanRole(kwargs.get('level'))
        self.joined = _parse_time(kwargs.get('joined'))

class CharacterClan:
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.owner_twitch_id = kwargs.get('owner')
        self.owner_id = kwargs.get('ownerUserId')
        self.level = kwargs.get('level')
        self.experience = kwargs.get('experience')
        self.name = kwargs.get('name')
        self.logo = kwargs.get('logo')
        self.skills = []
        skills = kwargs.get('clanSkills')
        if skills:
            for skill in skills:
                self.skills.append(ClanStat(**skill))

class CharacterItem:
    def __init__(self, **kwargs):
        self.item: Item = _items_id_data[kwargs.get('itemId')]
        self.amount = kwargs.get('amount')
        self.equipped = kwargs.get('equipped')
        self.soulbound = kwargs.get('soulbound')
        self.enchantment = kwargs.get('enchantment')

class CharacterStatusEffect:
    def __init__(self, **kwargs):
        self.effect = Effects(kwargs.get('type'))
        self.amount = kwargs.get('amount')
        self.duration = kwargs.get('duration')
        self.time_left = kwargs.get('timeLeft')
        self.start_time = _parse_time(kwargs.get('startUtc'))
        self.expires = _parse_time(kwargs.get('expiresUtc'))

class CharacterEquipment:
    def __init__(self, equipment: List[CharacterItem]):
        self.helmet: CharacterItem | None = None
        self.chest: CharacterItem | None = None
        self.gloves: CharacterItem | None = None
        self.leggings: CharacterItem | None = None
        self.boots: CharacterItem | None = None
        self.ring: CharacterItem | None = None
        self.amulet: CharacterItem | None = None
        self.staff: CharacterItem | None = None
        self.weapon: CharacterItem | None = None  # melee weapon
        self.bow: CharacterItem | None = None
        self.pet: CharacterItem | None = None
        self.shield: CharacterItem | None = None

        for item in equipment:
            if not item.equipped:
                continue
            match item.item.type:
                case ItemType.TwoHandedSword | ItemType.OneHandedSword:
                    self.weapon = item
                case ItemType.TwoHandedAxe | ItemType.OneHandedAxe:
                    self.weapon = item
                case ItemType.TwoHandedStaff:
                    self.staff = item
                case ItemType.TwoHandedBow:
                    self.bow = item
                case ItemType.TwoHandedSpear:
                    self.weapon = item
                case ItemType.Helmet:
                    self.helmet = item
                case ItemType.Chest:
                    self.chest = item
                case ItemType.Gloves:
                    self.gloves = item
                case ItemType.Boots:
                    self.boots = item
                case ItemType.Leggings:
                    self.leggings = item
                case ItemType.Shield:
                    self.shield = item
                case ItemType.Ring:
                    self.ring = item
                case ItemType.Amulet:
                    self.amulet = item
                case ItemType.Pet:
                    self.pet = item

    def __iter__(self):
        return [
            self.helmet, self.chest, self.gloves, self.leggings, self.boots, 
            self.ring, self.amulet, self.staff, self.weapon, self.bow, self.pet, 
            self.shield,
        ]

fighting_replacements = {
    "Atk": "Attack",
    "Heal": "Healing",
    "Def": "Defense",
    "Str": "Strength"
}

def _parse_time(iso_str: str):
    s = ""
    if iso_str[-1] == "Z":
        s = iso_str[:-1] + '+00:00'
    else:
        s = iso_str + '+00:00'
    return datetime.fromisoformat(s)

def _class_or_none(_obj: Any, _class: Any):
    if _obj is not None:
        return _class(**_obj)

def _getitem_or_none(_obj: Any, _obj2: Any):
    if _obj is not None:
        return _obj2[_obj]

def _call_or_none(_obj: Any, _callable: Callable):
    if _obj is not None:
        return _callable(_obj)

class Character:
    def __init__(self, data):
        self._raw: Dict = data
        self.id: str = data['id']
        self.user_id: str = data['userId']
        self.user_name: str = data['userName']
        self.identifier: str = data['identifier']
        self.character_index: int = data['characterIndex']+1
        if not self.identifier:
            self.identifier = str(self.character_index)
        self.name: str = self.identifier
        self.patreon_tier: int = data['patreonTier']
        self.is_hidden_in_highscore: bool = data['isHiddenInHighscore']
        self.coins: int = data['resources']['coins']

        self.is_admin: bool = data['isAdmin']
        self.is_moderator: bool = data['isModerator']
        self.is_rejoin: bool = data['isRejoin']  # what does this mean

        self.clan: CharacterClan | None = _class_or_none(data['clan'], CharacterClan)
        self.clan_role: CharacterClanRole | None = _class_or_none(data['clanRole'], CharacterClanRole)
        self.attack = CharacterStat(Skills.Attack, data['skills']['attack'], data['skills']['attackLevel'])
        self.defense = CharacterStat(Skills.Defense, data['skills']['defense'], data['skills']['defenseLevel'])
        self.strength = CharacterStat(Skills.Strength, data['skills']['strength'], data['skills']['strengthLevel'])
        self.health = CharacterStat(Skills.Health, data['skills']['health'], data['skills']['healthLevel'])
        self.magic = CharacterStat(Skills.Magic, data['skills']['magic'], data['skills']['magicLevel'])
        self.ranged = CharacterStat(Skills.Ranged, data['skills']['ranged'], data['skills']['rangedLevel'])
        self.woodcutting = CharacterStat(Skills.Woodcutting, data['skills']['woodcutting'], data['skills']['woodcuttingLevel'])
        self.fishing = CharacterStat(Skills.Fishing, data['skills']['fishing'], data['skills']['fishingLevel'])
        self.mining = CharacterStat(Skills.Mining, data['skills']['mining'], data['skills']['miningLevel'])
        self.crafting = CharacterStat(Skills.Crafting, data['skills']['crafting'], data['skills']['craftingLevel'])
        self.cooking = CharacterStat(Skills.Cooking, data['skills']['cooking'], data['skills']['cookingLevel'])
        self.farming = CharacterStat(Skills.Farming, data['skills']['farming'], data['skills']['farmingLevel'])
        self.slayer = CharacterStat(Skills.Slayer, data['skills']['slayer'], data['skills']['slayerLevel'])
        self.sailing = CharacterStat(Skills.Sailing, data['skills']['sailing'], data['skills']['sailingLevel'])
        self.healing = CharacterStat(Skills.Healing, data['skills']['healing'], data['skills']['healingLevel'])
        self.gathering = CharacterStat(Skills.Gathering, data['skills']['gathering'], data['skills']['gatheringLevel'])
        self.alchemy = CharacterStat(Skills.Alchemy, data['skills']['alchemy'], data['skills']['alchemyLevel'])
        self.combat_level = int(((self.attack.level + self.defense.level + self.health.level + self.strength.level) / 4) + ((self.ranged.level + self.magic.level + self.healing.level) / 8))
        #  (int)(((skills.AttackLevel + skills.DefenseLevel + skills.HealthLevel + skills.StrengthLevel) / 4f) + ((skills.RangedLevel + skills.MagicLevel + skills.HealingLevel) / 8f))
        self.stats = [
            self.attack, self.defense, self.strength, self.health, self.magic,
            self.ranged, self.woodcutting, self.fishing, self.mining, self.crafting,
            self.cooking, self.farming, self.slayer, self.sailing, self.healing,
            self.gathering, self.alchemy
        ]
        self._skill_dict = {
            Skills.Attack: self.attack,
            Skills.Defense: self.defense,
            Skills.Strength: self.strength,
            Skills.Health: self.health,
            Skills.Woodcutting: self.woodcutting,
            Skills.Fishing: self.fishing,
            Skills.Mining: self.mining,
            Skills.Crafting: self.crafting,
            Skills.Cooking: self.cooking,
            Skills.Farming: self.farming,
            Skills.Slayer: self.slayer,
            Skills.Magic: self.magic,
            Skills.Ranged: self.ranged,
            Skills.Sailing: self.sailing,
            Skills.Healing: self.healing,
            Skills.Gathering: self.gathering,
            Skills.Alchemy: self.alchemy
        }

        state = data['state']
        self.hp: int = state['health']
        self.in_raid: bool = state['inRaid']
        self.in_arena: bool = state['inArena']
        self.in_dungeon: bool = state['inDungeon']
        self.in_onsen: bool = state['inOnsen']
        self.has_joined_dungeon: bool = state['joinedDungeon']
        self.exp_per_hour: int = state['expPerHour']
        if not self.exp_per_hour:
            self.exp_per_hour = 0

        self.training: Skills | None = None
        self.island: Islands = _getitem_or_none(state['island'], Islands)
        self.destination: Islands = _getitem_or_none(state['destination'], Islands)
        self.waiting_for_ferry: bool = self.destination and self.destination == self.island
        self.estimated_level_time: timedelta = _call_or_none(state['estimatedTimeForLevelUp'], _parse_time)
        self.x: int = state['x']
        self.y: int = state['y']
        self.z: int = state['z']
        # self.rested_time_s = int(state['restedTime'])
        self.rested_time = timedelta(seconds=int(state['restedTime']))
        self.is_captain = state['isCaptain']

        self.auto_join_dungeon_count = state['autoJoinDungeonCounter']
        if state['autoJoinDungeonCounter'] == 2147483647:
            self.auto_join_dungeon_count = math.inf
        self.auto_join_raid_count = state['autoJoinRaidCounter']
        if state['autoJoinRaidCounter'] == 2147483647:
            self.auto_join_raid_count = math.inf
        
        self.dungeon_combat_style = _call_or_none(state['dungeonCombatStyle'], Skills)
        self.raid_combat_style = _call_or_none(state['raidCombatStyle'], Skills)

        self.items: List[CharacterItem] = []
        self._equipment: List[CharacterItem] = []
        self._id_item: Dict[str, CharacterItem] = {}
        for item in data['inventoryItems']:
            char_item = CharacterItem(**item)
            if char_item.equipped:
                self._equipment.append(char_item)
            else:
                self.items.append(char_item)
            self._id_item[char_item.item.id] = char_item
        self.equipment = CharacterEquipment(self._equipment)
        
        self.status_effects = []
        for effect in data['statusEffects']:
            self.status_effects.append(CharacterStatusEffect(**effect))

        self.target_item: CharacterItem | None = None
        if state['task'] == "Fighting":
            task_arg = state['taskArgument'].capitalize()
            replace = fighting_replacements.get(task_arg)
            if replace:
                task_arg = replace
            self.training = Skills[task_arg]
        elif (not state['task']) or state['task'].lower() == "none":
            pass
        else:
            self.training = Skills[state['task'].capitalize()]
            target_item_name, f_score = thefuzz.process.extract(state['taskArgument'], _items_names, limit=1, scorer=thefuzz.fuzz.ratio)[0]
            if f_score > 90:
                target_item = _items_name_data[target_item_name]
                inv_item = self.get_item(target_item)
                if not inv_item:
                    inv_item = CharacterItem(
                        item=target_item,
                        amount=0,
                        equipped=False,
                        soulbound=False,
                        enchantment=''
                    )
                self.target_item = inv_item

        if not self.training:
            if (not self.island) and (not self.destination == Islands.Ferry):
                self.training = Skills.Sailing


    def get_item(self, item: Item | str | itemdefs.Items):
        if isinstance(item, Item):
            result = self._id_item.get(item.id)
        elif isinstance(item, str):
            if item.count('-') == 4:
                result = self._id_item.get(item)
            else:
                item_query = get_item(item)
                if item_query:
                    result = self._id_item.get(item_query.id)
                else:
                    result = None
        elif isinstance(item, itemdefs.Items):
            result = self._id_item.get(item.value)
        else:
            raise ValueError("bro...")
        return result
    

    def get_skill(self, skill: Skills):
        return self._skill_dict[skill]


class ExpMult:
    def __init__(self, **kwargs):
        self.start_time = _parse_time(kwargs.get('startTime'))
        self.end_time = _parse_time(kwargs.get('endTime'))
        self.multiplier = kwargs.get('multiplier')
        self.event_name = kwargs.get("eventName")


class Ravenfall:
    def __init__(self, username: str, password: str):
        self._user = username
        self._pass = password
        self._auth = ""
        self._baseURL = "https://www.ravenfall.stream/api"

    async def login(self):
        await self._authenticate()
        if self._auth and not _items:
            await self.refresh_items()
    
    async def refresh_items(self):
        item_data = await get_item_data(self)
        _load_item_data(item_data)

    async def _authenticate(self):
        async with aiohttp.ClientSession() as s:
            r = await s.post(
                self._baseURL + "/auth",
                json={
                    "username": self._user,
                    "password": self._pass
                }
            )
            response = await r.text()
        if '"token"' in response:
            self._auth = str(base64.b64encode(bytes(response,"utf-8")),'utf-8')
            print("Ravenfall: Auth successful")
        else:
            print("Ravenfall: Auth unsuccessful!")

    async def _get(self,path):
        if not self._auth:
            print("Ravenfall: Not authenticated! Call login() first!")
            return {}
        async with aiohttp.ClientSession() as s:
            r = await s.get(
                self._baseURL + path,
                headers={
                    "auth-token": self._auth,
                    "Accept": "application/json"
                }
            )
            if r.status == 204:
                return None
            elif r.status != 200:
                print(f"WHAT (got {r.status})")
                raise Exception("WHAT")
            return await r.json()

    async def _items(self):
        return await self._get(f"/Items")
    
    async def _drops(self):
        return await self._get(f"/Items/drops")
    
    async def _redeemables(self):
        return await self._get(f"/Items/redeemable")
    
    async def _recipes(self):
        return await self._get(f"/Items/recipes")

    @alru_cache(ttl=3)
    async def _exp_multiplier(self):
        return await self._get(f"/Game/exp-multiplier")

    @alru_cache(ttl=4)
    async def _get_players_twitch(self, twitch_id, char_id=1):
        return await self._get(f"/Players/twitch/{twitch_id}/{char_id}")
    
    async def get_character(self, twitch_uid, character_id=1):
        result = await self._get_players_twitch(twitch_uid, character_id)
        if not result:
            return None
        return Character(result)
    
    async def get_global_mult(self):
        result = await self._exp_multiplier()
        return ExpMult(**result)

MAX_LEVEL = 999
experience_array = [0] * MAX_LEVEL

exp_for_level = 100
for level_index in range(MAX_LEVEL):
    level = level_index + 1
    tenth = math.trunc(level / 10) + 1
    incrementor = tenth * 100 + math.pow(tenth, 3)
    exp_for_level += math.trunc(incrementor)
    experience_array[level_index] = exp_for_level

def experience_for_level(level):
    if level - 2 >= len(experience_array):
        return experience_array[len(experience_array) - 1]
    return (0 if level - 2 < 0 else experience_array[level - 2])

def search_item(name: str, limit=10):
    search_result = thefuzz.process.extract(name, _items_names, limit=limit, scorer=thefuzz.fuzz.ratio)
    out_results = []
    for result, score in search_result:
        out_results.append((_items_name_data[result], score))
    return out_results

def get_item(name: str):
    return _items_name_data.get(name)

def get_raw_item_data():
    return _items

_dirname = os.path.dirname(__file__)

_items = []    
_items_name_data: Dict[str, Item] = {}
_items_id_data: Dict[str, Item] = {}
_items_names: List[str] = []
def _load_item_data(item_list):
    global _items
    global _items_name_data
    global _items_id_data
    global _items_names
    _items = item_list
    for item in _items:
        item_thing = Item(item)
        _items_name_data[item_thing.name] = item_thing
        _items_id_data[item_thing.id] = item_thing
        _items_names.append(item_thing.name)
    for item_id, item in _items_id_data.items():
        if item._craft_fail_item:
            item.craft_fail_item = _items_id_data[item._craft_fail_item]
        for ing in item._craft_ingredients:
            item.craft_ingredients.append(Ingredient(**{
                'item': _items_id_data[ing['item_id']],
                'amount': ing['amount']
            }))
        for uitem in item._used_in:
            item.used_in.append(_items_id_data[uitem])

with open(os.path.join(_dirname, 'data/items.json'), 'r') as f:
    _a = json.load(f)
    _load_item_data(_a)


fighting_skills = (
    Skills.Attack, Skills.Defense, Skills.Strength, Skills.Health,
    Skills.Magic, Skills.Ranged, Skills.Healing, Skills.All
)
combat_skills = fighting_skills
resource_skills = (
    Skills.Mining, Skills.Gathering, Skills.Woodcutting, Skills.Farming,
    Skills.Fishing
)