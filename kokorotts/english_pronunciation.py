"""Contextual English pronunciation corrections applied after Misaki G2P."""

from misaki.token import MToken


_ARITHMETIC_PRONUNCIATIONS = {
    "us": {
        "noun": "əɹˈɪθmətˌɪk",
        "adjective": "ˌɛɹɪθmˈɛTɪk",
    },
    "gb": {
        "noun": "əɹˈɪθmətɪk",
        "adjective": "ˌaɹɪθmˈɛtɪk",
    },
}


def correct_english_pronunciations(
    tokens: list[MToken], *, british: bool
) -> None:
    """Correct context-sensitive words that the compact POS tagger can mistag."""

    pronunciations = _ARITHMETIC_PRONUNCIATIONS["gb" if british else "us"]
    for index, token in enumerate(tokens):
        if token.text.casefold() != "arithmetic":
            continue
        following = tokens[index + 1] if index + 1 < len(tokens) else None
        form = (
            "adjective"
            if following is not None and following.tag.startswith("NN")
            else "noun"
        )
        token.phonemes = pronunciations[form]
