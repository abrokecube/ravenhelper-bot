import math
import ravenpy

from datetime import datetime, timezone, timedelta
from typing import List
from twitchio.ext import commands
from numerize import numerize
from ravenpy import Skills, Islands, ItemTypes
from utils import utils
from utils import langstuff
from utils import charutils

DEBUG = True
MAX_MSG_LENGTH = 485

skill_map = {
    "Attack": Skills.Attack,
    "atk": Skills.Attack,
    "att": Skills.Attack,
    
    "Defense": Skills.Defense,
    "def": Skills.Defense,
    
    "Strength": Skills.Strength,
    "str": Skills.Strength,
    
    "Health": Skills.Health,
    "hp": Skills.Health,
    
    "Woodcutting": Skills.Woodcutting,
    "wood": Skills.Woodcutting,
    "chop": Skills.Woodcutting,
    "wdc": Skills.Woodcutting,
    "chomp": Skills.Woodcutting,
    
    "Fishing": Skills.Fishing,
    "fish": Skills.Fishing,
    "fsh": Skills.Fishing,
    "fist": Skills.Fishing,
    
    "Mining": Skills.Mining,
    "mine": Skills.Mining,
    "min": Skills.Mining,
    "mining": Skills.Mining,
    
    "Crafting": Skills.Crafting,
    "craft": Skills.Crafting,
    
    "Cooking": Skills.Cooking,
    "cook": Skills.Cooking,
    "ckn": Skills.Cooking,
    
    "Farming": Skills.Farming,
    "farm": Skills.Farming,
    "fm": Skills.Farming,
    
    "Slayer": Skills.Slayer,
    "slay": Skills.Slayer,
    
    "Magic": Skills.Magic,
    
    "Ranged": Skills.Ranged,
    "range": Skills.Ranged,
    
    "Sailing": Skills.Sailing,
    "sail": Skills.Sailing,
    
    "Healing": Skills.Healing,
    "heal": Skills.Healing,
    
    "Gathering": Skills.Gathering,
    "gath": Skills.Gathering,
    
    "Alchemy": Skills.Alchemy,
    "brew": Skills.Alchemy,
    "alch": Skills.Alchemy,
    
    "all": Skills.All,
    
    "level": 'level',
    "combat": 'combat',
    "resource": 'resource',
    "*": 'every',
    "allall": 'every',
    "every": 'every',
}

class RavenCharacterCommands(commands.Component):
    def __init__(self, bot: commands.Bot, rf_api: ravenpy.RavenNest):
        self.bot = bot
        self.rf_api = rf_api

    @commands.command(aliases=('char','chars','characters'))
    async def character(self, ctx: commands.Context, *args: str):
        """Get information about a user's characters. 
        Supply a character name, a user name, or both (in that order) to get more 
        information about another user's characters or a specific one.
        
        Args:
            user (str, optional): Twitch username.
            character (str, optional): Character index or name.
        """
        result = await charutils.search_user_characters(self.rf_api, ctx, *args)
        if result is None:
            return
        user_chars = result.chars
        
        out_str = []
        is_single_char = len(user_chars) == 1
        for char in user_chars:
            char_name = utils.unping(utils.truncate_sentence(char.name, 40))

            if char_name in ['1', '2', '3']:
                char_name = f"Character {char_name}"
            else:
                char_name = f"{char_name}"
            where = ""
            if char.in_raid:
                where = "in a raid"
            if char.in_arena:
                where = "in the arena"
            if char.in_dungeon:
                where = "in a dungeon"
            if char.in_onsen:
                where = "in the onsen"
            entering_dungeon = ""
            if char.has_joined_dungeon and not char.in_dungeon:
                entering_dungeon = "entering the dungeon"

            index_and_combat_level = f"({char.character_index}, Lv{char.combat_level})"

            what = ""
            if char.training in (Skills.Attack, Skills.Defense, Skills.Strength, Skills.Health):
                what = f"training {char.training.name.lower()}"
            elif char.training in ravenpy.resource_skills:
                if char.target_item:
                    what = f"{char.training.name.lower()} {char.target_item.item.name.lower()}"
                else:
                    what = f"{char.training.name.lower()}"
            elif char.training == Skills.Alchemy:
                what = f"training alchemy"
            elif char.training == Skills.Sailing:
                pass
            elif char.training is None:
                pass
            else:
                what = f"{char.training.name.lower()}"

            if char.in_onsen:
                what = "resting"
            if char.destination == ravenpy.Islands.Ferry:
                what = f""

            target_item = ""
            if char.target_item and what and not char.in_onsen:
                target_item = f"{char.target_item.amount}× {char.target_item.item.name}"

            where_island = ""
            if char.island:
                where_island = f"at {char.island.name.capitalize()}"
            elif char.destination == Islands.Ferry:
                where_island = f"on the ferry"
            else:
                where_island = "sailing the seas"

            rested = ""
            if char.rested_time.total_seconds() > 0:
                s = utils.TimeSize.SMALL_SPACES if is_single_char else utils.TimeSize.SMALL
                rested = f"with {utils.format_seconds(char.rested_time.total_seconds(),s)} of rest time"
        
            captain = ""
            if char.is_captain:
                captain = "as the ship captain"

            destination = ""
            if char.waiting_for_ferry:
                destination = f"waiting for the ferry"

            stats = []
            if not char.in_onsen:
                for char_stat in char.training_stats:
                    skill_name = char_stat.skill.name.capitalize()
                    if not is_single_char:
                        skill_name = langstuff.skill_contractions[char_stat.skill]
                        stats.append(
                            f"{skill_name}: {char_stat.level} [+{char_stat.enchant_levels}] "\
                            f"({char_stat.level_exp/char_stat.total_exp_for_level:.1%})"
                        )
                    else:
                        stats.append(
                            f"{skill_name}: {char_stat.level} [+{char_stat.enchant_levels}] "\
                            f"({char_stat.level_exp/char_stat.total_exp_for_level:.1%}) "\
                            f"{char_stat.level_exp:,.0f}/{char_stat.total_exp_for_level:,.0f} EXP"
                        )
            combat_mult = 5
            train_time = ""
            now = datetime.now(timezone.utc)
            if char.estimated_level_time:
                train_end_time = char.estimated_level_time
            else:
                train_end_time = datetime(2000, 1, 1, tzinfo=timezone.utc)
            training_time_server = train_end_time - now
            if char.exp_per_hour > 0 and char.training:
                # closest_stat = min(*char.training_stats, key=lambda x: x.total_exp_for_level-x.level_exp)
                closest_stat = char.training_stats[0]
                exp_to_next_level = closest_stat.total_exp_for_level-closest_stat.level_exp
                training_time_exp = timedelta(seconds=(exp_to_next_level) / (char.exp_per_hour/60/60))
            else:
                training_time_exp = timedelta(weeks=9999)
            s = utils.TimeSize.SMALL_SPACES if is_single_char else utils.TimeSize.SMALL
            # train_time_format = utils.format_timedelta(training_time_server, s) + '/' + utils.format_timedelta(training_time_exp, s)
            train_time_diff = (training_time_exp - training_time_server)
            char_is_offline = train_time_diff.total_seconds() > 60*3  # 3 minutes
            if char.training in (Skills.Attack, Skills.Defense, Skills.Strength) and not (char.in_raid or char.in_dungeon):
                training_time_exp /= combat_mult
                training_time_server /= combat_mult
            # train_time_format = utils.format_timedelta(training_time_server, s)
            train_time_format = utils.format_timedelta(training_time_exp, s)
            if char.island and not char.in_onsen:
                if char_is_offline:
                    train_time = f""
                elif now < train_end_time:
                    if training_time_server.total_seconds() > 60*60*24*100:  # 99 days
                        train_time = f"Level in ∞"
                    else:
                        train_time = f"Level in {train_time_format}"
                    if (not is_single_char) and char.exp_per_hour == 0:
                        train_time = ""
                else:
                    train_time = f"Level in ---"
                    
            offline = "OFFLINE," if char_is_offline else ""

            exp_per_hr = f""
            if char.island and not char.in_onsen:
                if is_single_char:
                    exp_per_hr = f"{char.exp_per_hour:,} exp/hr"
                else:
                    exp_per_hr = f"{numerize.numerize(char.exp_per_hour,2)} exp/hr"

            status_effects = ""
            if is_single_char:
                char_statuses = []
                for status in char.status_effects:
                    char_statuses.append(
                        f"{langstuff.status_effect_names_short[status.effect]} "\
                        f"+{status.amount:.1%} for {utils.format_seconds(status.time_left)}"
                    )
                status_effects = utils.strjoin(', ', *char_statuses, before_end=' and ')
            else:
                if len(char.status_effects) > 0:
                    status_effects = f"{utils.pl(len(char.status_effects), 'active status effect')}"

            clan = ""
            if is_single_char:
                if char.clan:
                    preposition = "at"
                    clan_role = char.clan_role.role.name
                    if char.clan.owner_id == char.id:
                        clan_role = "Owner"
                    if clan_role in ["Member", "Owner"]:
                        preposition = "of"
                    clan = f"{clan_role} {preposition} clan {char.clan.name}"

            summary = utils.strjoin(
                " ", char_name, index_and_combat_level, "is", offline, what, where, entering_dungeon, where_island, captain, destination, rested
            )
            out_str.append(utils.strjoin(
                " – ", summary, target_item, utils.strjoin(', ', *stats), exp_per_hr, train_time, status_effects, clan
            ))
        # coins = f"{utils.pl(user_chars[0].coins, 'coins')}"
        user_name = f"{utils.unping(user_chars[0].user_name)}"
        out_msgs = utils.strjoin_len(" ✦ ", MAX_MSG_LENGTH, user_name, *out_str)
        out_msgs = utils.strextend(out_msgs, MAX_MSG_LENGTH, f" | Training time is estimated")
        # out = " ✦ ".join(out_str)
        for msg in out_msgs:
            await ctx.send(f"/me {msg}")

    @commands.command(aliases=('rec',))
    async def recommend(self, ctx: commands.Context, user: str = ''):
        """Get recommendations for all characters.
        
        Args:
            user (str, optional): Twitch username.
        """
        user_chars = await charutils.get_user_characters(self.rf_api, ctx, user)
        if user_chars is None:
            return
        
        has_armor_recs = False
        out_str = []
        for char in user_chars:
            char_name = utils.unping(utils.truncate_sentence(char.name, 40))
            index_and_combat_level = f"({char.character_index}, Lv{char.combat_level})"
            is_training_combat = False
            
            training = ""
            if char.training:
                training = f"[{char.training.name}]"
            else:
                training = f"Not training!"

            rec_island = ""
            if char.training and not char.training == Skills.Sailing:
                if char.training in (Skills.All, Skills.Health):
                    skill = max(char.attack, char.defense, char.strength, key=lambda x: x.level)
                else:
                    skill = char.get_skill(char.training)
                    
                is_training_combat = skill.skill in ravenpy.fighting_skills
                recommended_island = ravenpy.get_island_for_level(skill.level)
                if is_training_combat and skill.level < char.combat_level:
                    recommended_island = ravenpy.get_island_for_level(char.combat_level)
                
                if recommended_island != char.island:
                    rec_island = f"Sail to {recommended_island.name.capitalize()}"
            
            short_rec_armor = []
            rec_armor = ""
            rec_armor_mat = ravenpy.get_material_for_level(char.defense.level)
            eq = char.equipment
            armors = [
                (eq.helmet, 'Helmet'),
                (eq.chest, 'Chest'),
                (eq.gloves, 'Gloves'),
                (eq.leggings, 'Leggings'),
                (eq.boots, 'Boots'),
            ]
            if not eq.weapon or eq.weapon.item.type in (ItemTypes.OneHandedSword, ItemTypes.OneHandedAxe):
                armors.append((eq.shield, 'Shield'))
            for piece, short_l in armors:
                if (not piece) or piece.item.material != rec_armor_mat:
                    in_inventory = char.get_item(f"{langstuff.material_names[rec_armor_mat]} {short_l}")
                    if in_inventory:
                        short_rec_armor.append("*")
                    else:
                        short_rec_armor.append(short_l[0])
                    rec_armor = f"{langstuff.material_names[rec_armor_mat]} set"
                else:
                    short_rec_armor.append("-")
            if rec_armor:
                rec_armor = utils.strjoin(" ", rec_armor, utils.strenclose("(", ")", "", utils.strjoin('',*short_rec_armor)))
                has_armor_recs = True

            rec_weapon = ""
            if Skills.Health in (char.dungeon_combat_style, char.raid_combat_style) \
               or char.training in (Skills.All, Skills.Attack, Skills.Defense, Skills.Strength, Skills.Health) \
               or eq.weapon:
                rec_weapon_mat = ravenpy.get_material_for_level(char.attack.level)
                inv_check = []
                if not eq.weapon:
                    rec_weapon = f"{rec_weapon_mat.name} weapon"
                    inv_check.append(f"{rec_weapon_mat.name} Sword")
                    inv_check.append(f"{rec_weapon_mat.name} 2H Sword")
                    inv_check.append(f"{rec_weapon_mat.name} Axe")
                    inv_check.append(f"{rec_weapon_mat.name} 2H Axe")
                elif eq.weapon.item.material != rec_weapon_mat:
                    rec_weapon = f"{langstuff.material_names[rec_weapon_mat]} {utils.rm_words(eq.weapon.item.name, 1)}"
                    inv_check.append(rec_weapon)

                for item_name in inv_check:
                    if char.get_item(item_name):
                        rec_weapon += "*"
                        break

            rec_staff = ""
            if Skills.Healing in (char.dungeon_combat_style, char.raid_combat_style, char.training)\
               or Skills.Magic in (char.dungeon_combat_style, char.raid_combat_style, char.training)\
               or eq.staff:
                rec_mat = ravenpy.get_material_for_level(max(char.healing.level, char.magic.level))
                if (not eq.staff) or eq.staff.item.material != rec_mat:
                    rec_staff = f"{langstuff.material_names[rec_mat]} staff"
                    if char.get_item(f"{langstuff.material_names[rec_mat]} Staff"):
                        rec_staff += "*"
            
            rec_bow = ""
            if Skills.Ranged in (char.dungeon_combat_style, char.raid_combat_style, char.training)\
               or eq.bow:
                rec_mat = ravenpy.get_material_for_level(char.ranged.level)
                if (not eq.bow) or eq.bow.item.material != rec_mat:
                    rec_bow = f"{langstuff.material_names[rec_mat]} bow"
                    if char.get_item(f"{langstuff.material_names[rec_mat]} Bow"):
                        rec_bow += "*"

            char_recs = utils.strjoin(
                ' – ', rec_island, rec_armor, rec_weapon, rec_staff, rec_bow
            )
            if len(char_recs) > 0:
                out_str.append(utils.strjoin(' ', f"{char_name} {index_and_combat_level}:", training, '–', char_recs))
        if len(out_str) == 0:
            out_str.append(f"You're all good! Okay")

        if has_armor_recs:
            out_str[-1] += f" | {ctx.prefix}recsymbols if you're confused"
        await ctx.send(utils.strjoin('', f'/me Recommendations for {utils.unping(user_chars[0].user_name)} – ', utils.strjoin(' ✦ ', *out_str)))

    @commands.command()
    async def recsymbols(self, ctx: commands.Context):
        await ctx.send("/me "
        "The letters represent different armor pieces: "
        "H for Helmet, C for Chest, and so on. "
        "Armor pieces are arranged in the following order: "
        "Helmet, Chest, Gloves, Leggings, Boots, and Shield "
        "(from head to feet, with Shield as an extra piece). "
        "An asterisk (*) indicates that the armor piece is in your inventory, "
        "while a dash (-) signifies that it is missing.")

    @commands.command(aliases=('insp',))
    async def inspect(self, ctx: commands.Context, user: str = ''):
        """Get inspect URLs for all characters.
        
        Args:
            user (str, optional): Twitch username.
        """
        user_chars = await charutils.get_user_characters(self.rf_api, ctx, user)
        if user_chars is None:
            return

        out_str = [f"Inspect links for {utils.unping(user_chars[0].user_name)}"]
        for char in user_chars:
            index_and_combat_level = f"({char.character_index}, Lv{char.combat_level})"
            char_name = utils.unping(utils.truncate_sentence(char.identifier, 40))
            out_str.append(f"{char_name} {index_and_combat_level}: https://www.ravenfall.stream/inspect/{char.id}")
        if len(out_str) == 0:
            await ctx.send("This user has no characters.")
            return
        out = " • ".join(out_str)
        await ctx.send(f"/me {out}")

    @commands.command(aliases=('res','coins','coin'))
    async def resources(self, ctx: commands.Context, user: str = ''):
        """Get a user's coin amount and inventory value.
        
        Args:
            user (str, optional): Twitch username.
        """
        user_chars = await charutils.get_user_characters(self.rf_api, ctx, user)
        if user_chars is None:
            return
        user_name = utils.unping(user_chars[0].user_name)
        coin_amount = user_chars[0].coins
        worth_strings = []
        total_worth = coin_amount
        for char in user_chars:
            inventory_worth = 0
            for item in char.items:
                inventory_worth += item.item.sell_price * item.amount
            total_worth += inventory_worth
            worth_strings.append(
                f"{utils.unping(utils.truncate_sentence(char.name, 30))}: {utils.pl(inventory_worth, 'coin')}"
            )            
        await ctx.send(
            f"/me {user_name} has {utils.pl(coin_amount, 'coin')} ✦ "\
            f"Inventory worth: {utils.strjoin(' • ', *worth_strings)} ✦ "\
            f"Net worth: {utils.pl(total_worth, 'coin')}"
        )


    @commands.command()
    async def training(self, ctx: commands.Context, user: str = ''):
        """Get a user's currently training skills. 
        
        Args:
            user (str, optional): Twitch username.
        """
        user_chars = await charutils.get_user_characters(self.rf_api, ctx, user)
        if user_chars is None:
            return
        user_name = utils.unping(user_chars[0].user_name)
                    
        char_trainings = [f"{utils.get_char_identifier(x)} is training {x.training.name}" for x in user_chars]
        await ctx.send(
            f"{user_name} ✦ {utils.strjoin(' – ', *char_trainings)}",
            me=True
        )


    @commands.command(aliases=('island',))
    async def where(self, ctx: commands.Context, user: str = ''):
        """Get a user's current location. 
        
        Args:
            user (str, optional): Twitch username.
        """
        user_chars = await charutils.get_user_characters(self.rf_api, ctx, user)
        if user_chars is None:
            return
        user_name = utils.unping(user_chars[0].user_name)
        
        char_trainings = []
        
        for char in user_chars:
            what = ""                
            if char.in_onsen:
                what = "resting"

            where = ""
            if char.in_raid:
                where = "in a raid"
            if char.in_arena:
                where = "in the arena"
            if char.in_dungeon:
                where = "in a dungeon"
            if char.in_onsen:
                where = "in the onsen"
                
            entering_dungeon = ""
            if char.has_joined_dungeon and not char.in_dungeon:
                entering_dungeon = "entering the dungeon"

            where_island = ""
            if char.island:
                where_island = f"at {char.island.name.capitalize()}"
            elif char.destination == Islands.Ferry:
                where_island = f"on the ferry"
            else:
                where_island = "sailing the seas"

            captain = ""
            if char.is_captain:
                captain = "as the ship captain"

            destination = ""
            if char.waiting_for_ferry:
                destination = f"waiting for the ferry"

            summary = utils.strjoin(
                " ", utils.get_char_identifier(char), "is", what, where, entering_dungeon, where_island, captain, destination
            )
            char_trainings.append(summary)
            
        await ctx.send(
            f"{user_name} ✦ {utils.strjoin(' – ', *char_trainings)}",
            me=True
        )
        
    @commands.command()
    async def auto(self, ctx: commands.Context, user: str = ''):
        """Get a user's auto dungeon/raid/rest status.
        
        Args:
            user (str, optional): Twitch username.
        """
        user_chars = await charutils.get_user_characters(self.rf_api, ctx, user)
        if user_chars is None:
            return
        user_name = utils.unping(user_chars[0].user_name)
        char_strs = []
        for char in user_chars:
            char_statuses = []
            if char.auto_join_dungeon_count == math.inf:
                char_statuses.append("dungeons")
            elif char.auto_join_dungeon_count > 0:
                char_statuses.append(f"{utils.pl(char.auto_join_dungeon_count, 'dungeons')}")
                
            if char.auto_join_raid_count == math.inf:
                char_statuses.append("raids")
            elif char.auto_join_raid_count > 0:
                char_statuses.append(f"{utils.pl(char.auto_join_raid_count, 'raids')}")

            if char.is_auto_resting and (char.auto_rest_start is not None):
                if char.auto_rest_start != 0 or char.auto_rest_target != 120:
                    char_statuses.append(
                        f"resting from {char.auto_rest_start} min to {char.auto_rest_target} min"
                    )
                else:
                    char_statuses.append("resting")
            if len(char_statuses) == 0:
                char_statuses.append("none")
            char_name = utils.unping(utils.truncate_sentence(char.name, 30))
            char_strs.append(
                f"{char_name}: {utils.strjoin(', ', *char_statuses, before_end=' and ').capitalize()}"
            )
        await ctx.send(
            f"Auto status for {user_name} ✦ {utils.strjoin(' • ', *char_strs)}",
            me=True
        )
        
    @commands.command(aliases=('effects',))
    async def status(self, ctx: commands.Context, user: str = ''):
        """Get a user's active status effects.
        
        Args:
            user (str, optional): Twitch username.
        """
        user_chars = await charutils.get_user_characters(self.rf_api, ctx, user)
        if user_chars is None:
            return
        user_name = utils.unping(user_chars[0].user_name)
        char_strs = []        
        for char in user_chars:
            char_statuses = []
            for status in char.status_effects:
                char_statuses.append(
                    f"{langstuff.status_effect_names[status.effect]} "\
                    f"+{status.amount:.1%} for {utils.format_seconds(status.time_left)}"
                )
            if len(char_statuses) == 0:
                char_statuses.append("No active effects")

            char_name = utils.unping(utils.truncate_sentence(char.name, 30))
            char_strs.append(
                f"{char_name}: {utils.strjoin(', ', *char_statuses, before_end=' and ')}"
            )

        await ctx.send(
            f"Active status effects for {user_name} ✦ {utils.strjoin(' • ', *char_strs)}",
            me=True
        )
        
    @commands.command()
    async def rested(self, ctx: commands.Context, user: str = ''):
        """Get a user's rested status.
        
        Args:
            user (str, optional): Twitch username.
        """
        user_chars = await charutils.get_user_characters(self.rf_api, ctx, user)
        if user_chars is None:
            return
        user_name = utils.unping(user_chars[0].user_name)
        char_strs = []
        for char in user_chars:
            is_rested = char.rested_time.total_seconds() > 0
            char_str = "Not rested."
            rest_time = utils.format_timedelta(char.rested_time, utils.TimeSize.MEDIUM_SPACES)
            if char.in_onsen:
                char_str = f"Currently resting with {rest_time} of time."
            elif is_rested:
                char_str = f"Rested with {rest_time} of time."
            if char.auto_rest_start is not None:
                char_str += " "
                if char.in_onsen:
                    leave_time = utils.format_seconds((char.auto_rest_target-char.rested_time.total_seconds()/60)*60, utils.TimeSize.MEDIUM_SPACES)
                    char_str += f"Leaving in {leave_time}."
                elif is_rested:
                    enter_time = utils.format_seconds(((char.rested_time.total_seconds()/60)-char.auto_rest_start)*60, utils.TimeSize.MEDIUM_SPACES)
                    char_str += f"Returning in {enter_time}."
            
            char_name = utils.unping(utils.truncate_sentence(char.name, 30))
            char_strs.append(
                f"{char_name}: {char_str}"
            )
        await ctx.send(
            f"Rested status for {user_name} ✦ {utils.strjoin(' • ', *char_strs)}",
            me=True
        )
    
    @commands.command(aliases=('lastupdate','lastupdated?'))
    async def desync(self, ctx: commands.Context, user: str = ''):
        """Get a user's desync (time since last updated).
        
        Args:
            user (str, optional): Twitch username.
        """
        user_chars = await charutils.get_user_characters(self.rf_api, ctx, user)
        if user_chars is None:
            return
        user_name = utils.unping(user_chars[0].user_name)
        char_strs = []
        now = datetime.now(timezone.utc)
        for char in user_chars:
            desync_s = None
            if char.estimated_level_time and char.exp_per_hour > 0:
                training_time_server = char.estimated_level_time - now
                closest_stat = char.training_stats[0]
                exp_to_next_level = closest_stat.total_exp_for_level-closest_stat.level_exp
                training_time_exp = timedelta(seconds=(exp_to_next_level) / (char.exp_per_hour/60/60))
                train_time_diff = (training_time_exp - training_time_server)
                desync_s = train_time_diff.total_seconds()
                char_str = f"{utils.format_seconds(desync_s)}"
            else:
                char_str = f"Unknown"
                if char.is_resting:
                    char_str += " (resting)"
                elif not char.training:
                    char_str += " (not training)"
                elif char.training == Skills.Sailing:
                    char_str += " (sailing)"
            
            char_name = utils.unping(utils.truncate_sentence(char.name, 30))
            char_strs.append(
                f"{char_name}: {char_str}"
            )
        await ctx.send(
            f"Last update times for {user_name} ✦ {utils.strjoin(' • ', *char_strs)}",
            me=True
        )

    # _training_currently_calculating = set()
    
    # @commands.command(aliases=('train',))
    # async def training(self, ctx: commands.Context, user: str = ''):
    #     """Get a user's currently training skills. Provides a *slightly* more accurate
    #     training time estimate.
        
    #     Args:
    #         user (str, optional): Twitch username.
    #     """
    #     user_chars = await charutils.get_user_characters(self.rf_api, ctx, user)
    #     if user_chars is None:
    #         return
    #     user_name = user_chars[0].user_name
        
    #     calculate_training_time = True
    #     end_msg = "Calculating training time... (>30 seconds)"
    #     calc_key = f"{ctx.author.id}_{user_name}"
    #     if calc_key in self._training_currently_calculating:
    #         calculate_training_time = False
    #         end_msg = "Calculation is currently in progress..."
    #     else:
    #         self._training_currently_calculating.add(calc_key)
            
    #     char_trainings = [f"{get_char_identifier(x)} is training {x.training.name}" for x in user_chars]
    #     await ctx.send(
    #         f"{user_name} ✦ {utils.strjoin(' – ', *char_trainings)} ✦ {end_msg}",
    #         me=True
    #     )
        
    #     if not calculate_training_time:
    #         return
        
    #     samples = [[] for _ in range(len(user_chars))]
    #     target_samples = 10
    #     while min([len(x) for x in samples]) < target_samples:
    #         updated_char_tasks = []
    #         updated_char_indeces = []
    #         for idx, char in enumerate(user_chars):
    #             # if len(samples[idx]) < target_samples:
    #                 updated_char_tasks.append(self.rf_api.get_character(char.twitch_id, char.index, random.random()))
    #                 updated_char_indeces.append(idx)
    #         updated_chars = await asyncio.gather(*updated_char_tasks, return_exceptions=not DEBUG)
            
    #         for idx, char in zip(updated_char_indeces, updated_chars):
    #             char: ravenpy.Character
    #             est_ts = char.estimated_level_time.timestamp()
    #             recieve_ts = char.time_recieved_datetime.timestamp()
    #             exp_h = char.exp_per_hour
    #             stat = char.training_stats[0]
    #             est_ts_exp_h = recieve_ts + (stat.total_exp_for_level - stat.level_exp) / exp_h*60*60
    #             exp = stat.level_exp
    #             est_diff = (est_ts - est_ts_exp_h)
    #             if samples[idx] and exp_h != samples[idx][-1][2]:
    #                 samples[idx].clear()
    #                 logging.info("Exp rate is changing")
    #             if not samples[idx] or samples[idx][-1][0] != est_ts:
    #                 samples[idx].append((exp, recieve_ts, exp_h, est_diff))
    #                 # samples[idx].append((est_ts, recieve_ts, exp_h))
    #             else:
    #                 logging.info("Skipped a timestamp")
    #         await asyncio.sleep(4)
    #     avg_rates = []
    #     for data in samples:
    #         rates = []
    #         for i in range(1, len(data)):
    #             num_diff = data[i][0] - data[i - 1][0]
    #             time_diff = data[i][1] - data[i - 1][1]
    #             if time_diff != 0:
    #                 rates.append(num_diff / time_diff)
    #         avg_rates.append(sum(rates) / len(rates))
    #         logging.info([round(x[0], 3) for x in data])
    #         logging.info([round(x, 3) for x in rates])
            
    #     logging.info(avg_rates)
    #     char_estimates = []
    #     t = datetime.now(timezone.utc)
    #     for idx, char in enumerate(user_chars):
    #         stat = char.training_stats[0]
    #         rate = avg_rates[idx]
    #         # time_difference = char.estimated_level_time - t
    #         # actual_finish_time = t + time_difference / (1 - rate)
    #         # time_to_level = utils.format_timedelta(
    #         #     actual_finish_time-t, utils.TimeSize.MEDIUM_SPACES
    #         # )
    #         time_to_level = utils.format_seconds((stat.total_exp_for_level-stat.level_exp) / rate)
    #         char_identifier = get_char_identifier(char)
    #         char_estimates.append(
    #             f"{char_identifier}: {stat.skill.name} {stat.level} " \
    #             f"({stat.level_exp/stat.total_exp_for_level:.1%}) – Level in {time_to_level}"
    #         )
    #     await ctx.send(
    #         f"Estimated training time to next level for {user_name} ✦ " \
    #         f"{utils.strjoin(' ✦ ', *char_estimates)}",
    #         me=True
    #     )
    #     self._training_currently_calculating.remove(calc_key)

    @commands.command()
    async def stats(self, ctx: commands.Context, *args):
        """Get stats of a character
        
        Args:
            user (str, optional): Twitch username.
            character (str, optional): Character index or name.
            stat (str, optional): Stats to check (up to 10). You can also use
                'level' for combat level, 'resource' for resource skills,
                'combat' for combat skills, and 'every' for all skills.
        """
        result = await charutils.search_user_characters(
            self.rf_api, ctx, *args,
            author_chars_fallback=True,
            all_chars_fallback=True
        )
        if result is None:
            return
        user_chars = result.chars
        stat_query = utils.SplitQuery(skill_map.keys())
        
        match_results = utils.split_arguments(
            result.leftover_args,
            utils.SplitWildcard(),
            stat_query,
            utils.SplitWildcard(),
            stat_query,
            utils.SplitWildcard(),
            stat_query,
            utils.SplitWildcard(),
            stat_query,
            utils.SplitWildcard(),
            stat_query,
            utils.SplitWildcard(),
            stat_query,
            utils.SplitWildcard(),
            stat_query,
            utils.SplitWildcard(),
            stat_query,
            utils.SplitWildcard(),
            stat_query,
            utils.SplitWildcard(),
            stat_query,
        )
        skills_q_d = {}
        for thing in [x.text for x in match_results[1::2] if x.text]:
            skills_q_d[skill_map[thing]] = None
        
        skills = {}
        include_combat_lvl = False
        for thing in skills_q_d.keys():
            if isinstance(thing, Skills):
                if thing not in (Skills.All, Skills.Melee):
                    skills[thing] = None
                else:
                    skills[Skills.Attack] = None
                    skills[Skills.Defense] = None
                    skills[Skills.Strength] = None
                    skills[Skills.Health] = None
            elif thing == "level":
                # skills['level'] = None
                include_combat_lvl = True
            elif thing == 'combat':
                for skill in ravenpy.fighting_skills:
                    if skill not in (Skills.All, Skills.Melee):
                        skills[skill] = None
            elif thing == 'resource':
                for skill in ravenpy.resource_skills:
                    skills[skill] = None
            elif thing == 'every':
                for skill in ravenpy.Skills:
                    if skill not in (Skills.All, Skills.Melee):
                        skills[skill] = None
        
        specified_skills = False
        if len(user_chars) == 1 and not skills:
            ...
        elif not skills and len(user_chars) > 1:
            char_names = [x.name for x in user_chars]
            await ctx.send(f"uuh Please specify a character name, index or skill. " \
                f"(Characters: {utils.strjoin(', ', *char_names, before_end=' and ')}.)"
            )
            return
        else:
            specified_skills = True

        if not skills:
            for skill in ravenpy.Skills:
                if skill not in (Skills.All, Skills.Melee):
                    skills[skill] = None
        
        stats_str = []
        totals = [0] * len(user_chars)
        for skill in skills.keys():
            single_stat_str = []
            for idx, character in enumerate(user_chars):
                stat = character.get_skill(skill)
                stat_percent = ''
                if stat.level_exp > 0:
                    if len(user_chars) == 1 and specified_skills:
                        stat_percent = f'({stat.level_exp/stat.total_exp_for_level:.1%}) {stat.level_exp:,.0f}/{stat.total_exp_for_level:,} exp'
                    else:
                        stat_percent = f'({stat.level_exp/stat.total_exp_for_level:.1%})'
                train_indicate = ''
                if skill in character.training_skills:
                    train_indicate = '■ '
                stat_string = utils.strjoin(
                    ' ', f"{train_indicate}{stat.level}",
                    utils.strenclose('[', ']', '', utils.strprefix('+', stat.enchant_levels)),
                    stat_percent
                )
                single_stat_str.append(stat_string)
                totals[idx] += stat.level
                
            stat_name = ""
            if len(skills) < 7:
                stat_name = stat.skill.name
            else:
                stat_name = langstuff.skill_contractions[stat.skill]
            out_stat_str = utils.strjoin(
                ' ', stat_name,
                utils.strjoin(', ', *single_stat_str)
            )
            if len(user_chars) == 1 and skill in character.training_skills:
                out_stat_str = out_stat_str.upper()
            stats_str.append(out_stat_str)
        
        total_levels = ''
        if not specified_skills:
            total_levels = f"Total: {', '.join([str(x) for x in totals])}"
            
        char_combat_levels = utils.strjoin(', ', *[str(x.combat_level) for x in user_chars])
        combat_levels = ''
        if (not specified_skills) or include_combat_lvl:
            combat_levels = f"Combat level: {char_combat_levels}"
            
        char_names = utils.strjoin(', ', *[utils.unping(x.name) for x in user_chars], before_end=' and ')
        out_strings = utils.strjoin_len(' ✦ ', MAX_MSG_LENGTH,
            f"Stats for {utils.unping(user_chars[0].user_name)}: {char_names}",
            combat_levels,
        )
        out_strings = utils.strextend(
            out_strings, MAX_MSG_LENGTH,
            ' ✦ ', *utils.strjoin_list(' - ', *stats_str),
        )
        if total_levels:
            out_strings = utils.strextend(
                out_strings, MAX_MSG_LENGTH,
                ' ✦ ', total_levels
            )
        for text in out_strings:
            await ctx.send(text, me=True)

    @commands.command(aliases=('charitem','count'))
    async def items(self, ctx: commands.Context, *args):
        """Show how much of an item a user has.
        
        Args:
            user (str, optional): Twitch username.
            items (str): Item name(s) to check. Up to 10 item names will be accepted.
        """
        if not args:
            await ctx.send(f"uuh Please provide one or more item names")
            return
        args_filtered = list(args)
        user_q = ''
        if args_filtered[0][0] == '@' and utils.is_twitch_username(args_filtered[0]):
            user_q = args_filtered.pop(0)
        item_query = utils.get_item_split_query()
        item_query.match_threshold = 85
        result = utils.split_arguments(
            args_filtered,
            utils.SplitWildcard(),
            item_query,
            utils.SplitWildcard(),
            item_query,
            utils.SplitWildcard(),
            item_query,
            utils.SplitWildcard(),
            item_query,
            utils.SplitWildcard(),
            item_query,
            utils.SplitWildcard(),
            item_query,
            utils.SplitWildcard(),
            item_query,
            utils.SplitWildcard(),
            item_query,
            utils.SplitWildcard(),
            item_query,
            utils.SplitWildcard(),
            item_query,
        )
        if not user_q:
            user_q = result[0].text
        if not result[1].text:
            out_msg = "uuh No valid item names were provided."
            item_strs = []
            for x in range(5):
                iresult, iscore = result[1].match_results[x]
                if iscore < 50:
                    break
                item_strs.append(iresult)
            if item_strs:
                out_msg = f"{out_msg} (Did you mean {', '.join(item_strs)}?)"
            await ctx.send(out_msg)
            return
        items_q = {}
        for thing in [x.text for x in result[1::2] if x.text]:
            items_q[thing] = None
        user_chars = await charutils.get_user_characters(self.rf_api, ctx, user_q)
        if user_chars is None:
            return
        
        user_char_names = [utils.unping(x.name) for x in user_chars]
        items_str = []
        for item_name in items_q.keys():
            item_counts = []
            for char in user_chars:
                char: ravenpy.Character 
                char_item = char.get_all_item(item_name)
                if char_item:
                    total_count = sum([x.amount for x in char_item])
                else:
                    total_count = 0
                item_counts.append(f"×{total_count}")
            items_str.append(f"{item_name}: {', '.join(item_counts)}")
        out_text = utils.strjoin_len(
            '', MAX_MSG_LENGTH, f"Items for {utils.unping(user_chars[0].user_name)}: ",
            utils.strjoin(', ', *user_char_names, before_end=' and '),
            ' ✦ ', *utils.strjoin_list(' • ', *items_str)
        )
        for thing in out_text:
            await ctx.send(thing, me=True)
            