RA_TABLE = {
    1: "N",
    2: "R",
    3: "SR",
    4: "UR",
    5: "SSR",
}
AT_TABLE = {
    1: "Smile",
    2: "Pure",
    3: "Cool",
    4: "Assist."
}
CH_TABLE = {
    1: "Honoka",
    2: "Eli",
    3: "Kotori",
    4: "Umi",
    5: "Rin",
    6: "Maki",
    7: "Nozomi",
    8: "Hanayo",
    9: "Nico",

    101: "Chika",
    102: "Riko",
    103: "Kanan",
    104: "Dia",
    105: "You",
    106: "Yoshiko",
    107: "Hanamaru",
    108: "Mari",
    109: "Ruby",
}

def identify_by_resid(res_id):
    if len(res_id) != 8:
        return "malformed ResID"

    ra = int(res_id[0])
    at = int(res_id[1])
    ch = int(res_id[2:5])
    rd = int(res_id[5:])

    return "{1} {0} {2} +{3}".format(
        RA_TABLE.get(ra, "Sp."),
        AT_TABLE.get(at, "?"),
        CH_TABLE.get(ch, "@" + str(ch)),
        rd)