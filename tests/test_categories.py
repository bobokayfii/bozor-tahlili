from categories import CATEGORIES, category_keys


def test_categories_contains_eleven_entries():
    assert len(CATEGORIES) == 11


def test_all_category_keys_are_unique():
    keys = category_keys()
    assert len(keys) == len(set(keys))


def test_existing_categories_keep_original_keys():
    keys = category_keys()
    for legacy_key in ["avtokredit", "mikroqarz", "kredit_karta", "istemol_krediti"]:
        assert legacy_key in keys


def test_avtokredit_and_ipoteka_categories_use_down_payment_schema():
    down_payment_keys = {
        "avtokredit",
        "avtokredit_ikkilamchi",
        "avtokredit_brend_birlamchi",
        "avtokredit_brend_ikkilamchi",
        "avtokredit_elektro",
        "ipoteka_tijorat",
        "ipoteka_davlat",
    }
    by_key = {c.key: c for c in CATEGORIES}
    for key in down_payment_keys:
        assert by_key[key].schema == "credit_down_payment", key


def test_mikroqarz_karta_and_istemol_categories_use_special_terms_schema():
    special_terms_keys = {
        "mikroqarz",
        "mikroqarz_onlayn",
        "kredit_karta",
        "istemol_krediti",
    }
    by_key = {c.key: c for c in CATEGORIES}
    for key in special_terms_keys:
        assert by_key[key].schema == "credit_special_terms", key


def test_every_category_has_a_known_schema():
    known_schemas = {"credit_down_payment", "credit_special_terms"}
    assert all(c.schema in known_schemas for c in CATEGORIES)
