import twitchio
from twitchio.ext import commands
import thefuzz
from utils.utils import strjoin, strenclose
from docstring_parser import parse
import inspect

class HelpCommands(commands.Component):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.command(aliases=('commands',))
    async def help(self, ctx: commands.Context, command: str = "", argument: str = ""):
        """Shows information about available commands.
        
        Args:
            command (str, optional): A command to show details about.
            argument (str, optional): Argument of a command to show details about.
        """
        if not command in self.bot.commands:
            component_commands = {}
            for comm in self.bot.commands.values():
                if not comm.component in component_commands:
                    component_commands[comm.component] = set()
                component_commands[comm.component].add(comm.name)
            commands_out = []
            for comms in component_commands.values():
                commands_out.append(", ".join(sorted(tuple(comms))))
            # command_list = sorted([x.name for x in set(self.bot.commands.values())])
            bot_commands = " | ".join(commands_out)
            await ctx.reply(f"Commands: {bot_commands}")
            return

        command_class = self.bot.commands[command]
        command_func = self.bot.commands[command]._callback
        doc_string = command_func.__doc__
        nm_out = [f"Usage: {ctx.prefix}{command}"]
        description = ""
        doc_parsed = None
        command_arguments = {}
        if doc_string:
            doc_parsed = parse(doc_string)
            description = doc_parsed.description

        if doc_parsed and doc_parsed.params:
            for param in doc_parsed.params:
                param_str = param.arg_name
                if param.type_name:
                    param_str += f": {param.type_name}"
                if param.is_optional:
                    param_str = f"({param_str})"
                else:
                    param_str = f"<{param_str}>"
                nm_out.append(param_str)
                
                param_optional = ''
                if param.is_optional:
                    param_optional = 'Optional'
                    
                param_desc = strjoin(' – ', param_str, param_optional, param.description)
                command_arguments[param.arg_name] = param_desc
        else:
            func_inspect = inspect.signature(command_func)
            for param in [x for x in func_inspect.parameters.values()][2:]:
                param_str = param.name
                param_type = param.annotation
                param_type_name = ""
                param_is_optional = param.default != param.empty
                if param_type in (str, int, float):
                    param_type_name = param_type.__name__
                if param_type_name:
                    param_str += f": {param_type_name}"
                if param_is_optional:
                    param_str = f"({param_str})"
                else:
                    param_str = f"<{param_str}>"
                nm_out.append(param_str)
                
                param_optional = ''
                if param_is_optional:
                    param_optional = 'Optional'
                    
                param_desc = strjoin(' – ', param_str, param_optional, "(no description)")
                command_arguments[param.name] = param_desc
        
        if argument in command_arguments:
            await ctx.reply(command_arguments[argument])
            return
        
        name_and_usage = " ".join(nm_out)
        aliases = ""
        if command_class.aliases:
            alias_list = list(command_class.aliases)
            if command != command_class.name:
                alias_list.remove(command)
                alias_list.append(command_class.name)
            alias_list.sort()
            aliases = f"Aliases: {', '.join(alias_list)}"

        restrictions = ""
        if command_class.guards:
            restr_to = []
            for guard in command_class.guards:
                if guard.__doc__:
                    restr_to.append(guard.__doc__)
            restrictions = f"Limited to: {', '.join(restr_to)}"
        
        response = strjoin(' – ', name_and_usage, description, restrictions, aliases)
        await ctx.reply(response)
        ...