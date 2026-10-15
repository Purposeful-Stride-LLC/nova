"""Read-only data layer for the 2.1 GUI (no Qt imports; unit-testable).

Rules (council P0-0): one mode=ro SQLite connection, reused; no workforce upsert, no palace
writes, no row inserts or updates; artifact list from a cached, non-recursive scan refreshed at most every 60 s.
Every write the operator asks for goes to nova.cmdinbox (file IPC) and the daemon performs it.
"""
from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path

ART_TTL_S = 60.0


class RO:
    def __init__(self, home: Path | None = None):
        from nova import db
        self.home = Path(home) if home else db.home()
        self.db_file = self.home / "data" / "NOVA.db"
        self._con: sqlite3.Connection | None = None
        self._art: tuple[float, list[Path]] = (0.0, [])
        self.queries = 0

    def con(self) -> sqlite3.Connection:
        if self._con is None:
            self._con = sqlite3.connect(self.db_file.resolve().as_uri() + "?mode=ro", uri=True, timeout=2,
                                        check_same_thread=False)
            self._con.row_factory = sqlite3.Row
        return self._con

    def close(self) -> None:
        if self._con is not None:
            self._con.close()
            self._con = None

    def q(self, sql: str, args: tuple = ()) -> list[dict]:
        head = sql.lstrip().split(None, 1)[0].upper()
        if head not in ("SELECT", "PRAGMA", "WITH"):
            raise PermissionError("GUI is read-only: " + head)
        self.queries += 1
        try:
            return [dict(r) for r in self.con().execute(sql, args).fetchall()]
        except sqlite3.OperationalError:
            return []

    # ---- panels
    def jobs(self) -> list[dict]:
        from nova import sched
        return sched.job_table(rows_in=self.q("SELECT * FROM jobs ORDER BY id"))

    def counts(self) -> dict:
        one = lambda sql: (self.q(sql) or [{"n": None}])[0]["n"]
        return {"queue_pending": one("SELECT count(*) n FROM queue WHERE status IN ('queued','pending')"),
                "urls_approved": one("SELECT count(*) n FROM queue WHERE status='approved'"),
                "reports_open": one("SELECT count(*) n FROM reports WHERE status='open'"),
                "packets_fail": one("SELECT count(*) n FROM packets WHERE status='fail'"),
                "bites_expired": one("SELECT count(*) n FROM bites WHERE status='expired'"),
                "bites_played": one("SELECT count(*) n FROM bites WHERE status='played'")}

    def staff(self) -> list[dict]:
        return self.q("SELECT * FROM employees ORDER BY id")

    def bites(self, n: int = 16) -> list[dict]:
        return self.q("SELECT * FROM bites ORDER BY id DESC LIMIT ?", (n,))

    def reports(self, n: int = 40) -> list[dict]:
        return self.q("SELECT id, zulu, rank, title, status FROM reports WHERE status='open' ORDER BY rank DESC, id DESC LIMIT ?", (n,))

    def urls(self, n: int = 12) -> list[dict]:
        return self.q("SELECT * FROM queue WHERE description LIKE 'http%' ORDER BY id DESC LIMIT ?", (n,))

    def packets(self, n: int = 16) -> list[dict]:
        return self.q("SELECT id, status, dest, kind FROM packets WHERE status IN ('queued','delivered') ORDER BY id DESC LIMIT ?", (n,))

    def tables(self) -> list[str]:
        return [r["name"] for r in self.q("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]

    def table(self, name: str, needle: str = "", limit: int = 200) -> tuple[list[str], list[list[str]]]:
        if not name or not name.replace("_", "").isalnum():
            return [], []
        cols = [c["name"] for c in self.q(f"PRAGMA table_info([{name}])")]
        rows = self.q(f"SELECT * FROM [{name}] ORDER BY 1 DESC LIMIT {int(limit)}")
        out = []
        for r in rows:
            vals = [str(r.get(c)) for c in cols]
            if needle and needle.lower() not in " ".join(vals).lower():
                continue
            out.append(vals)
        return cols, out

    def media(self, n: int = 12, force: bool = False) -> list[Path]:
        """Newest stills + wavs. Cached; non-recursive scandir of two folders, at most every 60 s."""
        t, cache = self._art
        if not force and cache and time.time() - t < ART_TTL_S:
            return cache
        found = []
        for sub, ext in (("artifacts/vision", ".jpg"), ("artifacts", ".wav")):
            d = self.home / "data" / sub
            try:
                with os.scandir(d) as it:
                    found += [(e.stat().st_mtime, Path(e.path)) for e in it if e.is_file() and e.name.endswith(ext)]
            except OSError:
                pass
        found.sort(reverse=True)
        jpg = [p for _, p in found if p.suffix == ".jpg"][:n]
        wav = [p for _, p in found if p.suffix == ".wav"][:n]
        self._art = (time.time(), jpg + wav)
        return self._art[1]

    def health(self) -> dict:
        from nova import selfknow, gpulock
        h = {"tts": selfknow.tts_up(timeout=0.3), "ollama": gpulock.ollama_resident(timeout=0.8)}
        ml = self.home / "data" / "master.log"
        try:
            age = time.time() - ml.stat().st_mtime
            h["daemon"] = "UP" if age < 180 else f"quiet {int(age // 60)} min"
        except OSError:
            h["daemon"] = "unknown"
        th = self.q("SELECT zulu, body FROM facts WHERE whi='Ax-THERMAL' ORDER BY id DESC LIMIT 1")
        h["thermal"] = (th[0]["body"][:60] if th else "unknown")
        last = self.q("SELECT job, t1, err FROM master_log ORDER BY id DESC LIMIT 1")
        h["last_job"] = last[0] if last else None
        h["errors_1h"] = (self.q("SELECT count(*) n FROM master_log WHERE err<>'' AND t1>=strftime('%Y-%m-%dT%H:%M:%SZ','now','-1 hour')") or [{"n": None}])[0]["n"]
        h.update(self.counts())
        return h
