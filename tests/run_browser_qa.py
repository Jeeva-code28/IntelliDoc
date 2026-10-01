import os
import sys
import time
import json
import subprocess
import urllib.request
import urllib.error
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

BASE_DIR = Path(__file__).resolve().parent.parent
SCREENSHOT_DIR = BASE_DIR / "tests" / "screenshots_browser_qa"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
REPORT_LOG = []

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

def log(msg: str):
    print(f"[BROWSER_QA] {msg}")
    REPORT_LOG.append(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {msg}")

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

def run_all_browser_tests():
    server_proc = start_server_if_needed()
    log("Starting comprehensive browser tests against http://127.0.0.1:8000")
    
    playwright_ctx = sync_playwright().start()
    try:
        p = playwright_ctx
        # Launch Chromium headless with realistic viewport
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        
        # Track console logs and errors
        console_messages = []
        page.on("console", lambda msg: console_messages.append(f"[{msg.type}] {msg.text}"))
        page.on("pageerror", lambda exc: console_messages.append(f"[PAGE_ERROR] {exc}"))

        # -------------------------------------------------------------
        # STEP 1: Initial Navigation & DOM / UI Inspection
        # -------------------------------------------------------------
        log("Step 1: Navigating to http://127.0.0.1:8000...")
        page.goto("http://127.0.0.1:8000", wait_until="networkidle")
        
        # Check Title
        title = page.title()
        log(f"Page title: {title}")
        assert "Project NPN" in title, f"Unexpected title: {title}"
        
        # Inspect Brand & Header
        brand_h1 = page.locator(".brand-text h1").inner_text()
        brand_sub = page.locator(".brand-text .subtitle").inner_text()
        log(f"Brand Header: '{brand_h1}' | Subtitle: '{brand_sub}'")
        assert "Project NPN" in brand_h1
        
        # Inspect Drop Zone
        drop_text = page.locator(".drop-text").inner_text()
        drop_sub = page.locator(".drop-subtext").inner_text()
        log(f"Drop Zone text: '{drop_text}' | formats: '{drop_sub}'")
        assert "Upload" in drop_text or "Drag" in drop_text
        assert "PDF" in drop_sub
        
        # Inspect Provider Select Options
        provider_select = page.locator("#llmProviderSelect")
        options = provider_select.locator("option").all_inner_texts()
        option_values = [provider_select.locator("option").nth(i).get_attribute("value") for i in range(len(options))]
        log(f"LLM Provider Options: {list(zip(option_values, options))}")
        assert "ollama" in option_values
        assert "groq" in option_values
        assert "gemini" in option_values
        
        # Inspect Footer Spec Pills
        spec_pills = page.locator(".spec-pill").all_inner_texts()
        log(f"Sidebar Spec Pills: {spec_pills}")
        
        # Inspect Welcome Card & Sample Buttons (Create new chat to ensure fresh welcome state)
        page.click("#newChatBtn")
        page.wait_for_selector(".welcome-card h3", timeout=10000)
        welcome_h3 = page.locator(".welcome-card h3").inner_text()
        sample_btns = page.locator(".sample-btn").all_inner_texts()
        log(f"Welcome Title: '{welcome_h3}' | Sample Buttons ({len(sample_btns)}): {sample_btns}")
        assert len(sample_btns) >= 2
        
        # Capture Initial Screenshot
        ss1 = SCREENSHOT_DIR / "screenshot_01_initial_landing.png"
        page.screenshot(path=str(ss1), full_page=True)
        log(f"Captured: {ss1.name}")

        # -------------------------------------------------------------
        # STEP 2: Document Ingestion Flow & Real-Time Progress Bar
        # -------------------------------------------------------------
        log("Step 2: Testing Document Ingestion Flow with real-time progress updates...")
        fixture_pdf = (BASE_DIR / "tests" / "fixtures" / "browser_test_summary.pdf").resolve()
        assert fixture_pdf.is_file(), f"Fixture missing: {fixture_pdf}"
        
        # Trigger file upload via input
        initial_doc_count = page.locator("#docCountBadge").inner_text()
        log(f"Initial doc count badge: {initial_doc_count}")
        
        page.set_input_files("#fileInput", str(fixture_pdf))
        log(f"Uploaded file: {fixture_pdf.name}")
        
        # Verify progress card is visible
        progress_card = page.locator("#uploadProgressCard")
        page.wait_for_timeout(300)
        
        is_card_visible = not ("hidden" in (progress_card.get_attribute("class") or ""))
        progress_fname = page.locator("#progressFilename").inner_text()
        progress_pct = page.locator("#progressPercent").inner_text()
        progress_status = page.locator("#progressStatusText").inner_text()
        log(f"Progress Card Active: {is_card_visible} | File: '{progress_fname}' | Progress: {progress_pct} | Status: '{progress_status}'")
        
        ss2 = SCREENSHOT_DIR / "screenshot_02_upload_progress.png"
        page.screenshot(path=str(ss2), full_page=True)
        log(f"Captured: {ss2.name}")

        # Wait for document to complete ingestion and appear in list
        log("Waiting for ingestion completion...")
        page.wait_for_selector(f".doc-name:has-text('{fixture_pdf.name}')", timeout=30000)
        
        # Verify document appears in list with READY status
        doc_item = page.locator(f".doc-item:has-text('{fixture_pdf.name}')")
        doc_status = doc_item.locator(".status-badge").inner_text()
        new_doc_count = page.locator("#docCountBadge").inner_text()
        log(f"Ingestion Finished! Document: '{fixture_pdf.name}', Status Badge: '{doc_status}', New Count: {new_doc_count}")
        assert "ready" in doc_status.lower() or "ready" in doc_item.inner_text().lower()
        
        ss3 = SCREENSHOT_DIR / "screenshot_03_upload_completed.png"
        page.screenshot(path=str(ss3), full_page=True)
        log(f"Captured: {ss3.name}")

        # -------------------------------------------------------------
        # STEP 3: Chat Query Flow — Local Ollama Llama-3.1-8B
        # -------------------------------------------------------------
        log("Step 3: Testing Chat Query Flow with Ollama Local Llama-3.1-8B...")
        page.select_option("#llmProviderSelect", "ollama")
        selected_provider = page.locator("#llmProviderSelect").input_value()
        log(f"Selected Provider: {selected_provider}")
        assert selected_provider == "ollama"
        
        query_text = "What was the total quarterly revenue in Q2 2025 and the net profit margin according to the summary?"
        page.fill("#queryInput", query_text)
        log(f"Submitting Query: '{query_text}'")
        page.click("#sendBtn")
        
        # Verify user bubble created
        page.wait_for_selector(".message-bubble.user")
        last_user_msg = page.locator(".message-bubble.user").last.inner_text()
        log(f"User Bubble Rendered: '{last_user_msg}'")
        assert query_text in last_user_msg
        
        # Wait for assistant response
        log("Waiting for Ollama Llama-3.1-8B grounded response...")
        page.wait_for_selector(".message-bubble.assistant:last-child .formatted-answer", timeout=120000)
        
        last_assistant = page.locator(".message-bubble.assistant").last
        answer_text = last_assistant.locator(".formatted-answer").inner_text()
        log(f"Ollama Answer: {answer_text[:200]}...")
        assert len(answer_text) > 10
        
        # Check Latency Badge
        latency_badge = last_assistant.locator(".latency-badge").inner_text()
        meta_text = last_assistant.locator(".message-meta").inner_text()
        log(f"Performance Latency Badge: '{latency_badge}' | Meta: '{meta_text}'")
        assert "ms" in latency_badge
        
        # Check Verification Badge
        v_badge = last_assistant.locator(".verification-badge")
        v_badge_text = v_badge.inner_text() if v_badge.count() > 0 else "None"
        v_badge_class = v_badge.get_attribute("class") if v_badge.count() > 0 else ""
        log(f"Claim Verification Badge: '{v_badge_text}' (Class: {v_badge_class})")
        assert v_badge.count() > 0, "Verification badge must be rendered"
        
        # Check Citation Badges & Chips
        citation_badges = last_assistant.locator(".source-citation-badge").all_inner_texts()
        citation_chips = last_assistant.locator(".citation-chip").all_inner_texts()
        log(f"Source Citation Badges inline: {citation_badges} | Citation Chips: {citation_chips}")
        assert len(citation_chips) > 0, "Expected at least 1 citation chip"
        
        ss4 = SCREENSHOT_DIR / "screenshot_04_query_ollama_qwen.png"
        page.screenshot(path=str(ss4), full_page=True)
        log(f"Captured: {ss4.name}")

        # -------------------------------------------------------------
        # STEP 4: Multimodal Citation Chips & Deep Inspection Modal Drawer
        # -------------------------------------------------------------
        log("Step 4: Testing Citation Chip click and Modal Drawer inspection...")
        first_chip = last_assistant.locator(".citation-chip").first
        log(f"Clicking first citation chip: '{first_chip.inner_text()}'")
        first_chip.click()
        
        modal_overlay = page.locator("#citationModalOverlay")
        page.wait_for_timeout(500)
        modal_class = modal_overlay.get_attribute("class") or ""
        log(f"Modal Overlay Class after click: '{modal_class}'")
        assert "hidden" not in modal_class, "Modal overlay should be visible without hidden class"
        
        modal_badge = page.locator("#modalModalityBadge").inner_text()
        modal_title = page.locator("#modalCitationTitle").inner_text()
        modal_meta_rows = page.locator("#modalCitationBody .meta-row").all_inner_texts()
        snippet_content = page.locator("#modalCitationBody .snippet-content").inner_text()
        
        log(f"Modal Modality Badge: '{modal_badge}' | Title: '{modal_title}'")
        log(f"Modal Metadata Rows: {modal_meta_rows}")
        log(f"Modal Snippet Preview: {snippet_content[:150]}...")
        assert len(modal_title) > 0
        assert len(snippet_content) > 0
        
        ss5 = SCREENSHOT_DIR / "screenshot_05_citation_drawer_opened.png"
        page.screenshot(path=str(ss5), full_page=True)
        log(f"Captured: {ss5.name}")
        
        # Close Modal
        log("Closing citation modal drawer...")
        page.click(".close-modal-btn")
        page.wait_for_timeout(300)
        modal_class_closed = modal_overlay.get_attribute("class") or ""
        log(f"Modal Overlay Class after close: '{modal_class_closed}'")
        assert "hidden" in modal_class_closed, "Modal overlay should have hidden class after closing"

        # -------------------------------------------------------------
        # STEP 5: Provider Switching — Groq (Llama-3.3 70B)
        # -------------------------------------------------------------
        log("Step 5: Testing Provider Switching to Groq...")
        page.select_option("#llmProviderSelect", "groq")
        assert page.locator("#llmProviderSelect").input_value() == "groq"
        
        query_groq = "What amount was approved for the FY2026 share repurchase program?"
        page.fill("#queryInput", query_groq)
        log(f"Submitting Query via Groq: '{query_groq}'")
        page.click("#sendBtn")
        
        # Wait for assistant response
        page.wait_for_selector(".message-bubble.assistant:last-child .formatted-answer", timeout=45000)
        groq_assistant = page.locator(".message-bubble.assistant").last
        groq_answer = groq_assistant.locator(".formatted-answer").inner_text()
        groq_latency = groq_assistant.locator(".latency-badge").inner_text()
        groq_vbadge = groq_assistant.locator(".verification-badge").inner_text()
        log(f"Groq Answer: {groq_answer[:200]}...")
        log(f"Groq Latency: {groq_latency} | Verification: {groq_vbadge}")
        assert "500" in groq_answer or "repurchase" in groq_answer.lower()
        
        ss6 = SCREENSHOT_DIR / "screenshot_06_query_groq_llama.png"
        page.screenshot(path=str(ss6), full_page=True)
        log(f"Captured: {ss6.name}")

        # -------------------------------------------------------------
        # STEP 6: Provider Switching — Gemini Flash
        # -------------------------------------------------------------
        log("Step 6: Testing Provider Switching to Gemini Flash...")
        page.select_option("#llmProviderSelect", "gemini")
        assert page.locator("#llmProviderSelect").input_value() == "gemini"
        
        query_gemini = "What are the cash reserves and debt obligations mentioned in the summary?"
        page.fill("#queryInput", query_gemini)
        log(f"Submitting Query via Gemini: '{query_gemini}'")
        page.click("#sendBtn")
        
        page.wait_for_selector(".message-bubble.assistant:last-child .formatted-answer", timeout=45000)
        gemini_assistant = page.locator(".message-bubble.assistant").last
        gemini_answer = gemini_assistant.locator(".formatted-answer").inner_text()
        gemini_latency = gemini_assistant.locator(".latency-badge").inner_text()
        gemini_vbadge = gemini_assistant.locator(".verification-badge").inner_text()
        log(f"Gemini Answer: {gemini_answer[:200]}...")
        log(f"Gemini Latency: {gemini_latency} | Verification: {gemini_vbadge}")
        assert "4.2" in gemini_answer or "debt" in gemini_answer.lower() or "billion" in gemini_answer.lower()
        
        ss7 = SCREENSHOT_DIR / "screenshot_07_query_gemini_flash.png"
        page.screenshot(path=str(ss7), full_page=True)
        log(f"Captured: {ss7.name}")

        # -------------------------------------------------------------
        # STEP 7: Sample Query Flow
        # -------------------------------------------------------------
        log("Step 7: Testing Sample Query invocation...")
        # Check that useSampleQuery submits cleanly
        page.evaluate("useSampleQuery('What is the total revenue and profit margin breakdown in the financial tables?')")
        page.wait_for_selector(".message-bubble.assistant:last-child .formatted-answer", timeout=45000)
        sample_assistant = page.locator(".message-bubble.assistant").last
        sample_answer = sample_assistant.locator(".formatted-answer").inner_text()
        log(f"Sample Query Answer: {sample_answer[:200]}...")
        assert len(sample_answer) > 10
        
        ss8 = SCREENSHOT_DIR / "screenshot_08_sample_query_triggered.png"
        page.screenshot(path=str(ss8), full_page=True)
        log(f"Captured: {ss8.name}")

        log("Checking browser console errors...")
        errors = [m for m in console_messages if "[error]" in m.lower() or "[page_error]" in m.lower()]
        log(f"Total console messages: {len(console_messages)}, Errors: {len(errors)}")
        for err in errors:
            log(f"Console error: {err}")

        browser.close()
        log("ALL BROWSER TESTS COMPLETED SUCCESSFULLY!")
        return True, REPORT_LOG
    finally:
        try:
            playwright_ctx.stop()
        except Exception:
            pass
        if server_proc:
            log("Shutting down background server...")
            server_proc.terminate()

if __name__ == "__main__":
    success, logs = run_all_browser_tests()
    with open(BASE_DIR / "tests" / "browser_test_run.log", "w", encoding="utf-8") as f:
        f.write("\n".join(logs))
    sys.exit(0 if success else 1)
