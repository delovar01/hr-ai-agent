"""
Content deduplication via SimHash.

Two-level deduplication:
    URL-level       — handled by AgentState.is_url_processed() / mark_url_processed()
    Content-level   — this module, to catch the same story republished across sources

SimHash produces a 64-bit fingerprint such that textually similar documents
have a small Hamming distance between their fingerprints. We keep a rolling
window of fingerprints in agent state and compare each incoming item against it.

Pure Python, no external dependencies.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple


# Default threshold: Hamming distance in [0..64]. Smaller = stricter.
# Empirical guidance:
#   0       exact duplicate
#   1..3    near-duplicate (minor rewording / typos)
#   4..6    similar story, paraphrased
#   7..10   loosely related
#   11+     different
DEFAULT_THRESHOLD = 4

# SimHash fingerprint width in bits.
HASH_BITS = 64

# Minimum input length (in tokens) to produce a meaningful fingerprint.
# Below this we fall back to exact-hash matching only.
MIN_TOKENS_FOR_SIMHASH = 8

# Default n-gram size for shingling. Unigrams give robust overlap for
# document-level similarity and are forgiving to paraphrasing; n>1 is more
# precise but misses near-duplicates that rephrase freely.
SHINGLE_SIZE = 1

# Matches sequences of word characters in Unicode (ru/en/digits).
_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


@dataclass(frozen=True)
class DuplicateMatch:
    """Result of a duplicate lookup."""

    is_duplicate: bool
    distance: int
    matched_fingerprint: Optional[int] = None
    matched_item_id: Optional[str] = None


def _normalize(text: str) -> str:
    """Lowercase and strip surrounding whitespace. HTML tags are stripped naively."""
    if not text:
        return ""
    # Strip HTML-ish tags (RSS summaries often contain them).
    cleaned = re.sub(r"<[^>]+>", " ", text)
    return cleaned.lower().strip()


def _tokenize(text: str) -> List[str]:
    """Split normalized text into word tokens."""
    return _TOKEN_RE.findall(_normalize(text))


def _shingles(tokens: List[str], size: int = SHINGLE_SIZE) -> List[str]:
    """Produce word n-grams. Falls back to individual tokens for short inputs."""
    if len(tokens) < size:
        return tokens
    return [" ".join(tokens[i : i + size]) for i in range(len(tokens) - size + 1)]


def _hash64(token: str) -> int:
    """Stable 64-bit hash for a token. MD5 is used for determinism across Python runs."""
    digest = hashlib.md5(token.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], byteorder="big", signed=False)


def compute_simhash(text: str, bits: int = HASH_BITS) -> Optional[int]:
    """Compute SimHash fingerprint for ``text``.

    Returns None if the text is too short to produce a reliable fingerprint.
    """
    tokens = _tokenize(text)
    if len(tokens) < MIN_TOKENS_FOR_SIMHASH:
        return None

    features = _shingles(tokens)
    if not features:
        return None

    # Classic SimHash: for each bit position accumulate +1 or -1 per feature.
    counters = [0] * bits
    for feature in features:
        h = _hash64(feature)
        for i in range(bits):
            if h & (1 << i):
                counters[i] += 1
            else:
                counters[i] -= 1

    fingerprint = 0
    for i, counter in enumerate(counters):
        if counter > 0:
            fingerprint |= 1 << i
    return fingerprint


def hamming_distance(a: int, b: int) -> int:
    """Number of differing bits between two integers."""
    return (a ^ b).bit_count()


def exact_hash(text: str) -> str:
    """Stable SHA-1 hash of normalized text for exact-duplicate detection."""
    return hashlib.sha1(_normalize(text).encode("utf-8")).hexdigest()


class ContentDeduplicator:
    """Detects near-duplicate content via SimHash + exact-hash fallback.

    Maintains a rolling in-memory window of recent fingerprints. Callers are
    responsible for persisting the window through :meth:`export_state` and
    :meth:`load_state` (agent state integration lives in ``AgentState``).
    """

    def __init__(self, threshold: int = DEFAULT_THRESHOLD, max_window: int = 1000):
        if not 0 <= threshold <= HASH_BITS:
            raise ValueError(f"threshold must be in [0, {HASH_BITS}]")
        self.threshold = threshold
        self.max_window = max_window
        # Each entry: {"fingerprint": int | None, "exact": str, "item_id": str}
        self._entries: List[dict] = []

    def check(self, text: str, item_id: str = "") -> DuplicateMatch:
        """Check whether ``text`` duplicates any known entry.

        Does NOT register the text — call :meth:`add` explicitly after deciding
        to accept a non-duplicate item.
        """
        if not text:
            return DuplicateMatch(is_duplicate=False, distance=HASH_BITS)

        exact = exact_hash(text)
        fp = compute_simhash(text)

        best_distance = HASH_BITS
        best_entry: Optional[dict] = None

        for entry in self._entries:
            # Exact match short-circuits.
            if entry["exact"] == exact:
                return DuplicateMatch(
                    is_duplicate=True,
                    distance=0,
                    matched_fingerprint=entry.get("fingerprint"),
                    matched_item_id=entry.get("item_id"),
                )

            if fp is None or entry.get("fingerprint") is None:
                continue

            distance = hamming_distance(fp, entry["fingerprint"])
            if distance < best_distance:
                best_distance = distance
                best_entry = entry

        if best_entry is not None and best_distance <= self.threshold:
            return DuplicateMatch(
                is_duplicate=True,
                distance=best_distance,
                matched_fingerprint=best_entry.get("fingerprint"),
                matched_item_id=best_entry.get("item_id"),
            )

        return DuplicateMatch(is_duplicate=False, distance=best_distance)

    def add(self, text: str, item_id: str = "") -> Optional[int]:
        """Register text in the window. Returns its SimHash (may be None for short text)."""
        if not text:
            return None
        fp = compute_simhash(text)
        self._entries.append({
            "fingerprint": fp,
            "exact": exact_hash(text),
            "item_id": item_id,
        })
        if len(self._entries) > self.max_window:
            # Drop oldest entries.
            self._entries = self._entries[-self.max_window :]
        return fp

    def check_and_add(self, text: str, item_id: str = "") -> DuplicateMatch:
        """Convenience: check, then add iff not a duplicate."""
        match = self.check(text, item_id=item_id)
        if not match.is_duplicate:
            self.add(text, item_id=item_id)
        return match

    def __len__(self) -> int:
        return len(self._entries)

    # ---- Persistence helpers (used by AgentState) ----

    def export_state(self) -> List[dict]:
        """Serializable snapshot of the fingerprint window."""
        return list(self._entries)

    def load_state(self, entries: Iterable[dict]) -> None:
        """Restore window from a previously exported snapshot."""
        self._entries = [
            {
                "fingerprint": e.get("fingerprint"),
                "exact": e.get("exact", ""),
                "item_id": e.get("item_id", ""),
            }
            for e in entries
        ]
        if len(self._entries) > self.max_window:
            self._entries = self._entries[-self.max_window :]


def find_cross_source_duplicates(items: List[dict], threshold: int = DEFAULT_THRESHOLD) -> List[Tuple[int, int, int]]:
    """Find duplicate pairs within a list of items.

    Each item must have at least ``title`` and/or ``content``. Returns list of
    tuples ``(index_a, index_b, hamming_distance)`` for pairs that are
    duplicates.  Useful for cross-source duplicate analysis in reports.
    """
    fingerprints: List[Optional[int]] = []
    for item in items:
        text = " ".join(filter(None, [item.get("title"), item.get("content")]))
        fingerprints.append(compute_simhash(text))

    pairs: List[Tuple[int, int, int]] = []
    for i in range(len(items)):
        fi = fingerprints[i]
        if fi is None:
            continue
        for j in range(i + 1, len(items)):
            fj = fingerprints[j]
            if fj is None:
                continue
            d = hamming_distance(fi, fj)
            if d <= threshold:
                pairs.append((i, j, d))
    return pairs
