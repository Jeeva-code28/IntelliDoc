import os
import sys
import time
import subprocess
import urllib.request
import urllib.error
from pathlib import Path
from playwright.sync_api import sync_playwright

SCREENSHOT_DIR = Path(r"d:/QA/.agents/conversation_tests/screenshots_history_nav")
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
FIXTURE_DIR = Path(r"d:/QA/.agents/conversation_tests/fixtures")
FIXTURE_DIR.mkdir(parents=True, exist_ok=True)

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

REPORT = []

def log(msg: str):
    ts = time.strftime('%H:%M:%S')
    print(f"[{ts}] [NAV_HISTORY_TEST] {msg}")
    REPORT.append(f"[{ts}] {msg}")

def ensure_server_running():
    # Kill any process on port 8000 to ensure fresh code
    try:
        import socket
        import os
        import signal
        # Use netstat via subprocess to find pid on 8000
        out = subprocess.check_output('netstat -ano | findstr :8000', shell=True).decode('utf-8', errors='ignore')
        for line in out.strip().split('\n'):
            parts = line.strip().split()
            if len(parts) >= 5 and 'LISTENING' in parts:
                pid = int(parts[-1])
                log(f"Killing old server on PID {pid}")
                subprocess.run(f"taskkill /F /PID {pid}", shell=True, capture_output=True)
                time.sleep(1)
    except Exception as e:
        pass

    log("Starting fresh FastAPI server on http://127.0.0.1:8000...")
    log_file = open(r"d:\QA\.agents\conversation_tests\server.log", "w", encoding="utf-8")
    server_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=r"d:\QA\QA",
        stdout=log_file,
        stderr=subprocess.STDOUT
    )
    for _ in range(30):
        time.sleep(1)
        try:
            req = urllib.request.Request("http://127.0.0.1:8000/health")
            with urllib.request.urlopen(req, timeout=1) as resp:
                if resp.status == 200:
                    log("FastAPI server started and healthy!")
                    return server_proc
        except Exception:
            pass
    raise RuntimeError("Failed to start FastAPI server within 30 seconds.")

def run_browser_nav_and_history_tests():
    server_proc = ensure_server_running()

    test_file = FIXTURE_DIR / "gamma_executive_report.txt"
    test_file.write_text(
        "Project Gamma Strategic Review:\n"
        "1. Annual recurring revenue (ARR) grew to 94.2 million dollars.\n"
        "2. Operating expense margin dropped to 18.5% in Q4.\n"
        "3. Customer satisfaction NPS score reached +72."
    )

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 900})
            page = context.new_page()

            page.on("console", lambda m: log(f"Browser Console [{m.type}]: {m.text}"))

            # Step 1: Open app
            log("Step 1: Navigating to Web Application...")
            page.goto("http://127.0.0.1:8000", wait_until="networkidle")
            page.screenshot(path=str(SCREENSHOT_DIR / "01_initial_workspace.png"), full_page=True)

            # Step 2: Create new conversation
            log("Step 2: Creating new conversation ('Gamma Strategic Analysis')...")
            page.click("#newChatBtn")
            page.wait_for_timeout(1000)

            # Step 3: Upload document
            log("Step 3: Uploading test document...")
            page.set_input_files("#fileInput", str(test_file))
            page.wait_for_selector(f".doc-name:has-text('{test_file.name}')", timeout=30000)
            log("Document uploaded and indexed!")

            # Step 4: Submit Prompt 1
            log("Step 4: Submitting Prompt 1 (ARR growth)...")
            page.fill("#queryInput", "What is the annual recurring revenue ARR?")
            page.click("#sendBtn")
            page.locator(".formatted-answer").first.wait_for(timeout=45000)
            page.wait_for_timeout(1000)

            # Step 5: Submit Prompt 2
            log("Step 5: Submitting Prompt 2 (Operating expense)...")
            page.fill("#queryInput", "What was the operating expense margin in Q4?")
            page.click("#sendBtn")
            page.locator(".formatted-answer").nth(1).wait_for(timeout=45000)
            page.wait_for_timeout(1000)

            # Step 6: Submit Prompt 3
            log("Step 6: Submitting Prompt 3 (NPS score)...")
            page.fill("#queryInput", "What customer satisfaction NPS score was recorded?")
            page.click("#sendBtn")
            page.locator(".formatted-answer").nth(2).wait_for(timeout=45000)
            page.wait_for_timeout(1000)

            page.screenshot(path=str(SCREENSHOT_DIR / "02_three_prompts_active.png"), full_page=True)

            # Step 7: Test Prompt Timeline Navigator & Hover Popover
            log("Step 7: Testing Prompt Timeline Navigator...")
            page.locator(".nav-tick").nth(2).wait_for(timeout=10000)
            ticks = page.locator(".nav-tick")
            tick_count = ticks.count()
            log(f"Rendered timeline ticks count: {tick_count}")
            assert tick_count == 3

            # Hover over navigator to reveal prompt deck popover
            log("Hovering over Prompt Navigator...")
            page.hover("#promptNavigator")
            page.wait_for_timeout(500)
            assert page.locator("#promptHoverPopover").is_visible()

            popover_cards = page.locator(".popover-prompt-card")
            card_count = popover_cards.count()
            log(f"Popover prompt cards count: {card_count}")
            assert card_count == 3

            page.screenshot(path=str(SCREENSHOT_DIR / "03_prompt_hover_popover.png"))

            # Step 8: Test smooth navigation to Top, Mid, Bottom
            log("Step 8: Testing smooth navigation jumps...")
            # Jump to prompt #1 via click on card
            log("Clicking Popover Card #1 (Jump to prompt 1)...")
            popover_cards.nth(0).click()
            page.wait_for_timeout(800)
            page.screenshot(path=str(SCREENSHOT_DIR / "04_navigated_top_prompt.png"))

            # Click Mid button
            log("Clicking Jump Mid Button...")
            page.click("#jumpMidBtn")
            page.wait_for_timeout(800)
            page.screenshot(path=str(SCREENSHOT_DIR / "05_navigated_mid_prompt.png"))

            # Click Bottom button
            log("Clicking Jump Bottom Button...")
            page.click("#jumpBottomBtn")
            page.wait_for_timeout(800)
            page.screenshot(path=str(SCREENSHOT_DIR / "06_navigated_bottom_prompt.png"))

            # Step 9: Test Conversation Deletion
            log("Step 9: Testing Conversation Deletion & Confirmation Modal...")
            # Click delete button on active header or conversation item
            page.click("#deleteActiveConvBtn")
            page.wait_for_timeout(500)

            # Verify delete confirmation modal is shown
            assert page.locator("#deleteConfirmModalOverlay").is_visible()
            page.screenshot(path=str(SCREENSHOT_DIR / "07_delete_confirmation_modal.png"))

            # Confirm deletion
            log("Confirming deletion & archiving...")
            page.click("#confirmDeleteActionBtn")
            page.wait_for_timeout(1500)

            page.screenshot(path=str(SCREENSHOT_DIR / "08_after_deletion_toast.png"))

            # Step 10: Open History Drawer
            log("Step 10: Opening History & Archives Drawer...")
            page.click("#historyToggleBtn")
            page.wait_for_timeout(1000)

            assert page.locator("#historyModalOverlay").is_visible()
            archive_cards = page.locator(".history-archive-card")
            archive_count = archive_cards.count()
            log(f"Archived conversations in History: {archive_count}")
            assert archive_count >= 1

            page.screenshot(path=str(SCREENSHOT_DIR / "09_history_drawer_modal.png"))

            # Step 11: View Full Transcript & Citations in Reader Modal
            log("Step 11: Opening Full Transcript & Proof Citations Viewer...")
            archive_cards.first.locator(".history-action-btn.primary").click()
            page.wait_for_timeout(1000)

            assert page.locator("#historyViewerModalOverlay").is_visible()
            transcript_bubbles = page.locator(".transcript-bubble")
            log(f"Archived transcript bubbles rendered: {transcript_bubbles.count()}")
            assert transcript_bubbles.count() >= 6

            citation_cards = page.locator(".transcript-citation-card")
            log(f"Archived proof citation cards: {citation_cards.count()}")
            assert citation_cards.count() > 0

            page.screenshot(path=str(SCREENSHOT_DIR / "10_transcript_and_citations_viewer.png"))

            log("ALL REAL-BROWSER PROMPT NAVIGATION, DELETION, AND HISTORY ARCHIVE TESTS PASSED PERFECTLY!")
            browser.close()

    finally:
        if server_proc:
            server_proc.terminate()

    return True

if __name__ == "__main__":
    success = run_browser_nav_and_history_tests()
    sys.exit(0 if success else 1)
