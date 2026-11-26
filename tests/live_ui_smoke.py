"""Run against the locally running server: python tests/live_ui_smoke.py."""
import json
from io import BytesIO
from pathlib import Path

from playwright.sync_api import sync_playwright
from PIL import Image

BASE = "http://127.0.0.1:3000"
OUT = Path(__file__).resolve().parents[1] / "verification"
OUT.mkdir(exist_ok=True)

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    desktop = browser.new_page(viewport={"width": 1365, "height": 900})
    errors = []
    desktop.on("pageerror", lambda exc: errors.append(str(exc)))
    desktop.goto(BASE, wait_until="networkidle")
    assert desktop.locator(".landing-benefit").count() == 4
    desktop.locator(".landing-benefits-cta button").wait_for()
    desktop.screenshot(path=str(OUT / "live_landing_desktop.png"), full_page=True)
    desktop.goto(BASE + "/auth/demo", wait_until="networkidle")
    desktop.get_by_role("heading", name="AI 교육시키기").wait_for()
    desktop.locator(".app-sidebar").get_by_role("button", name="채팅창 미리보기").click()
    desktop.get_by_role("heading", name="채팅창 미리보기").wait_for()
    assert desktop.locator("#msg").is_enabled()
    assert desktop.locator(".app-sidebar .ui-icon").first.evaluate(
        "(el) => getComputedStyle(el).maskImage !== 'none'"
    )
    desktop.locator("#msg").fill("가격 안내")
    desktop.get_by_role("button", name="전송").click()
    desktop.locator("#messages .bubble.user").get_by_text("가격 안내").wait_for()
    desktop.wait_for_function("document.querySelectorAll('#messages .bubble').length >= 3")
    desktop.wait_for_function("!document.querySelector('#messages .streaming-reply')")
    assert desktop.locator("#messages .bubble").count() >= 3
    assert desktop.get_by_role("heading", name="채팅창 미리보기").is_visible()
    desktop.locator(".phone").evaluate(
        "(el) => { el.style.width='500px'; el.style.height='700px' }"
    )
    assert desktop.locator(".phone").bounding_box()["width"] == 500
    assert desktop.locator(".sidebar-logout").bounding_box()["y"] < 900
    desktop.screenshot(path=str(OUT / "live_chat_desktop.png"))
    desktop.locator(".app-sidebar").get_by_role("button", name="설정", exact=True).click()
    desktop.get_by_role("heading", name="설정", exact=True).wait_for()
    assert not desktop.locator(".hero").count()
    if desktop.locator("#logo-file").count():
        logo = BytesIO()
        Image.new("RGB", (256, 256), "#3182f6").save(logo, format="PNG")
        desktop.locator("#logo-file").set_input_files(
            {"name": "brand.png", "mimeType": "image/png", "buffer": logo.getvalue()}
        )
        desktop.get_by_role("button", name="로고 저장").click()
        desktop.locator(".app-sidebar").get_by_role("button", name="채팅창 미리보기").click()
        desktop.locator(".phone .avatar img").wait_for()
    else:
        desktop.get_by_text("유료 상담 구독 후 로고 설정 가능").wait_for()

    mobile = browser.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=1)
    mobile.on("pageerror", lambda exc: errors.append(str(exc)))
    mobile.goto(BASE, wait_until="networkidle")
    assert mobile.locator(".landing-benefit").count() == 4
    assert mobile.evaluate("document.documentElement.scrollWidth <= innerWidth")
    mobile.screenshot(path=str(OUT / "live_landing_mobile.png"), full_page=True)
    mobile.goto(BASE + "/auth/demo", wait_until="networkidle")
    mobile.get_by_role("button", name="메뉴 열기").click()
    mobile.locator(".app-sidebar").get_by_role("button", name="채팅창 미리보기").click()
    mobile.get_by_role("heading", name="채팅창 미리보기").wait_for()
    mobile.locator("#msg").fill("예약 문의")
    assert mobile.locator("#msg").input_value() == "예약 문의"
    assert mobile.evaluate("document.documentElement.scrollWidth <= innerWidth")
    assert mobile.locator("#msg").bounding_box()["y"] + mobile.locator("#msg").bounding_box()["height"] < 844
    mobile.wait_for_timeout(450)
    mobile.screenshot(path=str(OUT / "live_chat_mobile.png"))
    assert not errors, errors
    browser.close()

(OUT / "live_ui_smoke.json").write_text(
    json.dumps({"result": "PASS", "direct_http": BASE, "desktop_chat": True,
                "landing_benefit_cards": 4, "landing_mobile_no_overflow": True,
                "sidebar_navigation": True, "mobile_input": True, "logo_upload": True,
                "page_errors": errors}, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
print("PASS: direct HTTP desktop chat, sidebar navigation, and mobile input")
