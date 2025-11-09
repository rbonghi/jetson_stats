import re

_CLK_TREE = "/sys/kernel/debug/bpmp/debug/clk/clk_tree"
_LINE_RX = re.compile(r"^\s*([A-Za-z0-9_\.]+)\s+(\d+)\s+(\d+)\b", re.MULTILINE)

class BpmpSnapshot:
    """Parses clk_tree once and serves lookups without re-reading the file each time."""

    def __init__(self, text: str | None = None):
        self._text = text if text is not None else self._read_tree_text()
        self._idx = self._index(self._text)

    @staticmethod
    def _read_tree_text() -> str:
        try:
            with open(_CLK_TREE, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception:
            return ""

    @staticmethod
    def _index(text: str) -> dict[str, dict[str, int]]:
        idx: dict[str, dict[str, int]] = {}
        if not text:
            return idx
        for m in _LINE_RX.finditer(text):
            name, on, rate = m[1], int(m[2]), int(m[3])
            if "." in name:  # skip *.buf, etc.
                continue
            idx[name] = {"on": on, "rate": rate}
        return idx

    @property
    def index(self) -> dict[str, dict[str, int]]:
        return self._idx

    def rate_hz(self, clk_name: str) -> int | None:
        """Return Hz for exact clk name, nafll_<name>, or case-insensitive/substring fallbacks."""
        if clk_name in self._idx:
            return self._idx[clk_name]["rate"]
        nafll = f"nafll_{clk_name}"
        if nafll in self._idx:
            return self._idx[nafll]["rate"]
        low = clk_name.lower()
        for k, v in self._idx.items():
            if k.lower() == low:
                return v["rate"]
        return next(
            (v["rate"] for k, v in self._idx.items() if low in k.lower()), None
        )


def pick_clock(idx: dict[str, dict[str, int]], token: str, preferences: list[str]) -> str | None:
    """Case-insensitive match: try preferences first, then substring fallback on token."""
    for pref in preferences:
        for key in idx.keys():
            if pref.lower() == key.lower():
                return key
    lt = token.lower()
    for key in idx.keys():
        if lt in key.lower():
            return key
    return None
