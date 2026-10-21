"""pagewatch 真实流程自测。

起一个真的 uvicorn 进程跑 app，再起一个本地假页面服务当被监测对象：
建监测项 → 检查得首份快照 → 再查无变化 → 改假页面内容 → 再查报变化
→ diff 能看到改动行 → 提醒生成 → 标已读。全程走真实 HTTP，不碰外网。

用法：.venv/bin/python tests/live_selftest.py
全部通过时打印 ALL PASS 并以 0 退出；任一步失败以 1 退出。
"""

import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP = tempfile.mkdtemp(prefix="pagewatch-live-")
PAGE_FILE = os.path.join(TMP, "page.html")

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

CHECKS = []


def check(name, cond, extra=""):
    CHECKS.append((name, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {name} {extra}")


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class PageHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        with open(PAGE_FILE, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def main():
    with open(PAGE_FILE, "w", encoding="utf-8") as f:
        f.write(PAGE_V1)
    page_server = ThreadingHTTPServer(("127.0.0.1", 0), PageHandler)
    page_port = page_server.server_address[1]
    threading.Thread(target=page_server.serve_forever, daemon=True).start()
    page_url = f"http://127.0.0.1:{page_port}/item"

    app_port = free_port()
    base = f"http://127.0.0.1:{app_port}"
    env = dict(os.environ)
    env["PAGEWATCH_DB_PATH"] = os.path.join(TMP, "live.db")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app:app",
         "--host", "127.0.0.1", "--port", str(app_port)],
        cwd=ROOT, env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        # trust_env=False：避开云端代理环境变量对本地地址的干扰
        client = httpx.Client(base_url=base, timeout=20, trust_env=False)
        # 等服务起来
        up = False
        for _ in range(60):
            try:
                if client.get("/api/health").status_code == 200:
                    up = True
                    break
            except Exception:
                pass
            time.sleep(0.5)
        check("服务启动且健康检查 200", up)
        if not up:
            return 1

        r = client.post("/api/login", json={"username": "admin", "password": "错"})
        check("错误密码登录被拒 401", r.status_code == 401)

        r = client.post("/api/login", json={"username": "admin", "password": "admin123"})
        check("默认账号登录成功", r.status_code == 200)
        check("首次登录提示改密", r.json().get("must_change_password") is True)
        h = {"Authorization": f"Bearer {r.json()['token']}"}

        r = client.post("/api/watches", headers=h, json={
            "name": "保温杯价格页", "url": page_url, "interval_minutes": 60})
        check("建监测项 201", r.status_code == 201)
        wid = r.json()["id"]

        r = client.post(f"/api/watches/{wid}/check", headers=h)
        check("第一次检查成功", r.json().get("status") == "ok")
        check("第一份快照不算变化", r.json().get("is_change") is False)
        snap1 = r.json()["snapshot_id"]

        r = client.post(f"/api/watches/{wid}/check", headers=h)
        check("内容没变时不报变化", r.json().get("is_change") is False)
        r = client.get("/api/notifications", headers=h)
        check("无变化时没有提醒", r.json()["unread"] == 0)

        with open(PAGE_FILE, "w", encoding="utf-8") as f:
            f.write(PAGE_V2)
        r = client.post(f"/api/watches/{wid}/check", headers=h)
        check("改内容后检查报变化", r.json().get("is_change") is True)
        snap3 = r.json()["snapshot_id"]

        r = client.get("/api/watches", headers=h)
        check("监测项亮起未读变化标记", r.json()[0]["has_unread_change"] is True)

        r = client.get("/api/notifications", headers=h)
        check("生成一条未读提醒", r.json()["unread"] == 1)
        summary = r.json()["items"][0]["summary"] if r.json()["items"] else ""
        check("提醒摘要含增删行数", "新增 2 行" in summary and "删除 1 行" in summary,
              f"({summary})")

        r = client.get(f"/api/watches/{wid}/diff/{snap3}", headers=h)
        diff = r.json()
        pairs = [(row["type"], row["text"]) for row in diff["rows"]]
        check("diff 含改动行（价格 100→80）",
              ("del", "价格 100 元") in pairs and ("add", "价格 80 元") in pairs)
        check("diff 含新增行（限时包邮）", ("add", "限时包邮") in pairs)
        check("diff 计数正确", diff["added"] == 2 and diff["removed"] == 1)

        r = client.get(f"/api/watches/{wid}/diff/{snap1}", headers=h)
        check("第一份快照的 diff 标记为首份", r.json()["is_first"] is True)

        r = client.get(f"/api/watches/{wid}/snapshots", headers=h)
        check("快照共 3 份", len(r.json()) == 3)

        r = client.post(f"/api/watches/{wid}/seen", headers=h)
        check("查看后未读标记清除",
              client.get("/api/watches", headers=h).json()[0]["has_unread_change"] is False)

        r = client.get("/")
        check("首页可打开", r.status_code == 200 and "pagewatch" in r.text)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        page_server.shutdown()

    failed = [n for n, ok in CHECKS if not ok]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} 检查点通过")
    if failed:
        print("失败项：", "、".join(failed))
        return 1
    print("ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
