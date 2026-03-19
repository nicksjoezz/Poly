from playwright.sync_api import sync_playwright, expect

def verify_dev_check(page):
    # Go to the dashboard
    page.goto("http://localhost:8080")
    page.wait_for_timeout(1000)

    # Check title
    expect(page.locator("h1")).to_contain_text("WeatherArb")

    # Go to Dev Check tab
    page.click("button[data-tab='dev']")
    page.wait_for_timeout(500)

    # Check tab content
    expect(page.locator("h3:has-text('Trade Execution Analysis')")).to_be_visible()
    expect(page.locator("#download-logs-btn")).to_be_visible()

    page.screenshot(path="/home/jules/verification/dev_check_tab.png")

    # Click start to populate some scan data (it won't likely trade immediately but will show logs)
    page.click("button[data-tab='dashboard']")
    page.click("#main-control-btn")
    page.wait_for_timeout(5000)

    # Check Dev Check again
    page.click("button[data-tab='dev']")
    page.wait_for_timeout(500)
    page.screenshot(path="/home/jules/verification/dev_check_populated.png")

if __name__ == "__main__":
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(record_video_dir="/home/jules/verification/video")
        page = context.new_page()
        try:
            verify_dev_check(page)
        finally:
            context.close()
            browser.close()
