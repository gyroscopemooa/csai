"""Open an isolated CSAI administrator preview with interactive synthetic data."""
import argparse
import base64
import hashlib
import os
import secrets
import socket
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.request import urlopen
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
ADMIN = "local:operator"
STAFF = "google:local-preview-staff"
COUNT = 10
CHANNELS = ("public", "test", "naver", "kakao", "telegram", "line", "instagram")
SCENARIOS = (
    ("가족 촬영", "주말 예약 가능한 시간을 알려주세요."),
    ("기업 행사", "다음 달 세미나 촬영 견적이 필요합니다."),
    ("상품 재입고", "품절된 옵션은 언제 다시 주문할 수 있나요?"),
    ("예약 변경", "확정된 예약을 오후로 옮길 수 있을까요?"),
    ("배송 확인", "등록된 배송 상태를 어디서 볼 수 있나요?"),
    ("교환 요청", "포장만 개봉했는데 다른 옵션으로 교환하고 싶습니다."),
    ("환불 문의", "취소 전 환불 규정을 확인하고 싶습니다."),
    ("방문 안내", "대중교통과 주차 이용 방법을 알려주세요."),
    ("파일 전달", "납품 자료를 받을 수 있는 형식이 궁금합니다."),
    ("담당자 확인", "운영 시간 외에도 진행 상태를 확인할 수 있을까요?"),
)


def put(conn, table, **values):
    columns = ",".join(values)
    params = ",".join("?" for _ in values)
    conn.execute(f"INSERT INTO {table} ({columns}) VALUES ({params})", tuple(values.values()))


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def seed():
    from app import policies
    from billing import quote
    from reporting import summarize
    from store import DEFAULT, db, dump, now, uid, workspace

    stamp = now()
    day = datetime.now(ZoneInfo("Asia/Seoul")).replace(hour=0, minute=0, second=0, microsecond=0)
    with db(True) as conn:
        if conn.execute("SELECT 1 FROM workspace LIMIT 1").fetchone():
            raise RuntimeError("Use a new isolated SQLite database for administrator fixtures.")
        ws = workspace(conn, ADMIN)["id"]
        staff_ws = workspace(conn, STAFF)["id"]
        config = dict(DEFAULT, brand="관리자 샘플 작업공간", price="샘플 기본 상담 10,000원",
                      industries=["촬영"], desired_work=["예약", "견적", "고객 응대"])
        conn.execute("UPDATE workspace SET settings=?,plan='lite',enabled=1 WHERE id=?", (dump(config), ws))
        for identity in (ws, staff_ws):
            put(conn, "policy_acceptance", ws=identity, version=policies.VERSION, terms=1,
                privacy=1, ai=1, dpa=1, marketing=0, accepted=stamp)
        put(conn, "automation_ack", ws=ws, version=policies.VERSION, accepted=stamp)
        staff_token = os.environ["CSAI_FIXTURE_STAFF_SESSION"]
        put(conn, "session", token=staff_token, ws=staff_ws, expires=stamp + 86400)
        put(conn, "session_verified_email", token=staff_token, email="staff-01@example.invalid")
        put(conn, "commerce_settings", ws=ws, agent="", enabled=1)
        put(conn, "chat_photo_setting", ws=ws, agent="", enabled=1, files_enabled=1)
        put(conn, "web_call_setting", ws=ws, agent="", enabled=1)
        for kind in ("SMS", "알림톡"):
            put(conn, "message_balance", ws=ws, kind=kind, n=100)
        staff_member = uid()

        for index, (topic, question) in enumerate(SCENARIOS, 1):
            recorded = stamp - 3600 - index * 420
            suffix = f"{index:02}"
            label = f"샘플 {suffix} · {topic}"
            brand = uid()
            put(conn, "agent_profile", id=brand, ws=ws, slug=uid(), settings=dump(dict(config, brand=label)),
                faq="[]", published="{}", enabled=index % 2, slot=index)
            member = staff_member if index == 1 else uid()
            put(conn, "staff_member", id=member, ws=ws, email=f"staff-{suffix}@example.invalid",
                name=f"샘플 담당자 {suffix}", role="agent" if index % 2 else "viewer",
                agent="", assigned_only=1, identity=STAFF if index == 1 else "",
                state="active" if index == 1 else "revoked" if index % 3 == 0 else "pending",
                invite_hash="", expires=stamp - 1, created=recorded)
            put(conn, "trial_invite", id=uid(), code_hash=digest(uid()), chat_limit=50 + index * 10,
                credit_limit=20 + index * 5, booking_limit=10, expires=stamp - 1,
                days=14, created=recorded, revoked=index % 2)
            put(conn, "developer_key", id=uid(), ws=ws, label=label, digest=digest(uid()),
                scopes=dump(["chat:write"]), created=recorded, revoked=1)
            put(conn, "inbox_snippet", id=uid(), ws=ws, title=label, body=f"{topic} 관련 내용을 확인하고 안내하겠습니다.",
                created=recorded)
            put(conn, "private_brand_note", id=uid(), ws=ws, agent="", body=f"{label} 검토용 메모", created=recorded)
            put(conn, "faq", id=uid(), ws=ws, q=question, a=f"{topic} 안내는 예약 또는 구매 조건을 확인한 후 답변합니다.")
            put(conn, "file", id=uid(), ws=ws, name=f"샘플 업무 매뉴얼 {suffix}.txt", sha=digest(label),
                content=f"{topic} 문의를 받으면 필요한 정보를 확인하고 담당자에게 전달합니다.", images="[]", created=recorded)
            knowledge = {"style": "차분하고 명확한 안내", "rules": [f"{topic}는 확인 가능한 범위만 답변합니다."],
                         "faq": [{"q": question, "a": f"{topic} 조건을 확인합니다."}], "demo": True}
            put(conn, "training", id=uid(), ws=ws, state="review" if index % 2 else "published",
                estimate=0, cost=0, source=dump({"text": label, "agent": "", "images": []}),
                result=dump(knowledge), created=recorded)
            put(conn, "knowledge_version", id=uid(), ws=ws, content=dump(knowledge), created=recorded, label=label)
            for kind in ("training", "chat"):
                put(conn, "model_usage", id=uid(), ws=ws, kind=kind, model="gpt-6.2-sol", mode="simulation",
                    input_tokens=100 + index * 13, output_tokens=32 + index * 2, estimated_cost_usd=0, created=recorded)
            product = uid()
            put(conn, "commerce_product", id=product, ws=ws, agent="", sku=f"DEMO-{suffix}", name=label,
                variant="기본", price=10000 + index * 2000, stock=(index - 1) * 3, url="",
                description="관리자 화면 검토용 가상 상품", published=0, updated=recorded)
            market = ("smartstore", "coupang", "own")[(index - 1) % 3]
            reference = f"DEMO-ORDER-{suffix}"
            amount = 10000 + index * 2000
            put(conn, "commerce_order", id=uid(), ws=ws, agent="", channel=market, reference=reference,
                product=label, quantity=1, amount=amount, state=("received", "preparing", "shipped", "delivered", "cancelled")[(index-1)%5],
                carrier="", tracking="", created=recorded, updated=recorded)
            order_request = (
                {"kind": "education", "sku": "mini"},
                {"kind": "subscription", "plan": "lite", "addons": []},
                {"kind": "memory_import"},
            )[(index-1)%3]
            kind, items, price = quote(order_request)
            put(conn, "checkout_order", id=uid(), ws=ws, kind=kind, items=dump(items), amount=price,
                status=("pending", "failed", "cancelled", "refunded")[(index-1)%4],
                created=stamp - index * 90, client=f"fixture-{suffix}")
            put(conn, "ledger", id=uid(), ws=ws, kind="샘플 교육 내역", delta=0, ref=label, created=recorded)
            contact = uid()
            put(conn, "crm_contact", id=contact, ws=ws, name=f"샘플 고객 {suffix}", email=f"customer-{suffix}@example.invalid",
                notes=label, created=recorded, updated=recorded)
            item = uid()
            put(conn, "quote_item", id=item, ws=ws, name=label, price=amount, active=1, agent="")

            for offset, channel in enumerate(CHANNELS):
                thread, visitor = uid(), uid()
                status = ("open", "pending", "resolved")[(index - 1) % 3]
                put(conn, "visitor", token=visitor, ws=ws, expires=stamp + 86400,
                    kind="test" if channel == "test" else "public", agent="")
                put(conn, "thread", id=thread, ws=ws, visitor=visitor, kind=channel,
                    status=status, manual=int(status == "pending"), created=recorded + offset)
                turns = (
                    ("user", f"{label} · {question}"), ("assistant", "문의하신 내용을 확인하겠습니다."),
                    ("user", "기본 조건과 필요한 준비 사항도 알려주세요."), ("assistant", f"{topic}에 필요한 정보를 정리했습니다."),
                    ("user", "담당자가 확인해야 하는 부분이 있나요?"), ("staff", "샘플 기록을 확인 중입니다."),
                    ("user", "확인 후 다음 단계도 안내해 주세요."), ("assistant", "조건을 확인한 뒤 진행 방법을 안내하겠습니다."),
                    ("assistant", "이 메시지는 로컬 검수용이며 실제 안내나 발송 이력이 아닙니다."),
                    ("user", f"{topic} 진행 상태가 궁금합니다."),
                )
                issue_message = ""
                for position, (role, body) in enumerate(turns):
                    message = uid()
                    put(conn, "message", id=message, ws=ws, thread=thread, role=role, body=body,
                        created=recorded + offset + position * 5)
                    if position == 3:
                        issue_message = message

                if channel == "public":
                    put(conn, "consultation_source", ws=ws, thread=thread, source="link" if index % 2 else "widget")
                    put(conn, "staff_thread", ws=ws, thread=thread, member=staff_member)
                    put(conn, "inbox_assignment", ws=ws, thread=thread, assignee=f"샘플 담당자 {suffix}",
                        priority=("normal", "high", "urgent")[(index-1)%3], due_date=day.date().isoformat(), updated=recorded)
                    put(conn, "inbox_annotation", ws=ws, thread=thread, note=label, tags=dump(["로컬 샘플", topic]))
                    put(conn, "crm_thread", ws=ws, thread=thread, contact=contact)
                    put(conn, "quality_rating", ws=ws, thread=thread, score=3 + index % 3, created=recorded)
                    put(conn, "business_rating", ws=ws, thread=thread, score=3 + (index+1) % 3, created=recorded)
                    put(conn, "unknown", id=uid(), ws=ws, thread=thread, q=f"{question} · {suffix}", status="open", created=recorded)
                    put(conn, "answer_issue", id=uid(), ws=ws, thread=thread, message=issue_message, agent="",
                        note=f"{label} · 샘플 답변 검토", state="open", created=recorded)
                    put(conn, "commerce_request", id=uid(), ws=ws, agent="", thread=thread, client=uid(),
                        kind=("delivery", "exchange", "refund")[(index-1)%3], channel=market, reference=reference,
                        details=f"{topic} 요청 검수", state="pending", created=recorded, updated=recorded)
                    put(conn, "web_call", id=uid(), ws=ws, agent="", thread=thread, kind="audio" if index % 2 else "video",
                        state="ended", offer="", answer="", claim="", actor="customer",
                        created=recorded, expires=recorded + 600, updated=recorded)
                    attachment = uid()
                    raw = f"{label} - local fixture\n".encode("utf-8")
                    put(conn, "chat_photo", id=attachment, ws=ws, thread=thread, message=message,
                        sender="user", actor="customer", client=uid(), data=base64.b64encode(raw).decode("ascii"),
                        bytes=len(raw), created=recorded, mime="text/plain", filename=f"sample-{suffix}.txt")
                    seed_related(conn, ws, thread, visitor, label, item, amount, status, recorded, day, index, config)
                elif channel != "test":
                    # Terminal delivery records let the UI show failures without creating outbound work.
                    job = uid()
                    put(conn, "channel_job", id=job, ws=ws, channel=channel, event_key=uid(), body="",
                        status="failed", error="샘플 · 실제 전송 없이 생성한 오류 예시", created=recorded, updated=recorded)
                    put(conn, "channel_job_thread", ws=ws, job=job, thread=thread)

        for index in range(1, COUNT + 1):
            end = stamp - (index-1) * 86400
            start = end - 86400
            period = "daily:" + (day.date() - timedelta(days=index)).isoformat()
            put(conn, "report_history", id=uid(), ws=ws, period=period, start=start,
                end=end, summary=dump(summarize(conn, ws, start, end)), created=stamp)


def seed_related(conn, ws, thread, visitor, label, item, amount, status, stamp, day, index, config):
    from store import dump, uid

    start = day + timedelta(days=(index - 1) // 2, hours=10 if index % 2 else 14)
    booking = uid()
    put(conn, "booking", id=booking, ws=ws, visitor=visitor, start=start.isoformat(),
        end=(start + timedelta(minutes=config["duration"])).isoformat(), resource="default",
        payload=dump({"name": f"샘플 고객 {index:02}", "people": "2", "note": label}),
        version=config["template_version"], fields=dump(config["fields"]),
        status=("confirmed", "pending", "cancelled")[(index - 1) % 3],
        customer_ok=1, paid=0, token=uid(), created=stamp)
    event = uid()
    put(conn, "event_log", id=event, ws=ws, kind="booking", title=f"{label} 예약 검수", ref=booking,
        seen=index % 2, created=stamp)
    put(conn, "delivery", id=uid(), ws=ws, event=event, status="failed",
        error="샘플 · 실제 이메일 발송 없음", created=stamp)
    put(conn, "message_notify_delivery", id=uid(), ws=ws, event=event, kind="SMS", status="failed",
        created=stamp, updated=stamp)
    work = {}
    for kind in ("tasks", "quote", "leads", "complaints"):
        work[kind] = uid()
        put(conn, "work", id=work[kind], ws=ws, kind=kind, title=f"{label} · {kind}",
            details="로컬 검수용 요청 내용", status=status, created=stamp)
        put(conn, "work_link", ws=ws, thread=thread, kind=kind, work=work[kind])
    put(conn, "lead_profile", ws=ws, thread=thread, work=work["leads"], stage="new", source="staff", updated=stamp)
    put(conn, "quote_offer", id=uid(), ws=ws, work=work["quote"], thread=thread,
        items=dump([{"id": item, "name": label, "price": amount, "quantity": 1, "amount": amount}]),
        amount=amount, note="로컬 검수용 견적", status="draft", created=stamp)
    workflow = uid()
    put(conn, "custom_workflow", id=workflow, ws=ws, name=label, description="샘플 업무 연동", active=0, created=stamp)
    put(conn, "custom_job", id=uid(), ws=ws, workflow=workflow, work=work["tasks"],
        payload=dump({"title": label}), state="completed" if index % 2 else "failed",
        result="샘플 결과", created=stamp, updated=stamp)


def serve(port):
    if (os.getenv("DEMO_MODE") != "1" or os.getenv("SHARED_TEST_MODE") != "0"
            or os.getenv("CSAI_DB_BACKEND") != "sqlite" or os.getenv("PYTHON_DOTENV_DISABLED") != "1"
            or os.getenv("APP_URL") != f"http://localhost:{port}" or not os.getenv("DATA_DIR")
            or os.getenv("OPERATOR_OWNERS") != ADMIN or not os.getenv("CSAI_FIXTURE_STAFF_SESSION")):
        raise RuntimeError("The fixture server must be launched by the isolated preview command.")
    import uvicorn
    sys.path.insert(0, str(ROOT))
    seed()
    uvicorn.run("app:app", host="127.0.0.1", port=port, access_log=False)


def browser_preview(port, headless, server_python):
    from playwright.sync_api import sync_playwright

    # Let the existing CSAI server keep its port, database and browser cookies.
    base = f"http://localhost:{port}"
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", port))
    token, staff_token = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    inherited = ("SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP", "LOCALAPPDATA", "USERPROFILE")
    env = {key: os.environ[key] for key in inherited if key in os.environ}
    with tempfile.TemporaryDirectory(prefix="csai-admin-preview-") as folder:
        env.update(DATA_DIR=folder, APP_URL=base, DEMO_MODE="1", SHARED_TEST_MODE="0",
                   CSAI_DB_BACKEND="sqlite", PYTHON_DOTENV_DISABLED="1", PYTHONUTF8="1",
                   OPERATOR_OWNERS=ADMIN, LOCAL_OPERATOR_TOKEN=token, ENABLE_BACKGROUND_WORKER="0",
                   CSAI_FIXTURE_STAFF_SESSION=staff_token)
        path = Path(folder) / "server.log"
        with path.open("w+", encoding="utf-8") as log:
            process = subprocess.Popen([server_python, str(Path(__file__).resolve()), "--serve", "--port", str(port)],
                                       cwd=ROOT, env=env, stdout=log, stderr=log)
            try:
                for _ in range(80):
                    if process.poll() is not None:
                        log.seek(0)
                        raise RuntimeError(log.read())
                    try:
                        with urlopen(base + "/health", timeout=.5):
                            break
                    except OSError:
                        time.sleep(.25)
                else:
                    raise RuntimeError("The isolated administrator preview could not start.")
                with sync_playwright() as pw:
                    browser = pw.chromium.launch(channel="msedge", headless=headless)
                    admin = browser.new_page(viewport=None, no_viewport=True)
                    response = admin.request.post(base + "/auth/operator-local", data={"token": token}, max_redirects=0)
                    if response.status != 303:
                        raise RuntimeError(f"Local administrator sign-in failed: {response.status}")
                    admin.goto(base + "/#inbox")
                    admin.locator(".inbox-entry").first.wait_for()
                    staff = browser.new_page(viewport=None, no_viewport=True)
                    staff.context.add_cookies([{"name": "csai_session", "value": staff_token, "url": base,
                                                "httpOnly": True, "sameSite": "Lax"}])
                    staff.goto(base + "/#staff-desk")
                    if headless:
                        verify(admin, staff, base)
                    else:
                        admin.bring_to_front()
                        print(f"Administrator preview ready: {base}/#inbox", flush=True)
                        while browser.is_connected() and (not admin.is_closed() or not staff.is_closed()):
                            time.sleep(.25)
                            page = admin if not admin.is_closed() else staff
                            try:
                                page.wait_for_timeout(1)
                            except Exception:
                                if not page.is_closed():
                                    raise
            finally:
                process.terminate()
                process.wait(timeout=10)


def verify(admin, staff, base):
    def get(page, path):
        response = page.request.get(base + path)
        if not response.ok:
            raise RuntimeError(f"{path} returned {response.status}")
        return response.json()

    assert get(admin, "/api/me")["operator"]
    assert get(admin, "/api/me")["remaining"] == 10000
    for channel in CHANNELS:
        threads = get(admin, "/api/inbox?kind=" + channel)
        assert len(threads) == COUNT
        assert all(len(get(admin, "/api/inbox/" + t["id"])["messages"]) == 10 for t in threads)
    for path in ("/api/bookings", "/api/unknown", "/api/inbox-snippets", "/api/files",
                 "/api/training", "/api/knowledge/versions", "/api/faq", "/api/team",
                 "/api/operator/invites", "/api/quotes/items", "/api/quotes/offers", "/api/crm/contacts",
                 "/api/leads", "/api/events"):
        assert len(get(admin, path)) >= COUNT, path
    assert len(get(admin, "/api/work")) == COUNT * 4
    assert len(get(admin, "/api/agents/list")["agents"]) == COUNT
    assert len(get(admin, "/api/reports")["reports"]) == COUNT
    assert len(get(admin, "/api/billing/history")["orders"]) == COUNT
    assert sum(row["calls"] for row in get(admin, "/api/operator/costs")["rows"]) == COUNT * 2
    workflows = get(admin, "/api/custom-workflows")
    assert len(workflows["workflows"]) == len(workflows["jobs"]) == COUNT
    commerce = get(admin, "/api/commerce")
    assert all(len(commerce[key]) == COUNT for key in ("products", "orders", "requests"))
    memberships = get(staff, "/api/staff/memberships")
    assert len(memberships) == 1
    result = get(staff, "/api/staff/" + memberships[0]["id"] + "/threads")
    assert len(result) == COUNT
    for section in ("dashboard", "calendar", "education", "customers", "commerce", "team", "alerts",
                    "developer", "orders", "invites", "costs"):
        admin.evaluate("(section)=>location.hash=section", section)
        admin.locator(f'.layout[data-route={section!r}] main h1').wait_for()
        assert not admin.get_by_role("heading", name="오류", exact=True).count(), section
    staff.locator(".layout[data-route='staff-desk'] main h1").wait_for()
    assert not staff.get_by_role("heading", name="오류", exact=True).count()
    print("Verified 70 conversations, 700 messages, administrator screens and ten assigned staff conversations.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=3001)
    parser.add_argument("--server-python", default=sys.executable)
    parser.add_argument("--headless", action="store_true", help="Run browser and API checks, then exit.")
    parser.add_argument("--serve", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.serve:
        serve(args.port)
    else:
        browser_preview(args.port, args.headless, args.server_python)
