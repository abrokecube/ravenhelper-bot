import math
import asyncio
import twitchio
import ravenpy

from datetime import datetime, timezone
from typing import List
from twitchio.ext import commands
from numerize import numerize
from ravenpy import Skills, Islands, ItemTypes
from utils import utils
from utils import langstuff
from utils import charutils

DEBUG = True
MAX_MSG_LENGTH = 485

class RavenCharacterCommands(commands.Component):
    def __init__(self, bot: commands.Bot, rf_api: ravenpy.Ravenfall):
        self.bot = bot
        self.rf_api = rf_api

    @commands.command(aliases=('char',))
    async def character(self, ctx: commands.Context, *args: str):
        """Get information about a user's characters. 
        Supply a character name, a user name, or both (in that order) to get more 
        information about another user's characters or a specific one.
        """
        result = await charutils.search_user_characters(self.rf_api, ctx, *args)
        if result is None:
            return
        user_chars = result.chars
        
        out_str = []
        is_single_char = len(user_chars) == 1
        for char in user_chars:
            char_name = utils.truncate_sentence(char.name, 40)

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
            exp_to_next_level = math.inf
            num_skills_training = 0
            if not char.in_onsen:
                stats_to_show: List[Skills] = []
                if char.training in ravenpy.fighting_skills:
                    stats.append(f"HP: {char.hp}/{char.health.level}")
                    if char.training in (Skills.All, Skills.Health):
                        stats_to_show.extend([Skills.Attack, Skills.Defense, Skills.Strength])
                    else:
                        stats_to_show.append(char.training)
                elif not char.training:
                    pass
                else:
                    stats_to_show.append(char.training)
                if (not char.island) or char.destination == Islands.Ferry:
                    stats_to_show.append(Skills.Sailing)
                if char.has_joined_dungeon or char.in_raid:
                    stats_to_show.append(Skills.Slayer)

                for stat in stats_to_show:
                    char_stat = char.get_skill(stat)
                    exp_to_next = char_stat.total_exp_for_level - char_stat.level_exp
                    if exp_to_next < exp_to_next_level:
                        exp_to_next_level = exp_to_next
                    num_skills_training += 1
                    skill_name = char_stat.skill.name.capitalize()
                    if not is_single_char:
                        skill_name = langstuff.skill_contractions[stat]
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
                
            train_time = ""
            now = datetime.now(timezone.utc)
            if char.estimated_level_time:
                train_end_time = char.estimated_level_time
            else:
                train_end_time = datetime(2000, 1, 1, tzinfo=timezone.utc)
            training_time_server = train_end_time - now
            # if char.exp_per_hour > 0 and num_skills_training > 0:
            #     training_time_exp = timedelta(seconds=(exp_to_next_level) / (char.exp_per_hour/60/60/num_skills_training))
            # else:
            #     training_time_exp = math.inf
            s = utils.TimeSize.SMALL_SPACES if is_single_char else utils.TimeSize.SMALL
            train_time_format = utils.format_timedelta(training_time_server, s)
            if char.island and not char.in_onsen:
                if now < train_end_time:
                    if training_time_server.total_seconds() > 60*60*24*100:  # 99 days
                        train_time = f"Level in ∞"
                    else:
                        train_time = f"Level in {train_time_format}"
                    if (not is_single_char) and char.exp_per_hour == 0:
                        train_time = ""
                else:
                    train_time = f"Level in ---"

            exp_per_hr = f""
            if char.island and not char.in_onsen:
                if is_single_char:
                    exp_per_hr = f"{char.exp_per_hour:,} exp/hr"
                else:
                    exp_per_hr = f"{numerize.numerize(char.exp_per_hour,2)} exp/hr"

            auto_dung = ""
            if is_single_char:
                if char.auto_join_dungeon_count == math.inf:
                    auto_dung = "Auto-joining dungeons"
                elif char.auto_join_dungeon_count > 0:
                    auto_dung = f"Auto-joining {utils.pl(char.auto_join_dungeon_count, 'dungeons')}"
            auto_raid = ""
            if is_single_char:
                if char.auto_join_raid_count == math.inf:
                    auto_raid = "Auto-joining raids"
                elif char.auto_join_raid_count > 0:
                    auto_raid = f"Auto-joining {utils.pl(char.auto_join_raid_count, 'raids')}"
            auto_rest = ""
            if is_single_char:
                if char.is_auto_resting and (char.auto_rest_target is not None):
                    auto_rest = "Auto-resting"
                    if char.auto_rest_start != 0 or char.auto_rest_target != 120:
                        auto_rest = f"Auto-resting from {char.auto_rest_start}m to {char.auto_rest_target}m"

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
                " ", char_name, index_and_combat_level, "is", what, where, entering_dungeon, where_island, captain, destination, rested
            )
            out_str.append(utils.strjoin(
                " – ", summary, target_item, utils.strjoin(', ', *stats), exp_per_hr, train_time, auto_dung, auto_raid, auto_rest, clan
            ))
        # coins = f"{utils.pl(user_chars[0].coins, 'coins')}"
        user_name = f"󠀀{user_chars[0].user_name}"
        out_msgs = utils.strjoin_len(" ✦ ", MAX_MSG_LENGTH, user_name, *out_str)
        out_msgs = utils.strextend(out_msgs, MAX_MSG_LENGTH, f" | Training time is estimated")
        # out = " ✦ ".join(out_str)
        for msg in out_msgs:
            await ctx.reply(f"/me {msg}")

    @commands.command(aliases=('rec',))
    async def recommend(self, ctx: commands.Context, user: str = ''):
        """Get recommendations for all characters."""
        user_chars = await charutils.get_user_characters(self.rf_api, ctx, user)
        if user_chars is None:
            return
        
        has_armor_recs = False
        out_str = []
        for char in user_chars:
            char_name = utils.truncate_sentence(char.name, 40)
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
                if is_training_combat and skill.level < char.combat_level and char.combat_level < 300:
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
            out_str[-1] += " | ?recsymbols if you're confused"
        await ctx.reply(utils.strjoin('', f'/me Recommendations for {user_chars[0].user_name} – ', utils.strjoin(' ✦ ', *out_str)))

    @commands.command()
    async def recsymbols(self, ctx: commands.Context):
        await ctx.reply("/me "
        "The letters represent different armor pieces: "
        "H for Helmet, C for Chest, and so on. "
        "Armor pieces are arranged in the following order: "
        "Helmet, Chest, Gloves, Leggings, Boots, and Shield "
        "(from head to feet, with Shield as an extra piece). "
        "An asterisk (*) indicates that the armor piece is in your inventory, "
        "while a dash (-) signifies that it is missing.")

    @commands.command(aliases=('insp',))
    async def inspect(self, ctx: commands.Context, user: str = ''):
        """Get inspect URLs for all characters."""
        user_chars = await charutils.get_user_characters(self.rf_api, ctx, user)
        if user_chars is None:
            return

        out_str = [f"Inspect links for {user_chars[0].user_name}"]
        for char in user_chars:
            index_and_combat_level = f"({char.character_index}, Lv{char.combat_level})"
            char_name = utils.truncate_sentence(char.identifier, 40)
            out_str.append(f"{char_name} {index_and_combat_level}: https://www.ravenfall.stream/inspect/{char.id}")
        if len(out_str) == 0:
            await ctx.reply("This user has no characters.")
            return
        out = " • ".join(out_str)
        await ctx.reply(f"/me {out}")

    @commands.command(aliases=('res','coins','coin'))
    async def resources(self, ctx: commands.Context, user: str = ''):
        """Get a user's coin amount"""
        user_chars = await charutils.get_user_characters(self.rf_api, ctx, user)
        if user_chars is None:
            return
        user_name = user_chars[0].user_name
        coin_amount = user_chars[0].coins
        await ctx.reply(f"/me {user_name} has {utils.pl(coin_amount, 'coin')}")

    @commands.command()
    async def stats(self, ctx: commands.Context, *args):
        """Get stats of a character"""
        result = await charutils.search_user_characters(self.rf_api, ctx, *args, single_char_only=True)
        if result is None:
            return
        user_chars = result.chars
        
        stats_str = []
        total_levels = 0
        for stat in user_chars[0].stats:
            total_levels += stat.level
            stat_percent = ''
            if stat.level_exp > 0:
                stat_percent = f'({stat.level_exp/stat.total_exp_for_level:.0%})'
            stat_string = utils.strjoin(
                    ' ', langstuff.skill_contractions[stat.skill], stat.level,
                    utils.strenclose('[', ']', '', utils.strprefix('+', stat.enchant_levels)),
                    stat_percent
                )
            if stat.skill in user_chars[0].training_skills:
                stat_string = f"■ {stat_string.upper()}"
            else:
                if len(stats_str) > 0:
                    stat_string = f"- {stat_string}"
            stats_str.append(stat_string)
        
        char_name = utils.truncate_sentence(user_chars[0].identifier, 40)
        out_string = utils.strjoin(' ',
            f"Stats for {user_chars[0].user_name}: {char_name}", '✦', 
            f"Combat level: {user_chars[0].combat_level}", '✦', 
            ' '.join(stats_str),
            '✦', f"Total: {total_levels}"
        )
        await ctx.reply(out_string, me=True)
