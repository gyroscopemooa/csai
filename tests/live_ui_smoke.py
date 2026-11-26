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
    assert desktop.locator(".landing-roll-title .roll-letter-inner").count() > 40
    desktop.screenshot(path=str(OUT / "live_landing_desktop.png"), full_page=True)
    desktop.locator(".landing-benefit").nth(1).hover()
    desktop.wait_for_function("document.querySelector('.landing-benefit:nth-child(2) .roll-letter-inner').style.transform !== 'translateY(0%)'")
    assert desktop.get_by_text("퇴직금·해고 및 퇴직 절차").count() == 1
    assert "직원을 고용하는 편이 더 쌀 수도 있습니다." in desktop.locator(".landing-benefits .landing-lead").inner_text()
    assert desktop.locator(".unify-path").count() == 2
    desktop.locator(".unify-cta button").wait_for()
    desktop.locator(".landing-benefits-cta button").wait_for()
    desktop.goto(BASE + "/auth/demo", wait_until="networkidle")
    desktop.get_by_role("heading", name="서비스 정책 확인").wait_for()
    desktop.screenshot(path=str(OUT / "live_policy_desktop.png"), full_page=True)
    for key in ("terms", "privacy", "ai", "dpa"):
        desktop.locator("#policy-" + key).check()
    desktop.get_by_role("button", name="확인하고 계속하기").click()
    desktop.get_by_role("heading", name="AI 교육시키기").wait_for()
    desktop.get_by_role("button", name="AI 티 안 나게").click()
    assert "AI 티가 나지 않게" in desktop.locator("#training-text").input_value()
    desktop.locator("#training-conversation").fill("고객: 예약 가능한가요?\n나: 날짜 알려주시면 확인해드릴게요.")
    desktop.get_by_role("button", name="교육 비용 확인").first.click()
    desktop.locator("#estimate .banner").wait_for()
    desktop.screenshot(path=str(OUT / "live_education_desktop.png"), full_page=True)
    desktop.locator("#faq-q").fill("예약은 어떻게 하나요?")
    desktop.locator("#faq-a").fill("원하시는 날짜를 알려주세요.")
    desktop.get_by_role("button", name="교육 비용 확인").nth(1).click()
    desktop.get_by_role("heading", name="AI 교육 비용 확인").wait_for()
    desktop.locator(".modal").get_by_text("최대", exact=False).wait_for()
    desktop.locator(".modal").get_by_role("button", name="닫기").click()
    desktop.locator(".app-sidebar").get_by_role("button", name="AI 상담원 관리").click()
    desktop.get_by_role("heading", name="언제 추가 상담원이 필요한가요?").wait_for()
    desktop.get_by_text("기본 상담원 한 명으로 하나의 업체를 상담한다면 추가하지 않아도 됩니다.", exact=False).wait_for()
    desktop.screenshot(path=str(OUT / "live_extra_agent_guide_desktop.png"))
    desktop.locator(".app-sidebar").get_by_role("button", name="통합 상담함").click()
    desktop.get_by_role("heading", name="통합 상담함").wait_for()
    assert desktop.locator("#inbox-kind").count() == 1
    assert desktop.locator("#inbox-q").count() == 1
    desktop.locator(".inbox-entry").first.wait_for()
    assert desktop.locator(".inbox-entry").count() >= 8
    assert desktop.locator(".sample-tag").count() >= 8
    desktop.wait_for_timeout(500)
    desktop.screenshot(path=str(OUT / "live_inbox_toolbar_desktop.png"))
    desktop.locator(".inbox-entry").last.get_by_role("button", name="열기").click()
    desktop.get_by_text("메시지 22개").wait_for()
    assert desktop.locator(".inbox-conversation").evaluate("el => el.scrollHeight > el.clientHeight")
    assert desktop.locator(".inbox-list").evaluate("el => el.scrollHeight > el.clientHeight")
    desktop.screenshot(path=str(OUT / "live_inbox_samples_desktop.png"))
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
    desktop.get_by_role("button", name="로컬 상담 계속 테스트").click()
    desktop.get_by_text("로컬 테스트 구독을 적용했습니다.").wait_for()
    desktop.get_by_role("button", name="로컬 상담 계속 테스트").wait_for(state="detached")
    desktop.locator("#msg").fill("예약 문의")
    desktop.get_by_role("button", name="전송").click()
    desktop.locator("#messages .bubble.user").get_by_text("예약 문의").wait_for()
    desktop.wait_for_function("document.querySelectorAll('#messages .bubble').length >= 5")
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
    desktop.locator(".app-sidebar").get_by_role("button", name="추가 기능").click()
    desktop.get_by_role("heading", name="추가 연동 개발 예정").wait_for()
    assert desktop.get_by_role("row", name="인스타그램 DM 매우 높음 비즈니스 계정 공식 연동 검토 미정").count() == 1
    assert desktop.get_by_text("현재 구매·연결할 수 없으며 요금과 제공 시기는 미정").count() == 1

    mobile = browser.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=1)
    mobile.on("pageerror", lambda exc: errors.append(str(exc)))
    mobile.goto(BASE, wait_until="networkidle")
    assert mobile.locator(".landing-benefit").count() == 4
    assert mobile.locator(".landing-roll-title").count() == 4
    assert mobile.locator(".unify-path").count() == 2
    assert mobile.locator(".unify-cta button").is_visible()
    assert mobile.evaluate("document.documentElement.scrollWidth <= innerWidth")
    mobile.screenshot(path=str(OUT / "live_landing_mobile.png"), full_page=True)
    mobile.goto(BASE + "/auth/demo", wait_until="networkidle")
    mobile.get_by_role("heading", name="서비스 정책 확인").wait_for()
    assert mobile.evaluate("document.documentElement.scrollWidth <= innerWidth")
    mobile.screenshot(path=str(OUT / "live_policy_mobile.png"), full_page=True)
    for key in ("terms", "privacy", "ai", "dpa"):
        mobile.locator("#policy-" + key).check()
    mobile.get_by_role("button", name="확인하고 계속하기").click()
    mobile.get_by_role("heading", name="AI 교육시키기").wait_for()
    assert mobile.locator("#training-conversation").count() == 1
    assert mobile.evaluate("document.documentElement.scrollWidth <= innerWidth")
    mobile.screenshot(path=str(OUT / "live_education_mobile.png"), full_page=True)
    mobile.get_by_role("button", name="메뉴 열기").click()
    mobile.locator(".app-sidebar").get_by_role("button", name="AI 상담원 관리").click()
    mobile.get_by_role("heading", name="언제 추가 상담원이 필요한가요?").wait_for()
    assert mobile.evaluate("document.documentElement.scrollWidth <= innerWidth")
    mobile.screenshot(path=str(OUT / "live_extra_agent_guide_mobile.png"), full_page=True)
    mobile.get_by_role("button", name="메뉴 열기").click()
    mobile.locator(".app-sidebar").get_by_role("button", name="통합 상담함").click()
    mobile.get_by_role("heading", name="통합 상담함").wait_for()
    assert mobile.locator(".inbox-entry").count() >= 8
    mobile.locator(".inbox-entry").last.get_by_role("button", name="열기").click()
    mobile.get_by_text("메시지 22개").wait_for()
    assert mobile.evaluate("document.documentElement.scrollWidth <= innerWidth")
    mobile.locator(".inbox-conversation").scroll_into_view_if_needed()
    mobile.screenshot(path=str(OUT / "live_inbox_samples_mobile.png"))
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
                "landing_benefit_cards": 4, "unification_paths": 2,
                "inbox_channel_filter": True, "landing_mobile_no_overflow": True,
                "sidebar_navigation": True, "mobile_input": True, "logo_upload": True,
                "page_errors": errors}, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
print("PASS: direct HTTP desktop chat, sidebar navigation, and mobile input")
