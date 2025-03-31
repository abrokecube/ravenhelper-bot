import twitchio
from twitchio.ext import commands

class RavenTextCommands(commands.Component):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="materials",
                      aliases=(
                          "weapon", "weapons",
                          "sword", "1hsword", "1hswords",
                          "2hsword", "2hswords",
                          "katana", "katanas",
                          "axe", "axes", "1haxe", "1haxes",
                          "2haxe", "2haxes",
                          "spear", "spears",
                          "staff", "staffs", "staves", 
                          "bow", "bows",
                          "armor", "chest", "chests",
                          "leggings",
                          "boots",
                          "glove", "gloves",
                          "helmet", "helmets",
                          "shield", "shields"
                          ))
    async def comm_materials(self, ctx: commands.Context):
        msg_prefix = "🧱"
        msg_postfix = ""
        match ctx.invoked_with:
            case "weapon" | "weapons":
                msg_prefix = "[Weapon] ⚔️"
                msg_postfix = "Requires 3-5 bars"
            case "sword" | "1hsword" | "1hswords":
                msg_prefix = "[1h Sword] ⚔️"
                msg_postfix = "Requires 3 bars"
            case "2hsword" | "2hswords":
                msg_prefix = "[2h Sword] ⚔️"
                msg_postfix = "Requires 3 bars"
            case "katana" | "katanas":
                msg_prefix = "[Katana] 🥷"
                msg_postfix = "Requires 5 bars"
            case "axe" | "axes" | "1haxe" | "1haxes":
                msg_prefix = "[1h Axe] 🪓"
                msg_postfix = "Requires 5 bars"
            case "2haxe" | "2haxes":
                msg_prefix = "[2h Axe] 🪓"
                msg_postfix = "Requires 5 bars"
            case "spear" | "spears":
                msg_prefix = "[Spear] 🪡"
                msg_postfix = "Requires 4 bars and 2 logs"
            case "staff" | "staffs"| "staves":
                msg_prefix = "[Staff] 🪄"
                msg_postfix = "Requires 4 bars and 2 logs"
            case "bow" | "bows":
                msg_prefix = "[Bow] 🏹"
                msg_postfix = "Requires 4 bars and 2 logs"
            case "armor":
                msg_prefix = "[Armor set] 🛡️"
                msg_postfix = "Full set requires 22 bars"
            case "chest" | "chests":
                msg_prefix = "[Chest] 🛡️"
                msg_postfix = "Requires 5 bars"
            case "leggings":
                msg_prefix = "[Leggings] 🛡️"
                msg_postfix = "Requires 4 bars"
            case "boots":
                msg_prefix = "[Boots] 🛡️"
                msg_postfix = "Requires 3 bars"
            case "glove" | "gloves":
                msg_prefix = "[Gloves] 🛡️"
                msg_postfix = "Requires 3 bars"
            case "helmet" | "helmets":
                msg_prefix = "[Helmet] 🛡️"
                msg_postfix = "Requires 3 bars"
            case "shield" | "shields":
                msg_prefix = "[Shield] 🛡️"
                msg_postfix = "Requires 4 bars"
        
        if len(msg_postfix) > 0:
            msg_postfix = " | " + msg_postfix
        await ctx.reply(f"/me Minimum level to equip {msg_prefix} Bronze/Iron - 1 • Steel - 10 • Black - 20 • Mithril - 30 • " \
                        f"Adamantite - 50 • Rune - 70 • Dragon - 90 • Abraxas - 120 • " \
                        f"Phantom - 150 • Lionite/Lionsbane - 200 • Ethereum/Ether - 280 • Ancient - 340 • " \
                        f"Atlarus - 400{msg_postfix} | For elder equipment (level 500+), use {ctx.prefix}e{ctx.invoked_with}")


    @commands.command(name="ematerials",
                      aliases=(
                          "eweapon", "eweapons",
                          "esword", "e1hsword", "e1hswords",
                          "e2hsword", "e2hswords",
                          "ekatana", "ekatanas",
                          "eaxe", "eaxes", "e1haxe", "e1haxes",
                          "e2haxe", "e2haxes",
                          "espear", "espears",
                          "estaff", "estaffs", "estaves", 
                          "ebow", "ebows",
                          "earmor", "echest", "echests",
                          "eleggings",
                          "eboots",
                          "eglove", "egloves",
                          "ehelmet", "ehelmets",
                          "eshield", "eshields"
                          ))
    async def comm_ether_materials(self, ctx: commands.Context):
        msg_prefix = "Elder 🧱"
        msg_postfix = ""
        match ctx.invoked_with[1:]:
            case "weapon" | "weapons":
                msg_prefix = "[Weapon] ⚔️"
                msg_postfix = "Requires 3-5 bars"
            case "sword" | "1hsword" | "1hswords":
                msg_prefix = "[Elder 1h Sword] ⚔️"
                msg_postfix = "Requires 3 bars"
            case "2hsword" | "2hswords":
                msg_prefix = "[Elder 2h Sword] ⚔️"
                msg_postfix = "Requires 3 bars"
            case "katana" | "katanas":
                msg_prefix = "[Elder Katana] 🥷"
                msg_postfix = "Requires 5 bars"
            case "axe" | "axes" | "1haxe" | "1haxes":
                msg_prefix = "[Elder 1h Axe] 🪓"
                msg_postfix = "Requires 5 bars"
            case "2haxe" | "2haxes":
                msg_prefix = "[Elder 2h Axe] 🪓"
                msg_postfix = "Requires 5 bars"
            case "spear" | "spears":
                msg_prefix = "[Elder Spear] 🪡"
                msg_postfix = "Requires 4 bars and 2 logs"
            case "staff" | "staffs"| "staves":
                msg_prefix = "[Elder Staff] 🪄"
                msg_postfix = "Requires 4 bars and 2 logs"
            case "bow" | "bows":
                msg_prefix = "[Elder Bow] 🏹"
                msg_postfix = "Requires 4 bars and 2 logs"
            case "armor":
                msg_prefix = "[Elder Armor set] 🛡️"
                msg_postfix = "Full set requires 22 bars"
            case "chest" | "chests":
                msg_prefix = "[Elder Chest] 🛡️"
                msg_postfix = "Requires 5 bars"
            case "leggings":
                msg_prefix = "[Elder Leggings] 🛡️"
                msg_postfix = "Requires 4 bars"
            case "boots":
                msg_prefix = "[Elder Boots] 🛡️"
                msg_postfix = "Requires 3 bars"
            case "glove" | "gloves":
                msg_prefix = "[Elder Gloves] 🛡️"
                msg_postfix = "Requires 3 bars"
            case "helmet" | "helmets":
                msg_prefix = "[Elder Helmet] 🛡️"
                msg_postfix = "Requires 3 bars"
            case "shield" | "shields":
                msg_prefix = "[Elder Shield] 🛡️"
                msg_postfix = "Requires 4 bars"
        
        if len(msg_postfix) > 0:
            msg_postfix = " | " + msg_postfix
        await ctx.reply(f"/me Minimum level to equip {msg_prefix} E.Bronze - 500 • E.Iron - 525 • " \
                        "E.Steel - 550 • E.Mithril - 600 • E.Adamantite - 650 • E.Rune - 700 • " \
                        "E.Dragon - 750 • E.Abraxas - 800 • E.Phantom - 850 • E.Lionsbane - 875 • " \
                        f"E.Ether - 900 • E.Ancient - 950 • E.Atlarus - 999{msg_postfix}")

    @commands.command(aliases=('skill','train'))
    async def skills(self, ctx: commands.Context):
        await ctx.reply("/me Skills you can train: Woodcutting, Farming, Crafting, Cooking, Fishing, Alchemy, Gathering, Mining, Health, Attack, Defense, Strength, Magic, Ranged, Healing and Sailing")

    @commands.command(name="islands", aliases=("island", "destination", "destinations"))
    async def islands(self, ctx: commands.Context):
        await ctx.reply("/me 🏝️ Destinations: Home - 1-99 • Away - 50-150 • Ironhill - 100-300 • " \
                        "Kyo - 200-400 • Heim - 300-700 • Atria - 500-900 • Eldara - 700+")

    @commands.command(name="otherskills",aliases=("mining", "crafting", "fishing", "woodcutting", "cooking", "farming", "gathering", "alchemy"))
    async def noncombat(self, ctx: commands.Context):
        command = ctx.invoked_with
        postfix = ""
        if command == "mining":
            postfix = f" | To see ore mining levels, use {ctx.prefix}ore"
        elif command == "gathering":
            postfix = f" | To see item gathering levels, use {ctx.prefix}forage"
        elif command == "farming":
            postfix = f" | To see crop farming levels, use {ctx.prefix}crops"
        elif command == "fishing":
            postfix = f" | To see fish catching levels, use {ctx.prefix}fish"
        elif command == "woodcutting":
            postfix = f" | To see tree chopping levels, use {ctx.prefix}wood"
        await ctx.reply(f"/me 🏝️ Islands and level ranges to train {command.title()}: " \
                        "Home - 1-99 • Away - 50-150 • Ironhill - 100-300 • " \
                        f"Kyo - 200-400 • Heim - 300-700 • Atria - 500-900 • Eldara - 700+{postfix}")

    @commands.command(name="combatskills",aliases=("combat", "attack", "atk", "defense", "strength", "magic", "ranged", "healing"))
    async def combat(self, ctx: commands.Context):
        await ctx.reply("/me 🏝️ You can train any combat skill if your Combat Level is within these ranges for each island: " \
                        "Home - 1-99 • Away - 50-150 • Ironhill - 100-300 • Kyo - 200-400 — " \
                        "For training on the following islands, the combat skill itself needs to meet the level requirement: " \
                        f"Heim - 300-700 • Atria - 500-900 • Eldara - 700+")

    @commands.command()
    async def sailing(self, ctx: commands.Context):
        await ctx.reply("/me ⛵ Train Sailing by sailing between islands or by sailing with no destination.")

    @commands.command()
    async def enchanting(self, ctx: commands.Context):
        await ctx.reply("/me 🔮 Enchanting is a clan skill, meaning the only requirement for enchanting is to be a part of a clan.")

    @commands.command()
    async def slayer(self, ctx: commands.Context):
        await ctx.reply("/me ⚔️ Train Slayer by joining Raids and Dungeons.")

