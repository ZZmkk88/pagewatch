"""pagewatch 自动化测试。

抓取一律用假 fetcher 或本地假页面服务，不依赖外网。
调度线程在测试中关闭（PAGEWATCH_DISABLE_SCHEDULER=1），检查都手动触发。
"""

import os
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

_TMP = tempfile.mkdtemp(prefix="pagewatch-test-")
os.environ["PAGEWATCH_DB_PATH"] = os.path.join(_TMP, "test.db")
os.environ["PAGEWATCH_DISABLE_SCHEDULER"] = "1"

import app as app_module  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

app_module.init_db()
client = TestClient(app_module.app)

PAGE_V1 = """<html><head><title>商品页</title></head><body>
<h1>保温杯</h1>
<p>价格 <b>100</b> 元</p>
<p>库存充足</p>
</body></html>"""

PAGE_V2 = """<html><head><title>商品页</title></head><body>
<h1>保温杯</h1>
<p>价格 <b>80</b> 元</p>
<p>库存充足</p>
<p>限时包邮</p>
</body></html>"""


class FakeSite:
    """可变内容的假抓取源：改 html 就等于改了被监测的页面。"""

    def __init__(self, html):
        self.html = html

    def __call__(self, url):
        return 200, self.html


@pytest.fixture(autouse=True)
def clean_db():
    with app_module.get_db() as conn:
        for table in ("tokens", "notifications", "snapshots", "watches", "users"):
            conn.execute(f"DELETE FROM {table}")
    app_module.init_db()
    yield


def login(password="admin123"):
    r = client.post("/api/login", json={"username": "admin", "password": password})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['token']}"}


def make_watch(headers, name="商品页", url="http://fake.local/item", interval=30):
    r = client.post(
        "/api/watches",
        json={"name": name, "url": url, "interval_minutes": interval},
        headers=headers,
    )
    assert r.status_code == 201
    return r.json()


# ------------------------------------------------------------------ 登录


def test_login_wrong_password():
    r = client.post("/api/login", json={"username": "admin", "password": "错的"})
    assert r.status_code == 401


def test_unauthenticated_401():
    assert client.get("/api/watches").status_code == 401
    bad = {"Authorization": "Bearer not-a-real-token"}
    assert client.get("/api/watches", headers=bad).status_code == 401


def test_login_and_me():
    r = client.post("/api/login", json={"username": "admin", "password": "admin123"})
    assert r.status_code == 200
    assert r.json()["must_change_password"] is True
    me = client.get("/api/me", headers=login())
    assert me.json()["username"] == "admin"


def test_change_password_flow():
    h = login()
    wrong = client.post(
        "/api/change-password",
        json={"old_password": "不对", "new_password": "newpass1"},
        headers=h,
    )
    assert wrong.status_code == 400
    short = client.post(
        "/api/change-password",
        json={"old_password": "admin123", "new_password": "123"},
        headers=h,
    )
    assert short.status_code == 400
    ok = client.post(
        "/api/change-password",
        json={"old_password": "admin123", "new_password": "newpass1"},
        headers=h,
    )
    assert ok.status_code == 200
    r = client.post("/api/login", json={"username": "admin", "password": "newpass1"})
    assert r.status_code == 200
    assert r.json()["must_change_password"] is False


# ------------------------------------------------------------------ 监测项 CRUD


def test_watch_crud_and_validation():
    h = login()
    w = make_watch(h)
    wid = w["id"]
    assert w["paused"] is False

    bad_url = client.post(
        "/api/watches",
        json={"name": "x", "url": "ftp://a.b", "interval_minutes": 10},
        headers=h,
    )
    assert bad_url.status_code == 400
    bad_interval = client.post(
        "/api/watches",
        json={"name": "x", "url": "http://a.b", "interval_minutes": 0},
        headers=h,
    )
    assert bad_interval.status_code == 400

    upd = client.put(
        f"/api/watches/{wid}",
        json={"name": "改名了", "url": "http://fake.local/other", "interval_minutes": 15},
        headers=h,
    )
    assert upd.status_code == 200
    assert upd.json()["name"] == "改名了"
    assert upd.json()["interval_minutes"] == 15

    paused = client.post(f"/api/watches/{wid}/pause", headers=h)
    assert paused.json()["paused"] is True
    resumed = client.post(f"/api/watches/{wid}/resume", headers=h)
    assert resumed.json()["paused"] is False

    assert client.delete(f"/api/watches/{wid}", headers=h).status_code == 200
    assert client.get("/api/watches", headers=h).json() == []
    assert client.delete(f"/api/watches/{wid}", headers=h).status_code == 404


# ------------------------------------------------------------------ 文本抽取


def test_extract_text():
    html = """<html><head><title>标题页</title><style>.a{color:red}</style></head>
    <body>
      <h1>大标题</h1>
      <p>价格 <b>100</b> 元</p>
      <script>var secret = 1;</script>
      <ul><li>第一项</li><li>第二项</li></ul>
      <p>多余   空白
         折叠</p>
    </body></html>"""
    text = app_module.extract_text(html)
    lines = text.split("\n")
    assert "大标题" in lines
    assert "价格 100 元" in lines
    assert "第一项" in lines and "第二项" in lines
    assert "多余 空白 折叠" in lines
    assert "secret" not in text
    assert "color" not in text


# ------------------------------------------------------------------ diff


def test_compute_diff_unit():
    d = app_module.compute_diff("甲\n乙\n丙", "甲\n新\n丙\n丁")
    assert d["added"] == 2
    assert d["removed"] == 1
    assert d["changed"] is True
    types = [(r["type"], r["text"]) for r in d["rows"]]
    assert ("add", "新") in types
    assert ("del", "乙") in types
    same = app_module.compute_diff("甲\n乙", "甲\n乙")
    assert same["changed"] is False


# ------------------------------------------------------------------ 检查流程


def test_check_no_change_no_notification(monkeypatch):
    h = login()
    w = make_watch(h)
    monkeypatch.setattr(app_module, "fetch_url", FakeSite(PAGE_V1))
    r1 = client.post(f"/api/watches/{w['id']}/check", headers=h)
    assert r1.json() == {"status": "ok", "is_change": False,
                         "snapshot_id": r1.json()["snapshot_id"]}
    r2 = client.post(f"/api/watches/{w['id']}/check", headers=h)
    assert r2.json()["is_change"] is False
    snaps = client.get(f"/api/watches/{w['id']}/snapshots", headers=h).json()
    assert len(snaps) == 2
    assert all(s["is_change"] is False for s in snaps)
    notifs = client.get("/api/notifications", headers=h).json()
    assert notifs["unread"] == 0
    assert notifs["items"] == []


def test_check_change_notification_and_diff(monkeypatch):
    h = login()
    w = make_watch(h)
    site = FakeSite(PAGE_V1)
    monkeypatch.setattr(app_module, "fetch_url", site)
    client.post(f"/api/watches/{w['id']}/check", headers=h)

    site.html = PAGE_V2
    r = client.post(f"/api/watches/{w['id']}/check", headers=h)
    assert r.json()["is_change"] is True
    snap_id = r.json()["snapshot_id"]

    watch = client.get("/api/watches", headers=h).json()[0]
    assert watch["has_unread_change"] is True
    assert watch["last_changed_at"]

    notifs = client.get("/api/notifications", headers=h).json()
    assert notifs["unread"] == 1
    item = notifs["items"][0]
    assert item["watch_name"] == "商品页"
    assert "新增 2 行" in item["summary"] and "删除 1 行" in item["summary"]

    diff = client.get(f"/api/watches/{w['id']}/diff/{snap_id}", headers=h).json()
    assert diff["is_first"] is False
    assert diff["added"] == 2 and diff["removed"] == 1
    pairs = [(row["type"], row["text"]) for row in diff["rows"]]
    assert ("add", "价格 80 元") in pairs
    assert ("add", "限时包邮") in pairs
    assert ("del", "价格 100 元") in pairs

    # 标已读：单条接口 + seen 接口都应生效
    read = client.post(f"/api/notifications/{item['id']}/read", headers=h)
    assert read.status_code == 200
    assert client.get("/api/notifications", headers=h).json()["unread"] == 0
    seen = client.post(f"/api/watches/{w['id']}/seen", headers=h)
    assert seen.status_code == 200
    watch = client.get("/api/watches", headers=h).json()[0]
    assert watch["has_unread_change"] is False


def test_first_snapshot_diff_is_first(monkeypatch):
    h = login()
    w = make_watch(h)
    monkeypatch.setattr(app_module, "fetch_url", FakeSite(PAGE_V1))
    r = client.post(f"/api/watches/{w['id']}/check", headers=h)
    diff = client.get(
        f"/api/watches/{w['id']}/diff/{r.json()['snapshot_id']}", headers=h
    ).json()
    assert diff["is_first"] is True
    assert diff["previous_id"] is None


def test_snapshot_get_and_404(monkeypatch):
    h = login()
    w = make_watch(h)
    monkeypatch.setattr(app_module, "fetch_url", FakeSite(PAGE_V1))
    r = client.post(f"/api/watches/{w['id']}/check", headers=h)
    snap = client.get(
        f"/api/watches/{w['id']}/snapshots/{r.json()['snapshot_id']}", headers=h
    )
    assert snap.status_code == 200
    assert "保温杯" in snap.json()["text"]
    missing = client.get(f"/api/watches/{w['id']}/snapshots/99999", headers=h)
    assert missing.status_code == 404


def test_fetch_error_state(monkeypatch):
    h = login()
    w = make_watch(h)

    def boom(url):
        raise app_module.FetchError("HTTP 500")

    monkeypatch.setattr(app_module, "fetch_url", boom)
    r = client.post(f"/api/watches/{w['id']}/check", headers=h)
    assert r.json()["status"] == "error"
    assert "HTTP 500" in r.json()["error"]
    watch = client.get("/api/watches", headers=h).json()[0]
    assert watch["last_status"] == "error"
    assert "HTTP 500" in watch["last_error"]
    snaps = client.get(f"/api/watches/{w['id']}/snapshots", headers=h).json()
    assert snaps == []


def test_snapshot_cap_20():
    h = login()
    w = make_watch(h)
    counter = {"n": 0}

    def changing(url):
        counter["n"] += 1
        return 200, f"<html><body><p>第 {counter['n']} 版内容</p></body></html>"

    for _ in range(25):
        result = app_module.run_check(w["id"], fetcher=changing)
        assert result["status"] == "ok"
    snaps = client.get(f"/api/watches/{w['id']}/snapshots", headers=h).json()
    assert len(snaps) == 20
    notifs = client.get("/api/notifications", headers=h).json()
    assert notifs["unread"] == 24  # 除第一份外每次变化都提醒


def test_read_all_notifications(monkeypatch):
    h = login()
    w = make_watch(h)
    site = FakeSite(PAGE_V1)
    monkeypatch.setattr(app_module, "fetch_url", site)
    client.post(f"/api/watches/{w['id']}/check", headers=h)
    site.html = PAGE_V2
    client.post(f"/api/watches/{w['id']}/check", headers=h)
    assert client.get("/api/notifications", headers=h).json()["unread"] == 1
    client.post("/api/notifications/read-all", headers=h)
    after = client.get("/api/notifications", headers=h).json()
    assert after["unread"] == 0
    watch = client.get("/api/watches", headers=h).json()[0]
    assert watch["has_unread_change"] is False


# ------------------------------------------------------------------ 口径回归


def test_change_password_revokes_other_sessions():
    """口径总表第 2 条：改密后吊销其他会话，保留当前会话。"""
    h1 = login()
    h2 = login()
    assert client.get("/api/me", headers=h2).status_code == 200
    r = client.post(
        "/api/change-password",
        json={"old_password": "admin123", "new_password": "newpass1"},
        headers=h1,
    )
    assert r.status_code == 200
    assert client.get("/api/me", headers=h1).status_code == 200  # 当前会话保留
    assert client.get("/api/me", headers=h2).status_code == 401  # 其他会话已吊销


def test_docs_pages_closed():
    """口径总表第 6 条：接口文档页默认关闭，未登录不得访问。"""
    assert client.get("/docs").status_code == 404
    assert client.get("/redoc").status_code == 404
    assert client.get("/openapi.json").status_code == 404


def test_ssrf_blocks_private_targets():
    """口径总表第 9 条：抓取前拦截内网目标（默认不放开本地开关时）。"""
    with pytest.raises(app_module.FetchError) as exc:
        app_module.fetch_url("http://127.0.0.1:9/secret")
    assert "内网" in str(exc.value)
    with pytest.raises(app_module.FetchError):
        app_module.fetch_url("http://169.254.169.254/latest/meta-data/")


def test_check_watch_to_private_url_is_error(monkeypatch):
    monkeypatch.delenv("PAGEWATCH_ALLOW_PRIVATE_FETCH", raising=False)
    h = login()
    w = make_watch(h, url="http://127.0.0.1:9/secret")
    r = client.post(f"/api/watches/{w['id']}/check", headers=h)
    assert r.json()["status"] == "error"
    assert "内网" in r.json()["error"]
    watch = client.get("/api/watches", headers=h).json()[0]
    assert watch["last_status"] == "error"
    assert client.get(f"/api/watches/{w['id']}/snapshots", headers=h).json() == []


def test_overlong_input_rejected_with_lengths():
    """口径总表第 10 条：超长输入 400 拒绝，报错带上限与当前长度，不截断。"""
    h = login()
    r = client.post(
        "/api/watches",
        json={"name": "名" * 101, "url": "http://a.b", "interval_minutes": 10},
        headers=h,
    )
    assert r.status_code == 400
    assert "100" in r.json()["detail"] and "101" in r.json()["detail"]
    r = client.post(
        "/api/watches",
        json={"name": "x", "url": "http://a.b/" + "p" * 2000,
              "interval_minutes": 10},
        headers=h,
    )
    assert r.status_code == 400
    assert "2000" in r.json()["detail"]


def test_logout_revokes_only_current_session():
    """TASK-021 P1-3：退出登录只废止当前这次会话，其他会话保留。"""
    h1 = login()
    h2 = login()
    r = client.post("/api/logout", headers=h1)
    assert r.status_code == 200
    assert r.json() == {"ok": True}
    assert client.get("/api/me", headers=h1).status_code == 401  # 当前会话已废止
    assert client.get("/api/me", headers=h2).status_code == 200  # 其他会话保留
    # 已作废的令牌再调退出接口也返回 401
    assert client.post("/api/logout", headers=h1).status_code == 401


def test_snapshot_rotation_unlinks_notifications():
    """TASK-021 P1-4：轮转删旧快照前先解开提醒，无悬空指向，提醒数不变。"""
    h = login()
    w = make_watch(h)
    counter = {"n": 0}

    def changing(url):
        counter["n"] += 1
        return 200, f"<html><body><p>第 {counter['n']} 版内容</p></body></html>"

    for _ in range(25):
        result = app_module.run_check(w["id"], fetcher=changing)
        assert result["status"] == "ok"
    with app_module.get_db() as conn:
        dangling = conn.execute(
            "SELECT COUNT(*) FROM notifications n LEFT JOIN snapshots s"
            " ON n.snapshot_id = s.id"
            " WHERE n.snapshot_id IS NOT NULL AND s.id IS NULL"
        ).fetchone()[0]
        nulled = conn.execute(
            "SELECT COUNT(*) FROM notifications"
            " WHERE watch_id = ? AND snapshot_id IS NULL",
            (w["id"],),
        ).fetchone()[0]
    assert dangling == 0
    assert nulled == 4  # 被轮转掉的 4 份旧快照对应的提醒已解开，提醒行保留
    notifs = client.get("/api/notifications", headers=h).json()
    assert notifs["unread"] == 24
    sids = [n["snapshot_id"] for n in notifs["items"]]
    assert sum(1 for s in sids if s is None) == 4  # 解开的 4 条前端不再渲染按钮
    with app_module.get_db() as conn:
        kept = {r["id"] for r in conn.execute(
            "SELECT id FROM snapshots WHERE watch_id = ?", (w["id"],))}
    assert all(s in kept for s in sids if s is not None)


def test_ssrf_blocks_metadata_host_and_scheme():
    """TASK-021 P1-1 对账补充：云元数据主机名、非 http(s) 协议直接拦。"""
    with pytest.raises(app_module.FetchError) as exc:
        app_module.fetch_url("http://metadata.google.internal/latest/")
    assert "元数据" in str(exc.value)
    with pytest.raises(app_module.FetchError):
        app_module.fetch_url("file:///etc/passwd")
    with pytest.raises(app_module.FetchError) as exc2:
        app_module.fetch_url("http://100.100.100.200/latest/meta-data/")
    assert "内网" in str(exc2.value)


# ------------------------------------------------------------------ 真抓取（本地服务）


def test_fetch_url_against_local_server(monkeypatch):
    # 本地假服务在 127.0.0.1 上，按口径第 9 条需显式打开本地抓取开关
    monkeypatch.setenv("PAGEWATCH_ALLOW_PRIVATE_FETCH", "1")
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/ok":
                body = "<html><body><p>你好</p></body></html>".encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        status, html = app_module.fetch_url(f"http://127.0.0.1:{port}/ok")
        assert status == 200
        assert "你好" in html
        with pytest.raises(app_module.FetchError):
            app_module.fetch_url(f"http://127.0.0.1:{port}/missing")
    finally:
        server.shutdown()
