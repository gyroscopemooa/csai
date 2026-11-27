"""Verify account entry, versioned policy confirmation, and sandbox checkout."""
import os
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


BASE = os.getenv("CSAI_SMOKE_URL", "http://127.0.0.1:3000")
ARTIFACTS = os.getenv("CSAI_JOURNEY_SCREENSHOTS")
KEYS = ("terms", "privacy", "ai", "dpa")


def capture(page, name, width):
    if ARTIFACTS:
        path = Path(ARTIFACTS)
        path.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=path / f"{name}-{width}.png", animations="disabled", full_page=name != "checkout-after")


with sync_playwright() as pw:
    browser = pw.chromium.launch(channel="msedge")
    for width in (1440, 390):
        page = browser.new_page(viewport={"width": width, "height": 960}, has_touch=width < 600)
        page.set_default_timeout(7000)
        page.goto(BASE, wait_until="networkidle")
        page.get_by_role("button", name="Google로 시작하기").click()
        expect(page.get_by_role("heading", name="CS AI 시작하기")).to_be_visible()
        expect(page.get_by_role("button", name="Google로 계속하기")).to_be_visible()
        capture(page, "login-after", width)
        page.get_by_role("button", name="네이버 로그인 안내").click()
        expect(page.get_by_role("dialog", name="준비 중")).to_be_visible()
        page.keyboard.press("Escape")
        expect(page.get_by_role("button", name="네이버 로그인 안내")).to_be_focused()

        page.goto(BASE + "/auth/demo", wait_until="networkidle")
        policy = page.locator(".policy-consent")
        advance = page.get_by_role("button", name="확인하고 계속하기")
        master = page.locator("#policy-all")
        expect(advance).to_be_disabled()
        assert policy.evaluate("(el) => el.scrollWidth <= innerWidth")
        assert page.locator(".ui-confirm-row > a").evaluate_all(
            "(links) => links.every(link => link.offsetHeight >= 44 && link.offsetLeft === links[0].offsetLeft)"
        )
        capture(page, "policy-after", width)
        page.locator("#policy-privacy").check()
        assert master.evaluate("(el) => el.indeterminate")
        expect(advance).to_be_disabled()
        with page.expect_popup() as popup:
            page.get_by_role("link", name="개인정보처리방침 확인 내용 보기").click()
        document = popup.value
        expect(document.get_by_role("heading", level=1)).to_contain_text("개인정보처리방침")
        document.close()
        assert master.evaluate("(el) => el.indeterminate")
        expect(page.locator("#policy-terms")).not_to_be_checked()

        master.press("Space")
        for key in KEYS:
            expect(page.locator(f"#policy-{key}")).to_be_checked()
        expect(advance).to_be_enabled()
        page.locator("#policy-ai").uncheck()
        expect(advance).to_be_disabled()
        assert master.evaluate("(el) => el.indeterminate")
        page.locator("#policy-ai").check()
        expect(master).to_be_checked()
        master.uncheck()
        for key in KEYS:
            expect(page.locator(f"#policy-{key}")).not_to_be_checked()
        expect(advance).to_be_disabled()
        master.check()
        with page.expect_response("**/api/policies/accept") as acceptance:
            advance.click()
        assert acceptance.value.ok
        assert acceptance.value.request.post_data_json == {
            "version": acceptance.value.json()["version"], **dict.fromkeys(KEYS, True),
        }
        expect(policy).to_be_hidden()
        assert page.request.get(BASE + "/api/policies/status").json()["accepted"]

        page.goto(BASE + "/#setup", wait_until="networkidle")
        page.get_by_role("button", name="시작 안내 확인 완료").click()
        expect(page.get_by_role("button", name="시작 체크리스트 확인됨")).to_be_visible()

        page.goto(BASE + "/#credits", wait_until="networkidle")
        if page.get_by_role("button", name="로컬 테스트 충전").count():
            page.get_by_role("button", name="로컬 테스트 충전").click()
            checkout = page.get_by_role("dialog", name="테스트 주문 확인")
            finish = checkout.get_by_role("button", name="테스트 결제 완료")
            expect(finish).to_be_disabled()
            expect(checkout.get_by_text("교육 크레딧", exact=True)).to_be_visible()
            capture(page, "checkout-after", width)
            checkout.get_by_role("button", name="나중에 확인").click()
            expect(checkout).to_be_hidden()
            page.goto(BASE + "/#orders", wait_until="networkidle")
            page.get_by_role("button", name="테스트 주문 확인").click()
            expect(finish).to_be_disabled()
            checkout.locator("#checkout-confirm").check()
            with page.expect_response("**/sandbox-confirm") as payment:
                finish.click()
            assert payment.value.ok and payment.value.json()["status"] == "paid"
            expect(checkout).to_be_hidden()
        if width < 600:
            page.get_by_role("button", name="메뉴 열기").click()
        page.get_by_role("button", name="로그아웃").click()
        expect(page.get_by_role("heading", name="CS AI 시작하기")).to_be_visible()
        assert page.request.get(BASE + "/api/me").status == 401
        assert page.locator("html").evaluate("(el) => el.scrollWidth <= innerWidth")
        page.close()
    browser.close()

print("PASS: login, policy confirmation, keyboard and links, onboarding, sandbox checkout, and logout")
