import ravenpy
from dotenv import load_dotenv
import os
import asyncio
import json
from utils import langstuff
from utils.utils import format_seconds, TimeSize, strjoin
import pandas as pd

load_dotenv()
async def main():
    rf = ravenpy.Ravenfall(os.getenv("API_USER"), os.getenv("API_PASS"))
    await rf.login()
    await rf.refresh_items()

    items = [x for x in ravenpy.get_all_items() if x.effects]
    items.sort(key=lambda x: x.name)
    out_table = []
    for item in items:
        item_effects = []
        for effect in item.effects:
            stat_name = langstuff.status_effect_names[effect.effect]
            stat_duration = ""
            if effect.duration > 0:
                stat_duration = f"for {format_seconds(effect.duration, TimeSize.MEDIUM)}"
            stat_percent = ""
            if effect.percentage > 0:
                stat_percent = f"+{('%.1f' % (effect.percentage*100)).rstrip('0').rstrip('.')}%"
            stat_min = ""
            if effect.min_amount > 0:
                stat_min = f"(Min: {effect.min_amount})"
            item_effects.append(strjoin(' ', stat_name, stat_percent, stat_min, stat_duration))

        out_table.append({
            "Name": item.name,
            "Category": item.category.name,
            "Effects": "\n".join(item_effects)
        })

    table_pd = pd.DataFrame.from_dict(out_table)
    table_pd.to_excel('item_effects.xlsx', index=False)

asyncio.run(main())