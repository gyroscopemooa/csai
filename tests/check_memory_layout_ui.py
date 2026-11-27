"""Exercise the memory import UI and the shared file drop against a local server."""
import json
import os

from playwright.sync_api import expect, sync_playwright


BASE = os.getenv("CSAI_SMOKE_URL", "http://127.0.0.1:3000")
CONVERSATION = {
    "title": "사업 운영 질문",
    "create_time": 1735689600,
    "current_node": "a",
    "mapping": {"a": {"message": {
        "author": {"role": "user"},
        "content": {"content_type": "text", "parts": ["예시 사업 안내"]},
    }}},
}

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 390, "height": 844}, has_touch=True)
    page.goto(BASE + "/auth/demo", wait_until="networkidle")
    if page.locator("#policy-terms").count():
        for key in ("terms", "privacy", "ai", "dpa"):
            page.locator("#policy-" + key).check()
        page.get_by_role("button", name="확인하고 계속하기").click()
    page.goto(BASE + "/#education", wait_until="networkidle")
    page.locator('[data-education-method="memory"]').click()
    panel = page.locator("#memory-import")
    guide = panel.get_by_text("사업 정보만 간단히 가져오는 방법")
    guide.locator("..").press("Enter")
    expect(page.get_by_role("textbox", name="사업 정보 정리 요청 문구")).to_be_visible()
    guide.locator("..").press("Space")
    expect(page.get_by_role("textbox", name="사업 정보 정리 요청 문구")).to_be_hidden()

    submit = panel.get_by_role("button", name="파일 사전 확인")
    picker = panel.get_by_role("button", name="파일 선택")
    submit.click()
    expect(picker).to_be_focused()
    expect(panel.locator("#memory-file-status")).to_have_text("파일을 선택하세요.")
    with page.expect_file_chooser() as file_chooser:
        picker.press("Enter")
    file_chooser.value.set_files({
        "name": "conversations.json",
        "mimeType": "application/json",
        "buffer": json.dumps([CONVERSATION]).encode(),
    })
    expect(panel.locator("#memory-file-status")).to_have_text("conversations.json")
    submit.click()
    assert page.locator('input[name="consent"]').evaluate("(el) => el.validity.valueMissing")
    expect(panel.locator("#memory-preview")).to_be_empty()
    panel.locator('input[name="consent"]').check()
    panel.locator("#memory-start").fill("2026-01-01")
    panel.locator("#memory-end").fill("2025-12-31")
    submit.click()
    expect(page.get_by_text("시작일은 종료일보다 늦을 수 없습니다.")).to_be_visible()
    panel.locator("#memory-start").fill("2025-01-01")
    credits = page.request.get(BASE + "/api/me").json()["credits"]
    submit.click()
    expect(panel.get_by_role("heading", name="사전 확인 결과")).to_be_visible()
    expect(panel.get_by_text("사업 운영 질문", exact=False)).to_be_visible()
    panel.get_by_role("button", name="검색 결과 모두 선택").click()
    expect(panel.locator("[data-memory-total]")).to_contain_text("선택 1개")
    panel.locator("#memory-query").fill("일치하지 않는 제목")
    expect(panel.get_by_text("표시할 대화가 없습니다")).to_be_visible()
    assert page.request.get(BASE + "/api/me").json()["credits"] == credits
    if page.request.get(BASE + "/api/me").json()["sandbox_allowed"]:
        page.once("dialog", lambda dialog: dialog.accept())
        panel.get_by_role("button", name="선택 대화 이전 준비").click()
        dialog = page.get_by_role("dialog", name="외부 AI 기억 이전")
        expect(dialog).to_be_visible()
        dialog.press("Escape")
        expect(panel.get_by_role("button", name="진행 중인 이전 작업 열기")).to_be_visible()
        assert page.request.get(BASE + "/api/me").json()["credits"] == credits

    page.locator('[data-education-method="file"]').click()
    drop = page.locator("#file-drop")
    drop.evaluate("""(zone) => {
        const dataTransfer = new DataTransfer();
        dataTransfer.items.add(new File(['업무 안내'], 'training.txt', {type: 'text/plain'}));
        zone.dispatchEvent(new DragEvent('drop', {bubbles: true, dataTransfer}));
    }""")
    expect(page.locator("#file-drop-list")).to_contain_text("training.txt")
    page.get_by_role("button", name="선택한 파일 등록").click()
    expect(page.get_by_text("자료 등록 완료")).to_be_visible()
    page.locator('[data-education-method="memory"]').click()
    expect(panel.locator("#memory-file-status")).to_have_text("conversations.json")
    for width in (320, 390, 768, 1440):
        page.set_viewport_size({"width": width, "height": 844})
        assert page.locator("html").evaluate("(el) => el.scrollWidth <= innerWidth")
    browser.close()

print("PASS: memory accordion, keyboard selection, consent, date validation, local preview, and education file drop")
