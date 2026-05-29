# Generates items.py

from dotenv import load_dotenv
import os
from re import sub
import json

_ = load_dotenv()

with open('./ravenpy/data/items.json') as f:
    items = json.load(f)

def camel(s):
    s = sub(r"(_|-)+", " ", s).title().replace(" ", "")
    return ''.join(s)

def main():
    out_text = []
    out_text.append("""from enum import Enum

class Items(Enum):
""")
    for item in items:
        item_name = camel(item['name'])
        out_text.append(f"    {item_name} = '{item['id']}'\n")
        # item.
    if os.path.exists('./ravenpy/itemdefs.py'):
        input("itemdefs.py exists..., press any key to continue!")
        input("Do it again!")
        input("Again!")
    with open('./ravenpy/itemdefs.py', 'w') as f:
       f.write("".join(out_text))
    
main()