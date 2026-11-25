import json
import re
from pathlib import Path

STARTER = Path(__file__).resolve().parent
COMMON_WORDS = set(
    "a an at by do for how i if in is it of on or should the to we what when where who".split()
)


def read_data(filename):
    return json.loads((STARTER / filename).read_text(encoding="utf-8"))


def load_handbook():
    return read_data("handbook.json")


def words(text):
    return set(re.findall(r"[a-z0-9]+", text.lower())) - COMMON_WORDS


def search_passages(question, passages, limit=3):
    """Rank supplied passages by shared words. Ties are sorted by passage ID."""
    query_words = words(question)
    matches = []
    for passage in passages:
        passage_words = words(passage["title"] + " " + passage["text"])
        shared_words = len(query_words & passage_words)
        if shared_words:
            matches.append((shared_words, passage))
    matches.sort(key=lambda match: (-match[0], match[1]["id"]))
    return [passage for _, passage in matches[:limit]]
