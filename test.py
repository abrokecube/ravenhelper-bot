import thefuzz.fuzz
import thefuzz.process
from utils.utils import split_arguments, SplitQuery, SplitWildcard
import thefuzz
import ravenpy

print(thefuzz.process.extractOne('goldleaf', ravenpy.get_all_item_names(), scorer=thefuzz.fuzz.ratio))
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