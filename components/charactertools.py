from twitchio.ext import commands
import ravenpy

from utils import charutils

class RavenCharacterTools(commands.Component):
    def __init__(self, bot: commands.Bot, rf_api: ravenpy.Ravenfall):
        self.bot = bot
        self.rf_api = rf_api
