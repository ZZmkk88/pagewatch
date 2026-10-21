"""pagewatch — 网页变化监测（静态文本快照 + 逐行对比 + 站内提醒）

单文件 FastAPI + SQLite 应用。只抓静态 HTML 并抽取可见文本，
不做浏览器渲染；调度为进程内线程，按每个监测项自己的间隔执行。
"""

import difflib
import hashlib
import os
import re
import secrets
import sqlite3
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get(
    "PAGEWATCH_DB_PATH", os.path.join(BASE_DIR, "data", "pagewatch.db")
)
STATIC_DIR = os.path.join(BASE_DIR, "static")

FETCH_TIMEOUT = 15  # 秒
FETCH_MAX_BYTES = 2_000_000  # 单页最多读 2MB
SNAPSHOT_KEEP = 20  # 每个监测项最多保留的快照数
SCHEDULER_TICK = 10  # 调度线程醒来间隔（秒）

DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin123"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.isoformat()


# ---------------------------------------------------------------- 数据库


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), 120_000
    )
    return f"{salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, _ = stored.split("$", 1)
    except ValueError:
        return False
    return secrets.compare_digest(hash_password(password, salt), stored)


def init_db() -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with get_db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                must_change_password INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS tokens (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                expires_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS watches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                url TEXT NOT NULL,
                interval_minutes INTEGER NOT NULL DEFAULT 60,
                paused INTEGER NOT NULL DEFAULT 0,
                last_checked_at TEXT,
                last_status TEXT NOT NULL DEFAULT '',
                last_error TEXT NOT NULL DEFAULT '',
                has_unread_change INTEGER NOT NULL DEFAULT 0,
                last_changed_at TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                watch_id INTEGER NOT NULL REFERENCES watches(id) ON DELETE CASCADE,
                created_at TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                text TEXT NOT NULL,
                is_change INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                watch_id INTEGER NOT NULL REFERENCES watches(id) ON DELETE CASCADE,
                snapshot_id INTEGER,
                created_at TEXT NOT NULL,
                summary TEXT NOT NULL,
                is_read INTEGER NOT NULL DEFAULT 0
            );
            """
        )
        row = conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()
        if row["n"] == 0:
            conn.execute(
                "INSERT INTO users (username, password_hash, must_change_password)"
                " VALUES (?, ?, 1)",
                (DEFAULT_USERNAME, hash_password(DEFAULT_PASSWORD)),
            )


# ---------------------------------------------------------------- 文本抽取


_SKIP_TAGS = {"script", "style", "noscript", "template", "svg", "iframe"}
_BLOCK_TAGS = {
    "address", "article", "aside", "blockquote", "br", "dd", "div", "dl",
    "dt", "fieldset", "figcaption", "figure", "footer", "form", "h1", "h2",
    "h3", "h4", "h5", "h6", "header", "hr", "li", "main", "nav", "ol",
    "p", "pre", "section", "table", "td", "th", "tr", "ul",
}


class _TextExtractor(HTMLParser):
    """把 HTML 抽成按行组织的可见文本：块级元素断行，行内空白折叠。"""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._buf: list[str] = []
        self.lines: list[str] = []

    def _flush(self) -> None:
        text = re.sub(r"\s+", " ", "".join(self._buf)).strip()
        self._buf = []
        if text:
            self.lines.append(text)

    def handle_starttag(self, tag, attrs):
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
        if tag in _BLOCK_TAGS:
            self._flush()

    def handle_endtag(self, tag):
        if tag in _SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1
        if tag in _BLOCK_TAGS:
            self._flush()

    def handle_data(self, data):
        if self._skip_depth == 0:
            self._buf.append(data)

    def get_text(self) -> str:
        self._flush()
        return "\n".join(self.lines)


def extract_text(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    parser.close()
    return parser.get_text()


# ---------------------------------------------------------------- 抓取


class FetchError(Exception):
    pass


def fetch_url(url: str, timeout: int = FETCH_TIMEOUT,
              max_bytes: int = FETCH_MAX_BYTES) -> tuple[int, str]:
    """抓一个页面，返回 (HTTP 状态码, HTML 文本)。失败抛 FetchError。"""
    req = Request(url, headers={"User-Agent": "pagewatch/1.0 (text monitor)"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            status = resp.status
            chunks = []
            read = 0
            while read <= max_bytes:
                chunk = resp.read(min(65536, max_bytes + 1 - read))
                if not chunk:
                    break
                chunks.append(chunk)
                read += len(chunk)
            raw = b"".join(chunks)
            charset = resp.headers.get_content_charset() or "utf-8"
    except HTTPError as e:
        raise FetchError(f"HTTP {e.code}") from e
    except (URLError, TimeoutError, OSError) as e:
        raise FetchError(f"抓取失败：{e}") from e
    if status >= 400:
        raise FetchError(f"HTTP {status}")
    try:
        return status, raw.decode(charset, errors="replace")
    except (LookupError, UnicodeDecodeError):
        return status, raw.decode("utf-8", errors="replace")


# ---------------------------------------------------------------- diff


def compute_diff(old_text: str, new_text: str) -> dict:
    """逐行对比，返回渲染用的行列表与增删计数。"""
    old_lines = old_text.split("\n") if old_text else []
    new_lines = new_text.split("\n") if new_text else []
    rows = []
    added = removed = 0
    matcher = difflib.SequenceMatcher(a=old_lines, b=new_lines, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for line in old_lines[i1:i2]:
                rows.append({"type": "same", "text": line})
        if tag in ("delete", "replace"):
            for line in old_lines[i1:i2]:
                rows.append({"type": "del", "text": line})
                removed += 1
        if tag in ("insert", "replace"):
            for line in new_lines[j1:j2]:
                rows.append({"type": "add", "text": line})
                added += 1
    return {"rows": rows, "added": added, "removed": removed,
            "changed": added > 0 or removed > 0}


# ---------------------------------------------------------------- 检查逻辑


def run_check(watch_id: int, fetcher=None) -> dict:
    """对一个监测项执行一次检查：抓取→存快照→判变→（变了）发提醒。"""
    fetcher = fetcher or fetch_url
    with get_db() as conn:
        watch = conn.execute(
            "SELECT * FROM watches WHERE id = ?", (watch_id,)
        ).fetchone()
        if watch is None:
            return {"status": "missing"}
        now = iso(utcnow())
        try:
            _status, html = fetcher(watch["url"])
            text = extract_text(html)
        except Exception as e:  # 抓取失败只记录状态，绝不拖垮调度
            message = str(e)[:300] or e.__class__.__name__
            conn.execute(
                "UPDATE watches SET last_checked_at = ?, last_status = 'error',"
                " last_error = ? WHERE id = ?",
                (now, message, watch_id),
            )
            return {"status": "error", "error": message}

        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        prev = conn.execute(
            "SELECT * FROM snapshots WHERE watch_id = ? ORDER BY id DESC LIMIT 1",
            (watch_id,),
        ).fetchone()
        is_change = 1 if (prev is not None and prev["content_hash"] != digest) else 0
        cur = conn.execute(
            "INSERT INTO snapshots (watch_id, created_at, content_hash, text,"
            " is_change) VALUES (?, ?, ?, ?, ?)",
            (watch_id, now, digest, text, is_change),
        )
        snapshot_id = cur.lastrowid
        # 只保留最近 SNAPSHOT_KEEP 份
        conn.execute(
            "DELETE FROM snapshots WHERE watch_id = ? AND id NOT IN"
            " (SELECT id FROM snapshots WHERE watch_id = ?"
            "  ORDER BY id DESC LIMIT ?)",
            (watch_id, watch_id, SNAPSHOT_KEEP),
        )
        conn.execute(
            "UPDATE watches SET last_checked_at = ?, last_status = 'ok',"
            " last_error = '' WHERE id = ?",
            (now, watch_id),
        )
        if is_change:
            diff = compute_diff(prev["text"], text)
            summary = f"新增 {diff['added']} 行，删除 {diff['removed']} 行"
            conn.execute(
                "INSERT INTO notifications (watch_id, snapshot_id, created_at,"
                " summary) VALUES (?, ?, ?, ?)",
                (watch_id, snapshot_id, now, summary),
            )
            conn.execute(
                "UPDATE watches SET has_unread_change = 1, last_changed_at = ?"
                " WHERE id = ?",
                (now, watch_id),
            )
        return {"status": "ok", "is_change": bool(is_change),
                "snapshot_id": snapshot_id}


# ---------------------------------------------------------------- 调度线程


_scheduler_stop = threading.Event()


def _scheduler_loop() -> None:
    while not _scheduler_stop.wait(SCHEDULER_TICK):
        try:
            now = utcnow()
            with get_db() as conn:
                rows = conn.execute(
                    "SELECT id, interval_minutes, last_checked_at FROM watches"
                    " WHERE paused = 0"
                ).fetchall()
            for row in rows:
                due = True
                if row["last_checked_at"]:
                    last = datetime.fromisoformat(row["last_checked_at"])
                    due = last + timedelta(minutes=row["interval_minutes"]) <= now
                if due:
                    try:
                        run_check(row["id"])
                    except Exception:
                        pass  # 单个监测项出问题不许影响其他监测项
        except Exception:
            pass  # 调度线程自身兜底，下一轮继续


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    thread = None
    if os.environ.get("PAGEWATCH_DISABLE_SCHEDULER") != "1":
        _scheduler_stop.clear()
        thread = threading.Thread(target=_scheduler_loop, daemon=True)
        thread.start()
    yield
    _scheduler_stop.set()


app = FastAPI(title="pagewatch", lifespan=lifespan)


# ---------------------------------------------------------------- 鉴权


class LoginIn(BaseModel):
    username: str
    password: str


class ChangePasswordIn(BaseModel):
    old_password: str
    new_password: str


def current_user(authorization: str | None = Header(default=None)) -> sqlite3.Row:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")
    token = authorization[len("Bearer "):]
    with get_db() as conn:
        row = conn.execute(
            "SELECT u.* FROM tokens t JOIN users u ON u.id = t.user_id"
            " WHERE t.token = ? AND t.expires_at > ?",
            (token, iso(utcnow())),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    return row


@app.get("/api/health")
def health():
    return {"status": "ok", "app": "pagewatch"}


@app.post("/api/login")
def login(body: LoginIn):
    with get_db() as conn:
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?", (body.username,)
        ).fetchone()
        if user is None or not verify_password(body.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="用户名或密码不正确")
        token = secrets.token_urlsafe(32)
        conn.execute(
            "INSERT INTO tokens (token, user_id, expires_at) VALUES (?, ?, ?)",
            (token, user["id"], iso(utcnow() + timedelta(hours=24))),
        )
    return {"token": token,
            "must_change_password": bool(user["must_change_password"])}


@app.get("/api/me")
def me(user: sqlite3.Row = Depends(current_user)):
    return {"username": user["username"],
            "must_change_password": bool(user["must_change_password"])}


@app.post("/api/change-password")
def change_password(body: ChangePasswordIn,
                    user: sqlite3.Row = Depends(current_user)):
    if len(body.new_password) < 6:
        raise HTTPException(status_code=400, detail="新密码至少 6 位")
    if not verify_password(body.old_password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="原密码不正确")
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET password_hash = ?, must_change_password = 0"
            " WHERE id = ?",
            (hash_password(body.new_password), user["id"]),
        )
    return {"ok": True}


# ---------------------------------------------------------------- 监测项


class WatchIn(BaseModel):
    name: str
    url: str
    interval_minutes: int = 60


def _validate_watch(body: WatchIn) -> tuple[str, str, int]:
    name = body.name.strip()
    if not name or len(name) > 100:
        raise HTTPException(status_code=400, detail="名称必填且不超过 100 字")
    url = body.url.strip()
    if len(url) > 2000 or not (url.startswith("http://") or url.startswith("https://")):
        raise HTTPException(status_code=400, detail="网址必须以 http:// 或 https:// 开头")
    if not (1 <= body.interval_minutes <= 10080):
        raise HTTPException(status_code=400, detail="检查间隔需在 1 到 10080 分钟之间")
    return name, url, body.interval_minutes


def _watch_out(row: sqlite3.Row) -> dict:
    data = dict(row)
    data["paused"] = bool(data["paused"])
    data["has_unread_change"] = bool(data["has_unread_change"])
    return data


def _get_watch_or_404(conn: sqlite3.Connection, watch_id: int) -> sqlite3.Row:
    row = conn.execute(
        "SELECT * FROM watches WHERE id = ?", (watch_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="监测项不存在")
    return row


@app.get("/api/watches")
def list_watches(user: sqlite3.Row = Depends(current_user)):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT w.*, (SELECT COUNT(*) FROM snapshots s"
            " WHERE s.watch_id = w.id) AS snapshot_count FROM watches w"
            " ORDER BY w.id"
        ).fetchall()
    return [_watch_out(r) for r in rows]


@app.post("/api/watches", status_code=201)
def create_watch(body: WatchIn, user: sqlite3.Row = Depends(current_user)):
    name, url, interval = _validate_watch(body)
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO watches (name, url, interval_minutes, created_at)"
            " VALUES (?, ?, ?, ?)",
            (name, url, interval, iso(utcnow())),
        )
        row = _get_watch_or_404(conn, cur.lastrowid)
    return _watch_out(row)


@app.put("/api/watches/{watch_id}")
def update_watch(watch_id: int, body: WatchIn,
                 user: sqlite3.Row = Depends(current_user)):
    name, url, interval = _validate_watch(body)
    with get_db() as conn:
        _get_watch_or_404(conn, watch_id)
        conn.execute(
            "UPDATE watches SET name = ?, url = ?, interval_minutes = ?"
            " WHERE id = ?",
            (name, url, interval, watch_id),
        )
        return _watch_out(_get_watch_or_404(conn, watch_id))


@app.delete("/api/watches/{watch_id}")
def delete_watch(watch_id: int, user: sqlite3.Row = Depends(current_user)):
    with get_db() as conn:
        _get_watch_or_404(conn, watch_id)
        conn.execute("DELETE FROM watches WHERE id = ?", (watch_id,))
    return {"ok": True}


@app.post("/api/watches/{watch_id}/pause")
def pause_watch(watch_id: int, user: sqlite3.Row = Depends(current_user)):
    with get_db() as conn:
        _get_watch_or_404(conn, watch_id)
        conn.execute("UPDATE watches SET paused = 1 WHERE id = ?", (watch_id,))
        return _watch_out(_get_watch_or_404(conn, watch_id))


@app.post("/api/watches/{watch_id}/resume")
def resume_watch(watch_id: int, user: sqlite3.Row = Depends(current_user)):
    with get_db() as conn:
        _get_watch_or_404(conn, watch_id)
        conn.execute("UPDATE watches SET paused = 0 WHERE id = ?", (watch_id,))
        return _watch_out(_get_watch_or_404(conn, watch_id))


@app.post("/api/watches/{watch_id}/check")
def check_watch(watch_id: int, user: sqlite3.Row = Depends(current_user)):
    with get_db() as conn:
        _get_watch_or_404(conn, watch_id)
    return run_check(watch_id)


@app.post("/api/watches/{watch_id}/seen")
def mark_watch_seen(watch_id: int, user: sqlite3.Row = Depends(current_user)):
    with get_db() as conn:
        _get_watch_or_404(conn, watch_id)
        conn.execute(
            "UPDATE watches SET has_unread_change = 0 WHERE id = ?", (watch_id,)
        )
        conn.execute(
            "UPDATE notifications SET is_read = 1 WHERE watch_id = ?",
            (watch_id,),
        )
    return {"ok": True}


# ---------------------------------------------------------------- 快照与 diff


@app.get("/api/watches/{watch_id}/snapshots")
def list_snapshots(watch_id: int, user: sqlite3.Row = Depends(current_user)):
    with get_db() as conn:
        _get_watch_or_404(conn, watch_id)
        rows = conn.execute(
            "SELECT id, watch_id, created_at, content_hash, is_change,"
            " length(text) AS text_len FROM snapshots WHERE watch_id = ?"
            " ORDER BY id DESC",
            (watch_id,),
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["is_change"] = bool(d["is_change"])
        out.append(d)
    return out


@app.get("/api/watches/{watch_id}/snapshots/{snapshot_id}")
def get_snapshot(watch_id: int, snapshot_id: int,
                 user: sqlite3.Row = Depends(current_user)):
    with get_db() as conn:
        _get_watch_or_404(conn, watch_id)
        row = conn.execute(
            "SELECT * FROM snapshots WHERE id = ? AND watch_id = ?",
            (snapshot_id, watch_id),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="快照不存在")
    data = dict(row)
    data["is_change"] = bool(data["is_change"])
    return data


@app.get("/api/watches/{watch_id}/diff/{snapshot_id}")
def get_diff(watch_id: int, snapshot_id: int,
             user: sqlite3.Row = Depends(current_user)):
    with get_db() as conn:
        _get_watch_or_404(conn, watch_id)
        row = conn.execute(
            "SELECT * FROM snapshots WHERE id = ? AND watch_id = ?",
            (snapshot_id, watch_id),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="快照不存在")
        prev = conn.execute(
            "SELECT * FROM snapshots WHERE watch_id = ? AND id < ?"
            " ORDER BY id DESC LIMIT 1",
            (watch_id, snapshot_id),
        ).fetchone()
    if prev is None:
        lines = row["text"].split("\n") if row["text"] else []
        return {"is_first": True, "previous_id": None,
                "rows": [{"type": "add", "text": line} for line in lines],
                "added": len(lines), "removed": 0, "changed": False}
    diff = compute_diff(prev["text"], row["text"])
    diff["is_first"] = False
    diff["previous_id"] = prev["id"]
    return diff


# ---------------------------------------------------------------- 提醒


@app.get("/api/notifications")
def list_notifications(user: sqlite3.Row = Depends(current_user)):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT n.*, w.name AS watch_name FROM notifications n"
            " JOIN watches w ON w.id = n.watch_id ORDER BY n.id DESC LIMIT 100"
        ).fetchall()
        unread = conn.execute(
            "SELECT COUNT(*) AS n FROM notifications WHERE is_read = 0"
        ).fetchone()["n"]
    out = []
    for r in rows:
        d = dict(r)
        d["is_read"] = bool(d["is_read"])
        out.append(d)
    return {"items": out, "unread": unread}


@app.post("/api/notifications/{notification_id}/read")
def read_notification(notification_id: int,
                      user: sqlite3.Row = Depends(current_user)):
    with get_db() as conn:
        cur = conn.execute(
            "UPDATE notifications SET is_read = 1 WHERE id = ?",
            (notification_id,),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="提醒不存在")
    return {"ok": True}


@app.post("/api/notifications/read-all")
def read_all_notifications(user: sqlite3.Row = Depends(current_user)):
    with get_db() as conn:
        conn.execute("UPDATE notifications SET is_read = 1")
        conn.execute("UPDATE watches SET has_unread_change = 0")
    return {"ok": True}


# ---------------------------------------------------------------- 静态页与启动


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "8000")),
    )
