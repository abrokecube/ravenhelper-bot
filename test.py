import thefuzz.fuzz
import thefuzz.process
from utils.utils import split_arguments, SplitQuery, SplitWildcard
import thefuzz
import ravenpy
import json

aga = """{\"type\":\"pin-message\",\"data\":{\"id\":\"60e6817c-4065-4c78-8eab-97948801d0e1\",\"pinned_by\":{\"id\":\"756734432\",\"display_name\":\"abrokecube\"},\"message\":{\"id\":\"60e6817c-4065-4c78-8eab-97948801d0e1\",\"sender\":{\"id\":\"756734432\",\"display_name\":\"abrokecube\",\"badges\":[{\"id\":\"broadcaster\",\"version\":\"1\"},{\"id\":\"rplace-2023\",\"version\":\"1\"}],\"chat_color\":\"#D2691E\"},\"content\":{\"text\":\"wow\",\"fragments\":[{\"text\":\"wow\"}]},\"type\":\"MOD\",\"starts_at\":1744947509,\"updated_at\":1744947509,\"ends_at\":1744948709,\"sent_at\":1744947509}}}"""

objecasdfsf = json.loads(aga)
...

# print(thefuzz.process.extractOne('goldleaf', ravenpy.get_all_item_names(), scorer=thefuzz.fuzz.ratio))
# string_list_1 = [
#     'peenaur',
#     'snipper',
#     'job job',
#     ''
# ]
# string_list_2 = [
#     'btmc',
#     'veedal987',
#     'among us',
#     ''
# ]
# print([x.text for x in split_arguments(
#     'peenaur among us sus bruh bruh bruh bruh  bruh bruh bruh bruh  ', 
#     SplitQuery(['abrokecube', '']),
#     SplitQuery(string_list_1),
#     SplitQuery(string_list_2),
#     SplitWildcard()
# )])