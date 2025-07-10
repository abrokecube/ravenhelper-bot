import twitchio
from twitchio.ext import commands
import thefuzz
from utils.utils import strjoin, strenclose
from docstring_parser import parse
import inspect

def index_or_none(obj_, index):
    if index >= len(obj_):
        return None
    else:
        return obj_[index]

def helptext(bot: commands.Bot, arg: str, prefix: str) -> str:
    args = arg.split()
    
    full_arg_command = index_or_none(args, 0)
    arg_command = index_or_none(args, 0)
    arg_parameter = index_or_none(args, 1)

    if not arg_command in bot.commands:
        component_commands = {}
        for comm in bot.commands.values():
            if not comm.component in component_commands:
                component_commands[comm.component] = set()
            component_commands[comm.component].add(comm.name)
        commands_out = []
        for comms in component_commands.values():
            commands_out.append(", ".join(sorted(tuple(comms))))
        # command_list = sorted([x.name for x in set(bot.commands.values())])
        bot_commands = " | ".join(commands_out)
        return f"Commands: {bot_commands}"

    command_class = bot.commands[arg_command]
    command_func = bot.commands[arg_command]._callback
    
    idx = 1
    while True:
        subcommand_names = set()
        if isinstance(command_class, commands.Group):
            for subcommand in command_class.commands.values():
                subcommand_names.add(subcommand.name)
            arg_subcommand = index_or_none(args, idx)
            if arg_subcommand in command_class.commands:
                command_class = command_class.commands[arg_subcommand]
                command_func = command_class._callback
            else:
                break
            arg_command = index_or_none(args, idx)
            arg_parameter = index_or_none(args, idx+1)
            full_arg_command += f" {arg_command}"
            idx += 1
        else:
            break
        
    doc_string = command_func.__doc__
    nm_out = [f"Usage: {prefix}{full_arg_command}"]
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
    
    if arg_parameter in command_arguments:
        return command_arguments[arg_parameter]
    
    name_and_usage = " ".join(nm_out)
    aliases = ""
    if command_class.aliases:
        alias_list = list(command_class.aliases)
        if arg_command != command_class.name:
            alias_list.remove(arg_command)
            alias_list.append(command_class.name)
        alias_list.sort()
        aliases = f"Aliases: {', '.join(alias_list)}"
        
    subcommands = ""
    if subcommand_names:
        subcommands = f"Subcommands: {', '.join(subcommand_names)}"

    restrictions = ""
    if command_class.guards:
        restr_to = []
        for guard in command_class.guards:
            if guard.__doc__:
                restr_to.append(guard.__doc__)
        restrictions = f"Limited to: {', '.join(restr_to)}"
    
    response = strjoin(' – ', name_and_usage, description, subcommands, restrictions, aliases)
    return response

class HelpCommands(commands.Component):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.command(aliases=('commands',))
    async def help(self, ctx: commands.Context, *args: str):
        """Shows information about available commands.
        
        Args:
            command (str, optional): A command to show details about.
            argument (str, optional): Argument of a command to show details about.
        """
        ctx.reply(helptext(self.bot, strjoin(' ', *args), ctx.prefix))