"""GUI acceptance tests (council P0-0..P1-4) — offscreen Qt, scratch-DB copy, chat model stubbed."""
import os, re, sys, time, unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from conftest_home import Home, sha  # noqa: E402

try:
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication, QPushButton
    HAVE_QT = True
except Exception:
    HAVE_QT = False

KIT = Path(__file__).resolve().parents[1]
TIMING = {}


@unittest.skipUnless(HAVE_QT, "PySide6 not installed")
class Gui(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.h = Home(from_scratch=True)  # ONE scratch-DB copy per run (keeps TEMP small)

    @classmethod
    def _home_env(cls):
        os.environ["NOVA_HOME"] = str(cls.h.d)

    def setUp(self):
        self._home_env()
        v = self.h.d / "data/artifacts/vision"; v.mkdir(parents=True, exist_ok=True)
        from PySide6.QtGui import QImage
        img = QImage(8, 8, QImage.Format_RGB32); img.fill(0x334455); img.save(str(v / "Ax-CAM-0_t.jpg"))
        (self.h.d / "data/artifacts/tts_t.wav").write_bytes(b"RIFF0000")
        from nova.gui import app as gapp
        self.win, self.ui = gapp.build(self.app, start_timers=False)
        self.ui["auto_confirm"] = True
        self.dbsha, self.dbm = sha(self.h.db()), self.h.db().stat().st_mtime

    def tearDown(self):
        self.ui["ro"].close(); self.win.close()

    def pump(self, ms=50):
        end = time.time() + ms / 1000
        while time.time() < end:
            self.app.processEvents(); time.sleep(0.005)

    def unchanged(self):
        self.assertEqual(sha(self.h.db()), self.dbsha)
        self.assertEqual(self.h.db().stat().st_mtime, self.dbm)
        self.assertFalse((self.h.d / "data/NOVA.db-wal").exists() and (self.h.d / "data/NOVA.db-wal").stat().st_size > 0)

    def test_p0_0_readonly_refresh(self):
        t0 = time.perf_counter()
        for _ in range(60):  # 60 health ticks = 5 min at 5 s
            self.ui["refresh_health"]()
        TIMING["health_tick_ms"] = round((time.perf_counter() - t0) * 1000 / 60, 1)
        for i in range(11):
            self.ui["stack"].setCurrentIndex(i); self.ui["refresh_panel"]()
        self.unchanged()
        src = "\n".join((KIT / "nova/gui" / f).read_text(encoding="utf-8") for f in ("app.py", "ro.py", "worker.py"))
        self.assertIsNone(re.search(r"put_fact|ensure_|\bINSERT\b|\bUPDATE\b", src))

    def test_p0_0b_model_dropdown(self):
        mb = self.ui["model_box"]
        for i in range(10):
            mb.setCurrentIndex(i % mb.count())
        self.assertEqual(mb.itemText(0), "qwen3:8b")
        self.unchanged()

    def test_p0_0c_panel_tick_cost(self):
        ro = self.ui["ro"]; ro.media(force=True)
        t0 = time.perf_counter(); q0 = ro.queries
        self.ui["stack"].setCurrentIndex(3); self.ui["refresh_panel"]()
        TIMING["ops_panel_ms"] = round((time.perf_counter() - t0) * 1000, 1)
        TIMING["ops_panel_queries"] = ro.queries - q0
        t0 = time.perf_counter(); ro.media()
        TIMING["media_cached_ms"] = round((time.perf_counter() - t0) * 1000, 2)
        self.assertLess(TIMING["media_cached_ms"], 5)
        self.assertNotIn("rglob", (KIT / "nova/gui/ro.py").read_text() + (KIT / "nova/gui/app.py").read_text())

    def test_p0_1_send_button(self):
        self.ui["chat_in"].setPlainText("/help")
        QTest.mouseClick(self.ui["btn_send"], Qt.LeftButton)
        log = self.ui["chat_log"].toPlainText()
        self.assertIn("YOU: /help", log); self.assertIn("NOVA: GUI slash", log)

    def test_p0_2_quick_keys(self):
        q = self.ui["quick"]
        QTest.keyClicks(q, "/help")
        self.assertEqual(q.text(), "/help")
        QTest.keyClick(q, Qt.Key_Return)
        self.assertIn("YOU: /help", self.ui["chat_log"].toPlainText())
        self.assertEqual(q.text(), ""); self.assertEqual(self.ui["chat_in"].toPlainText(), "")

    def test_p0_3_status_slice(self):
        self.ui["say_status"]("x" * 300)
        self.assertEqual(len(self.ui["status"].text()), 64)

    def test_p0_4_show_media(self):
        self.ui["stack"].setCurrentIndex(7); self.ui["refresh_panel"]()
        ml = self.ui["media_list"]
        items = [ml.item(i) for i in range(ml.count())]
        jpg = [i for i in items if i.text().endswith(".jpg")][0]
        wav = [i for i in items if i.text().endswith(".wav")][0]
        self.ui["show_media"](jpg); self.assertFalse(self.ui["pix"].pixmap().isNull())
        self.ui["show_media"](wav); self.assertIn("audio", self.ui["pix"].text())

    def test_p0_5_hidden_and_wired(self):
        btns = self.win.findChildren(QPushButton)
        labels = " | ".join(b.text() for b in btns)
        for bad in ("SAVE STATE", "CANCEL JOB", "PAUSE SESSION", "RESUME", "Tick jobs", "AVATAR", "moondream", "Play next bite", "Automate"):
            self.assertNotIn(bad, labels)
        dead = [b.text() for b in btns if b.receivers("2clicked(bool)") == 0 and b.receivers("2clicked()") == 0]
        self.assertEqual(dead, [])

    def test_p1_2_worker_stream_and_cancel(self):
        import nova.chat as chat

        def fake(text, model=None, on_token=None, cancel=None, **k):
            for t in ("one ", "two ", "three"):
                if cancel is not None and cancel.is_set():
                    return {"visible": "partial", "spoken": [], "notes": [], "cancelled": True}
                on_token(t); time.sleep(0.2)
            return {"visible": "one two three", "spoken": [], "notes": [], "cancelled": False}
        orig = chat.ask; chat.ask = fake
        try:
            self.ui["chat_in"].setPlainText("hello")
            t0 = time.perf_counter(); self.ui["send"]()
            TIMING["send_returns_ms"] = round((time.perf_counter() - t0) * 1000, 1)
            self.assertLess(TIMING["send_returns_ms"], 100)  # UI not blocked
            self.assertTrue(self.ui["btn_cancel"].isEnabled())
            for _ in range(200):
                self.pump(20)
                if self.ui["worker"] is None:
                    break
            self.assertIn("NOVA: one two three", self.ui["chat_log"].toPlainText())
            self.ui["chat_in"].setPlainText("again"); self.ui["send"](); self.pump(100)
            QTest.mouseClick(self.ui["btn_cancel"], Qt.LeftButton)
            for _ in range(200):
                self.pump(20)
                if self.ui["worker"] is None:
                    break
            self.assertIn("NOVA: partial", self.ui["chat_log"].toPlainText())
        finally:
            chat.ask = orig
        self.unchanged()

    def test_p1_3_knows_panel_exact(self):
        from nova import masks, selfknow
        fixed = selfknow.gather()
        og = selfknow.gather; selfknow.gather = lambda: dict(fixed)
        try:
            self.ui["render_knows"]()
            self.assertEqual(self.ui["know_box"].toPlainText().encode(), masks.context_blocks(2).encode())
            sp = masks.chat_system_prompt("brief", [], 2)
            self.assertTrue(sp.startswith(masks.context_blocks(2)))
        finally:
            selfknow.gather = og

    def test_p1_4_health_counts(self):
        from nova import selfknow
        self.ui["refresh_health"]()
        h = self.ui["health"]
        c = self.h.rw()
        self.assertEqual(h["reports_open"], c.execute("SELECT count(*) FROM reports WHERE status='open'").fetchone()[0])
        self.assertEqual(h["packets_fail"], c.execute("SELECT count(*) FROM packets WHERE status='fail'").fetchone()[0])
        c.close()
        self.assertEqual(h["tts"], selfknow.tts_up(timeout=0.3))
        self.assertIn("TTS :8000 " + ("UP" if h["tts"] else "DOWN"), self.ui["health_label"].text())

    def test_p2_1_approve_routes_through_daemon(self):
        from nova import cmdinbox
        self.ui["stack"].setCurrentIndex(4); self.ui["refresh_panel"]()
        rl = self.ui["rep_list"]
        if rl.count() == 0:
            self.skipTest("no open reports in scratch copy")
        rl.setCurrentRow(0); rid = int(rl.currentItem().text().split()[0])
        self.ui["op"]("report.close", {"id": rid}, "test")
        self.unchanged()  # GUI wrote a command file, not the DB
        self.assertEqual(len(cmdinbox.listing("approved")), 1)
        c = self.h.rw(); n0 = c.execute("SELECT count(*) FROM reports WHERE status='open'").fetchone()[0]; c.close()
        cmdinbox.execute_approved()  # the daemon side
        c = self.h.rw(); n1 = c.execute("SELECT count(*) FROM reports WHERE status='open'").fetchone()[0]
        ml = c.execute("SELECT count(*) FROM master_log WHERE job='cmd:report.close'").fetchone()[0]; c.close()
        self.assertEqual(n1, n0 - 1); self.assertEqual(ml, 1)

    @classmethod
    def tearDownClass(cls):
        cls.h.close()
        if TIMING:
            out = os.environ.get("NOVA_TIMING_OUT")
            if out:
                import json
                Path(out).write_text(json.dumps(TIMING, indent=1))
            print("TIMING", TIMING)


if __name__ == "__main__":
    unittest.main()
