"""PySide6 cosmic console. Client of NOVA.db. Does not own the scheduler."""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    try:
        from PySide6.QtCore import Qt, QTimer
        from PySide6.QtGui import QPixmap
        from PySide6.QtWidgets import (
            QApplication,
            QComboBox,
            QFrame,
            QHBoxLayout,
            QHeaderView,
            QLabel,
            QLineEdit,
            QListWidget,
            QMainWindow,
            QMessageBox,
            QPushButton,
            QScrollArea,
            QSizePolicy,
            QStackedWidget,
            QTableWidget,
            QTableWidgetItem,
            QTextEdit,
            QVBoxLayout,
            QWidget,
        )
    except ImportError:
        print("PySide6 missing. pip install PySide6")
        print("TUI: python -m nova.tui")
        return

    from nova import bites, db, office, ollama_talk, senses
    from nova.tui import term
    from nova.tui.term import ask, handle, state as tstate

    app = QApplication(sys.argv)
    # Pocket TTS gate: must be :8000 (manual). Offer to start parallel serve window if down.
    # NOVA daemon is separate (python -m nova / START_NOVA) and is not stopped here.
    try:
        from nova import pocket as pocket_mod
        if not pocket_mod.serve_up():
            ans = QMessageBox.question(
                None,
                "Pocket TTS",
                "Pocket TTS is not running on http://127.0.0.1:8000.\n\n"
                "Should it be activated?\n\n"
                "Yes = open a parallel serve window (:8000)\n"
                "No = stay off (NOVA stays quiet)",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if ans == QMessageBox.Yes:
                rec = pocket_mod.start_serve_window()
                QMessageBox.information(
                    None,
                    "Pocket TTS",
                    f"Serve start requested on :8000.\n{rec}\n\n"
                    "Daemon (if started via START_NOVA / nova.launch) keeps running in the background.",
                )
    except Exception as _tts_exc:
        print("tts check:", _tts_exc)

    qss = Path(__file__).with_name("console.qss")
    if qss.is_file():
        app.setStyleSheet(qss.read_text(encoding="utf-8"))

    win = QMainWindow()
    win.setWindowTitle("NOVA 1.7 — COSMIC CONSOLE")
    root = QWidget()
    mainlay = QHBoxLayout(root)

    deck = QWidget()
    deck.setObjectName("CommandDeck")
    deck.setMinimumWidth(200)
    deck.setMaximumWidth(320)
    deck.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
    dlay = QVBoxLayout(deck)
    dlay.addWidget(QLabel("COMMAND DECK"))
    import json

    deck_path = Path(__file__).with_name("deck.json")
    tiles = json.loads(deck_path.read_text(encoding="utf-8")).get("tiles") if deck_path.is_file() else []
    buttons = []
    brand = Path(__file__).resolve().parents[2] / "ascii" / "brand" / "banner.jpg"
    if brand.is_file():
        banner = QLabel()
        banner.setPixmap(QPixmap(str(brand)).scaled(220, 120))
        dlay.addWidget(banner)
    btn_play = QPushButton("Play next bite")
    btn_tick = QPushButton("Tick jobs now")
    status = QLabel("offline private")

    stack = QStackedWidget()

    chat_w = QWidget()
    cl = QVBoxLayout(chat_w)
    chat_log = QTextEdit()
    chat_log.setReadOnly(True)
    chat_in = QLineEdit()
    chat_in.setPlaceholderText("ask the palace...")
    cl.addWidget(QLabel("ASTROCOMMS"))
    model_box = QComboBox()
    try:
        tags = ollama_talk.tags() or []
    except Exception:
        tags = []
    if not tags:
        tags = ["llama3-groq-tool-use:8b", "qwen3:8b", "moondream"]
    for t in tags:
        model_box.addItem(t)
    prefer = "llama3-groq-tool-use:8b"
    if prefer in tags:
        model_box.setCurrentText(prefer)
    tstate["model"] = model_box.currentText()
    cl.addWidget(model_box)
    cl.addWidget(chat_log)
    cl.addWidget(chat_in)

    def pick_model(_=None):
        tstate["model"] = model_box.currentText()

    model_box.currentTextChanged.connect(pick_model)

    def send():
        text = chat_in.text().strip()
        if not text:
            return
        chat_in.clear()
        tstate["model"] = model_box.currentText()
        chat_log.append("YOU: " + text)
        try:
            if text.startswith("/"):
                handle(text)
                reply = "\n".join(tstate.get("hist", [])[-2:])
            else:
                reply = ask(text)
        except Exception as exc:
            reply = str(exc)
        chat_log.append("NOVA: " + reply)

    chat_in.returnPressed.connect(send)

    sonic = QWidget()
    sl = QVBoxLayout(sonic)
    sl.addWidget(QLabel("SONIC ARCHIVE"))
    bite_list = QListWidget()
    sl.addWidget(bite_list)

    core = QWidget()
    ol = QVBoxLayout(core)
    ol.addWidget(QLabel("AI CORE MATRIX (masks, not jackets)"))
    staff_list = QListWidget()
    ol.addWidget(staff_list)

    ops = QWidget()
    opl = QVBoxLayout(ops)
    opl.addWidget(QLabel("SYSTEM OPS"))
    job_list = QListWidget()
    url_in = QLineEdit()
    url_in.setPlaceholderText("https://  drop a link")
    btn_url = QPushButton("queue URL")
    opl.addWidget(job_list)
    opl.addWidget(url_in)
    opl.addWidget(btn_url)

    rec = QWidget()
    rl = QVBoxLayout(rec)
    rl.addWidget(QLabel("MISSION RECORDS"))
    rec_box = QTextEdit()
    rec_box.setReadOnly(True)
    rl.addWidget(rec_box)

    mail_w = QWidget()
    ml = QVBoxLayout(mail_w)
    ml.addWidget(QLabel("MAIL ROOM"))
    mail_list = QListWidget()
    btn_mail = QPushButton("Deliver 3")
    ml.addWidget(mail_list)
    ml.addWidget(btn_mail)

    palace_w = QWidget()
    pl = QVBoxLayout(palace_w)
    pl.addWidget(QLabel("PALACE"))
    table_box = QComboBox()
    palace_search = QLineEdit()
    palace_search.setPlaceholderText("filter rows...")
    palace_table = QTableWidget()
    palace_table.setSortingEnabled(True)
    palace_table.setAlternatingRowColors(True)
    palace_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
    palace_table.horizontalHeader().setStretchLastSection(True)
    pl.addWidget(table_box)
    pl.addWidget(palace_search)
    pl.addWidget(palace_table)

    view_w = QWidget()
    vl = QVBoxLayout(view_w)
    vl.addWidget(QLabel("VIEWPORT"))
    media_list = QListWidget()
    pix = QLabel("select a still")
    pix.setMinimumHeight(220)
    btn_cam = QPushButton("cam0 + moondream")
    vl.addWidget(media_list)
    vl.addWidget(pix)
    vl.addWidget(btn_cam)

    spawn_w = QWidget()
    spl = QVBoxLayout(spawn_w)
    spl.addWidget(QLabel("SPAWN STATUS"))
    spawn_list = QListWidget()
    spl.addWidget(spawn_list)

    for w in (chat_w, sonic, core, ops, rec, mail_w, palace_w, view_w, spawn_w):
        stack.addWidget(w)
    def go_panel(idx: int, note: str = "") -> None:
        if 0 <= idx < stack.count():
            stack.setCurrentIndex(idx)
        if note:
            status.setText(note[:64])

    def on_tile(tid: str, panel, why: str) -> None:
        tid = (tid or "").lower()
        # Always jump to mapped panel when present
        if panel is not None:
            go_panel(int(panel))
        # Special live actions (100% wired — status + focus, no silent no-ops)
        if tid == "whatsapp":
            status.setText("WHATSAPP: use chat /wa link | /wa status | /wa send approve")
            chat_in.setPlaceholderText("/wa status   or   /wa link")
            go_panel(0, "WHATSAPP → ASTROCOMMS")
        elif tid == "claw":
            status.setText("OPENCLAW: mail openclaw@local — leash, not swallow")
            go_panel(5, "OPENCLAW → MAIL")
        elif tid == "qwen":
            status.setText("QWEN: mail qwen@local coder handoffs")
            go_panel(5, "QWEN → MAIL")
        elif tid == "breaks":
            status.setText("BREAKS: report cards / tool-break")
            go_panel(4, "BREAKS → RECORDS")
            refresh()
        elif tid == "brain":
            status.setText("BRAIN: staff / model seam (masks not jackets)")
            go_panel(2, "BRAIN → CORE")
        elif tid in {"ingest", "jobs", "webgate"}:
            status.setText(f"{tid.upper()}: SYSTEM OPS board/jobs")
            go_panel(3, f"{tid.upper()} → OPS")
        elif tid == "status":
            status.setText("STATUS: spawn registry")
            go_panel(8, "STATUS → SPAWN")
            refresh()
        elif tid == "palace":
            status.setText("PALACE: SQLite viewer")
            go_panel(6)
        elif why:
            status.setText((why or tid)[:64])

    for tile in tiles:
        b = QPushButton(tile.get("label") or tile.get("id"))
        b.setObjectName(tile.get("neon") or "neonCyan")
        b.setToolTip(tile.get("why") or "")
        live = bool(tile.get("live", True))
        b.setEnabled(live)
        if not live:
            b.setText((tile.get("label") or "DEAD") + "  ·")
        tid = tile.get("id") or ""
        panel = tile.get("panel")
        why = tile.get("why") or ""
        if live:
            b.clicked.connect(
                lambda _=False, i=tid, p=panel, w=why: on_tile(i, p, w)
            )
        dlay.addWidget(b)
        buttons.append(b)
    dlay.addWidget(QLabel("SOUND TRIGGERS"))
    dlay.addWidget(btn_play)
    dlay.addWidget(btn_tick)
    dlay.addStretch()
    dlay.addWidget(status)

    def refresh():
        try:
            office.ensure_workforce()
        except Exception:
            pass
        job_list.clear()
        try:
            for j in db.jobs():
                job_list.addItem(
                    f"{j['id']:3} {j['name']:22} {j['every_s']}s en={j['enabled']}"
                )
        except Exception as exc:
            job_list.addItem(str(exc))
        staff_list.clear()
        try:
            for e in office.staff():
                staff_list.addItem(
                    f"{e['id']:18} v={e.get('voice')} jobs={e.get('jobs_run')}"
                )
        except Exception:
            pass
        bite_list.clear()
        try:
            for b in bites.queued(16):
                bite_list.addItem(
                    f"{b['id']} {b['status']:7} {b['worker']} {b['line'][:40]}"
                )
        except Exception:
            pass
        try:
            lines = [
                f"r{r['rank']} {r['status']} {r['title']}"
                for r in office.reports(open_only=False)[:16]
            ]
            breaks = [ln for ln in lines if "tool break" in ln.lower() or "break" in ln.lower()]
            head = ("BREAKS\n" + "\n".join(breaks[:6]) + "\n\n") if breaks else ""
            rec_box.setPlainText(head + "\n".join(lines) or "no records")
        except Exception as exc:
            rec_box.setPlainText(str(exc))
        try:
            qrows = db.queue_rows()
            for q in qrows[:8]:
                job_list.addItem(f"Q {q['id']} {q['status']} {q['description'][:40]}")
        except Exception:
            pass
        mail_list.clear()
        try:
            for p in office.inbox("queued", 16) + office.inbox("delivered", 8):
                mail_list.addItem(f"{p['id']} {p['status']} ->{p['dest']} {str(p.get('kind'))}")
        except Exception:
            pass
        if table_box.count() == 0:
            try:
                con = db.connect()
                tabs = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
                con.close()
                table_box.addItems(tabs)
            except Exception:
                pass
        spawn_list.clear()
        try:
            from nova.spawnutil import list_spawns

            for s in list_spawns():
                flag = "ALIVE" if s.get("alive") else "dead"
                spawn_list.addItem(f"{s.get('name')} pid={s.get('pid')} {flag}")
        except Exception as exc:
            spawn_list.addItem(str(exc))
        media_list.clear()
        try:
            art_dir = db.home() / "data" / "artifacts"
            for pth in list(art_dir.rglob("*.jpg"))[-12:] + list(art_dir.rglob("*.wav"))[-8:]:
                media_list.addItem(str(pth))
        except Exception:
            pass

    def play():
        res = bites.play_next()
        status.setText(str(res.get("tts") or res)[:48])
        refresh()

    def tick_now():
        from nova import sched

        ran = sched.tick()
        status.setText(f"tick {len(ran)}")
        refresh()

    btn_play.clicked.connect(play)
    btn_tick.clicked.connect(tick_now)

    def deliver():
        res = office.deliver_inbox(3)
        status.setText(f"mail {len(res)}")
        refresh()

    def show_table(_=None):
        name = table_box.currentText().strip()
        if not name or not name.replace("_", "").isalnum():
            return
        needle = palace_search.text().strip().lower()
        con = db.connect()
        try:
            cols = [c[1] for c in con.execute(f"PRAGMA table_info([{name}])").fetchall()]
            rows = con.execute(f"SELECT * FROM [{name}] ORDER BY 1 DESC LIMIT 200").fetchall()
            palace_table.setSortingEnabled(False)
            palace_table.clear()
            palace_table.setColumnCount(len(cols))
            palace_table.setHorizontalHeaderLabels(cols)
            kept = []
            for r in rows:
                vals = [str(r[c] if hasattr(r, "keys") else r[i]) for i, c in enumerate(cols)]
                if needle and needle not in " ".join(vals).lower():
                    continue
                kept.append(vals)
            palace_table.setRowCount(len(kept))
            for i, vals in enumerate(kept):
                for j, v in enumerate(vals):
                    palace_table.setItem(i, j, QTableWidgetItem(v[:240]))
            palace_table.setSortingEnabled(True)
            status.setText(f"palace {name} rows={len(kept)}")
        except Exception as exc:
            palace_table.setRowCount(0)
            palace_table.setColumnCount(1)
            palace_table.setHorizontalHeaderLabels(["error"])
            palace_table.setRowCount(1)
            palace_table.setItem(0, 0, QTableWidgetItem(str(exc)))
        finally:
            con.close()

    def show_media():
        item = media_list.currentItem()
        if not item:
            return
        path = Path(item.text())
        if path.suffix.lower() in {".jpg", ".jpeg", ".png"}:
            pix.setPixmap(QPixmap(str(path)).scaled(480, 280))
        elif path.suffix.lower() == ".wav":
            from nova import pocket

            pocket._play(path)
            pix.setText(path.name)

    def cam_see():
        res = senses.save_still(0)
        path = res.get("path")
        tags = senses.vision_tags()
        extra = {}
        if path and tags:
            extra = senses.describe(path, "moondream" if any("moondream" in t for t in tags) else tags[0])
        status.setText(str(extra.get("text") or res)[:48])
        refresh()

    btn_mail.clicked.connect(deliver)
    table_box.currentTextChanged.connect(show_table)
    palace_search.textChanged.connect(show_table)
    media_list.itemClicked.connect(lambda *_: show_media())
    btn_cam.clicked.connect(cam_see)

    def add_url():
        from nova import board

        u = url_in.text().strip()
        try:
            board.enqueue_url(u)
            url_in.clear()
            status.setText("queued " + u[:32])
        except Exception as exc:
            status.setText(str(exc))
        refresh()

    btn_url.clicked.connect(add_url)

    timer = QTimer()
    timer.timeout.connect(refresh)
    timer.start(4000)
    refresh()

    deck_scroll = QScrollArea()
    deck_scroll.setObjectName("CommandDeckScroll")
    deck_scroll.setWidgetResizable(True)
    deck_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    deck_scroll.setFrameShape(QFrame.NoFrame)
    deck_scroll.setWidget(deck)
    deck_scroll.setMinimumWidth(200)
    deck_scroll.setMaximumWidth(340)
    deck_scroll.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

    # Re-home stack panels into scroll areas (keeps deck panel indices stable)
    panels = [stack.widget(i) for i in range(stack.count())]
    while stack.count():
        stack.removeWidget(stack.widget(0))
    for panel in panels:
        wrap = QScrollArea()
        wrap.setWidgetResizable(True)
        wrap.setFrameShape(QFrame.NoFrame)
        wrap.setWidget(panel)
        stack.addWidget(wrap)

    mainlay.addWidget(deck_scroll)
    mainlay.addWidget(stack, stretch=1)
    win.setCentralWidget(root)
    win.setMinimumSize(800, 480)
    win.resize(1100, 640)
    if qss.is_file():
        app.setStyleSheet(qss.read_text(encoding="utf-8"))
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
