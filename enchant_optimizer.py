#!/usr/bin/env python3
"""Rank enchantable items by clan enchanting XP per second at a given enchanting level.

Mirrors the RavenNest server logic:
  - EnchantmentManager.EnchantItem   (attribute roll, XP grant, cooldown)
  - GameMath.GetEnchantingExperience  (XP per successful enchant)
  - GameMath.GetItemLevel / GetMaxEnchantingAttributeCount / GetMaxEnchantmentCountBySkill
  - GameMath.ExperienceArray          (ExperienceForLevel)

Input is the ravenpy items.json (lowercase keys: id, name, level, category,
equip_requirements as [{skill, level}]).

Usage:
  python enchant_optimizer.py --level 45
  python enchant_optimizer.py --level 45 --members 5 --top 20
  python enchant_optimizer.py path/to/items.json --level 45
"""

import argparse
import json
import math
from dataclasses import dataclass

DEFAULT_ITEMS_PATH = r"C:\Users\borkedcube\Documents\Python Projects\ravenbot-py\ravenpy\data\items.json"

MAX_LEVEL = 999
MAX_ENCHANT_COUNT = 10
MIN_EXP_PCT = 0.001
MAX_EXP_PCT = 1.5
ENCHANT_INTERVAL_MIN = 60
MIN_ENCHANT_SECONDS = 30

# Index order matches RavenNest.Models.ItemCategory (ravenpy/enums.py).
CATEGORY_NAMES = [
    "Weapon", "Armor", "Ring", "Amulet", "Food", "Potion", "Pet", "Resource",
    "StreamerToken", "Scroll", "Skin", "Cosmetic",
]
ENCHANTABLE_CATEGORIES = {"weapon", "armor", "ring", "amulet", "cosmetic"}


def _build_experience_table():
    table = []
    exp = 100
    for idx in range(MAX_LEVEL):
        level = idx + 1
        tenth = math.trunc(level / 10) + 1
        exp += math.trunc(tenth * 100 + tenth ** 3)
        table.append(exp)
    return table


EXPERIENCE_TABLE = _build_experience_table()


def exp_for_level(level):
    if level - 2 >= len(EXPERIENCE_TABLE):
        return EXPERIENCE_TABLE[-1]
    return 0 if level - 2 < 0 else EXPERIENCE_TABLE[level - 2]


def item_level(item):
    """GameMath.GetItemLevel: the larger of Level and the sum of equip requirement levels."""
    required = sum(req.get("level", 0) for req in item.get("equip_requirements", []))
    return max(required, item.get("level", 0))


def category_name(item):
    category = item.get("category")
    if isinstance(category, int):
        return CATEGORY_NAMES[category] if 0 <= category < len(CATEGORY_NAMES) else str(category)
    return str(category)


def enchanting_exp(skill_level, attribute_count, lvl):
    """XP granted by one successful enchant (GameMath.GetEnchantingExperience)."""
    exp = lvl * 100 + attribute_count * 25
    exp += exp * (skill_level / MAX_LEVEL) * 0.25
    need = exp_for_level(skill_level + 1)
    return math.trunc(max(need * MIN_EXP_PCT, min(exp, need * MAX_EXP_PCT)))


def roll_attribute_count(rng, success, skill_level, max_attr, max_enchantments):
    """One roll of EnchantmentManager.EnchantItem, returning the attribute count."""
    if rng <= success:
        attr = max(1, max_attr)
    elif rng <= success * 1.33:
        attr = max(1, math.floor(max_attr * 0.5))
    elif rng <= success * 2:
        attr = max(1, math.floor(max_attr * 0.33))
    elif rng >= 0.75:
        attr = 1
    else:
        attr = 0

    attr = max(0, min(max_enchantments, attr))

    if attr == 0:
        if success >= 0.05 and skill_level < 10 and rng <= 0.5:
            attr = 1
        if success >= 0.1 and skill_level < 20 and rng <= 0.25:
            attr = 1
    return attr


def attribute_distribution(skill_level, lvl):
    """Exact probability of each attribute count for one attempt, {count: probability}.

    The roll is uniform, and the outcome only changes at the breakpoints below,
    so integrating each interval at its midpoint gives the exact distribution.
    """
    success = skill_level / lvl
    max_attr = max(1, lvl // 50)
    max_enchantments = max(MAX_ENCHANT_COUNT, skill_level // 3)

    raw_cuts = {0.0, 1.0, success, success * 1.33, success * 2, 0.25, 0.5, 0.75}
    cuts = sorted(min(1.0, max(0.0, c)) for c in raw_cuts)

    probs = {}
    for lo, hi in zip(cuts, cuts[1:]):
        if hi <= lo:
            continue
        attr = roll_attribute_count((lo + hi) / 2, success, skill_level, max_attr, max_enchantments)
        probs[attr] = probs.get(attr, 0.0) + (hi - lo)
    return probs


def cooldown_seconds(skill_level, scale):
    """GameMath-free copy of EnchantmentManager.GetCooldown, in seconds."""
    return max(MIN_ENCHANT_SECONDS, ENCHANT_INTERVAL_MIN * 60 * scale - skill_level)


@dataclass
class Result:
    name: str
    item_id: str
    level: int
    category: str
    success_chance: float
    xp_per_enchant: float
    cooldown_success: float
    cooldown_fail: float
    expected_cooldown: float
    xp_per_second: float
    craft_items: int | None  # total ingredient quantity, None if the item has no recipe


def evaluate(item, skill_level):
    lvl = item_level(item)
    success = skill_level / lvl
    probs = attribute_distribution(skill_level, lvl)

    # Cooldown scale depends only on the success ratio, not on the roll result.
    factor = min(1.0, 1.0 / success)
    cd_success = cooldown_seconds(skill_level, factor)
    cd_fail = cooldown_seconds(skill_level, factor * 0.1)

    p_success = sum(p for attr, p in probs.items() if attr > 0)
    xp_per_attempt = sum(p * enchanting_exp(skill_level, attr, lvl) for attr, p in probs.items() if attr > 0)
    expected_cd = p_success * cd_success + (1 - p_success) * cd_fail

    ingredients = item.get("craft_ingredients") or []
    craft_items = sum(ing.get("amount", 0) for ing in ingredients) if ingredients else None

    return Result(
        name=item.get("name") or "?",
        item_id=str(item.get("id", "")),
        level=lvl,
        category=category_name(item),
        success_chance=p_success,
        xp_per_enchant=xp_per_attempt / p_success if p_success > 0 else 0.0,
        cooldown_success=cd_success,
        cooldown_fail=cd_fail,
        expected_cooldown=expected_cd,
        xp_per_second=xp_per_attempt / expected_cd,
        craft_items=craft_items,
    )


def format_duration(seconds):
    seconds = int(round(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h{m:02d}m{s:02d}s"
    if m:
        return f"{m}m{s:02d}s"
    return f"{s}s"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("items", nargs="?", default=DEFAULT_ITEMS_PATH, help="ravenpy items.json (default: ravenbot-py copy)")
    parser.add_argument("--level", type=int, required=True, help="your clan's current enchanting level")
    parser.add_argument("--top", type=int, default=15, help="how many items to show (default 15)")
    parser.add_argument(
        "--members", type=int, default=1,
        help="how many clan members will enchant in parallel. Cooldowns are per character, so XP adds up.",
    )
    parser.add_argument(
        "--sort", choices=["craft", "rate"], default="craft",
        help="craft: fewest crafting items first, items with no recipe last (default). rate: highest XP/sec first.",
    )
    args = parser.parse_args()

    if args.level < 1:
        parser.error("--level must be at least 1")

    with open(args.items, encoding="utf-8") as f:
        items = json.load(f)

    results = []
    for item in items:
        if category_name(item).lower() not in ENCHANTABLE_CATEGORIES:
            continue
        if item_level(item) <= 0:
            continue
        results.append(evaluate(item, args.level))

    if not results:
        print("No enchantable items found in the file.")
        return

    if args.sort == "craft":
        # Craftable items first, fewest ingredients first; ties broken by XP/sec.
        # Items with no recipe go last.
        results.sort(key=lambda r: (r.craft_items is None, r.craft_items or 0, -r.xp_per_second))
    else:
        results.sort(key=lambda r: r.xp_per_second, reverse=True)

    print(f"Enchanting level {args.level}, {len(results)} enchantable items, {args.members} member(s), sorted by {args.sort}\n")
    header = f"{'#':>3}  {'Item':<32} {'Lv':>4} {'Cat':<8} {'Craft':>5} {'Succ%':>6} {'XP/ench':>9} {'Cooldown':>9} {'Clan XP/hr':>12}"
    print(header)
    print("-" * len(header))

    for rank, r in enumerate(results[: args.top], start=1):
        xp_per_hour = r.xp_per_second * 3600 * args.members
        craft = "n/a" if r.craft_items is None else str(r.craft_items)
        print(
            f"{rank:>3}  {r.name[:32]:<32} {r.level:>4} {r.category[:8]:<8} {craft:>5} "
            f"{r.success_chance * 100:>5.1f}% {r.xp_per_enchant:>9.0f} "
            f"{format_duration(r.expected_cooldown):>9} {xp_per_hour:>12,.0f}"
        )

    best = max(results, key=lambda r: r.xp_per_second)
    print(
        f"\nHighest rate: {best.name} (level {best.level}). Success cooldown {format_duration(best.cooldown_success)}, "
        f"fail cooldown {format_duration(best.cooldown_fail)}."
    )


if __name__ == "__main__":
    main()
