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


def test_all_categories_use_credit_schema():
    assert all(c.schema == "credit" for c in CATEGORIES)
