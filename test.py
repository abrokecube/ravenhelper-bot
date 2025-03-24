from utils.utils import split_arguments, SplitQuery, SplitWildcard
import ravenpy
string_list_1 = [
    'peenaur',
    'snipper',
    'job job',
    ''
]
string_list_2 = [
    'btmc',
    'veedal987',
    'among us',
    ''
]
print(split_arguments(
    'peenaur', 
    SplitQuery(['abrokecube', '']),
    SplitQuery(string_list_1),
    SplitQuery(string_list_2),
    SplitWildcard()
))