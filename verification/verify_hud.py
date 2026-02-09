from playwright.sync_api import sync_playwright
import os

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 500, "height": 200})

        base_dir = "/app/ui/web_ui"
        file = "hud.html"
        path = f"file://{os.path.join(base_dir, file)}"

        print(f"Loading {path}...")
        try:
            page.goto(path)
            # Use 'load' instead of 'networkidle' and maybe a short sleep
            page.wait_for_load_state("load")
            page.wait_for_timeout(1000)

            screenshot_path = f"verification/hud.png"
            page.screenshot(path=screenshot_path, omit_background=True)
            print(f"Captured {screenshot_path}")
        except Exception as e:
            print(f"Error capturing {file}: {e}")

        browser.close()

if __name__ == "__main__":
    run()
