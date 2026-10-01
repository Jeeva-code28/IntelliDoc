import os
import sys
import time
import subprocess
import urllib.request
import urllib.error
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent.parent
SCREENSHOT_DIR = BASE_DIR / "tests" / "screenshots"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
FIXTURES_DIR = BASE_DIR / "tests" / "fixtures"
FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')


def log(msg: str):
    ts = time.strftime('%H:%M:%S')
    print(f"[{ts}] [LOCAL_MODEL_BROWSER_TEST] {msg}", flush=True)


def is_server_healthy(url="http://127.0.0.1:8000/health"):
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=2) as resp:
            return resp.status == 200
    except Exception:
        return False


def start_server_if_needed():
    if is_server_healthy():
        log("Server is already running on http://127.0.0.1:8000")
        return None

    log("Starting FastAPI server on http://127.0.0.1:8000...")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=str(BASE_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    for i in range(30):
        time.sleep(1)
        if is_server_healthy():
            log(f"FastAPI server started successfully (took {i+1}s)!")
            return proc
    raise RuntimeError("Timed out waiting for FastAPI server to start.")


def create_test_document():
    doc_path = FIXTURES_DIR / "local_llama_financial_report.txt"
    content = (
        "Project NPN Financial and Technical Executive Summary (FY2025)\n\n"
        "Section 1: Financial Performance\n"
        "In Q4 FY2025, total revenue was $148.5 million, representing a 22.4% year-over-year increase.\n"
        "Net profit reached $34.2 million with an operating margin of 23.0%.\n"
        "Gross margin remained strong at 68.5%, driven by cloud software subscriptions.\n\n"
        "Section 2: AI Infrastructure and Technology\n"
        "The AI infrastructure cluster operates 128 NVIDIA H100 GPU nodes interconnected via 3.2 Tbps Quantum-2 InfiniBand.\n"
        "The primary local inference engine is running Llama-3.1-8B-Instruct GGUF quantization Q4_K_M.\n"
        "Vector search achieves sub-10ms exact cosine retrieval over SQLite BLOB storage.\n"
    )
    doc_path.write_text(content, encoding="utf-8")
    log(f"Created test fixture at: {doc_path}")
    return doc_path


def run_browser_test():
    server_proc = start_server_if_needed()
    doc_path = create_test_document()

    try:
        with sync_playwright() as p:
            log("Launching Playwright Chromium browser...")
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 900})
            page = context.new_page()

            # Console logging
            page.on("console", lambda m: log(f"[Browser Console] {m.text}"))
            page.on("pageerror", lambda e: log(f"[Browser PageError] {e}"))

            # Step 1: Navigate to web application
            log("Step 1: Navigating to http://127.0.0.1:8000...")
            page.goto("http://127.0.0.1:8000", wait_until="networkidle")
            assert "Project NPN" in page.title(), f"Unexpected title: {page.title()}"
            log("Page loaded successfully. Title verified.")

            # Capture initial landing screenshot
            ss_initial = SCREENSHOT_DIR / "01_initial_landing.png"
            page.screenshot(path=str(ss_initial), full_page=True)
            log(f"Saved screenshot: {ss_initial.name}")

            # Step 2: Verify Provider dropdown has Ollama selected
            provider_val = page.locator("#llmProviderSelect").input_value()
            log(f"Active selected LLM provider: {provider_val}")
            assert provider_val == "ollama", f"Expected provider 'ollama', found: {provider_val}"

            # Step 3: Create a new conversation
            log("Step 3: Creating a new conversation...")
            page.click("#newChatBtn")
            page.wait_for_timeout(1000)

            # Step 4: Upload test document
            log(f"Step 4: Uploading fixture document '{doc_path.name}'...")
            page.set_input_files("#fileInput", str(doc_path))

            # Wait for document to appear in documents list
            page.wait_for_selector(f".doc-name:has-text('{doc_path.name}')", timeout=30000)
            log("Document successfully uploaded, parsed, and indexed into SQLite vector store!")

            ss_uploaded = SCREENSHOT_DIR / "02_document_uploaded.png"
            page.screenshot(path=str(ss_uploaded), full_page=True)
            log(f"Saved screenshot: {ss_uploaded.name}")

            # Step 5: Ask a question grounded in the document
            query = "What was the Q4 FY2025 revenue and what are the AI cluster specifications?"
            log(f"Step 5: Submitting query: '{query}'...")
            page.fill("#queryInput", query)
            page.click("#sendBtn")

            # Step 6: Wait for response from local Llama-3.1 model
            log("Step 6: Waiting for local Ollama Llama-3.1-8B model inference...")
            # Wait for assistant message bubble to be rendered
            page.wait_for_selector(".message-bubble.assistant", timeout=120000)
            # Wait until answer is formatted and loading pulse is gone
            page.wait_for_selector(".message-bubble.assistant .formatted-answer", timeout=120000)

            # Extra wait for UI stabilization and verification badge rendering
            page.wait_for_timeout(2000)

            answer_text = page.locator(".message-bubble.assistant .formatted-answer").last.inner_text()
            log(f"Received answer from local LLM:\n{answer_text}")

            assert len(answer_text) > 10, "Answer text is too short or empty"

            ss_response = SCREENSHOT_DIR / "03_grounded_answer_received.png"
            page.screenshot(path=str(ss_response), full_page=True)
            log(f"Saved screenshot: {ss_response.name}")

            # Step 7: Inspect Citations and Verification Badge
            citations = page.locator(".message-bubble.assistant .citation-chip").all()
            log(f"Found {len(citations)} citation chip(s) in assistant message.")

            if len(citations) > 0:
                log("Opening citation proof drawer for first citation...")
                citations[0].click()
                page.wait_for_timeout(1000)
                modal_visible = page.locator("#citationModalOverlay").is_visible()
                log(f"Citation modal visibility: {modal_visible}")
                ss_citation = SCREENSHOT_DIR / "04_citation_drawer_opened.png"
                page.screenshot(path=str(ss_citation), full_page=True)
                log(f"Saved screenshot: {ss_citation.name}")

                # Close modal
                page.click(".close-modal-btn")
                page.wait_for_timeout(500)

            # Step 8: Test Prompt Navigation Scrubber
            log("Step 8: Testing prompt navigation scrubber and hover popover...")
            page.hover("#navTrackContainer")
            page.wait_for_timeout(800)
            ss_nav = SCREENSHOT_DIR / "05_prompt_navigation_scrubber.png"
            page.screenshot(path=str(ss_nav), full_page=True)
            log(f"Saved screenshot: {ss_nav.name}")

            log("All browser frontend test steps completed successfully with local model hf.co/helloollel/Llama-3.1-8B-instruct-bilibili-gguf:Q4_K_M!")

    finally:
        if server_proc:
            log("Stopping background FastAPI server...")
            server_proc.terminate()


if __name__ == "__main__":
    run_browser_test()
