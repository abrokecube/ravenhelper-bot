from enum import Enum
from multipledispatch import dispatch
import json

class StatusEffectType(Enum):
    NoEffect = 0
    Heal = 1
    HealOverTime = 2
    IncreasedStrength = 3
    IncreasedDefense = 4
    IncreasedDodge = 5
    IncreasedHitChance = 6
    IncreasedMovementSpeed = 7
    IncreasedAttackSpeed = 8
    IncreasedCastSpeed = 9
    IncreasedAttackPower = 10
    IncreasedRangedPower = 11
    IncreasedMagicPower = 12
    IncreasedHealingPower = 13
    IncreasedExperienceGain = 14
    IncreaseCriticalHit = 15
    AttackAttributePoison = 16
    AttackAttributeBleeding = 17
    AttackAttributeBurning = 18
    AttackAttributeHealthSteal = 19
    Poison = 20
    Bleeding = 21
    Burning = 22
    Damage = 23
    ReducedHitChance = 24
    ReducedMovementSpeed = 25
    ReducedAttackSpeed = 26
    ReducedCastSpeed = 27
    IncreasedCriticalHitDamage = 28
    RemoveItem = 29
    AddItem = 30
    TeleportToIsland = 31

item_materials = {
    'Bronze': 1,
    'Iron': 2,
    'Steel': 3,
    'Black': 4,
    'Mithril': 5,
    'Adamantite': 6,
    'Rune': 7,
    'Dragon': 8,
    'Abraxas': 9,
    'Phantom': 10,
    'Lionsbane': 11,
    'Ether': 12,
    'Ancient': 13,
    'Atlarus': 14
}


effects = None
regularPotionDuration = 120
greatPotionDuration = 600
item_effects = {}
item_raid_drops = {}
def GetOrCreateItemStatusEffect(_, item_name, status_effect: StatusEffectType, duration=-1, percentage=0, min_amount=0):
    item = {
        "name": item_name,
        "effects": [
            {
                # "name": status_effect_names[status_effect.value],
                "id": status_effect.value,
                "duration": duration,
                "percentage": percentage,
                "min_amount": min_amount
            }
        ]
    }
    item_effects[item_name] = item

def EnsureItemStatusEffects(item_name, *effects):
    item = {
        "name": item_name,
        "effects": effects
    }
    item_effects[item_name] = item

@dispatch(StatusEffectType, float, int)
def Effect(status_effect, percentage, min_amount):
    return Effect(status_effect, -1, percentage, min_amount)

@dispatch(StatusEffectType, int, float, int)
def Effect(status_effect, duration, percentage, min_amount):
    return {
        # "name": status_effect_names[status_effect.value],
        "id": status_effect.value,
        "duration": duration,
        "percentage": percentage,
        "min_amount": min_amount
    }

@dispatch(str, float, int, int)
def EnsureDrop(item, drop_rate, tier, slayerLevelRequirement):
    return EnsureDrop(0, 0, item, drop_rate, drop_rate, tier, slayerLevelRequirement)

@dispatch(str, float, float, int, int)
def EnsureDrop(item, max_drop, min_drop, tier, slayerLevelRequirement):
    return EnsureDrop(0, 0, item, max_drop, min_drop, tier, slayerLevelRequirement)

@dispatch(int, int, str, float, float, int, int)
def EnsureDrop(month_start, months_length, item, max_drop, min_drop, tier, slayerLevelRequirement):
    item_out = {
        "name": item,
        "month_start": month_start,
        "months_length": months_length,
        "min_drop": min_drop,
        "max_drop": max_drop,
        "tier": tier,
        "slayer_requirement": slayerLevelRequirement
    }
    item_raid_drops[item] = item_out
# ----------- GAME CODE -------------------

# Regular Potions
GetOrCreateItemStatusEffect(effects, "DefensePotion", StatusEffectType.IncreasedDefense, regularPotionDuration, 0.20, 5)
GetOrCreateItemStatusEffect(effects, "StrengthPotion", StatusEffectType.IncreasedStrength, regularPotionDuration, 0.20, 5)
GetOrCreateItemStatusEffect(effects, "MagicPotion", StatusEffectType.IncreasedMagicPower, regularPotionDuration, 0.20, 5)
GetOrCreateItemStatusEffect(effects, "RangedPotion", StatusEffectType.IncreasedRangedPower, regularPotionDuration, 0.20, 5)
GetOrCreateItemStatusEffect(effects, "HealingPotion", StatusEffectType.IncreasedHealingPower, regularPotionDuration, 0.20, 5)

# Great Potions
GetOrCreateItemStatusEffect(effects, "GreatDefensePotion", StatusEffectType.IncreasedDefense, greatPotionDuration, 0.40, 10)
GetOrCreateItemStatusEffect(effects, "GreatStrengthPotion", StatusEffectType.IncreasedStrength, greatPotionDuration, 0.40, 10)
GetOrCreateItemStatusEffect(effects, "GreatMagicPotion", StatusEffectType.IncreasedMagicPower, greatPotionDuration, 0.40, 10)
GetOrCreateItemStatusEffect(effects, "GreatRangedPotion", StatusEffectType.IncreasedRangedPower, greatPotionDuration, 0.40, 10)
GetOrCreateItemStatusEffect(effects, "GreatHealingPotion", StatusEffectType.IncreasedHealingPower, greatPotionDuration, 0.40, 10)
GetOrCreateItemStatusEffect(effects, "HealthPotion", StatusEffectType.Heal, 0.15, 10) # will heal 15% of max health or 10 hp minimum.
GetOrCreateItemStatusEffect(effects, "GreatHealthPotion", StatusEffectType.Heal, 0.40, 50) # will heal 40% of max health or 50 hp minimum.
GetOrCreateItemStatusEffect(effects, "RegenPotion", StatusEffectType.HealOverTime, 15, 0.25, 50) # will heal total of 25% of max health or minimum 25 hp over the duration of 15 seconds.

# Fish dishes
EnsureItemStatusEffects("Sprat", Effect(StatusEffectType.Heal, 0.03, 3))
EnsureItemStatusEffects("Shrimp", Effect(StatusEffectType.Heal, 0.04, 4))
EnsureItemStatusEffects("RedSeaBass", Effect(StatusEffectType.Heal, 0.06, 10))
EnsureItemStatusEffects("Bass", Effect(StatusEffectType.Heal, 0.08, 12))
EnsureItemStatusEffects("Perch", Effect(StatusEffectType.Heal, 0.10, 15))
EnsureItemStatusEffects("Salmon", Effect(StatusEffectType.Heal, 0.12, 20), Effect(StatusEffectType.IncreasedStrength, 90, 0.05, 2))
EnsureItemStatusEffects("Crab", Effect(StatusEffectType.Heal, 0.15, 25), Effect(StatusEffectType.IncreasedDefense, 90, 0.05, 2))
EnsureItemStatusEffects("Lobster", Effect(StatusEffectType.Heal, 0.20, 25), Effect(StatusEffectType.IncreasedAttackPower, 120, 0.07, 3))
EnsureItemStatusEffects("BlueLobster", Effect(StatusEffectType.Heal, 0.25, 30), Effect(StatusEffectType.IncreasedMagicPower, 120, 0.08, 3))
EnsureItemStatusEffects("Swordfish", Effect(StatusEffectType.Heal, 0.25, 30), Effect(StatusEffectType.IncreasedAttackSpeed, 180, 0.10, 3))
EnsureItemStatusEffects("PufferFish", Effect(StatusEffectType.Heal, 0.30, 35), Effect(StatusEffectType.IncreasedDodge, 150, 0.10, 0))
EnsureItemStatusEffects("Octopus", Effect(StatusEffectType.Heal, 0.35, 40), Effect(StatusEffectType.IncreasedMagicPower, 240, 0.12, 4))
EnsureItemStatusEffects("MantaRay", Effect(StatusEffectType.Heal, 0.40, 50), Effect(StatusEffectType.IncreasedMovementSpeed, 240, 0.10, 0))
EnsureItemStatusEffects("Kraken", Effect(StatusEffectType.Heal, 0.45, 60), Effect(StatusEffectType.IncreasedExperienceGain, 300, 0.12, 0))
#EnsureItemStatusEffects("Kraken", Effect(StatusEffectType.Heal, 0.45, 60), Effect(StatusEffectType.IncreasedAttackPower, 150, 0.12, 0), Effect(StatusEffectType.IncreasedMovementSpeed, 150, 0.12, 0))

# other dishes
EnsureItemStatusEffects("RedWine", Effect(StatusEffectType.Heal, 0.05, 5), Effect(StatusEffectType.ReducedHitChance, 180, 0.05, 0), Effect(StatusEffectType.IncreasedStrength, 180, 0.05, 2))
EnsureItemStatusEffects("HamSandwich", Effect(StatusEffectType.Heal, 0.08, 10))
EnsureItemStatusEffects("RoastedChicken", Effect(StatusEffectType.Heal, 0.10, 15))
EnsureItemStatusEffects("RoastBeef", Effect(StatusEffectType.Heal, 0.15, 25), Effect(StatusEffectType.IncreasedStrength, 180, 0.07, 3))
EnsureItemStatusEffects("RoastedPork", Effect(StatusEffectType.Heal, 0.12, 20), Effect(StatusEffectType.IncreasedDefense, 150, 0.06, 3))
EnsureItemStatusEffects("CookedChickenLeg", Effect(StatusEffectType.Heal, 0.10, 15))
EnsureItemStatusEffects("Steak", Effect(StatusEffectType.Heal, 0.18, 28), Effect(StatusEffectType.IncreasedStrength, 200, 0.08, 3))

EnsureItemStatusEffects("Prings", Effect(StatusEffectType.Heal, 0.2, 30), Effect(StatusEffectType.IncreaseCriticalHit, 60, .1, 5))

EnsureItemStatusEffects("GrilledCheese", Effect(StatusEffectType.Heal, 0.09, 12), Effect(StatusEffectType.IncreasedDefense, 100, 0.05, 2))
EnsureItemStatusEffects("ApplePie", Effect(StatusEffectType.Heal, 0.14, 22), Effect(StatusEffectType.IncreasedMagicPower, 150, 0.05, 3))
EnsureItemStatusEffects("Bread", Effect(StatusEffectType.Heal, 0.06, 8))
EnsureItemStatusEffects("Skewers", Effect(StatusEffectType.Heal, 0.11, 18), Effect(StatusEffectType.IncreasedAttackSpeed, 140, 0.06, 2))
EnsureItemStatusEffects("HotChocolate", Effect(StatusEffectType.Heal, 0.05, 8), Effect(StatusEffectType.IncreasedHitChance, 120,  0.05, 0))
EnsureItemStatusEffects("ChocolateChipCookies", Effect(StatusEffectType.Heal, 0.07, 10), Effect(StatusEffectType.IncreaseCriticalHit, 120, 0.10, 0))

# Burnt :o
EnsureItemStatusEffects("BurnedGrilledCheese", Effect(StatusEffectType.Heal, 0.02, 2))
EnsureItemStatusEffects("BurnedChicken", Effect(StatusEffectType.Heal, 0.02, 2))
EnsureItemStatusEffects("BurnedBeef", Effect(StatusEffectType.Heal, 0.02, 2))
EnsureItemStatusEffects("BurnedPork", Effect(StatusEffectType.Heal, 0.02, 2))
EnsureItemStatusEffects("BurnedChickenLeg", Effect(StatusEffectType.Heal, 0.02, 2))
EnsureItemStatusEffects("BurnedSteak", Effect(StatusEffectType.Heal, 0.02, 2))
EnsureItemStatusEffects("BurnedApplePie", Effect(StatusEffectType.Heal, 0.02, 2))
EnsureItemStatusEffects("BurnedBread", Effect(StatusEffectType.Heal, 0.02, 2))
EnsureItemStatusEffects("BurnedSkewers", Effect(StatusEffectType.Heal, 0.02, 2))
EnsureItemStatusEffects("BurnedChocolateChipCookies", Effect(StatusEffectType.Heal, 0.02, 2))

# Failed fish dishes based on 20% of original dish's healing values
EnsureItemStatusEffects("BurnedSprat", Effect(StatusEffectType.Heal, 0.006, 1))
EnsureItemStatusEffects("BurnedShrimp", Effect(StatusEffectType.Heal, 0.008, 1))
EnsureItemStatusEffects("BurnedRedSeaBass", Effect(StatusEffectType.Heal, 0.012, 2))
EnsureItemStatusEffects("BurnedBass", Effect(StatusEffectType.Heal, 0.016, 2))
EnsureItemStatusEffects("BurnedPerch", Effect(StatusEffectType.Heal, 0.020, 3))
EnsureItemStatusEffects("BurnedSalmon", Effect(StatusEffectType.Heal, 0.024, 4))
EnsureItemStatusEffects("BurnedCrab", Effect(StatusEffectType.Heal, 0.030, 5))
EnsureItemStatusEffects("BurnedLobster", Effect(StatusEffectType.Heal, 0.040, 5))
EnsureItemStatusEffects("BurnedBlueLobster", Effect(StatusEffectType.Heal, 0.050, 6))
EnsureItemStatusEffects("BurnedSwordfish", Effect(StatusEffectType.Heal, 0.050, 6))
EnsureItemStatusEffects("BurnedPufferFish", Effect(StatusEffectType.Heal, 0.060, 7))
EnsureItemStatusEffects("BurnedOctopus", Effect(StatusEffectType.Heal, 0.070, 8))
EnsureItemStatusEffects("BurnedMantaRay", Effect(StatusEffectType.Heal, 0.080, 10))
EnsureItemStatusEffects("BurnedKraken", Effect(StatusEffectType.Heal, 0.090, 12))

# Failed special dishes
# I'm basing these values on the CookedKraken for now, but these dishes may be considered special enough to have a bit more.
EnsureItemStatusEffects("MuddledLeviathanBroth", Effect(StatusEffectType.Heal, 0.09, 12))
EnsureItemStatusEffects("RuinedGuardianDelight", Effect(StatusEffectType.Heal, 0.09, 12))

# Special dishes
EnsureItemStatusEffects("LeviathansRoyalStew", Effect(StatusEffectType.Heal, 0.50, 80), Effect(StatusEffectType.IncreasedDefense, 360, 0.15, 5), Effect(StatusEffectType.IncreasedStrength, 360, 0.15, 5))
EnsureItemStatusEffects("PoseidonsGuardianFeast", Effect(StatusEffectType.Heal, 0.65, 100), Effect(StatusEffectType.IncreasedMagicPower, 600, 0.20, 8), Effect(StatusEffectType.IncreasedAttackPower, 600, 0.20, 8), Effect(StatusEffectType.IncreasedHealingPower, 600, 0.20, 8))

# Teleportation
# GetOrCreateItemStatusEffect(effects, "TomeOfHome", StatusEffectType.TeleportToIsland, Island.Home)
# GetOrCreateItemStatusEffect(effects, "TomeOfAway", StatusEffectType.TeleportToIsland, Island.Away)
# GetOrCreateItemStatusEffect(effects, "TomeOfIronhill", StatusEffectType.TeleportToIsland, Island.Ironhill)
# GetOrCreateItemStatusEffect(effects, "TomeOfKyo", StatusEffectType.TeleportToIsland, Island.Kyo)
# GetOrCreateItemStatusEffect(effects, "TomeOfHeim", StatusEffectType.TeleportToIsland, Island.Heim)
# GetOrCreateItemStatusEffect(effects, "TomeOfAtria", StatusEffectType.TeleportToIsland, Island.Atria)
# GetOrCreateItemStatusEffect(effects, "TomeOfEldara", StatusEffectType.TeleportToIsland, Island.Eldara)
# GetOrCreateItemStatusEffect(effects, "TomeOfTeleportation", StatusEffectType.TeleportToIsland, Island.Any)

EnsureDrop(12, 1, "SantaHat", 0.05, 0.02,0,0) # Santa hat 
EnsureDrop(12, 1, "ChristmasToken", 0.05, 0.025,0,0) # Christmas Token
EnsureDrop(10, 1, "HalloweenToken", 0.05, 0.025,0,0) # Halloween Token

# Pet drops, available in all types of dungeon or raids
EnsureDrop("FoxPet", 0.05,0,0)
EnsureDrop("DeerPet", 0.05,0,0)
EnsureDrop("BearPet", 0.05,0,0)
EnsureDrop("BlueOrbPet", 0.05,0,0)
EnsureDrop("WolfPet", 0.05,0,0)
EnsureDrop("GreenOrbPet", 0.05,0,0)
EnsureDrop("PolarBearPet", 0.05,0,0)
EnsureDrop("RedOrbPet", 0.05,0,0)

EnsureDrop("Rajah", 0.05,0,0)
EnsureDrop("RavenPet", 0.05,0,0)

EnsureDrop("RedPandaPet", 0.05,0,0)

EnsureDrop("Raccoon", 0.05,0,0)
EnsureDrop("BrownRaccoon", 0.05,0,0)
EnsureDrop("OctopusPet", 0.04,0,0)
EnsureDrop("BabyRaccoon", 0.02,0,0)

EnsureDrop("Cat", 0.04,0,0)
EnsureDrop("Beige Cat", 0.04,0,0)
EnsureDrop("Cream Cat", 0.04,0,0)
EnsureDrop("Black Cat", 0.04,0,0)
EnsureDrop("Mix Cat", 0.04,0,0)
EnsureDrop("Orange Cat", 0.04,0,0)
EnsureDrop("Raccoon Cat", 0.04,0,0)
EnsureDrop("Siamese Cat", 0.04,0,0)

EnsureDrop("BronzeBar", 0.05,0,0)
EnsureDrop("IronBar", 0.05,0,0)
EnsureDrop("SteelBar", 0.05,0,0)
EnsureDrop("MithrilBar", 0.05,0,0)
EnsureDrop("AdamantiteBar", 0.05,0,0)

# drop resources! this should be mid tier resources
EnsureDrop("Lavender", 0.05,0,0)
EnsureDrop("Elderflower", 0.05,0,0)
EnsureDrop("Valerian", 0.05,0,0)
EnsureDrop("Chamomile", 0.05,0,0)
EnsureDrop("Coriander", 0.05,0,0)
EnsureDrop("Paprika", 0.05,0,0)
EnsureDrop("Turmeric", 0.05,0,0)
EnsureDrop("Sugar", 0.05,0,0)
EnsureDrop("Cinnamon", 0.05,0,0)
EnsureDrop("Apple", 0.05,0,0)
EnsureDrop("Carrots", 0.05,0,0)
EnsureDrop("Garlic", 0.05,0,0)
EnsureDrop("Onion", 0.05,0,0)
EnsureDrop("Milk", 0.05,0,0)

# make sure we drop black stuff
EnsureDrop("Black Helmet", 0.05,0,0)
EnsureDrop("Black Chest", 0.05,0,0)
EnsureDrop("Black Gloves", 0.05,0,0)
EnsureDrop("Black Leggings", 0.05,0,0)
EnsureDrop("Black Boots", 0.05,0,0)
EnsureDrop("Black Shield", 0.05,0,0)
EnsureDrop("Black Staff", 0.05,0,0)
EnsureDrop("Black Bow", 0.05,0,0)
EnsureDrop("Black Katana", 0.05,0,0)
EnsureDrop("Black Axe", 0.05,0,0)
EnsureDrop("Black Sword", 0.05,0,0)
EnsureDrop("Black 2h axe", 0.05,0,0)
EnsureDrop("Black 2h sword", 0.05,0,0)
EnsureDrop("Black Spear", 0.05,0,0)

# Dropping non-craftables
EnsureDrop("ArchersRing", 0.05,0,0)
EnsureDrop("ArchersRingII", 0.05,0,0)
EnsureDrop("ArchersRingIII", 0.05,0, 30)
EnsureDrop("MagesRing", 0.05,0,0)
EnsureDrop("MagesRingII", 0.05,0,0)
EnsureDrop("MagesRingIII", 0.05, 0,30)

# Dropping tome resources
EnsureDrop("Hearthstone", 0.05,0,0)
EnsureDrop("WanderersGem", 0.05,0,0)
EnsureDrop("IronEmblem", 0.04,0,0)
EnsureDrop("KyoCrystal", 0.04,0,0)
EnsureDrop("HeimRune", 0.03,0,0)
EnsureDrop("AtriasFeather", 0.03,0,0)
EnsureDrop("EldarasMark", 0.03,0,0)

# scrolls
EnsureDrop("ExpMultiplierScroll", 0.02,0,0)
EnsureDrop("RaidScroll", 0.02,0,0)
EnsureDrop("DungeonScroll", 0.01,0,0)

# Exclusive to Heroic
EnsureDrop("MagesRingIV", 0.05, 4, 60)
EnsureDrop("ArchersRingIV", 0.05, 4, 60)
EnsureDrop("ArchmagesPendant", 0.05, 4, 100)
EnsureDrop("KnightsEmblem", 0.05, 4, 100)
EnsureDrop("OwlsEyeRing", 0.05, 4, 100)
EnsureDrop("RingOfTheCelestial", 0.05, 4, 100)
EnsureDrop("WarriorsMightRing", 0.05, 4, 100)
EnsureDrop("WindcallersAmulet", 0.05, 4, 100)

EnsureDrop("DragonBar", 0.05, 4,0)
EnsureDrop("AbraxasBar", 0.05, 4,0)
EnsureDrop("PhantomBar", 0.05, 4,0)
EnsureDrop("LioniteBar", 0.05, 4,0)
EnsureDrop("EthereumBar", 0.05, 4,0)
EnsureDrop("AncientBar", 0.05, 4,0)
EnsureDrop("AtlarusBar", 0.05, 4,0)
EnsureDrop("RawPufferFish", 0.05, 4,0)
EnsureDrop("RawOctopus", 0.05, 4,0)
EnsureDrop("RawMantaRay", 0.05, 4,0)
EnsureDrop("RawKraken", 0.05, 4,0)
EnsureDrop("Cacao", 0.05, 4,0)
EnsureDrop("Truffle", 0.05, 4,0)
EnsureDrop("Goldenrod", 0.05, 4,0)
EnsureDrop("Wormwood", 0.05, 4,0)
EnsureDrop("Skullcap", 0.05, 4,0)
EnsureDrop("LemonBalm", 0.05, 4,0)
EnsureDrop("Realmstone", 0.05, 4,0)

with open("./ravenpy/data/internal_game_data.json", "w") as f:
    json.dump({
        "item_effects": item_effects,
        "item_raid_drops": item_raid_drops
    }, f, indent=2)
