from bot.config import Settings
from bot.handlers.booking import normalize_phone
from bot.texts import TEXTS


def test_normalize_phone():
    assert normalize_phone("+998 90 123-45-67") == "+998901234567"
    assert normalize_phone("998901234567") == "+998901234567"
    assert normalize_phone("salom") is None
    assert normalize_phone("123") is None


def test_all_languages_have_same_keys():
    assert TEXTS["ru"].keys() == TEXTS["uz"].keys()


def test_settings_parse_admin_ids(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "1:x")
    monkeypatch.setenv("ADMIN_IDS", "111, 222")
    assert Settings(_env_file=None).admin_ids == [111, 222]
