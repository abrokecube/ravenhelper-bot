#!/usr/bin/env python3
"""Plan the chat craft commands needed to make a list of wanted items.

Reads a CSV with header `item_name,quantity` and the ravenpy items.json, then prints:
  1. the total raw ingredients needed (items with no recipe), sorted by name
  2. craft commands in build order: intermediates first, requested items last

Assumptions:
  - Each craft command produces exactly 1 of the item.
  - Ingredients are consumed exactly as listed in craft_ingredients.
  - Crafting failure chances are ignored.
  - An item with no recipe (empty craft_ingredients) is a raw material that must be gathered or bought.

Verbs come from craft_skill: Crafting -> !craft, Cooking -> !cook, Alchemy -> !brew.
Any other non-null craft_skill prints a warning and uses !craft.

Usage:
  python craft_plan.py wanted.csv
  python craft_plan.py wanted.csv --items path/to/items.json
"""

import argparse
import csv
import json
import sys
from collections import deque

DEFAULT_ITEMS_PATH = r"C:\Users\borkedcube\Documents\Python Projects\ravenbot-py\ravenpy\data\items.json"

VERBS = {"Crafting": "!craft", "Cooking": "!cook", "Alchemy": "!brew"}


def fail(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    sys.exit(1)


def normalize(name: str) -> str:
    return name.strip().lower()


def load_items(path: str) -> tuple[dict[str, dict], dict[str, dict]]:
    """Return (items by id, items by normalized name). The first item wins on a duplicate name."""
    try:
        with open(path, encoding="utf-8") as f:
            items = json.load(f)
    except (OSError, ValueError) as e:
        fail(f"cannot read items file {path}: {e}")

    by_id = {}
    by_name = {}
    for item in items:
        by_id[item["id"]] = item
        key = normalize(item["name"])
        if key in by_name:
            print(f"warning: duplicate item name '{item['name']}', using the first one", file=sys.stderr)
        else:
            by_name[key] = item
    return by_id, by_name


def read_wanted(path: str, by_name: dict[str, dict]) -> dict[str, int]:
    """Return {item id: quantity} from the CSV. Repeated rows for one item are summed."""
    demand: dict[str, int] = {}
    try:
        f = open(path, encoding="utf-8-sig", newline="")
    except OSError as e:
        fail(f"cannot read CSV {path}: {e}")

    with f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or not {"item_name", "quantity"} <= set(reader.fieldnames):
            fail("CSV header must be: item_name,quantity")
        for row in reader:
            name = (row.get("item_name") or "").strip()
            item = by_name.get(normalize(name))
            if item is None:
                fail(f"unknown item '{name}'")
            raw_qty = (row.get("quantity") or "").strip()
            try:
                qty = int(raw_qty)
            except ValueError:
                fail(f"quantity for '{name}' is not a positive integer: '{raw_qty}'")
            if qty < 1:
                fail(f"quantity for '{name}' is not a positive integer: '{raw_qty}'")
            demand[item["id"]] = demand.get(item["id"], 0) + qty
    return demand


def plan(demand: dict[str, int], by_id: dict[str, dict]) -> tuple[list[str], dict[str, int]]:
    """Return (item ids in topological order, total units needed for each item id).

    Kahn's algorithm over the recipe graph: an item is only expanded after every
    parent that uses it has been resolved, so its total demand is final by then.
    """
    reachable: set[str] = set()
    stack = list(demand)
    while stack:
        iid = stack.pop()
        if iid not in reachable:
            reachable.add(iid)
            stack.extend(ing["item_id"] for ing in by_id[iid].get("craft_ingredients") or [])

    indegree = dict.fromkeys(reachable, 0)
    for iid in reachable:
        for ing in by_id[iid].get("craft_ingredients") or []:
            indegree[ing["item_id"]] += 1

    need = {iid: demand.get(iid, 0) for iid in reachable}
    queue = deque(iid for iid in reachable if indegree[iid] == 0)
    order = []
    while queue:
        iid = queue.popleft()
        order.append(iid)
        item = by_id[iid]
        recipe = item.get("craft_ingredients") or []
        crafts = need[iid] if recipe else 0  # one craft per unit needed
        for ing in recipe:
            child = ing["item_id"]
            need[child] += crafts * ing["amount"]
            indegree[child] -= 1
            if indegree[child] == 0:
                queue.append(child)

    if len(order) < len(reachable):
        stuck = sorted(by_id[i]["name"] for i in reachable if indegree[i] > 0)
        fail("recipe cycle detected among: " + ", ".join(stuck))
    return order, need


def verb_for(item: dict) -> str:
    skill = item.get("craft_skill")
    if skill is None:
        return "!craft"
    if skill in VERBS:
        return VERBS[skill]
    print(f"warning: unknown craft_skill '{skill}' for '{item['name']}', using !craft", file=sys.stderr)
    return "!craft"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("csv", help="CSV with header item_name,quantity")
    parser.add_argument("--items", default=DEFAULT_ITEMS_PATH, help="ravenpy items.json (default: ravenbot-py copy)")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    by_id, by_name = load_items(args.items)
    demand = read_wanted(args.csv, by_name)
    order, need = plan(demand, by_id)

    raw = sorted((by_id[i]["name"], need[i]) for i in order if not by_id[i].get("craft_ingredients"))
    print("== Total ingredients needed ==")
    for name, qty in raw:
        print(f"{name} x {qty}")

    print("\n== Craft commands (in order) ==")
    for iid in reversed(order):  # ingredients before the items that use them
        item = by_id[iid]
        if item.get("craft_ingredients"):
            verb = verb_for(item)
            count = need[iid]
            # One command per item; the trailing number tells the bot how many to craft.
            suffix = f" {count}" if count > 1 else ""
            print(f"{verb} {item['name']}{suffix}")


if __name__ == "__main__":
    main()
