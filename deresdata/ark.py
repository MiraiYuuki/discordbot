import sqlite3
import json
import requests
import unicodedata
from itertools import starmap
from collections import namedtuple, defaultdict
from . import httputils
try:
    from . import query
    from .query import InvalidQueryError
except SystemError:
    import query
    from query import InvalidQueryError

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta_v2 (
    truth_version  TEXT,
    keywords_time  INT
);

CREATE TABLE IF NOT EXISTS names_v1 (
    chara_id    INT PRIMARY KEY,
    chara_name  TEXT
);

CREATE TABLE IF NOT EXISTS cards_v1 (
    root_id     INT PRIMARY KEY,
    awakened_id INT,
    rarity      INT,
    attribute   INT,
    chara_id    INT,
    sort_key    INT,
    av_flag     INT
);

CREATE TABLE IF NOT EXISTS keywords_v1 (
    refs_id     INT,
    word        TEXT,
    position    INT
);
"""
CLEAR_DB = """
DELETE FROM meta_v2;
DELETE FROM names_v1;
DELETE FROM cards_v1;
"""
filterable_card_data_t = namedtuple("filterable_card_data_t",
    ("root_id", "awakened_id", "rarity", "attribute", "chara_id", "sort_key", "av_flag", "kw_relevance"))


def type_(d):
    return (d & 0xF0000000) >> 28

def referred_id(d):
    return d & 0x0FFFFFFF

def event_type(e):
    return e & 0x7

def gacha_is_limited(e):
    return e & 0x1

async def build_ark():
    conn = sqlite3.connect("drst_search_index.db")
    prep_db(conn)

    conn.executescript(CLEAR_DB)
    conn.commit()

    print("Building name list...")
    ns = await httputils.cfetch("https://starlight.kirara.ca/api/v2/char_t/all?keys=chara_id,conventional")
    conn.executemany("INSERT INTO names_v1 VALUES (:chara_id, lower(:conventional))",
        ns["result"])

    cs = await httputils.cfetch("https://starlight.kirara.ca/api/v2/card_t/all?keys=id,evolution_id,rarity,attribute,chara_id")
    conn.executemany("INSERT INTO cards_v1 VALUES (:id, :evolution_id, :rarity, :attribute, :chara_id, 0, 0)",
        cs["result"])

    flg_bag = defaultdict(lambda: 0)
    rls_bag = {}
    hl = await httputils.cfetch("https://starlight.kirara.ca/api/private/history")
    for he in hl["result"]:
        if not he["added_cards"]:
            continue

        base_flg = 0
        if type_(he["descriptor"]) == 2:
            base_flg |= query.NL_FILTER_EVENT
            base_flg |= (0b00010000 << event_type(he["extra_type_info"]))
        if type_(he["descriptor"]) == 3:
            base_flg |= query.NL_FILTER_GACHA

        cl = json.loads(he["added_cards"])
        for key in cl:
            for cid in cl[key]:
                flg_bag[cid] = base_flg
                rls_bag[cid] = he["start_time"]

        for cid in cl.get("limited", []):
            flg_bag[cid] |= query.NL_FILTER_LIMITED

    conn.executemany("UPDATE cards_v1 SET sort_key = ?, av_flag = ? WHERE root_id = ?",
        map(lambda x: (rls_bag[x], flg_bag[x], x), [x["id"] for x in cs["result"]]))

    meta = await httputils.cfetch("https://starlight.kirara.ca/api/v1/info")
    conn.execute("INSERT INTO meta_v2 VALUES (?, ?)", (meta["truth_version"], 0))

    conn.commit()
    conn.close()

def title_split(t):
    words = unicodedata.normalize("NFD", t)
    buf = []

    for ch in words:
        ca = unicodedata.category(ch)
        if ca[0] in {"S", "Z", "P"}:
            if buf:
                yield "".join(buf).lower()
                buf = []
            continue

        if ca[0] == "M":
            continue

        buf.append(ch)
    else:
        if buf:
            yield "".join(buf).lower()

async def build_keywords():
    conn = sqlite3.connect("drst_search_index.db")
    prep_db(conn)
    conn.execute("DELETE FROM keywords_v1")

    cs = await httputils.cfetch("https://starlight.kirara.ca/api/v2/card_t/all?keys=id,title")
    id_map = {k["id"]: k["title"]
              for k in cs["result"] if k["title"]}
    tl_list = list(set(id_map.values()))
    tl_dictionary = await httputils.ctlstrings(tl_list)

    inserts = 0
    curs = conn.cursor()
    for id in id_map:
        tl_result = tl_dictionary.get(id_map[id])
        if tl_result is None:
            continue

        for pos, word in enumerate(title_split(tl_result)):
            if len(word) >= 3:
                curs.execute("INSERT INTO keywords_v1 VALUES (?, ?, ?)", (id, word, pos))
                inserts += 1

    conn.commit()
    conn.close()

    return (inserts, len(id_map))

def needs_update(current_truth_version):
    conn = sqlite3.connect("drst_search_index.db")
    prep_db(conn)

    result = conn.execute("SELECT truth_version FROM meta_v2").fetchone()
    conn.close()
    if result is None or result[0] != current_truth_version:
        return 1

    return 0

def prep_db(c):
    c.executescript(SCHEMA)
    c.commit()

def chara_id_from_name(conn, name):
    if len(name) == 1:
        x = name + ["%"]
        frontwards = " ".join(x)
        backwards = " ".join(reversed(x))
    else:
        frontwards = " ".join(name)
        backwards = " ".join(reversed(name))

    if len(name) == 1:
        q = "SELECT chara_id FROM names_v1 WHERE chara_name = ? OR chara_name LIKE ? OR chara_name LIKE ?"
        result = conn.execute(q, (name[0], frontwards, backwards))
    else:
        q = "SELECT chara_id FROM names_v1 WHERE chara_name LIKE ? OR chara_name LIKE ?"
        result = conn.execute(q, (frontwards, backwards))

    result = result.fetchone()

    return result[0] if result else None

def exec_query(query_):
    if isinstance(query_, query.drst_named_id_query_t):
        return exec_query_direct(query_)
    else:
        return exec_query_search(query_)

def exec_query_direct(query):
    conn = sqlite3.connect("drst_search_index.db")
    cards = conn.execute("SELECT *, 0 FROM cards_v1 WHERE root_id = ? OR awakened_id = ?", (query.id, query.id))

    row = cards.fetchone()
    conn.close()

    if row is None:
        raise InvalidQueryError("That card doesn't exist, nya.")
    else:
        return [filterable_card_data_t(*row)]

def exec_query_search(query):
    conn = sqlite3.connect("drst_search_index.db")

    restrict_char_id = chara_id_from_name(conn, query.keywords[-2:])
    consumed = 2

    if restrict_char_id is None:
        restrict_char_id = chara_id_from_name(conn, query.keywords[-1:])
        consumed = 1

    if restrict_char_id is not None:
        kwds = query.keywords[:-consumed]
    else:
        kwds = query.keywords

    if kwds:
        in_placeholder = ",".join("?" * len(kwds))
        QUERY = """
        SELECT cards_v1.*, COUNT(refs_id) AS kwsort FROM keywords_v1
        LEFT JOIN cards_v1 ON (refs_id == root_id)
        WHERE WORD IN ({0}) {1}
        GROUP BY refs_id
        ORDER BY kwsort DESC, rarity DESC, sort_key DESC
        """.format(in_placeholder, "AND chara_id = ?" if restrict_char_id else "")

        tt = tuple(kwds)
        if restrict_char_id:
            tt += (restrict_char_id,)
        cards = conn.execute(QUERY, tt)
    else:
        if not restrict_char_id:
            raise InvalidQueryError("There aren't any idols with that nyame.")

        cards = conn.execute("SELECT *, 0 FROM cards_v1 WHERE chara_id = ? ORDER BY rarity DESC, sort_key DESC", (restrict_char_id,))

    cards = list(starmap(filterable_card_data_t, cards.fetchall()))

    conn.close()

    cards = list(filter(lambda x: all(f(x) for f in query.filters), cards))

    if query.ordinal:
        try:
            return [sorted(cards, key=lambda x: (20 - x.rarity, x.sort_key), reverse=1)[-query.ordinal]]
        except IndexError:
            raise InvalidQueryError("There aren't that many cards of her, nya.")

    return cards

if __name__ == '__main__':
    #build_ark()
    from query import parse_query
    print(exec_query(parse_query("token kaede")))
    print(exec_query(parse_query("groove kaede")))
