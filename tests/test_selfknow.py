import os, sqlite3, tempfile, time, unittest
from datetime import datetime, timezone
from pathlib import Path

from nova import selfknow, stimuli, masks

T = datetime(2026, 10, 15, 0, 5, tzinfo=timezone.utc)
FIX = {"generated": T, "jobs": [("holmes", 1), ("cam:0", 1), ("lille-tick", 0)], "facts": 10,
       "observations": 20, "chunks": 3, "reports_open": 2, "packets_fail": 1,
       "cam_last": datetime(2026, 10, 14, 23, 59, tzinfo=timezone.utc), "tts_up": False,
       "ollama": ["qwen3:8b"], "handlers": ["holmes"]}


class SelfTests(unittest.TestCase):
    def test_deterministic(self):
        self.assertEqual(selfknow.text(dict(FIX)), selfknow.text(dict(FIX)))
        self.assertIn("2026-10-14 19:05 CT", selfknow.text(FIX))
        self.assertIn("2 enabled jobs: holmes, cam:0", selfknow.text(FIX))

    def test_tts_down(self):
        self.assertIn("Pocket TTS :8000 — DOWN", selfknow.text(FIX))
        self.assertIn("— UP", selfknow.text(dict(FIX, tts_up=True)))

    def test_missing_unknown(self):
        p = {"generated": T}
        s = selfknow.text(p)
        self.assertIn("Scheduler: unknown", s)
        self.assertIn("TTS :8000 — unknown", s)
        self.assertIn("Last still: unknown", s)
        self.assertIn("loaded now: unknown", s)

    def test_length(self):
        n = len(selfknow.text(FIX))
        self.assertTrue(600 <= n <= 1300, n)

    def test_panel_identical(self):
        self.assertEqual(selfknow.panel_text(FIX).encode(), selfknow.text(FIX).encode())

    def test_injected_block_matches_panel(self):
        orig = masks.context_blocks
        masks.context_blocks = lambda: selfknow.text(FIX)
        try:
            self.assertIn(selfknow.panel_text(FIX), masks.apply("brief", selfknow=True))
            self.assertNotIn("SELF (", masks.apply("brief", selfknow=False))
        finally:
            masks.context_blocks = orig


class NowTests(unittest.TestCase):
    def _home(self):
        d = Path(tempfile.mkdtemp())
        (d / "data" / "artifacts" / "vision").mkdir(parents=True)
        jpg = d / "data" / "artifacts" / "vision" / "Ax-CAM-0_x.jpg"
        jpg.write_bytes(b"x")
        ts = datetime(2026, 10, 14, 23, 59, tzinfo=timezone.utc).timestamp()
        os.utime(jpg, (ts, ts))
        (d / "data" / "master.log").write_text(
            "pad\n2026-10-14T19:32:01Z job=cam:0 ms=1 err= ok\n"
            "2026-10-14T23:43:57Z job=thermal-check ms=1 err= band=cool temp=54.0 llm_ok=True\n"
            "2026-10-15T00:01:00Z job=holmes ms=1 err=boom probes=0\n", encoding="utf-8")
        con = sqlite3.connect(d / "data" / "NOVA.db")
        con.executescript("CREATE TABLE reports(id INTEGER PRIMARY KEY, zulu, rank, title, body, status);"
                          "CREATE TABLE packets(id INTEGER PRIMARY KEY, status);"
                          "CREATE TABLE facts(id INTEGER PRIMARY KEY, zulu, whi, title, body);"
                          "INSERT INTO reports VALUES(1,'2026-10-14T23:58:54Z',1,'tool break: pocket.speak','','open');"
                          "INSERT INTO packets VALUES(1,'fail');")
        con.commit(); con.close()
        return d

    def test_now_deterministic(self):
        h = self._home()
        a = stimuli.now(15, home=h, at=T); b = stimuli.now(15, home=h, at=T)
        self.assertEqual(a, b)
        self.assertIn("never trigger actions".upper(), a.upper())
        self.assertIn("18:59 CT cam:0 photo saved", a)
        # 2.1: latest reading only, age-stamped when older than the window
        self.assertIn("band=cool", a)
        self.assertIn("21 min old", a)
        self.assertEqual(a.count("thermal"), 1)
        self.assertIn("daemon gap 2026-10-14 14:32 CT", a)
        self.assertIn("job holmes error: boom", a)
        self.assertIn("tool break: pocket.speak", a)
        self.assertIn("failed packets total: 1", a)

    def test_now_missing(self):
        d = Path(tempfile.mkdtemp())
        a = stimuli.now(15, home=d, at=T)
        self.assertIn("cam: unknown", a); self.assertIn("reports: unknown", a); self.assertIn("thermal: unknown", a)


JOBS10 = ["holmes", "maintain", "whistle", "cam:0", "homestead-cycle", "ingest-drain", "docs-scout",
          "docs-ingest", "thermal-check", "nova-diary"]
FIX10 = dict(FIX, jobs=[(n, 1) for n in JOBS10], job_ids={n: i + 1 for i, n in enumerate(JOBS10)},
             facts=15351, observations=33613, chunks=385, reports_open=78, packets_fail=2,
             ollama=["qwen3.5:9b"])


class V2Tests(unittest.TestCase):
    def test_v2_length(self):
        for tts in (True, False, None):
            n = len(selfknow.text(dict(FIX10, tts_up=tts), version=2))
            self.assertTrue(600 <= n <= 900, n)

    def test_v2_voice_state(self):
        self.assertIn("UP; I can speak", selfknow.text(dict(FIX10, tts_up=True), version=2))
        down = selfknow.text(dict(FIX10, tts_up=False), version=2)
        self.assertIn("DOWN; I cannot speak", down)
        self.assertNotIn("If DOWN", down)

    def test_v2_job_ids(self):
        self.assertIn("cam:0 #4", selfknow.text(FIX10, version=2))

    def test_v2_order_and_rules(self):
        from nova import parser
        orig = masks.context_blocks
        masks.context_blocks = lambda version=1: selfknow.text(FIX10, version=version)
        try:
            hits = [{"whi": "Tx-HUNT-MISS", "title": "old q"}, {"whi": "Ax-1", "title": "real"}]
            sp = masks.chat_system_prompt("brief", hits, 2)
            self.assertTrue(sp.startswith("SELF ("))
            self.assertLess(sp.index("RULES"), sp.index("You are NOVA brief"))
            self.assertNotIn("Tx-HUNT-MISS", sp)
            self.assertIn("Ax-1 real", sp)
            self.assertNotIn("Holmes finished", sp)
            self.assertNotIn("Zulu.", sp)
            self.assertNotIn("Status clear", sp)
            sp0 = masks.chat_system_prompt("brief", hits, 0)
            self.assertIn(parser.GRAMMAR, sp0)
            self.assertNotIn("SELF (", sp0)
        finally:
            masks.context_blocks = orig

    def test_hunt_readonly_no_write(self):
        from nova import db
        d = Path(tempfile.mkdtemp())
        old = os.environ.get("NOVA_HOME")
        os.environ["NOVA_HOME"] = str(d)
        try:
            con = db.connect(); con.close()  # create schema once (writer path)
            before = db.db_path().read_bytes()
            self.assertEqual(db.hunt("zzqx nothing here", readonly=True), [])
            self.assertEqual(db.db_path().read_bytes(), before)
            db.hunt("zzqx nothing here")  # legacy path still logs the miss
            con = db.connect_ro()
            self.assertEqual(con.execute("SELECT count(*) FROM facts WHERE whi='Tx-HUNT-MISS'").fetchone()[0], 1)
            con.close()
            self.assertEqual(db.hunt("zzqx", readonly=True), [])  # miss row filtered from hits
        finally:
            if old is None:
                os.environ.pop("NOVA_HOME", None)
            else:
                os.environ["NOVA_HOME"] = old


if __name__ == "__main__":
    unittest.main()
