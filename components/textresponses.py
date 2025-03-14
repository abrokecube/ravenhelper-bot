import twitchio
from twitchio.ext import commands

class RavenTextResponses(commands.Component):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Component.listener()
    async def event_message(self, payload: twitchio.ChatMessage) -> None:
        print(f"[{payload.broadcaster.name}] - {payload.chatter.name}: {payload.text}")

    @commands.command(name="materials",
                      aliases=(
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
                        f"Atlarus - 400{msg_postfix}")

    @commands.command(aliases=('training','train','skill'))
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
            postfix = " | To see ore mining levels, use ?ore"
        elif command == "gathering":
            postfix = " | To see item gathering levels, use ?forage"
        elif command == "farming":
            postfix = " | To see crop farming levels, use ?crops"
        elif command == "fishing":
            postfix = " | To see fish catching levels, use ?fish"
        elif command == "woodcutting":
            postfix = " | To see tree chopping levels, use ?wood"
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

    @commands.command(aliases=("ore","bar","bars","miningitems"))
    async def ores(self, ctx: commands.Context):
        await ctx.reply(
            "/me ⛏️ Mining level required to obtain ores: " \
            "Copper and Tin - 1 • Sapphire - 10 • Iron - 15 • Silver and Emerald - 20 • " \
            "Coal and Ruby - 30 • Gold - 40 • Mithril - 60 • Adamantite - 80 • " \
            "Rune - 110 • Dragon - 180 • Eldrium - 250 • Abraxas - 350 • " \
            "Phantom - 450 • Lionite - 575 • Ethereum - 700 • Ancient - 850 • Atlarus - 999"
        )

    @commands.command(aliases=("foraging","gatheringitems"))
    async def forage(self, ctx: commands.Context):
        await ctx.reply(
            "/me 🧺 Gathering level required to obtain items: " \
            "Water - 1 • Sand - 5 • Yarrow, Yeast - 10 • Mushroom - 15 • " \
            "Hemp, Salt - 20 • Black Pepper - 25 • Resin - 30 • Comfrey - 40 • " \
            "Sage - 60 • Lavender - 80 • Elderflower - 100 • Valerian - 120 • " \
            "Chamomile - 140 • Red Clover - 180 • Mugworth - 230 • GoldenRod - 280 • " \
            "Wormwood - 330 • Skullcap - 400 • Lemon Balm - 500"
        )

    @commands.command(aliases=("crop","farmingitems"))
    async def crops(self, ctx: commands.Context):
        await ctx.reply(
            "/me 🌾 Farming level required to obtain items: " \
            "Wheat - 1 • Potato - 5 • Tomato - 10 • Cumin - 30 • Coriander - 40 • " \
            "Paprika - 50 • Turmeric - 60 • Apple - 70 • Carrots - 80 • " \
            "Garlic - 90 • Onion - 100 • Sugar - 100 • Milk - 120 • " \
            "Cinnamon - 120 • Eggs - 140 • Chicken - 160 • Pork - 200 • Beef - 240 • " \
            "Grapes - 320 • Cacao - 400 • Truffle - 800"
        )

    @commands.command(aliases=("fishes","fishingitems"))
    async def fish(self, ctx: commands.Context):
        await ctx.reply(
            "/me 🎣 Fishing level required to obtain items: " \
            "Sprat - 1 • Shrimp - 5 • Red Sea Bass - 20 • Bass - 50 • " \
            "Perch - 70 • Salmon - 100 • Crab - 130 • Lobster - 170 • " \
            "Blue Lobster - 220 • Sword Fish - 280 • Puffer Fish - 350 • " \
            "Octopus - 420 • Manta Ray - 500 • Kraken - 700 • Leviathan - 900"
        )

    @commands.command(aliases=("woodcuttingitems",))
    async def wood(self, ctx: commands.Context):
        await ctx.reply(
            "/me 🌳 Woodcutting level required to obtain logs: " \
            "Logs - 1 • Bristle - 10 • Glowbark - 15 • Mystwood - 30 • " \
            "Sandrift - 50 • Pineheart - 70 • Ebonshade - 100 • Rune - 110 • " \
            "Ironbark - 130 • Frostbite - 170 • Dragonwood - 200 • " \
            "Goldwillow - 240 • Shadowoak - 300"
        )
