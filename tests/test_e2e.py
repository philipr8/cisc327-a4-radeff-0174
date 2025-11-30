from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:5000"


def test_add_and_borrow_book():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(BASE_URL)
        page.get_by_role("link", name="Catalog").click()

        page.get_by_role("link", name="Add New Book").click()
        page.fill("input#title", "E2E Test Book")
        page.fill("input#author", "Philip QA")
        page.fill("input#isbn", "9999999999999")
        page.fill("input#total_copies", "3")
        page.get_by_role("button", name="Add Book to Catalog").click()
        page.wait_for_timeout(1000)

        page.goto(BASE_URL)
        page.get_by_role("link", name="Catalog").click()
        row = page.locator("tbody tr", has_text="E2E Test Book")
        page.wait_for_timeout(500)
        assert row.count() > 0

        avail_before = row.locator("td").nth(4).text_content()
        assert "3/3" in avail_before

        patron_input = row.locator("input[name='patron_id']")
        patron_input.fill("123456")
        row.get_by_role("button", name="Borrow").click()
        page.wait_for_timeout(1000)

        page.goto(BASE_URL)
        page.get_by_role("link", name="Catalog").click()
        row_after = page.locator("tbody tr", has_text="E2E Test Book")
        avail_after = row_after.locator("td").nth(4).text_content()
        assert "2/3" in avail_after

        browser.close()
