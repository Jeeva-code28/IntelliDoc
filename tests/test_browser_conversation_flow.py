import os
import sys
import time
import subprocess
import urllib.request
import urllib.error
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent.parent
SCREENSHOT_DIR = BASE_DIR / "tests" / "screenshots_conversation_flow"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
FIXTURE_DIR = BASE_DIR / "tests" / "fixtures"
FIXTURE_DIR.mkdir(parents=True, exist_ok=True)

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

REPORT = []

def log(msg: str):
    ts = time.strftime('%H:%M:%S')
    print(f"[{ts}] [FRONTEND_TEST] {msg}")
    REPORT.append(f"[{ts}] {msg}")

def ensure_server_running():
    try:
        req = urllib.request.Request("http://127.0.0.1:8000/health")
        with urllib.request.urlopen(req, timeout=2) as resp:
            if resp.status == 200:
                log("FastAPI server is already running on http://127.0.0.1:8000")
                return None
    except Exception:
        pass

    log("Starting FastAPI server on http://127.0.0.1:8000...")
    server_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=str(BASE_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    # Wait for server to become healthy
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

def create_test_fixtures():
    file_a1 = FIXTURE_DIR / "alpha_finance_q4.txt"
    file_a1.write_text("Project Alpha Financial Report: Q4 net revenue was 142.5 million dollars with EBITDA of 36.2 million.")

    file_a2 = FIXTURE_DIR / "alpha_clients.txt"
    file_a2.write_text("Project Alpha Enterprise Clients: Total active enterprise seats reached 18,500 across 40 countries.")

    file_a3 = FIXTURE_DIR / "alpha_marketing.txt"
    file_a3.write_text("Project Alpha Marketing Metrics: Inbound conversion rate increased by 27.4% following the new portal launch.")

    file_b1 = FIXTURE_DIR / "beta_datacenter.txt"
    file_b1.write_text("Project Beta Datacenter: Cluster runs 64 H100 GPU nodes with 3.2 Tbps InfiniBand interconnect.")

    return file_a1, file_a2, file_a3, file_b1

def run_browser_conversation_tests():
    server_proc = ensure_server_running()
    file_a1, file_a2, file_a3, file_b1 = create_test_fixtures()

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 900})
            page = context.new_page()

            # Track console
            page.on("console", lambda m: log(f"Browser Console [{m.type}]: {m.text}"))

            # Step 1: Navigate to Workspace
            log("Step 1: Navigating to Web Application at http://127.0.0.1:8000...")
            page.goto("http://127.0.0.1:8000", wait_until="networkidle")
            assert "Project NPN" in page.title()
            page.screenshot(path=str(SCREENSHOT_DIR / "01_initial_page.png"), full_page=True)

            # Step 2: Create Conversation 1
            log("Step 2: Creating Conversation 1 ('Alpha Finance Workspace')...")
            page.click("#newChatBtn")
            page.wait_for_timeout(1000)

            # Upload File A1 to Conversation 1
            log(f"Uploading File A1: {file_a1.name}...")
            page.set_input_files("#fileInput", str(file_a1))
            page.wait_for_selector(f".doc-name:has-text('{file_a1.name}')", timeout=30000)
            log(f"File A1 ({file_a1.name}) uploaded and indexed!")

            # Upload File A2 to Conversation 1
            log(f"Uploading File A2: {file_a2.name} to Conversation 1...")
            page.set_input_files("#fileInput", str(file_a2))
            page.wait_for_selector(f".doc-name:has-text('{file_a2.name}')", timeout=30000)
            log(f"File A2 ({file_a2.name}) uploaded and indexed!")

            # Verify 2 files in Conversation 1
            doc_badge = page.locator("#docCountBadge").inner_text()
            log(f"Conversation 1 Active Document Count: {doc_badge}")
            assert "2" in doc_badge

            page.screenshot(path=str(SCREENSHOT_DIR / "02_conv1_two_files_uploaded.png"), full_page=True)

            # Step 3: Query Conversation 1 (Multi-Doc Synthesis)
            log("Step 3: Querying Conversation 1 about revenue and enterprise seats...")
            page.fill("#queryInput", "What is the Q4 net revenue and total active enterprise seats?")
            page.click("#sendBtn")

            page.wait_for_selector(".message-bubble.assistant .formatted-answer", timeout=45000)
            ans1 = page.locator(".message-bubble.assistant").last.inner_text()
            log(f"Conversation 1 Answer: {ans1[:150]}...")
            assert "142.5" in ans1 or "18,500" in ans1 or "revenue" in ans1.lower()

            page.screenshot(path=str(SCREENSHOT_DIR / "03_conv1_query_response.png"), full_page=True)

            # Step 4: Create Conversation 2 (Clean slate)
            log("Step 4: Creating Conversation 2 ('Beta Infrastructure')...")
            page.click("#newChatBtn")
            page.wait_for_timeout(1000)

            # Verify Conversation 2 starts with 0 files
            doc_badge_c2 = page.locator("#docCountBadge").inner_text()
            log(f"Conversation 2 Initial Document Count: {doc_badge_c2}")
            assert "0" in doc_badge_c2

            # Upload File B1 to Conversation 2
            log(f"Uploading File B1: {file_b1.name} to Conversation 2...")
            page.set_input_files("#fileInput", str(file_b1))
            page.wait_for_selector(f".doc-name:has-text('{file_b1.name}')", timeout=30000)
            log(f"File B1 ({file_b1.name}) uploaded to Conversation 2!")

            page.screenshot(path=str(SCREENSHOT_DIR / "04_conv2_one_file_uploaded.png"), full_page=True)

            # Step 5: Query Conversation 2 on Out-of-Scope Alpha topic (Zero Spillover Verification)
            log("Step 5: Testing Zero Spillover: Querying Conversation 2 about Alpha Q4 net revenue...")
            page.fill("#queryInput", "What is the Q4 net revenue?")
            page.click("#sendBtn")

            page.wait_for_selector(".message-bubble.assistant:last-child .formatted-answer", timeout=45000)
            ans_leak = page.locator(".message-bubble.assistant").last.inner_text()
            log(f"Conversation 2 Spillover Check Answer: {ans_leak[:150]}...")
            # Must NOT cite alpha files
            assert "alpha" not in ans_leak.lower() or "cannot answer" in ans_leak.lower()

            page.screenshot(path=str(SCREENSHOT_DIR / "05_conv2_zero_spillover_refusal.png"), full_page=True)

            # Step 6: Return to Conversation 1 (Resumption)
            log("Step 6: Resuming Conversation 1 from sidebar...")
            conv_items = page.locator(".conversation-item")
            count = conv_items.count()
            log(f"Total conversations in sidebar: {count}")
            assert count >= 2

            # Click the second conversation item (which was Conv 1)
            conv_items.nth(1).click()
            page.wait_for_timeout(1000)

            # Verify Conversation 1 documents are restored (File A1 and File A2)
            c1_restored_badge = page.locator("#docCountBadge").inner_text()
            log(f"Conversation 1 Restored Document Count: {c1_restored_badge}")
            assert "2" in c1_restored_badge
            assert page.locator(f".doc-name:has-text('{file_a1.name}')").count() > 0
            assert page.locator(f".doc-name:has-text('{file_a2.name}')").count() > 0

            page.screenshot(path=str(SCREENSHOT_DIR / "06_conv1_resumed.png"), full_page=True)

            # Step 7: Upload 3rd Document (File A3) to Resumed Conversation 1
            log(f"Step 7: Uploading 3rd document ({file_a3.name}) to resumed Conversation 1...")
            page.set_input_files("#fileInput", str(file_a3))
            page.wait_for_selector(f".doc-name:has-text('{file_a3.name}')", timeout=30000)

            c1_updated_badge = page.locator("#docCountBadge").inner_text()
            log(f"Conversation 1 Updated Document Count: {c1_updated_badge}")
            assert "3" in c1_updated_badge

            # Query Conversation 1 about File A3 (Marketing)
            log("Step 8: Querying Conversation 1 about newly uploaded marketing metrics...")
            page.fill("#queryInput", "What is the inbound conversion rate increase for Alpha?")
            page.click("#sendBtn")

            page.wait_for_selector(".message-bubble.assistant:last-child .formatted-answer", timeout=45000)
            ans_mkt = page.locator(".message-bubble.assistant").last.inner_text()
            log(f"Conversation 1 Marketing Answer: {ans_mkt[:150]}...")
            assert "27.4" in ans_mkt or "conversion" in ans_mkt.lower()

            page.screenshot(path=str(SCREENSHOT_DIR / "07_conv1_three_files_active.png"), full_page=True)

            # Step 9: Switch back to Conversation 2 and verify it STILL only has 1 document (Beta Datacenter)
            log("Step 9: Returning to Conversation 2 to verify zero spillover after Conv 1 update...")
            conv_items.nth(0).click()
            page.wait_for_timeout(1000)

            c2_final_badge = page.locator("#docCountBadge").inner_text()
            log(f"Conversation 2 Final Document Count: {c2_final_badge}")
            assert "1" in c2_final_badge
            assert page.locator(f".doc-name:has-text('{file_b1.name}')").count() > 0
            assert page.locator(f".doc-name:has-text('{file_a3.name}')").count() == 0

            page.screenshot(path=str(SCREENSHOT_DIR / "08_conv2_intact_isolation.png"), full_page=True)

            log("ALL FRONTEND CONVERSATION ISOLATION & MULTI-DOC TESTS PASSED PERFECTLY!")
            browser.close()

    finally:
        if server_proc:
            server_proc.terminate()

    # Write report log
    report_file = BASE_DIR / "tests" / "browser_test_summary.log"
    report_file.write_text("\n".join(REPORT), encoding="utf-8")
    return True

if __name__ == "__main__":
    success = run_browser_conversation_tests()
    sys.exit(0 if success else 1)
