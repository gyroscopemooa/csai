"""Check package coverage and animated selections in the local pricing UI."""
import os
from pathlib import Path

from playwright.sync_api import sync_playwright

base = os.getenv("CSAI_SMOKE_URL", "http://127.0.0.1:3000")
shot = Path(__file__).resolve().parents[1] / "verification" / "pricing_package_selected.png"
with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1365, "height": 900})
    page.goto(base + "/auth/demo", wait_until="networkidle")
    if page.get_by_role("heading", name="서비스 정책 확인").count():
        for key in ("terms", "privacy", "ai", "dpa"):
            page.locator("#policy-" + key).check()
        page.get_by_role("button", name="확인하고 계속하기").click()
    page.goto(base + "/#pricing", wait_until="networkidle")
    page.get_by_role("heading", name="맞춤 구독 구성").wait_for()
    page.locator('[data-price-key="package-booking_pack"]').click()
    covered = page.locator('[data-price-key="addon-calendar"]')
    assert "is-covered" in covered.get_attribute("class")
    assert covered.locator("input").is_disabled()
    page.wait_for_function("parseFloat(document.querySelector('[data-price-key=\"addon-calendar\"] .price-strike').style.width) > 95")
    assert "22,800원" in page.locator("#quote-price").inner_text()
    page.locator('[data-price-key="package-all"]').click()
    assert not page.locator('[data-price-key="package-booking_pack"] input').is_checked()
    assert "49,800원" in page.locator("#quote-price").inner_text()
    assert page.evaluate("fetch('/api/billing/quote',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({kind:'subscription',plan:'lite',addons:['all']})}).then(r=>r.json()).then(x=>x.amount)") == 69800
    assert "is-covered" in page.locator('[data-price-key="addon-calendar"]').get_attribute("class")
    assert "is-covered" not in page.locator('[data-price-key="addon-external_api"]').get_attribute("class")
    page.locator(".price-task-package").first.locator("summary").click()
    assert page.locator(".price-task-children>div").count() == 25
    page.screenshot(path=str(shot), full_page=True)
    page.locator('[data-price-key="package-customer_pack"]').click()
    assert not page.locator('[data-price-key="package-all"] input').is_checked()
    assert "19,800원" in page.locator("#quote-price").inner_text()
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    browser.close()
print("PASS: package coverage, strike spring, quote, mobile width")
