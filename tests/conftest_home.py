"""Shared temp-home helpers for 2.1 tests. Every test runs on a throwaway NOVA_HOME.
NOVA_SCRATCH_DB (optional) = path to the read-only scratch copy of NOVA.db; it is COPIED, never opened rw."""
import hashlib, os, shutil, sqlite3, tempfile
from pathlib import Path


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


class Home:
    def __init__(self, from_scratch: bool = False):
        self.d = Path(tempfile.mkdtemp(prefix="nova21_"))
        (self.d / "data" / "config").mkdir(parents=True)
        self.old = os.environ.get("NOVA_HOME")
        os.environ["NOVA_HOME"] = str(self.d)
        src = os.environ.get("NOVA_SCRATCH_DB")
        self.scratch = bool(from_scratch and src and Path(src).is_file())
        if self.scratch:
            s = sqlite3.connect(Path(src).resolve().as_uri() + "?mode=ro", uri=True)
            t = sqlite3.connect(self.d / "data" / "NOVA.db")
            s.backup(t); t.close(); s.close()
        else:
            from nova import db, office, bites
            db.connect().close(); office._ensure(); bites._ensure()

    def db(self) -> Path:
        return self.d / "data" / "NOVA.db"

    def rw(self) -> sqlite3.Connection:
        c = sqlite3.connect(self.db()); c.row_factory = sqlite3.Row
        return c

    def close(self):
        if self.old is None:
            os.environ.pop("NOVA_HOME", None)
        else:
            os.environ["NOVA_HOME"] = self.old
