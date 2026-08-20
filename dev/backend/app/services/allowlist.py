"""C8 allowlist -- which of the patient's medications this build can actually
verify from a photograph (NB08 build spec section 4.1/4.2, Muthu's session
decision D-2 of 2026-08-14: the allowlist STANDS at 11 supported / 4 excluded).

WHY THIS LIVES IN THE BACKEND AND NOT IN THE PROMOTED COPY
----------------------------------------------------------
`app/data/allowlist/supported_dins.csv` is an ADDITIVE, provenance-headered
copy of the NB08 prototype file and is never edited. The prototype's own loader
(`NB08_Notebook/src/nb08_lexicon.py`) drags in pandas and the whole reference
pipeline, none of which the API server needs, so only the ~40 lines of
membership semantics are re-stated here. They are re-stated EXACTLY:

  * keys are SB2 token form, ``DIN`` + the UNPADDED integer;
  * a zero-padded key is a hard error, never silently re-padded -- the padding
    trap costs a ballot of zero candidates and a `reject` that is
    indistinguishable from a genuine rejection (nb08_lexicon.canonical_din);
  * "unsupported" means status != supported OR absent from the file entirely.
    Build spec 4.2 forbids either being silently dropped;
  * an EMPTY allowlist is valid and means "nothing is supported yet". There is
    no default membership and no fallback.

Profile DINs arrive here in the app's canonical 8-digit form and MUST be put
through `din_utils.to_sb2_token` first. Never hand-roll that conversion.

ASCII only.
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

_DIN_RE = re.compile(r"^DIN(\d+)$")

#: The promoted copy. Read-only at runtime.
ALLOWLIST_CSV = Path(__file__).resolve().parent.parent / "data" / "allowlist" / "supported_dins.csv"

_COLUMNS = ("din", "product_key", "status", "reason", "evidence_ref")
SUPPORTED = "supported"


def canonical_din(din: str) -> str:
    """The reference's key form: ``DIN`` + the UNPADDED integer.

    Raises on a zero-padded value rather than fixing it: silently re-padding
    would hide a real inconsistency between whatever produced the profile and
    the reference, and the symptom downstream is a wrong-looking `reject` with
    no error anywhere. See nb08_lexicon.canonical_din for the full note.
    """
    s = str(din).strip().upper()
    m = _DIN_RE.match(s)
    if not m:
        raise ValueError(
            f"malformed DIN {din!r}: expected 'DIN' followed by digits. "
            "The reference keys on 'DIN' + the unpadded integer"
        )
    digits = m.group(1)
    if len(digits) > 1 and digits[0] == "0":
        raise ValueError(
            f"zero-padded DIN {din!r}: the reference keys on the UNPADDED integer. "
            "Convert with din_utils.to_sb2_token, never by hand"
        )
    return f"DIN{digits}"


@dataclass(frozen=True)
class AllowRow:
    din: str
    product_key: str
    status: str
    reason: str
    evidence_ref: str


class Allowlist:
    """Membership only. It answers "can this build verify that medication",
    never "which pill is this" -- Verify-Don't-Identify."""

    def __init__(self, rows: Dict[str, AllowRow]):
        self._rows = rows

    # -- construction ---------------------------------------------------------

    @classmethod
    def from_records(cls, records: Iterable[Sequence]) -> "Allowlist":
        out: Dict[str, AllowRow] = {}
        for r in records:
            din = canonical_din(r[0])
            if din in out:
                raise ValueError(
                    f"allowlist contains {din} twice -- membership must be unambiguous"
                )
            out[din] = AllowRow(
                din=din,
                product_key=str(r[1]).strip(),
                status=str(r[2]).strip().lower(),
                reason=str(r[3]),
                evidence_ref=str(r[4]),
            )
        return cls(out)

    @classmethod
    def from_csv(cls, path: Path | str) -> "Allowlist":
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"allowlist not found: {path}")
        with path.open(newline="", encoding="utf-8-sig") as fh:
            # Strip the provenance header. Only LEADING comment lines are
            # dropped: a '#' appearing later would mean the file is not the
            # shape we think it is, and DictReader will say so.
            lines = fh.read().splitlines(keepends=True)
        body = [ln for i, ln in enumerate(lines) if not (ln.lstrip().startswith("#"))]
        rdr = csv.DictReader(body)
        missing = set(_COLUMNS) - set(rdr.fieldnames or [])
        if missing:
            raise RuntimeError(
                f"allowlist {path} is missing columns {sorted(missing)} -- refusing to "
                "derive membership from a file whose shape is not the expected one"
            )
        return cls.from_records([tuple(row[c] for c in _COLUMNS) for row in rdr])

    # -- the questions --------------------------------------------------------

    def is_supported(self, din: str) -> bool:
        r = self._rows.get(canonical_din(din))
        return r is not None and r.status == SUPPORTED

    def product_key(self, din: str) -> Optional[str]:
        r = self._rows.get(canonical_din(din))
        return r.product_key if r else None

    def dins(self) -> List[str]:
        return sorted(d for d, r in self._rows.items() if r.status == SUPPORTED)

    def unsupported(self, profile_dins: Iterable[str]) -> List[str]:
        """Profile members this build does NOT support (build spec 4.2).

        Includes DINs with status != supported AND DINs absent from the file
        entirely -- both are "we cannot verify this".
        """
        return sorted({canonical_din(d) for d in profile_dins if not self.is_supported(d)})

    def supported_subset(self, profile_dins: Iterable[str]) -> List[str]:
        """The tokens that may be sent to the sidecar, order-preserved.

        Muthu's D-2: filtering happens BEFORE the sidecar call. An excluded
        medication must never be scored, because scoring it is the only way it
        could ever come back `verify`.
        """
        seen: set[str] = set()
        out: List[str] = []
        for d in profile_dins:
            token = canonical_din(d)
            if token in seen:
                continue
            seen.add(token)
            if self.is_supported(token):
                out.append(token)
        return out

    def universe(self) -> List[str]:
        return sorted(self._rows)

    def __len__(self) -> int:
        return len(self._rows)


@lru_cache(maxsize=1)
def get_allowlist() -> Allowlist:
    """Process-wide singleton. The file is configuration Muthu owns; it does
    not change while the server is up."""
    return Allowlist.from_csv(ALLOWLIST_CSV)
