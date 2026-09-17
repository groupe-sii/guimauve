from guimauve.models.replay import Replay

# --- name: required + not blank ---


def test_name_blank_is_rejected(real_file):
    errors = Replay(name="   ", path=real_file).resolve()
    assert any(e["type"] == "empty" and e["loc"] == ("name",) for e in errors)


# --- path: required + must exist ---


def test_path_required_missing():
    errors = Replay(name="x").resolve()
    assert any(e["type"] == "missing" and e["loc"] == ("path",) for e in errors)


def test_path_not_found_reports_error(tmp_path):
    missing = tmp_path / "nope.replay"
    errors = Replay(name="x", path=missing).resolve()
    assert errors[0]["type"] == "file_not_found"
    assert errors[0]["loc"] == ("path",)
    assert errors[0]["ctx"]["path"] == str(missing)


def test_valid_replay(real_file):
    assert Replay(name="run1", path=real_file).resolve() == []


# --- private attrs / properties ---


def test_alias_and_is_new_defaults(real_file):
    r = Replay(name="x", path=real_file)
    assert r.alias is None
    assert r.is_new is False
