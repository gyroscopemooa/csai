"""Verify logo upload and paid design preview against a running local server."""
import os
from io import BytesIO

from PIL import Image
from playwright.sync_api import sync_playwright

base = os.getenv("CSAI_SMOKE_URL", "http://127.0.0.1:3000")
with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 390, "height": 844})
    page.goto(base + "/auth/demo", wait_until="networkidle")
    if page.get_by_role("heading", name="서비스 정책 확인").count():
        for key in ("terms", "privacy", "ai", "dpa"):
            page.locator("#policy-" + key).check()
        page.get_by_role("button", name="확인하고 계속하기").click()
    page.get_by_role("button", name="메뉴 열기").click()
    page.locator("#demo-view").select_option("free")
    page.locator(".sidebar-tenant").get_by_text("FREE 요금제").wait_for()
    page.goto(base + "/#preview", wait_until="networkidle")
    page.get_by_role("heading", name="업체 이미지와 채팅 디자인").wait_for()
    page.locator("#chat-theme").select_option("toss")
    assert "theme-toss" in page.locator(".phone").get_attribute("class")
    assert page.get_by_role("button", name="디자인 저장").count() == 0
    image = BytesIO()
    Image.new("RGB", (120, 120), "#3182f6").save(image, format="PNG")
    page.locator("#logo-file").set_input_files({"name": "brand.png", "mimeType": "image/png", "buffer": image.getvalue()})
    page.get_by_role("button", name="로고 저장").click()
    page.locator(".phone .avatar img").wait_for()
    page.get_by_role("button", name="메뉴 열기").click()
    page.locator("#demo-view").select_option("developer")
    page.wait_for_function("document.querySelector('#demo-view')?.value === 'developer'")
    page.get_by_role("heading", name="채팅창 미리보기").wait_for()
    page.locator("#chat-theme").select_option("toss")
    page.get_by_role("button", name="디자인 저장").click()
    page.get_by_text("채팅 디자인을 저장했습니다.").wait_for()
    assert page.evaluate("fetch('/api/appearance').then(r=>r.json()).then(x=>x.theme)") == "toss"
    page.reload(wait_until="networkidle")
    page.wait_for_function("document.querySelector('#chat-theme')?.value === 'toss'")
    assert "theme-toss" in page.locator(".phone").get_attribute("class")
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    browser.close()
print("PASS: free logo, design preview, paid design save, mobile width")
