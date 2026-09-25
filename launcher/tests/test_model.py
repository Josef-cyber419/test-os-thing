from hearth import config as cfg
from hearth.model import Home, Nav


def make(*row_sizes):
    return cfg.parse({"rows": [
        {"title": f"r{r}", "apps": [{"id": f"{r}.{c}", "name": "x", "command": "x"} for c in range(n)]}
        for r, n in enumerate(row_sizes)
    ]})


def test_navigation_clamps_at_edges():
    home = Home(make(3, 2))
    home.move(Nav.LEFT)
    home.move(Nav.UP)
    assert home.selected.id == "0.0"
    for _ in range(5):
        home.move(Nav.RIGHT)
    assert home.selected.id == "0.2"


def test_rows_remember_their_column():
    home = Home(make(3, 2))
    home.move(Nav.RIGHT)
    home.move(Nav.RIGHT)
    home.move(Nav.DOWN)
    assert home.selected.id == "1.0"
    home.move(Nav.UP)
    assert home.selected.id == "0.2"


def test_select_id():
    home = Home(make(3, 2))
    assert home.select_id("1.1")
    assert home.selected.id == "1.1"
    assert not home.select_id("missing")


def test_empty_config_is_safe():
    home = Home(cfg.Config(rows=()))
    home.move(Nav.DOWN)
    assert home.selected is None
