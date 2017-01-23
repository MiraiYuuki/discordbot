import shlex
import re
import requests
from collections import namedtuple, OrderedDict

class FlagFilter(object):
    def __init__(self, flag, exp=None):
        self.flag = flag
        self.expect = exp if exp is not None else flag

    def match(self, card):
        return (card.av_flag & self.flag) == self.expect

    def __call__(self, card):
        return self.match(card)

drst_nl_query_t = namedtuple("drst_nl_query_t",
    ("keywords", "filters", "ordinal", "is_awake"))
drst_named_id_query_t = namedtuple("drst_named_id_query_t",
    ("id", "is_awake"))

NL_FILTER_LIMITED   =  0b00000001
NL_FILTER_RATES     =  0b00000010
NL_FILTER_EVENT     =  0b00000100
NL_FILTER_GACHA     =  0b00001000
NL_FILTER_CINFEST   =  0b00001011

NL_FILTER_TOKEN     =  0b00010100
NL_FILTER_CARAVAN   =  0b00100100
NL_FILTER_GROOVE    =  0b01000100
NL_FILTER_PARTY     =  0b10000100
NL_FILTER_PARADE    = 0b100000100

DRST_NL_FILTERFLAG_WORDS = OrderedDict((
    (re.compile("ga(c|s)ha"),          FlagFilter(NL_FILTER_GACHA)),
    (re.compile("lim(ited)?"),         FlagFilter(NL_FILTER_LIMITED | NL_FILTER_GACHA)),
    (re.compile("perm(a(nent)?)?"),    FlagFilter(NL_FILTER_GACHA | NL_FILTER_LIMITED, NL_FILTER_GACHA)),
    (re.compile("(s|c)infes(t)?"),     FlagFilter(NL_FILTER_LIMITED | NL_FILTER_CINFEST)),
    (re.compile("event"),              FlagFilter(NL_FILTER_EVENT)),

    (re.compile("token"),              FlagFilter(NL_FILTER_TOKEN)),
    (re.compile("groove|medley"),      FlagFilter(NL_FILTER_GROOVE)),
    (re.compile("party|coop"),         FlagFilter(NL_FILTER_PARTY)),
    (re.compile("parade"),             FlagFilter(NL_FILTER_PARADE)),
    (re.compile("caravan"),            FlagFilter(NL_FILTER_CARAVAN)),

    (re.compile("cute|cool|passion"),  lambda x: 1),
))
DRST_NL_GEX_RESTRICT_ORDINAL = re.compile("([1-9][0-9]*)$")
DRST_NL_GEX_DIRECT_ID = re.compile("'([0-9]+)")

DRST_NL_RARITIES = {"ssr": lambda x: x.rarity == 7,
                    "sr":  lambda x: x.rarity == 5,
                    "r":   lambda x: x.rarity == 3,
                    "n":   lambda x: x.rarity == 1}

class InvalidQueryError(Exception):
    pass

def parse_query(query):
    dm = DRST_NL_GEX_DIRECT_ID.match(query.strip())
    if dm:
        the_id = int(dm.group(1))
        return drst_named_id_query_t(the_id, not (the_id % 2))

    words = query.lower().strip().split()

    wants_awakened = 0
    restrict_ordinal = None
    idol = None
    filters = []

    filtered_words = []

    # step 1: find filter words
    for word in words:
        found_ordinal = DRST_NL_GEX_RESTRICT_ORDINAL.search(word)
        if found_ordinal:
            if restrict_ordinal is not None:
                raise InvalidQueryError("You cannyot specify an ordinyal more than once in your query, nya.")
            restrict_ordinal = int(found_ordinal.group(1))
            word = word[:-len(found_ordinal.group(1))]

        if word in DRST_NL_RARITIES:
            filters.append(DRST_NL_RARITIES[word.lower()])
            continue

        if word in {"awakened", "idolized", "transformed", "evolved"}:
            wants_awakened = 1
            continue

        for regex, pfilter in DRST_NL_FILTERFLAG_WORDS.items():
            if regex.match(word):
                filters.append(pfilter)
                break
        else:
            filtered_words.append(word)

    # print("filters", filters)
    # print("words", filtered_words)
    # print("restrict_ordinal", restrict_ordinal)

    # if restrict_ordinal and not has_rarity_filter:
    #     # print("no rarity filter in query, but ordinal given - assuming ssr")
    #     filters.append(DRST_NL_RARITIES["ssr"])

    return drst_nl_query_t(filtered_words, filters, restrict_ordinal, wants_awakened)

TEST_QUERIES = [
    "miku2",
    "ssr miku",
    "ssr maekawa miku",
    "sr kako",
    "arisu2",
    "ssr2 kanako",
    "cinfes nana",
    "nana abe cinfest",
    "riina",
    "event natsuki",
    "mayu groove",
    "cinfes limited mayu",
    "cinfest2 mayu1",
]

if __name__ == '__main__':
    for query in TEST_QUERIES:
        print(parse_query(query))
