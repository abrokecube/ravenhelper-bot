import ravenpy
from dotenv import load_dotenv
import os
import asyncio
import json

load_dotenv()
async def main():
    rf = ravenpy.RavenNest(os.getenv("API_USER"), os.getenv("API_PASS"))
    await rf.login()
    await rf.refresh_items()
    dirname = os.path.dirname(__file__)
    with open(os.path.join(dirname, "./ravenpy/data/items.json"), 'w') as f:
        json.dump(ravenpy.get_raw_item_data(), f, indent=2)

    # ravenpy._rf_items
asyncio.run(main())