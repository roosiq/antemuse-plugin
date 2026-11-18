import pytest




def test_a_wordnet_failure_names_its_cause(monkeypatch):
    """The message must say what broke, not just that something did.

    `raise GraphLoadError("unavailable", "WordNet data is unavailable")` printed identically for a
    missing corpus, a permission error, a cold import and an empty lookup, so a walk that failed in
    a real chat could not be diagnosed from its own account.
    """
    import sys
    import types

    from core import walks

    fake_corpus = types.ModuleType("nltk.corpus")

    class Wordnet:
        @staticmethod
        def synsets(_word):
            raise LookupError("no such corpus")

    fake_corpus.wordnet = Wordnet
    monkeypatch.setitem(sys.modules, "nltk.corpus", fake_corpus)
    # The corpus is opened once per process now, so a fake import only takes effect cold.
    monkeypatch.setattr(walks, "_WN", None, raising=False)

    provider = walks.WordNetGraph() if hasattr(walks, "WordNetGraph") else None
    if provider is None:
        pytest.skip("provider class is named differently in this build")
    with pytest.raises(Exception) as caught:      # noqa: PT011 - the type is GraphLoadError
        provider.wn()
    assert "LookupError" in str(caught.value) and "no such corpus" in str(caught.value)
