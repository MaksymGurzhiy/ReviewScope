"""Auto-capture UI screenshots with playwright.

Strategy:
  1. Take a fresh screenshot of every PUBLIC page that does not require auth.
  2. For authenticated pages, fall back to the existing _extracted_images/*.png
     until the user provides credentials.
"""
from __future__ import annotations
import os
import shutil
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
DIAG = ROOT / "docs" / "diagrams"
EXTRACTED = ROOT / "_extracted_images"
DIAG.mkdir(parents=True, exist_ok=True)

FRONTEND = os.environ.get("RS_FRONTEND_URL", "http://localhost:3000")
EMAIL = os.environ.get("RS_EMAIL", "")
PASSWORD = os.environ.get("RS_PASSWORD", "")

VIEWPORT = {"width": 1280, "height": 800}


def capture_public_pages(context):
    page = context.new_page()
    page.set_viewport_size(VIEWPORT)

    # --- Landing / Login ---
    page.goto(FRONTEND, wait_until="networkidle", timeout=30_000)
    page.wait_for_timeout(1000)
    page.screenshot(path=str(DIAG / "fig_3_3_login.png"), full_page=False)
    print("  -> fig_3_3_login.png")

    # try register / sign-up if visible
    try:
        page.click("text=/Sign up|Register|Зареєструватися|Реєстрація/i", timeout=2000)
        page.wait_for_timeout(800)
        page.screenshot(path=str(DIAG / "fig_3_4_register.png"))
        print("  -> fig_3_4_register.png")
    except Exception:
        # fallback: re-use login screen
        shutil.copy(DIAG / "fig_3_3_login.png", DIAG / "fig_3_4_register.png")
        print("  -> fig_3_4_register.png  (fallback - same as login)")

    page.close()


def capture_authenticated_pages(context):
    """Try to log in and snap dashboard/upload/results."""
    if not EMAIL or not PASSWORD:
        print("  (skipping authenticated capture - no RS_EMAIL/RS_PASSWORD)")
        return

    page = context.new_page()
    page.set_viewport_size(VIEWPORT)
    page.goto(FRONTEND, wait_until="networkidle")
    page.fill('input[type="email"]', EMAIL)
    page.fill('input[type="password"]', PASSWORD)
    page.click('button:has-text("Sign in"), button:has-text("Login"), button:has-text("Вхід")')
    page.wait_for_load_state("networkidle", timeout=15_000)
    page.wait_for_timeout(1500)

    page.screenshot(path=str(DIAG / "fig_3_5_dashboard.png"))
    print("  -> fig_3_5_dashboard.png")

    # try open upload screen
    try:
        page.click("text=/New Analysis|Upload|Завантажити|Створити/i", timeout=2000)
        page.wait_for_timeout(800)
        page.screenshot(path=str(DIAG / "fig_3_6_upload.png"))
        print("  -> fig_3_6_upload.png")
    except Exception:
        print("  (could not navigate to upload screen)")

    page.close()


def fallback_from_extracted():
    """Use already-extracted screenshots if playwright failed / user not logged in."""
    mapping = {
        "image1.png": "fig_3_3_login.png",       # landing
        "image2.png": "fig_3_4_upload.png",      # upload widget
        "image3.png": "fig_3_5_loaded.png",      # file loaded
        "image4.png": "fig_3_6_progress.png",    # progress
        "image5.png": "fig_3_7_sentiment.png",   # sentiment
        "image6.png": "fig_3_8_keyphrases.png",  # key phrases
        "image7.png": "fig_3_9_insights.png",    # insights & recommendations
        "image8.png": "fig_3_10_full.png",       # whole report
    }
    for src, dst in mapping.items():
        src_path = EXTRACTED / src
        dst_path = DIAG / dst
        if src_path.exists() and not dst_path.exists():
            shutil.copy(src_path, dst_path)
            print(f"  fallback {src} -> {dst}")


def main():
    print(f"Capturing UI screenshots from {FRONTEND} ...")
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            ctx = browser.new_context()
            try:
                capture_public_pages(ctx)
                capture_authenticated_pages(ctx)
            finally:
                browser.close()
    except Exception as e:  # noqa: BLE001
        print(f"  playwright error: {e}")

    print("Filling missing screenshots from _extracted_images ...")
    fallback_from_extracted()
    print("Done.")


if __name__ == "__main__":
    main()
