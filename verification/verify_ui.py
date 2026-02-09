from playwright.sync_api import sync_playwright
import os

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Increase viewport size to capture full designs
        page = browser.new_page(viewport={"width": 1280, "height": 800})

        base_dir = "/app/ui/web_ui"
        files = ["hud.html", "index.html", "session.html", "settings.html", "about.html"]

        os.makedirs("verification", exist_ok=True)

        for file in files:
            path = f"file://{os.path.join(base_dir, file)}"
            print(f"Loading {path}...")
            try:
                page.goto(path)
                # Wait for tailwind to load (network idle)
                page.wait_for_load_state("networkidle")
                # Take screenshot
                screenshot_path = f"verification/{file.replace('.html', '.png')}"
                # For HUD, maybe we want a transparent background? Playwright supports omit_background=True
                omit_bg = (file == "hud.html")
                page.screenshot(path=screenshot_path, omit_background=omit_bg)
                print(f"Captured {screenshot_path}")
            except Exception as e:
                print(f"Error capturing {file}: {e}")

        browser.close()

if __name__ == "__main__":
    run()
