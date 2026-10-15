"""fieldkit 2.1 tests: gates, scheduler, command inbox, chat guards, self-improve loop, disk dry-run,
portable paths, versions, staged guard. All on throwaway homes (and copies of the scratch DB)."""
import json, os, re, sqlite3, subprocess, sys, time, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from conftest_home import Home, sha  # noqa: E402

KIT = Path(__file__).resolve().parents[1]


class Base(unittest.TestCase):
    scratch = False

    def setUp(self):
        self.h = Home(self.scratch)

    def tearDown(self):
        self.h.close()


class Portable(unittest.TestCase):
    def test_no_hardcoded_user_paths(self):
        bad = re.compile(r"[A-Za-z]:\\\\?Users\\\\?[A-Za-z]|D:\\\\?pg\\\\?ai|/Users/[a-z]+/|C:/Users/")
        hits = []
        for p in (KIT / "nova").rglob("*.py"):
            for i, ln in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if bad.search(ln):
                    hits.append(f"{p.relative_to(KIT)}:{i}")
        self.assertEqual(hits, [])

    def test_paths_resolve_from_home(self):
        h = Home()
        try:
            from nova import paths
            self.assertEqual(paths.home(), h.d.resolve())
            self.assertTrue(str(paths.steward_log()).startswith(str(h.d.resolve())))
            self.assertEqual(paths.watson_roots(), [h.d.resolve()])
        finally:
            h.close()

    def test_versions(self):
        import nova
        self.assertEqual(nova.__version__, "2.1.0")
        self.assertTrue((KIT / "VERSION").read_text().startswith("2.1.0"))
        for f in ("nova/splash.py", "nova/tui/term.py", "nova/gui/app.py"):
            s = (KIT / f).read_text(encoding="utf-8")
            self.assertNotRegex(s, r"NOVA 1\.[0-9]|Terminal 1\.4|\"1\.7 attach")


class Gates(Base):
    def test_empty_allowlist_refuses(self):
        from nova import gates
        r = gates.host_allowed("https://example.com/x")
        self.assertFalse(r["allow"]); self.assertIn("REFUSES", r["reason"])

    def test_allowlist(self):
        from nova import gates
        (self.h.d / "data/config/gates.json").write_text(json.dumps({"net_allowlist": ["docs.python.org", "*.wikipedia.org"]}))
        self.assertTrue(gates.host_allowed("https://docs.python.org/3/").get("allow"))
        self.assertTrue(gates.host_allowed("https://en.wikipedia.org/wiki/X").get("allow"))
        self.assertFalse(gates.host_allowed("https://evil.example/").get("allow"))
        self.assertFalse(gates.host_allowed("ftp://docs.python.org/").get("allow"))

    def test_bad_config_fails_closed(self):
        from nova import gates
        (self.h.d / "data/config/gates.json").write_text("{not json")
        self.assertFalse(gates.host_allowed("https://docs.python.org/").get("allow"))

    def test_web_and_crawl_refuse_unknown_host_without_network(self):
        from nova import crawl
        from nova.hands import web
        r = web.fetch("https://unknown-host.invalid/")
        self.assertTrue(r.get("refused")); self.assertFalse(r["ok"])
        self.assertTrue(crawl.crawl("https://unknown-host.invalid/").get("refused"))
        self.assertTrue((self.h.d / "data/gates/gates.jsonl").is_file())

    def test_chat_scope(self):
        from nova import cmdinbox
        self.assertTrue(cmdinbox.propose("ingest.clear_standing", {}, source="chat").get("refused"))
        self.assertTrue(cmdinbox.propose("job.pause", {"id": 4}, source="chat").get("ok"))
        self.assertTrue(cmdinbox.propose("rm.rf", {}, source="operator").get("refused"))

    def test_rag_judge_fails_closed(self):
        import urllib.request
        from nova import rag
        orig = urllib.request.urlopen
        urllib.request.urlopen = lambda *a, **k: (_ for _ in ()).throw(OSError("down"))
        try:
            r = rag._small_judge("q", "some snippet")
        finally:
            urllib.request.urlopen = orig
        self.assertFalse(r["include"]); self.assertTrue(r.get("fail_closed"))

    def test_chamber_no_auto_promote(self):
        from nova import chamber
        self.assertFalse(chamber.AUTO_PROMOTE_RAG)

    def test_governor_hook_error_dry_run_vs_enforce(self):
        from nova import governor

        class Boom:
            def execute(self, *a, **k):
                raise RuntimeError("x")
        governor._CACHE["cfg"] = None
        self.assertTrue(governor.gate_fact(Boom(), "Ax-T", "t", "b"))  # dry-run default: allow + log
        (self.h.d / "data/config/governor.json").write_text(json.dumps({"enforce": True}))
        governor.config(force=True)
        self.assertFalse(governor.gate_fact(Boom(), "Ax-T", "t", "b"))  # enforce: fail closed
        (self.h.d / "data/config/governor.json").write_text(json.dumps({"enforce": False}))
        governor.config(force=True)

    def test_governor_report_readonly(self):
        from nova import governor
        before = sha(self.h.db())
        rep = governor.dry_run_report(self.h.db(), governor.config(force=True))
        self.assertEqual(rep["mode"], "dry-run")
        self.assertEqual(sha(self.h.db()), before)
        self.assertTrue((self.h.d / "data/governor/governor_dryrun_report.json").is_file())


class Inbox(Base):
    def test_approve_then_daemon_executes(self):
        from nova import cmdinbox, db
        jid = db.job_add("holmes-x", 300)
        r = cmdinbox.propose("job.pause", {"id": jid}, source="chat", why="test")
        self.assertEqual(r["state"], "proposed")
        self.assertEqual(cmdinbox.execute_approved(), [])  # nothing runs while only proposed
        self.assertEqual([j for j in db.jobs() if j["id"] == jid][0]["enabled"], 1)
        cmdinbox.approve(r["id"], by="test")
        done = cmdinbox.execute_approved()
        self.assertEqual(len(done), 1); self.assertTrue(done[0]["result"]["ok"])
        self.assertEqual([j for j in db.jobs() if j["id"] == jid][0]["enabled"], 0)
        self.assertEqual(len(cmdinbox.listing("done")), 1)

    def test_duplicate_and_deny(self):
        from nova import cmdinbox
        a = cmdinbox.propose("job.run_now", {"id": 1}); b = cmdinbox.propose("job.run_now", {"id": 1})
        self.assertTrue(b.get("duplicate"))
        cmdinbox.deny(a["id"]); self.assertEqual(len(cmdinbox.listing("denied")), 1)

    def test_url_approve_feeds_drain(self):
        from nova import board, cmdinbox
        from nova.hands import web
        qid = board.enqueue_url("https://docs.python.org/3/")
        calls = []
        orig = web.fetch
        web.fetch = lambda u, **k: (calls.append(u), {"ok": True})[1]
        try:
            self.assertTrue(board.drain_one().get("empty"))  # queued != approved: not fetched
            cmdinbox.operator_command("url.approve", {"id": qid}, by="test"); cmdinbox.execute_approved()
            r = board.drain_one()
        finally:
            web.fetch = orig
        self.assertEqual(r.get("id"), qid); self.assertEqual(calls, ["https://docs.python.org/3/"])

    def test_report_close_one(self):  # council P2-1
        from nova import cmdinbox, office
        ids = [office.report(1, f"r{i}", "b") for i in range(3)]
        cmdinbox.operator_command("report.close", {"id": ids[0]}, by="test"); cmdinbox.execute_approved()
        c = self.h.rw()
        self.assertEqual(c.execute("SELECT count(*) FROM reports WHERE status='open'").fetchone()[0], 2)
        self.assertEqual(c.execute("SELECT count(*) FROM master_log WHERE job='cmd:report.close'").fetchone()[0], 1)


class Sched(Base):
    def _jobs(self, names):
        from nova import db
        return {n: db.job_add(n, 300) for n in names}

    def test_table_fields(self):
        from nova import sched
        self._jobs(["holmes", "maintain"])
        row = sched.job_table()[0]
        for k in ("id", "name", "cadence_s", "priority", "gpu", "last_run", "next_run", "last_error", "enabled", "fails"):
            self.assertIn(k, row)
        self.assertIn("gpu", sched.table_text())

    def test_priority_backoff_gpu(self):
        from nova import sched, gpulock
        ids = self._jobs(["whistle", "maintain", "codesum:x", "thermal-check"])
        ran = []

        def fake(name):
            ran.append(name)
            return {"job": name, "ms": 1, "err": "boom" if name == "whistle" else "", "note": ""}
        orig = sched.run_named; sched.run_named = fake
        try:
            out = sched.tick()
            self.assertEqual(ran[0], "thermal-check")  # highest priority first
            self.assertEqual(len([n for n in ran if sched.meta(n)["gpu"] == "heavy"]), 1)  # one heavy per tick
            st = sched.load_state()
            self.assertEqual(st[str(ids["whistle"])]["fails"], 1)
            self.assertGreater(st[str(ids["whistle"])]["backoff_until"], time.time() + 30)
            # held lock by someone else -> heavy deferred, not failed
            ran.clear()
            gpulock.acquire("other", "heavy")
            sched.request_run_now(ids["maintain"]); sched.request_run_now(ids["codesum:x"])
            out = sched.tick()
            self.assertTrue(any("gpu_busy" in (r.get("note") or "") for r in out))
            self.assertEqual([n for n in ran if sched.meta(n)["gpu"] == "heavy"], [])
            gpulock.release("other")
        finally:
            sched.run_named = orig

    def test_backoff_growth_and_reset(self):
        from nova import sched
        jid = self._jobs(["holmes"])["holmes"]
        a = sched.record(jid, "e")["backoff_until"]; b = sched.record(jid, "e")["backoff_until"]
        self.assertGreater(b - time.time(), a - time.time())
        self.assertEqual(sched.record(jid, "")["fails"], 0)

    def test_task_stimulus_proposes_never_executes(self):
        from nova import cmdinbox, office, sched, taskstim, stimuli
        office.report(2, "tool break: pocket.speak", "x"); office.report(1, "tool break: pocket.speak", "y")
        ids = self._jobs(["holmes", "task-stimulus"])
        r = taskstim.run()
        self.assertTrue(any("HIL reports open" in ln for ln in r["now"]))
        self.assertTrue(any("stale check" in ln for ln in r["now"]))
        n = len(cmdinbox.listing("proposed")); self.assertGreater(n, 0)
        self.assertEqual(taskstim.run()["proposed"], 0)  # dedup
        orig = sched.run_named
        sched.run_named = lambda name: {"job": name, "ms": 1, "err": "", "note": ""}
        try:
            sched.tick()
        finally:
            sched.run_named = orig
        self.assertEqual(len(cmdinbox.listing("proposed")), n)  # still waiting for HIL
        self.assertEqual(len(cmdinbox.listing("done")), 0)
        self.assertIn("TASK", stimuli.now(15))


class ChatGuard(unittest.TestCase):
    P_UP = {"tts_up": True, "job_ids": {"cam:0": 4, "holmes": 1}}
    P_DOWN = {"tts_up": False, "job_ids": {"cam:0": 4}}

    def test_speak_tags_dropped(self):
        from nova import chat
        g = chat.guard("What can't you do?", "I cannot delete. [speak anna] Nope. [/speak]", self.P_UP)
        self.assertEqual(g["spoken"], []); self.assertNotIn("[speak", g["visible"])
        g = chat.guard("Tell me a joke", "Ha. [speak anna] Knock knock. [/speak]", self.P_DOWN)
        self.assertEqual(g["spoken"], [])
        g = chat.guard("Tell me a joke", "Ha. [speak anna] Knock knock. [/speak]", self.P_UP)
        self.assertEqual(len(g["spoken"]), 1)

    def test_command_ids(self):
        from nova import chat
        g = chat.guard("Turn off the camera job.", "I will not do it from chat. /job off cam:0", self.P_UP)
        self.assertIn("/job off 4", g["visible"])
        self.assertEqual(chat.proposals(g["visible"]), [("job.pause", {"id": 4})])

    def test_voice_answer(self):
        from nova import chat
        g = chat.guard("Can you speak to me right now?", "I cannot speak right now. [speak anna] Voice is down. [/speak]", self.P_UP)
        self.assertTrue(g["visible"].startswith("Yes.")); self.assertEqual(g["spoken"], [])
        g = chat.guard("Can you speak to me right now?", "Yes, I can speak.", self.P_DOWN)
        self.assertTrue(g["visible"].startswith("No."))
        g = chat.guard("Can you speak to me right now?", "Yes, Pocket TTS is UP; I can speak aloud.", self.P_UP)
        self.assertNotIn("voice answer replaced from SELF", g["notes"])


class SelfImprove(Base):
    def test_loop(self):
        import tempfile
        from nova import selfimprove as si
        sb = Path(tempfile.mkdtemp(prefix="sb_"))
        (sb / "tests").mkdir()
        (sb / "tests" / "test_ok.py").write_text("from pkg import v\ndef test_v():\n    assert v.X == 2\n")
        (sb / "pkg").mkdir(); (sb / "pkg" / "__init__.py").write_text(""); (sb / "pkg" / "v.py").write_text("X = 1\n")
        r = si.propose("bump X", "test", {"pkg/v.py": "X = 2\n"}, tests=["-q", "tests"])
        pid = r["pid"]
        self.assertTrue(si.approve(pid).get("refused"))  # no review yet
        si.review(pid, "skeptic", "oppose", "no")
        self.assertTrue(si.approve(pid).get("refused"))  # opposed
        si.review(pid, "skeptic", "agree", "ok")
        self.assertTrue(si.apply(pid, sb).get("refused"))  # no approval
        self.assertTrue(si.approve(pid)["ok"])
        self.assertTrue(si.apply(pid, sb).get("refused"))  # no sandbox marker
        (sb / ".nova_sandbox").write_text("sandbox")
        self.assertTrue(si.apply(pid, sb)["ok"])
        v = si.verify(pid, sb)
        self.assertEqual(v["rc"], 0, v)
        p = si.record_proof(pid, sb)
        self.assertTrue(p["ok"]); self.assertIn("PROOF:", p["line"])

    def test_council_review_parsing(self):
        from nova import selfimprove as si
        pid = si.propose("t", "w", {"a.txt": "x"})["pid"]
        si.council_review(pid, ask=lambda prompt: "OPPOSE. risky", seats=("reviewer",))
        self.assertFalse(si.status(pid)["review_ok"])


class Disk(Base):
    def test_dry_run_never_deletes(self):
        from nova import disk
        v = self.h.d / "data/artifacts/vision"; v.mkdir(parents=True)
        old = time.time() - 30 * 86400
        for i in range(210):
            f = v / f"s{i:03}.jpg"; f.write_bytes(b"x" * 10); os.utime(f, (old, old))
        a = self.h.d / "data/artifacts"
        (a / "tts_1.wav").write_bytes(b"abc"); (a / "tts_1_play.wav").write_bytes(b"abc")
        (self.h.d / "data/NOVA.db.bak-1").write_bytes(b"1"); (self.h.d / "data/NOVA.db.bak-2").write_bytes(b"22")
        before = set(self.h.d.rglob("*"))
        rep = disk.dry_run_report(self.h.d)
        items = {i["rule"]: i for i in rep["items"]}
        self.assertEqual(items["stills"]["count"], 10)
        self.assertEqual(items["tts_play_dupes"]["count"], 1)
        self.assertEqual(items["db_backups"]["count"], 1)
        after = set(self.h.d.rglob("*"))
        self.assertTrue(before <= after)  # nothing removed
        self.assertEqual({p.name for p in after - before} - {"run"}, {"disk_dryrun.json"})
        self.assertFalse(rep["apply_enabled"])

    def test_no_unlink_in_daemon_paths(self):
        for f in ("nova/sched.py", "nova/disk.py", "nova/cmdinbox.py", "nova/gpulock.py", "nova/taskstim.py"):
            self.assertNotIn(".unlink(", (KIT / f).read_text(encoding="utf-8"), f)


class StagedGuard(unittest.TestCase):
    def test_refuses_without_home(self):
        if not (KIT / "STAGED").is_file():
            self.skipTest("not a staged kit")
        env = {k: v for k, v in os.environ.items() if k != "NOVA_HOME"}
        r = subprocess.run([sys.executable, "-c", "import nova.__main__ as m; print(m.staged_guard())"],
                           cwd=str(KIT), env=env, capture_output=True, text=True, timeout=60)
        self.assertIn("refusing", r.stdout)
        env["NOVA_HOME"] = str(KIT.parent / "_not_a_scratch_home_test")  # never the live kit
        r = subprocess.run([sys.executable, "-c", "import nova.__main__ as m; print(m.staged_guard())"],
                           cwd=str(KIT), env=env, capture_output=True, text=True, timeout=60)
        self.assertIn("not one of the scratch homes", r.stdout)


if __name__ == "__main__":
    unittest.main()


class ChatGuard2(unittest.TestCase):
    def test_action_claim_removed(self):
        from nova import chat
        g = chat.guard("Pause the whistle job, then tell me what you did.", "/job off 3  I paused the whistle job.",
                       {"tts_up": True, "job_ids": {"whistle": 3}})
        self.assertNotIn("I paused", g["visible"]); self.assertIn("/job off 3", g["visible"])
        self.assertIn("Not done", g["visible"])
        g = chat.guard("What can't you do?", "I cannot change jobs.", {"tts_up": True})
        self.assertEqual(g["visible"], "I cannot change jobs.")


class ChatGuard3(unittest.TestCase):
    def test_unrelated_command_removed(self):
        from nova import chat
        g = chat.guard("Fetch https://x.example and summarize it.", "I will not do it from chat. /job off 4.", {"job_ids": {"cam:0": 4}})
        self.assertNotIn("/job", g["visible"])
        g = chat.guard("Turn off the camera job.", "I will not do it from chat. /job off 4", {"job_ids": {"cam:0": 4}})
        self.assertIn("/job off 4", g["visible"])

    def test_rules_have_no_copyable_job_example(self):
        from nova import masks
        self.assertNotIn("/job off 4", masks.RULES_V2)


class ChatGuard4(unittest.TestCase):
    def test_malformed_tag_and_bare_claim(self):
        from nova import chat
        g = chat.guard("Pause the whistle job, then tell me what you did.",
                       "/speak anna] Paused the whistle job as requested. [/speak]", {"tts_up": True, "job_ids": {"whistle": 3}})
        self.assertNotIn("speak", g["visible"].lower()); self.assertNotIn("Paused", g["visible"])
        self.assertIn("Not done", g["visible"])


class SchedRestart(Base):
    def test_next_run_from_db_stamp(self):
        from nova import db, sched
        jid = db.job_add("holmes", 300)
        c = self.h.rw(); c.execute("UPDATE jobs SET last_zulu=? WHERE id=?", (db.zulu(), jid)); c.commit(); c.close()
        self.assertEqual([r for r in sched.due() if r["id"] == jid], [])  # ran just now -> not due
        row = [r for r in sched.job_table() if r["id"] == jid][0]
        self.assertTrue(row["next_run"].endswith("CT")); self.assertTrue(row["last_run"].endswith("CT"))


class ChatGuard5(unittest.TestCase):
    def test_capabilities_and_next_have_no_tags(self):
        from nova import chat
        for q in ("What are your capabilities?", "What should you work on next?"):
            g = chat.guard(q, "Stuff. [speak anna] Hi there. [/speak]", {"tts_up": True})
            self.assertEqual(g["spoken"], [], q)
