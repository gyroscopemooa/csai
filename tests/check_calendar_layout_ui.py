"""Verify that the calendar layout retains both schedule lookup and booking workflows."""
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from playwright.sync_api import expect, sync_playwright


BASE = os.getenv("CSAI_SMOKE_URL", "http://127.0.0.1:3000")
TODAY = datetime.now(ZoneInfo("Asia/Seoul")).date()
FIRST, SECOND, THIRD = (str(TODAY + timedelta(days=days)) for days in (3, 7, 10))
TOOLS = ("맞춤 일정 양식", "직접 일정 등록", "예약 설정", "담당자 관리")


def answer(response):
    assert response.ok, (response.url, response.status, response.text())
    return response.json()


def post(request, path, data):
    return answer(request.post(BASE + path, data=data))


def customer_booking(request, token, date, time, title):
    form = answer(request.get(BASE + "/api/booking/form/" + token))
    item = post(request, "/api/booking/draft", {
        "token": token, "version": form["template_version"], "start": date + "T" + time,
        "payload": {"title": title},
    })
    return post(request, f"/api/booking/{item['id']}/confirm", {
        "token": token, "confirmation": item["token"],
    })


with sync_playwright() as pw:
    browser = pw.chromium.launch(channel="msedge")
    page = browser.new_page(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")
    page.set_default_timeout(7000)
    page.goto(BASE + "/auth/demo", wait_until="networkidle")
    if page.locator("#policy-all").count():
        page.locator("#policy-all").check()
        page.get_by_role("button", name="확인하고 계속하기").click()
    page.locator(".layout main").wait_for()
    post(page.request, "/api/demo/billing", {
        "plan": "lite", "addons": ["calendar", "change_booking", "extra_agent", "google_calendar"],
    })
    def patch_settings(data):
        answer(page.request.patch(BASE + "/api/settings", data=data))
    patch_settings({
        "enabled": True, "closed_days": [], "modes": {"booking": "manual", "change": "manual"},
        "fields": [{"key": "title", "type": "text", "label": "예약명", "required": True}],
    })
    brand = post(page.request, "/api/agents", {"create": True, "brand": "별도 일정 브랜드", "welcome": "안녕하세요"})
    customer = pw.request.new_context()
    slug = answer(page.request.get(BASE + "/api/me"))["slug"]
    token = post(customer, "/api/session", {"slug": slug})["token"]
    pending = customer_booking(customer, token, FIRST, "13:00", "첫 날짜 승인 대기")
    assert pending["status"] == "pending"
    change_booking = customer_booking(customer, token, THIRD, "13:00", "변경 요청 예약")
    cancel_booking = customer_booking(customer, token, THIRD, "16:00", "취소 요청 예약")
    for booking in (change_booking, cancel_booking):
        post(page.request, f"/api/bookings/{booking['id']}", {"action": "approve"})
    change = post(customer, f"/api/customer/bookings/{change_booking['id']}/change", {
        "token": token, "action": "change", "start": THIRD + "T14:00", "confirmed": True,
    })
    cancel = post(customer, f"/api/customer/bookings/{cancel_booking['id']}/change", {
        "token": token, "action": "cancel", "confirmed": True,
    })
    assert change["state"] == cancel["state"] == "pending"
    patch_settings({"payment_required": True})
    paid_pending = customer_booking(customer, token, SECOND, "13:00", "둘째 날짜 결제 대기")
    assert paid_pending["status"] == "pending_payment"
    page.goto(BASE + "/#calendar", wait_until="networkidle")
    page.reload(wait_until="networkidle")
    toolbar = page.get_by_role("group", name="일정 등록 및 설정")
    queue = page.locator("#calendar-booking-task")
    requests = page.locator("#calendar-change-task")
    results = page.locator("#calendar-results")
    count = queue.locator("[data-task-count]")
    expect(count).to_have_text("2건")
    expect(requests.locator("[data-task-count]")).to_have_text("2건")
    for name in TOOLS:
        expect(toolbar.get_by_role("button", name=name)).to_be_visible()
    toolbar.get_by_role("button", name="맞춤 일정 양식").click()
    expect(page.get_by_role("heading", name="맞춤 일정 등록 양식")).to_be_visible()
    page.get_by_role("button", name="돌아가기").click()
    toolbar.get_by_role("button", name="예약 설정").click()
    expect(page.get_by_role("heading", name="예약 설정", exact=True)).to_be_visible()
    page.goto(BASE + "/#calendar", wait_until="networkidle")
    toolbar.get_by_role("button", name="담당자 관리").click()
    expect(page.get_by_role("dialog", name="담당자 관리")).to_be_visible()
    page.keyboard.press("Escape")
    toolbar.get_by_role("button", name="직접 일정 등록").click()
    manual = page.get_by_role("dialog", name="수동 일정 등록")
    manual.locator("#manual-start").fill(FIRST + "T16:00")
    manual.locator("#manual-title").fill("직접 등록 일정")
    manual.locator("#manual-paid").check()
    with page.expect_response("**/api/bookings") as created:
        manual.get_by_role("button", name="일정 등록", exact=True).click()
    assert answer(created.value)["status"] == "confirmed"

    period = page.locator("#calendar-period-toggle")
    period.click()
    expect(period).to_be_focused()
    page.locator("#range-start").fill(FIRST)
    page.locator("#range-end").fill(FIRST)
    page.locator(".calendar-range-fields").get_by_role("button", name="조회", exact=True).click()
    expect(count).to_have_text("1건")
    expect(results.get_by_text("직접 등록 일정")).to_be_visible()
    for name in ("완료", "취소", "일정 변경", "구글 일정 동기화"):
        expect(results.get_by_role("button", name=name, exact=True)).to_be_visible()
    pending_filter = page.get_by_role("group", name="일정 상태").get_by_role("button", name="승인·결제 대기")
    pending_filter.click()
    expect(pending_filter).to_have_attribute("aria-pressed", "true")
    expect(pending_filter).to_be_focused()
    expect(results.get_by_text("첫 날짜 승인 대기")).to_be_visible()
    expect(results.get_by_text("직접 등록 일정")).to_have_count(0)
    period.click()
    expect(count).to_have_text("2건")
    expect(queue.get_by_text("둘째 날짜 결제 대기")).to_be_visible()
    expect(results.get_by_text("둘째 날짜 결제 대기")).to_have_count(0)
    queue.locator(".line").filter(has_text="둘째 날짜 결제 대기").get_by_role("button", name="확인 및 확정").click()
    approval = page.get_by_role("dialog", name="예약 확정")
    approval.locator("#paid-ok").check()
    with page.expect_response(f"**/api/bookings/{paid_pending['id']}") as approved:
        approval.get_by_role("button", name="확정", exact=True).click()
    assert answer(approved.value)["status"] == "confirmed"
    expect(count).to_have_text("1건")

    with page.expect_response(f"**/api/booking-changes/{change['id']}") as accepted:
        requests.locator(".line").filter(has_text="일정 변경 요청").get_by_role("button", name="승인", exact=True).click()
    assert answer(accepted.value)["ok"]
    with page.expect_response(f"**/api/booking-changes/{cancel['id']}") as rejected:
        requests.locator(".line").filter(has_text="취소 요청").get_by_role("button", name="거절", exact=True).click()
    assert answer(rejected.value)["ok"]
    expect(requests.locator("[data-task-count]")).to_have_text("0건")
    expect(requests.get_by_text("승인 완료", exact=True)).to_be_visible()
    expect(requests.get_by_text("거절", exact=True)).to_be_visible()

    page.locator("#calendar-brand").select_option(brand["id"])
    expect(page.locator(".calendar-workspace")).to_have_attribute("data-calendar-scope", brand["id"])
    expect(count).to_have_text("0건")
    for name, dialog_title in (("맞춤 일정 양식", "브랜드 맞춤 일정 양식"), ("예약 설정", "브랜드 예약 설정")):
        toolbar.get_by_role("button", name=name).click()
        expect(page.get_by_role("dialog", name=dialog_title)).to_be_visible()
        page.keyboard.press("Escape")
    page.get_by_role("button", name="다음 달").press("Enter")
    page.get_by_role("button", name="이전 달").press("Enter")
    for width in (768, 390, 320):
        page.set_viewport_size({"width": width, "height": 900})
        assert page.locator("html").evaluate("(el) => el.scrollWidth <= innerWidth")
        for name in TOOLS:
            expect(toolbar.get_by_role("button", name=name)).to_be_visible()
        expect(period).to_be_visible()
    customer.dispose()
    browser.close()

print("PASS: tools, brands, date and status scope, booking approval, and change/cancel history")
