"""Two defects found by running /dream on a real Windows chat, not by reading the code."""
def _seed(session, turns, monkeypatch=None):
    from core import engine, recall, sources
    engine.clear()
    # The day's own turns, not this checkout's commit subjects: the test is about pairing.
    if monkeypatch is not None:
        monkeypatch.setattr(sources, "projects", lambda: [])
    for t in turns:
        recall.remember(t, session=session)


def test_a_two_pair_dose_compares_different_things(monkeypatch):
    """The dose took choices[:2], which is (0,1) and (0,2) - every pair anchored on subject 0.

    With four things from the day there are two independent comparisons available; the dose
    reused one anchor instead of covering the material.
    """
    turns = ["the parser keeps failing on nested quotes",
             "the coffee shop closed after twenty years",
             "I want the walk to feel like wandering",
             "the budget review moved to thursday"]
    from core import sources
    _seed("cover", turns, monkeypatch)
    items = sources.day_connections(2, keyed=True, session="cover")
    sides = []
    for _, line, _ in items:
        body = line.split("·", 1)[1] if "·" in line else line
        left, _, right = body.partition("↔")
        sides.append((left.strip(), right.strip()))
    assert len(sides) == 2, items
    used = {s for pair in sides for s in pair}
    assert len(used) == 4, f"a 2-pair dose over 4 things must cover all four, got {sides}"


def test_three_things_still_get_all_three_compared(monkeypatch):
    turns = ["the parser keeps failing on nested quotes",
             "the coffee shop closed after twenty years",
             "I want the walk to feel like wandering"]
    from core import sources
    _seed("cover3", turns, monkeypatch)
    items = sources.day_connections(2, keyed=True, session="cover3")
    used = set()
    for _, line, _ in items:
        body = line.split("·", 1)[1] if "·" in line else line
        left, _, right = body.partition("↔")
        used.add(left.strip())
        used.add(right.strip())
    assert len(used) == 3, f"two pairs over three things must reach all three, got {used}"


def test_a_pasted_command_is_not_the_persons_concepts():
    """`tar -xzf antemuse-0.12.7.tar.gz` gave concepts antemuse-0, python, scripts, install.

    Single tokens, so the earlier claim held in letter - but a filename fragment is not
    something a reader would recognise as the person's material.
    """
    from core import sources
    cmd = "tar -xzf antemuse-0.12.7.tar.gz\ncd antemuse-0.12.7\npython scripts\\install.py"
    terms = sources._terms_of(cmd)
    junk = {"antemuse-0", "python", "scripts", "install", "tar", "xzf", "antemuse-0-12-7"}
    assert not (set(terms) & junk), f"a command paste contributed {sorted(set(terms) & junk)}"


def test_prose_still_yields_its_real_terms():
    from core import sources
    terms = sources._terms_of("the parser keeps failing on nested quotes")
    assert {"parser", "nested", "quotes"} <= set(terms), terms


def test_daydream_also_compares_different_things(monkeypatch):
    """Same defect, same dose: /daydream reused its left side too."""
    from core import sources
    turns = ["the parser keeps failing on nested quotes",
             "the coffee shop closed after twenty years",
             "I want the walk to feel like wandering",
             "the budget review moved to thursday"]
    _seed("dd-cover", turns, monkeypatch)
    items = sources.memory_pairs(2, keyed=True, session="dd-cover")
    used = set()
    for _, line, _ in items:
        one = line.split("one:", 1)[1].split("·", 1)[0].strip()
        two = line.split("two:", 1)[1].split("·", 1)[0].strip()
        used.add(one)
        used.add(two)
    assert len(used) == 4, f"a 2-pair daydream over 4 turns must cover all four, got {used}"
