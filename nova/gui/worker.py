"""Chat worker for the 2.1 GUI: runs nova.chat.ask off the UI thread, streams tokens, cancellable."""
from __future__ import annotations

import threading

from PySide6.QtCore import QThread, Signal


class ChatWorker(QThread):
    token = Signal(str)
    finished_reply = Signal(dict)

    def __init__(self, text: str, model: str, parent=None):
        super().__init__(parent)
        self.text, self.model = text, model
        self.cancel_event = threading.Event()

    def cancel(self) -> None:
        self.cancel_event.set()

    def run(self) -> None:
        from nova import chat
        try:
            r = chat.ask(self.text, model=self.model, on_token=self.token.emit, cancel=self.cancel_event,
                         stream=True, propose=True)
        except Exception as exc:  # never crash the UI thread
            r = {"visible": f"[chat error] {exc}", "spoken": [], "notes": ["error"]}
        self.finished_reply.emit(r)
