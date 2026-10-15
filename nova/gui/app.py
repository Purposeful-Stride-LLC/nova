"""NOVA 2.1 operator console (PySide6). A thin, READ-ONLY client.

The daemon owns the scheduler, DB writes, models and TTS. This window:
  - reads NOVA.db on one mode=ro connection (gui/ro.py); 0 DB writes per tick;
  - chats on a worker thread (gui/worker.py) with streaming + Cancel (qwen3:8b, ctx 8192, think:false);
  - shows a health strip and a 'What NOVA knows' panel (exact SELF/NOW text);
  - routes every operator action (job pause/resume/run-now, approve/close one report, approve URL,
    approve-all, clear standing ingest, deliver mail) through the command inbox (file IPC); the
    daemon executes approved commands on its next tick.
Controls that are not implemented (Save State, Cancel Job, Pause/Resume session, Tick, AVATAR,
VOICE/MASK/RATE, cam+moondream, play bite, automate toggle) are hidden in 2.1.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HIDDEN_2_1 = ("save_state", "cancel_job", "pause", "resume", "tick", "avatar", "voice", "mask", "rate",
              "cam_see", "play_bite", "automate_toggle")
CHAT_MODEL_DEFAULT = "qwen3:8b"


def build(app=None, start_timers: bool = True):
    """Build the window and return (win, ui) where ui exposes widgets for tests."""
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtGui import QPixmap
    from PySide6.QtWidgets import (QApplication, QComboBox, QFrame, QHBoxLayout, QHeaderView, QLabel,
                                   QLineEdit, QListWidget, QMainWindow, QMessageBox, QPushButton, QScrollArea,
                                   QSizePolicy, QStackedWidget, QTableWidget, QTableWidgetItem, QTextEdit,
                                   QVBoxLayout, QWidget)

    from nova import VERSION_LABEL, cmdinbox, masks
    from nova.gui.ro import RO

    app = app or QApplication.instance() or QApplication(sys.argv)
    ro = RO()
    ui: dict = {"ro": ro, "worker": None, "last_prompt": ""}
    qss = Path(__file__).with_name("console.qss")

    win = QMainWindow()
    win.setWindowTitle(f"{VERSION_LABEL} — OPERATOR CONSOLE (read-only)")
    root = QWidget()
    outer = QVBoxLayout(root)
    health = QLabel("health: …")
    health.setObjectName("HealthStrip")
    health.setWordWrap(True)
    outer.addWidget(health)
    mainlay = QHBoxLayout()
    outer.addLayout(mainlay, stretch=1)
    status = QLabel("read-only console")

    def say_status(text: str) -> None:
        status.setText(str(text)[:64])  # 2.1: slice the string, not setText()'s None

    # ---------------- deck
    deck = QWidget()
    deck.setObjectName("CommandDeck")
    dlay = QVBoxLayout(deck)
    dlay.addWidget(QLabel("COMMAND DECK"))
    brand = Path(__file__).resolve().parents[2] / "ascii" / "brand" / "banner.jpg"
    if brand.is_file():
        b = QLabel()
        b.setPixmap(QPixmap(str(brand)).scaled(220, 120))
        dlay.addWidget(b)
    stack = QStackedWidget()

    # ---------------- 0 chat
    chat_w = QWidget()
    cl = QVBoxLayout(chat_w)
    cl.setContentsMargins(8, 8, 8, 36)
    cl.addWidget(QLabel("ASTROCOMMS"))
    model_box = QComboBox()
    model_box.addItems([CHAT_MODEL_DEFAULT, "llama3-groq-tool-use:8b", "qwen3.5:9b"])
    model_box.setCurrentText(CHAT_MODEL_DEFAULT)  # no router/catalog call (no palace writes)
    model_box.setToolTip("Chat model. Default qwen3:8b, num_ctx 8192, think:false (fits 8 GB VRAM).")
    cl.addWidget(model_box)
    chat_log = QTextEdit()
    chat_log.setReadOnly(True)
    chat_in = QTextEdit()
    chat_in.setAcceptRichText(False)
    chat_in.setPlaceholderText("ask NOVA…  (Ctrl+Enter or Send)")
    chat_in.setMaximumHeight(140)
    btn_send = QPushButton("Send")
    btn_cancel = QPushButton("Cancel")
    btn_cancel.setEnabled(False)
    cl.addWidget(chat_log, stretch=1)
    cl.addWidget(chat_in)
    row = QHBoxLayout()
    quick = QLineEdit()
    quick.setPlaceholderText("/help · /sched · /cmd list   (Enter sends)")
    row.addWidget(quick, stretch=1)
    row.addWidget(btn_cancel)
    row.addWidget(btn_send)
    cl.addLayout(row)

    def _on_token(tok: str) -> None:
        cur = chat_log.textCursor()
        cur.movePosition(cur.MoveOperation.End)
        cur.insertText(tok)
        chat_log.setTextCursor(cur)

    def _on_done(r: dict) -> None:
        chat_log.append("NOVA: " + (r.get("visible") or ""))
        props = [p for p in r.get("proposed") or [] if p.get("ok")]
        if props:
            chat_log.append("  [proposed for approval: " + ", ".join(f"{p['verb']} {p['args']}" for p in props) + " → PROPOSALS panel]")
        if r.get("notes"):
            chat_log.append("  [guard: " + "; ".join(r["notes"]) + "]")
        if r.get("contention"):
            chat_log.append("  [GPU: other heavy model resident: " + ", ".join(m["name"] for m in r["contention"]) + "]")
        ui["last_prompt"] = r.get("system_prompt") or ui["last_prompt"]
        btn_send.setEnabled(True)
        btn_cancel.setEnabled(False)
        ui["worker"] = None

    def send() -> None:
        text = chat_in.toPlainText().strip()
        if not text or ui["worker"] is not None:
            return
        chat_in.clear()
        chat_log.append("YOU: " + text)
        if text.startswith("/"):
            run_slash(text)
            return
        from nova.gui.worker import ChatWorker
        w = ChatWorker(text, model_box.currentText(), parent=win)
        chat_log.append("NOVA (streaming): ")
        w.token.connect(_on_token)
        w.finished_reply.connect(_on_done)
        ui["worker"] = w
        btn_send.setEnabled(False)
        btn_cancel.setEnabled(True)
        w.start()

    def cancel() -> None:
        if ui["worker"] is not None:
            ui["worker"].cancel()
            say_status("chat cancel requested")

    def run_slash(cmd: str) -> None:
        """Read-only slash commands in the GUI; anything that writes becomes a proposal."""
        low = cmd.lower().strip()
        from nova import sched
        if low in ("/help", "help"):
            out = "GUI slash: /help /sched /cmd list /cmd approve ID /cmd deny ID /self\nWrites go via the PROPOSALS panel; use the TUI for other commands."
        elif low.startswith("/sched"):
            out = sched.table_text(ro.jobs())
        elif low.startswith("/self"):
            out = masks.context_blocks(2)
        elif low.startswith("/cmd"):
            p = cmd.split()
            if len(p) > 2 and p[1] in ("approve", "deny"):
                out = str((cmdinbox.approve if p[1] == "approve" else cmdinbox.deny)(p[2], by="gui"))
            else:
                out = "\n".join(f"{r['id']} {r['verb']} {r['args']} from={r['source']}" for r in cmdinbox.listing("proposed")) or "no proposals"
        else:
            out = "not available in the read-only GUI; use the TUI (python -m nova.tui)"
        chat_log.append("NOVA: " + out)

    def quick_send() -> None:
        cmd = quick.text().strip()
        if cmd:
            chat_log.append("YOU: " + cmd)  # 2.1: echo to the LOG, not the input box
            run_slash(cmd if cmd.startswith("/") else "/" + cmd)
            quick.clear()

    btn_send.clicked.connect(send)  # 2.1: the visible Send button (single instance) is connected
    btn_cancel.clicked.connect(cancel)
    quick.returnPressed.connect(quick_send)  # default QLineEdit key handling: typing works

    def _chat_key(e):
        if e.key() in (Qt.Key_Return, Qt.Key_Enter) and (e.modifiers() & Qt.ControlModifier):
            send()
            return
        QTextEdit.keyPressEvent(chat_in, e)

    chat_in.keyPressEvent = _chat_key  # type: ignore

    # ---------------- 1 sonic, 2 core
    sonic = QWidget(); sl = QVBoxLayout(sonic); sl.addWidget(QLabel("SONIC ARCHIVE (read-only)"))
    bite_list = QListWidget(); sl.addWidget(bite_list)
    core = QWidget(); ol = QVBoxLayout(core); ol.addWidget(QLabel("AI CORE MATRIX (read-only)"))
    staff_list = QListWidget(); ol.addWidget(staff_list)

    # ---------------- 3 ops: scheduler table + URL board
    ops = QWidget(); opl = QVBoxLayout(ops); opl.addWidget(QLabel("SYSTEM OPS — scheduler (actions go to the daemon)"))
    job_table = QTableWidget()
    job_table.setSelectionBehavior(QTableWidget.SelectRows)
    job_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
    opl.addWidget(job_table, stretch=1)
    jrow = QHBoxLayout()
    btn_pause = QPushButton("Pause job"); btn_resume = QPushButton("Resume job"); btn_run = QPushButton("Run now")
    for b_ in (btn_pause, btn_resume, btn_run):
        jrow.addWidget(b_)
    opl.addLayout(jrow)
    url_list = QListWidget(); opl.addWidget(url_list)
    url_in = QLineEdit(); url_in.setPlaceholderText("https://  drop a link (queued for approval; host must be allowlisted)")
    urow = QHBoxLayout()
    btn_url = QPushButton("Queue URL"); btn_url_ok = QPushButton("Approve URL"); btn_url_no = QPushButton("Deny URL")
    for b_ in (btn_url, btn_url_ok, btn_url_no):
        urow.addWidget(b_)
    opl.addWidget(url_in); opl.addLayout(urow)
    btn_clear = QPushButton("Clear standing ingest…")
    opl.addWidget(btn_clear)

    # ---------------- 4 records (HIL reports)
    rec = QWidget(); rl = QVBoxLayout(rec); rl.addWidget(QLabel("MISSION RECORDS — open HIL reports"))
    rep_list = QListWidget(); rl.addWidget(rep_list, stretch=1)
    rrow = QHBoxLayout()
    btn_rep_ok = QPushButton("Approve one"); btn_rep_close = QPushButton("Close one"); btn_rep_all = QPushButton("Approve All…")
    for b_ in (btn_rep_ok, btn_rep_close, btn_rep_all):
        rrow.addWidget(b_)
    rl.addLayout(rrow)

    # ---------------- 5 mail
    mail_w = QWidget(); ml = QVBoxLayout(mail_w); ml.addWidget(QLabel("MAIL ROOM"))
    mail_list = QListWidget(); btn_mail = QPushButton("Deliver 3 (via daemon)")
    ml.addWidget(mail_list); ml.addWidget(btn_mail)

    # ---------------- 6 palace
    palace_w = QWidget(); pl = QVBoxLayout(palace_w); pl.addWidget(QLabel("PALACE (mode=ro)"))
    table_box = QComboBox(); palace_search = QLineEdit(); palace_search.setPlaceholderText("filter rows…")
    palace_table = QTableWidget(); palace_table.setSortingEnabled(True)
    pl.addWidget(table_box); pl.addWidget(palace_search); pl.addWidget(palace_table)

    # ---------------- 7 viewport
    view_w = QWidget(); vl = QVBoxLayout(view_w); vl.addWidget(QLabel("VIEWPORT (cached scan; Rescan to refresh)"))
    media_list = QListWidget(); pix = QLabel("select a still"); pix.setMinimumHeight(220)
    btn_rescan = QPushButton("Rescan")
    vl.addWidget(media_list); vl.addWidget(pix); vl.addWidget(btn_rescan)

    # ---------------- 8 spawn
    spawn_w = QWidget(); spl = QVBoxLayout(spawn_w); spl.addWidget(QLabel("SPAWN STATUS"))
    spawn_list = QListWidget(); spl.addWidget(spawn_list)

    # ---------------- 9 knows, 10 proposals
    know_w = QWidget(); kl = QVBoxLayout(know_w); kl.addWidget(QLabel("WHAT NOVA KNOWS — exact SELF/NOW text injected into chat"))
    know_box = QTextEdit(); know_box.setReadOnly(True); kl.addWidget(know_box)
    last_box = QTextEdit(); last_box.setReadOnly(True); kl.addWidget(QLabel("Last system prompt actually sent (byte-exact):")); kl.addWidget(last_box)
    btn_know = QPushButton("Re-render"); kl.addWidget(btn_know)
    prop_w = QWidget(); prl = QVBoxLayout(prop_w); prl.addWidget(QLabel("PROPOSALS — chat / task-stimulus / GUI; nothing runs until approved"))
    prop_list = QListWidget(); prl.addWidget(prop_list, stretch=1)
    prow = QHBoxLayout(); btn_p_ok = QPushButton("Approve"); btn_p_no = QPushButton("Deny")
    prow.addWidget(btn_p_ok); prow.addWidget(btn_p_no); prl.addLayout(prow)

    panels = [chat_w, sonic, core, ops, rec, mail_w, palace_w, view_w, spawn_w, know_w, prop_w]
    for w in panels:
        wrap = QScrollArea(); wrap.setWidgetResizable(True); wrap.setFrameShape(QFrame.NoFrame); wrap.setWidget(w)
        stack.addWidget(wrap)

    # ---------------- tiles (only live ones are shown; dead tiles hidden)
    deck_path = Path(__file__).with_name("deck.json")
    tiles = json.loads(deck_path.read_text(encoding="utf-8")).get("tiles") if deck_path.is_file() else []
    tiles = [t for t in tiles if t.get("live", True)] + [
        {"id": "knows", "label": "WHAT NOVA KNOWS", "panel": 9, "neon": "neonCyan"},
        {"id": "proposals", "label": "PROPOSALS", "panel": 10, "neon": "neonGreen"}]
    buttons = []
    for t in tiles:
        b_ = QPushButton(t.get("label") or t.get("id"))
        b_.setObjectName(t.get("neon") or "neonCyan")
        b_.setToolTip(t.get("why") or "")
        pnl = t.get("panel")
        b_.clicked.connect(lambda _=False, p=pnl: (stack.setCurrentIndex(int(p)) if p is not None else None, refresh_panel()))
        dlay.addWidget(b_)
        buttons.append(b_)
    dlay.addStretch()
    dlay.addWidget(status)

    # ---------------- helpers
    def confirm(title: str, text: str) -> bool:
        if ui.get("auto_confirm") is not None:  # tests
            return bool(ui["auto_confirm"])
        return QMessageBox.question(win, title, text, QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes

    def op(verb: str, args: dict, label: str) -> None:
        if not confirm("Send to daemon", f"{label}\n\nThe daemon runs it on its next tick. Continue?"):
            return
        r = cmdinbox.operator_command(verb, args, by="gui")
        say_status(f"{verb} {'queued' if r.get('ok') else r.get('error')}")
        refresh_panel()

    def _sel_id(lst: QListWidget):
        it = lst.currentItem()
        try:
            return int(it.text().split()[0]) if it else None
        except ValueError:
            return None

    def _sel_job():
        r = job_table.currentRow()
        it = job_table.item(r, 0) if r >= 0 else None
        return int(it.text()) if it else None

    btn_pause.clicked.connect(lambda: (_sel_job() is not None) and op("job.pause", {"id": _sel_job()}, f"Pause job {_sel_job()}"))
    btn_resume.clicked.connect(lambda: (_sel_job() is not None) and op("job.resume", {"id": _sel_job()}, f"Resume job {_sel_job()}"))
    btn_run.clicked.connect(lambda: (_sel_job() is not None) and op("job.run_now", {"id": _sel_job()}, f"Run job {_sel_job()} now"))
    btn_url.clicked.connect(lambda: url_in.text().strip().startswith("http") and (op("url.enqueue", {"url": url_in.text().strip()}, "Queue URL " + url_in.text().strip()[:60]), url_in.clear()))
    btn_url_ok.clicked.connect(lambda: _sel_id(url_list) is not None and op("url.approve", {"id": _sel_id(url_list)}, f"Approve URL {_sel_id(url_list)}"))
    btn_url_no.clicked.connect(lambda: _sel_id(url_list) is not None and op("url.deny", {"id": _sel_id(url_list)}, f"Deny URL {_sel_id(url_list)}"))
    btn_rep_ok.clicked.connect(lambda: _sel_id(rep_list) is not None and op("report.approve", {"id": _sel_id(rep_list)}, f"Approve report {_sel_id(rep_list)}"))
    btn_rep_close.clicked.connect(lambda: _sel_id(rep_list) is not None and op("report.close", {"id": _sel_id(rep_list)}, f"Close report {_sel_id(rep_list)}"))
    btn_rep_all.clicked.connect(lambda: op("reports.approve_all", {}, "Approve ALL open reports"))
    btn_clear.clicked.connect(lambda: op("ingest.clear_standing", {}, "Clear standing ingest (DB backup first; facts kept)"))
    btn_mail.clicked.connect(lambda: op("mail.deliver", {"n": 3}, "Deliver 3 packets"))

    def _prop_id():
        it = prop_list.currentItem()
        return it.text().split()[0] if it else None

    btn_p_ok.clicked.connect(lambda: _prop_id() and (cmdinbox.approve(_prop_id(), by="gui"), refresh_panel()))
    btn_p_no.clicked.connect(lambda: _prop_id() and (cmdinbox.deny(_prop_id(), by="gui"), refresh_panel()))

    def show_media(item=None) -> None:
        """2.1: defined. JPG -> preview; WAV -> path shown (no playback from the console)."""
        item = item or media_list.currentItem()
        if item is None:
            return
        p = Path(item.text())
        if p.suffix.lower() in (".jpg", ".jpeg", ".png") and p.is_file():
            pix.setPixmap(QPixmap(str(p)).scaledToWidth(480))
            say_status("still " + p.name)
        else:
            pix.setText("audio: " + p.name)
            say_status("audio " + p.name)

    media_list.itemClicked.connect(show_media)
    btn_rescan.clicked.connect(lambda: (ro.media(force=True), refresh_panel()))

    def show_table(_=None) -> None:
        cols, rows = ro.table(table_box.currentText().strip(), palace_search.text().strip())
        palace_table.setSortingEnabled(False)
        palace_table.clear()
        palace_table.setColumnCount(len(cols)); palace_table.setHorizontalHeaderLabels(cols)
        palace_table.setRowCount(len(rows))
        for i, vals in enumerate(rows):
            for j, v in enumerate(vals):
                palace_table.setItem(i, j, QTableWidgetItem(v[:240]))
        palace_table.setSortingEnabled(True)

    table_box.currentTextChanged.connect(show_table)
    palace_search.textChanged.connect(show_table)

    def render_knows() -> None:
        know_box.setPlainText(masks.context_blocks(2))
        last_box.setPlainText(ui["last_prompt"] or "(no chat yet)")

    btn_know.clicked.connect(render_knows)

    # ---------------- refresh: health every 5 s; only the visible panel
    def refresh_health() -> None:
        h = ro.health()
        oll = h.get("ollama")
        oll_s = "unknown" if oll is None else (", ".join(f"{m['name']} {m['size'] / 1e9:.1f}GB" for m in oll) or "none loaded")
        health.setText(f"daemon {h['daemon']} | TTS :8000 {'UP' if h['tts'] else 'DOWN'} | Ollama {oll_s} | "
                       f"thermal {h['thermal']} | queue {h['queue_pending']} | reports open {h['reports_open']} | "
                       f"packets fail {h['packets_fail']} | bites {h['bites_played']} played / {h['bites_expired']} expired | "
                       f"errors 1h {h['errors_1h']} | proposals {len(cmdinbox.listing('proposed'))}")
        ui["health"] = h

    def refresh_panel() -> None:
        i = stack.currentIndex()
        if i == 1:
            bite_list.clear(); bite_list.addItems([f"{b['id']} {b.get('status')} {b.get('worker')} {str(b.get('line'))[:40]}" for b in ro.bites()])
        elif i == 2:
            staff_list.clear(); staff_list.addItems([f"{e['id']:18} v={e.get('voice')} jobs={e.get('jobs_run')}" for e in ro.staff()])
        elif i == 3:
            rows = ro.jobs()
            cols = ["id", "name", "cadence_s", "priority", "gpu", "enabled", "last_run", "next_run", "fails", "last_error"]
            job_table.setColumnCount(len(cols)); job_table.setHorizontalHeaderLabels(cols); job_table.setRowCount(len(rows))
            for r_, j in enumerate(rows):
                for c_, k in enumerate(cols):
                    job_table.setItem(r_, c_, QTableWidgetItem(str(j.get(k))))
            url_list.clear(); url_list.addItems([f"{q['id']} {q['status']} {q['description'][:60]}" for q in ro.urls()])
        elif i == 4:
            rep_list.clear(); rep_list.addItems([f"{r['id']} r{r['rank']} {r['title'][:80]}" for r in ro.reports()])
        elif i == 5:
            mail_list.clear(); mail_list.addItems([f"{p['id']} {p['status']} ->{p['dest']} {p.get('kind')}" for p in ro.packets()])
        elif i == 6 and table_box.count() == 0:
            table_box.addItems(ro.tables())
        elif i == 7:
            media_list.clear(); media_list.addItems([str(p) for p in ro.media()])
        elif i == 8:
            spawn_list.clear()
            try:
                from nova.spawnutil import list_spawns
                spawn_list.addItems([f"{s.get('name')} pid={s.get('pid')} {'ALIVE' if s.get('alive') else 'dead'}" for s in list_spawns()])
            except Exception as exc:
                spawn_list.addItem(str(exc))
        elif i == 9:
            render_knows()
        elif i == 10:
            prop_list.clear(); prop_list.addItems([f"{r['id']} {r['verb']} {r['args']} from={r['source']} {r.get('why', '')[:60]}" for r in cmdinbox.listing("proposed")])

    ui.update(win=win, app=app, health=None, health_label=health, status=status, chat_in=chat_in, chat_log=chat_log,
              btn_send=btn_send, btn_cancel=btn_cancel, quick=quick, model_box=model_box, stack=stack, buttons=buttons,
              media_list=media_list, pix=pix, show_media=show_media, refresh_panel=refresh_panel,
              refresh_health=refresh_health, say_status=say_status, know_box=know_box, render_knows=render_knows,
              op=op, prop_list=prop_list, job_table=job_table, rep_list=rep_list, send=send, run_slash=run_slash)

    deck_scroll = QScrollArea(); deck_scroll.setWidgetResizable(True); deck_scroll.setWidget(deck)
    deck_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff); deck_scroll.setFrameShape(QFrame.NoFrame)
    deck_scroll.setMaximumWidth(340); deck_scroll.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
    mainlay.addWidget(deck_scroll)
    mainlay.addWidget(stack, stretch=1)
    win.setCentralWidget(root)
    win.resize(1300, 720)
    if qss.is_file():
        app.setStyleSheet(qss.read_text(encoding="utf-8"))  # once
    refresh_health()
    refresh_panel()
    if start_timers:
        t = QTimer(win); t.timeout.connect(refresh_health); t.start(5000)
        ui["timer"] = t
    return win, ui


def main() -> None:
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print("PySide6 missing. pip install PySide6\nTUI: python -m nova.tui")
        return
    app = QApplication.instance() or QApplication(sys.argv)
    win, _ui = build(app)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
