"""Step 3a — which CNP textbook serves which class and subject.

CNP book code -> list of (curriculum file key, subject code). Books not listed are excluded on
purpose: exercise workbooks (تمارين, English Activity Books), lycées/collèges pilotes editions,
and collèges techniques books. '?' comments mark assumptions still to confirm.
"""
SCI3 = ["3eme-mathematiques", "3eme-sciences-experimentales", "3eme-informatique", "3eme-techniques"]
SCIB = ["bac-mathematiques", "bac-sciences-experimentales", "bac-informatique", "bac-techniques"]
ALL2 = ["2eme-lettres", "2eme-sciences", "2eme-technologie-informatique", "2eme-economie-services", "2eme-sport"]
ALL3 = SCI3 + ["3eme-lettres", "3eme-economie-gestion", "3eme-sport"]
ALLB = SCIB + ["bac-lettres", "bac-economie-gestion", "bac-sport"]
OPT3 = SCI3 + ["3eme-lettres", "3eme-economie-gestion"]
OPTB = SCIB + ["bac-lettres", "bac-economie-gestion"]

def m(classes, *subjects):
    if isinstance(classes, str): classes = [classes]
    return [(c, s) for c in classes for s in subjects]

MAP = {
    # primaire
    "101110": m("1ere-primaire", "ARAB"), "102105": m("1ere-primaire", "MATH"),
    "101215": m("2eme-primaire", "ARAB"), "102210": m("2eme-primaire", "MATH"),
    "101315": m("3eme-primaire", "ARAB"), "102306": m("3eme-primaire", "MATH"), "103304": m("3eme-primaire", "EVEIL"),
    "101410": m("4eme-primaire", "ARAB"), "101411": m("4eme-primaire", "ARAB"), "102407": m("4eme-primaire", "MATH"),
    "103404": m("4eme-primaire", "EVEIL"), "121410": m("4eme-primaire", "FRAN"),
    "101509": m("5eme-primaire", "ARAB"), "101510": m("5eme-primaire", "ARAB"), "102511": m("5eme-primaire", "MATH"),
    "103504": m("5eme-primaire", "EVEIL"), "111512": m("5eme-primaire", "HIST", "GEO", "CIVIQ"), "121511": m("5eme-primaire", "FRAN"),
    "101611": m("6eme-primaire", "ARAB"), "101612": m("6eme-primaire", "ARAB"), "102609": m("6eme-primaire", "MATH"),
    "103604": m("6eme-primaire", "EVEIL"), "111612": m("6eme-primaire", "HIST", "GEO"), "121614": m("6eme-primaire", "FRAN"),
    # collège
    **{c: m(k, s) for k, rows in {
        "7eme-base": [("101708", "ARAB"), ("101710", "ARAB"), ("102707", "MATH"), ("103702", "PHYS"), ("105704", "SVT"),
                      ("111706", "ISLAM"), ("121707", "FRAN"), ("128703", "TECHNO"), ("141705", "ANGL")],
        "8eme-base": [("101806", "ARAB"), ("101808", "ARAB"), ("102805", "MATH"), ("103802", "PHYS"), ("105804", "SVT"),
                      ("111807", "ISLAM"), ("121804", "FRAN"), ("128803", "TECHNO"), ("141806", "ANGL")],
        "9eme-base": [("101908", "ARAB"), ("101909", "ARAB"), ("102905", "MATH"), ("103902", "PHYS"), ("105905", "SVT"),
                      ("111909", "ISLAM"), ("121905", "FRAN"), ("128903", "TECHNO"), ("141906", "ANGL")],
    }.items() for c, s in rows},
    "133701": m(["7eme-base", "8eme-base", "9eme-base"], "INFO"),  # one book for the 3 years, split by_class
    "111707": m("7eme-base", "HIST", "GEO", "CIVIQ"), "111809": m("8eme-base", "HIST", "GEO", "CIVIQ"),
    "111911": m("9eme-base", "HIST", "GEO", "CIVIQ"),
    # 1ère secondaire (tronc commun + sport)
    "201103": m(["1ere-secondaire", "1ere-sport"], "ARAB"), "201104": m(["1ere-secondaire", "1ere-sport"], "ARAB"),
    "206103": m(["1ere-secondaire", "1ere-sport"], "GEO"), "207103": m(["1ere-secondaire", "1ere-sport"], "HIST"),
    "211105": m(["1ere-secondaire", "1ere-sport"], "ISLAM"), "211107": m(["1ere-secondaire", "1ere-sport"], "CIVIQ"),
    "221104": m(["1ere-secondaire", "1ere-sport"], "FRAN"), "222104": m("1ere-secondaire", "MATH"),
    "222105": m("1ere-sport", "MATH"),  # cover: "Section sport" (222104 is the tronc commun book)
    "223103": m(["1ere-secondaire", "1ere-sport"], "PHYS"), "224101": m(["1ere-secondaire", "1ere-sport"], "PHYS"),
    "225104": m("1ere-secondaire", "SVT"), "225105": m("1ere-sport", "BIO"), "228103": m("1ere-secondaire", "TECHNO"),
    "241104": m(["1ere-secondaire", "1ere-sport"], "ANGL"),
    # 2ème
    "201202": m([c for c in ALL2 if c != "2eme-sport"], "ARAB"), "201203": m([c for c in ALL2 if c != "2eme-sport"], "ARAB"),
    "206203": m(["2eme-lettres", "2eme-economie-services"], "GEO"), "206271": m(["2eme-sciences", "2eme-technologie-informatique"], "GEO"),
    "207202": m(["2eme-lettres", "2eme-economie-services"], "HIST"), "207271": m(["2eme-sciences", "2eme-technologie-informatique"], "HIST"),
    "211203": m(ALL2, "CIVIQ"), "211204": m(ALL2, "ISLAM"), "221203": m(ALL2, "FRAN"), "241203": m(ALL2, "ANGL"),
    "222221": m("2eme-lettres", "MATH"), "222231": m(["2eme-sciences", "2eme-technologie-informatique"], "MATH"),
    "222232": m(["2eme-sciences", "2eme-technologie-informatique"], "MATH"), "222261": m("2eme-economie-services", "MATH"),
    "222281": m("2eme-sport", "MATH"),
    "201281": m("2eme-sport", "ARAB"),  # catalogue title says maths, but the book is "كتاب العربيّة للسنة الثانية رياضة"
    "223231": m("2eme-sciences", "PHYS"), "224231": m("2eme-sciences", "PHYS"),
    "223272": m("2eme-technologie-informatique", "PHYS"), "224271": m("2eme-technologie-informatique", "PHYS"),
    "225202": m("2eme-lettres", "SVT"), "225232": m("2eme-sciences", "SVT"), "225281": m("2eme-sport", "BIO"),
    "228233": m(["2eme-sciences", "2eme-technologie-informatique"], "TECHNO"), "229262": m("2eme-economie-services", "GEST"),
    # 3ème
    "201302": m(SCI3 + ["3eme-economie-gestion"], "ARAB"), "201321": m("3eme-lettres", "ARAB"), "201381": m("3eme-sport", "ARAB"),
    "206321": m(["3eme-lettres", "3eme-economie-gestion"], "GEO"), "206331": m(SCI3, "GEO"),
    "207321": m(["3eme-lettres", "3eme-economie-gestion"], "HIST"), "207331": m(SCI3, "HIST"),
    "210301": m(SCI3 + ["3eme-economie-gestion", "3eme-sport"], "PHILO"), "210322": m("3eme-lettres", "PHILO"),
    "211306": m(SCI3, "ISLAM"), "211321": m("3eme-lettres", "ISLAM"), "211322": m("3eme-lettres", "CIVIQ"),
    "221302": m(SCI3 + ["3eme-economie-gestion", "3eme-sport"], "FRAN"), "221321": m("3eme-lettres", "FRAN"),
    "222322": m("3eme-lettres", "MATH"), "222333": m("3eme-sciences-experimentales", "MATH"), "222334": m("3eme-sciences-experimentales", "MATH"),
    "222343": m("3eme-mathematiques", "MATH"), "222344": m("3eme-mathematiques", "MATH"), "222351": m("3eme-techniques", "MATH"),
    "222362": m("3eme-economie-gestion", "MATH"), "222371": m("3eme-informatique", "MATH"), "222381": m("3eme-sport", "MATH"),
    "223332": m("3eme-mathematiques", "PHYS"), "224332": m("3eme-mathematiques", "PHYS"),
    "223333": m("3eme-sciences-experimentales", "PHYS"), "224333": m("3eme-sciences-experimentales", "PHYS"),
    "223351": m("3eme-techniques", "PHYS"), "224351": m("3eme-techniques", "PHYS"),
    "223371": m("3eme-informatique", "PHYS"), "224371": m("3eme-informatique", "PHYS"),
    "225321": m("3eme-lettres", "SVT"), "225333": m("3eme-sciences-experimentales", "SVT"), "225342": m("3eme-mathematiques", "SVT"),
    "225381": m("3eme-sport", "BIO"), "228362": m("3eme-techniques", "TECHNO"), "228363": m("3eme-techniques", "TECHNO"),
    "229364": m("3eme-economie-gestion", "GEST"), "241303": m(ALL3, "ANGL"),
    "251301": m(OPT3, "RUSSE"), "261304": m(OPT3, "ALLEM"), "271301": m(OPT3, "CHIN"), "281304": m(OPT3, "ITAL"), "291302": m(OPT3, "ESPA"),
    # Bac
    "201403": m(SCIB + ["bac-economie-gestion"], "ARAB"), "201421": m("bac-lettres", "ARAB"), "201422": m("bac-lettres", "ARAB"),
    "201481": m("bac-sport", "ARAB"),
    "206422": m(["bac-lettres", "bac-economie-gestion"], "HISTGEO"), "207422": m(["bac-lettres", "bac-economie-gestion"], "HISTGEO"),
    "210402": m(SCIB + ["bac-economie-gestion", "bac-sport"], "PHILO"), "210422": m("bac-lettres", "PHILO"), "210423": m("bac-lettres", "PHILO"),
    "211421": m("bac-lettres", "ISLAM"),
    "221402": m(SCIB + ["bac-economie-gestion", "bac-sport"], "FRAN"), "221421": m("bac-lettres", "FRAN"),
    "222422": m("bac-lettres", "MATH"), "222433": m("bac-sciences-experimentales", "MATH"), "222434": m("bac-sciences-experimentales", "MATH"),
    "222445": m("bac-mathematiques", "MATH"), "222446": m("bac-mathematiques", "MATH"), "222451": m("bac-techniques", "MATH"),
    "222463": m("bac-economie-gestion", "MATH"), "222472": m("bac-informatique", "MATH"), "222481": m("bac-sport", "MATH"),
    "223432": m("bac-mathematiques", "PHYS"), "224432": m("bac-mathematiques", "PHYS"),
    "223433": m("bac-sciences-experimentales", "PHYS"), "224433": m("bac-sciences-experimentales", "PHYS"),
    "223451": m("bac-techniques", "PHYS"), "224451": m("bac-techniques", "PHYS"),  # ? title says "شعبة الرياضيات", code says Techniques
    "223471": m("bac-informatique", "PHYS"), "224471": m("bac-informatique", "PHYS"),
    "225421": m("bac-lettres", "SVT"), "225432": m("bac-sciences-experimentales", "SVT"), "225441": m("bac-mathematiques", "SVT"),
    "225481": m("bac-sport", "BIO"), "228461": m("bac-techniques", "TECHNO"), "228462": m("bac-techniques", "TECHNO"),
    "229464": m("bac-economie-gestion", "GEST"), "241403": m(ALLB, "ANGL"),
    "261401": m(OPTB, "ALLEM"), "271401": m(OPTB, "CHIN"), "281403": m(OPTB, "ITAL"), "291401": m(OPTB, "ESPA"),
}
# English Activity Books (workbooks for the Student's Books) are excluded: 141706, 141807, 141907
ASSUMED = {"222105", "201281", "224451", "201302", "210301", "221302", "201403", "210402", "221402"}


BATCHES = {
    "bac": lambda cls: cls.startswith("bac-"),
    "3eme": lambda cls: cls.startswith("3eme-") and not cls.endswith("primaire"),
    "lycee12": lambda cls: cls.startswith(("1ere-secondaire", "1ere-sport", "2eme-")) and not cls.endswith("primaire"),
    "college": lambda cls: cls.endswith("-base"),
    "primaire": lambda cls: cls.endswith("-primaire"),
    "all": lambda cls: True,
}


def batch(name: str) -> list[str]:
    """Book codes serving the classes of a batch (as processed: bac, 3eme, lycee12, college, primaire)."""
    keep = BATCHES[name]
    return [code for code, pairs in MAP.items() if any(keep(cls) for cls, _ in pairs)]
