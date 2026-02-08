#!/usr/bin/env python3
"""Record a precisely-timed demo video to sync with voiceover."""

from playwright.sync_api import sync_playwright
import time

# Exact durations from voiceover (in seconds)
TIMINGS = {
    'dashboard': 10.76,
    'pipeline': 10.71,
    'schedule': 8.71,
    'contacts': 11.16,
    'companies': 8.21,
    'closing': 8.61,
}

def record_demo():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1280, 'height': 720},
            record_video_dir='/Users/michaelvicenzino/clawd/stride-feature-branch/synced/',
            record_video_size={'width': 1280, 'height': 720}
        )
        page = context.new_page()
        
        # SECTION 1: Dashboard (10.76s)
        print("Recording Dashboard...")
        page.goto('https://stride-jobs.vercel.app/demo')
        page.wait_for_load_state('networkidle')
        time.sleep(2)  # Initial load settle
        page.evaluate('window.scrollBy(0, 250)')
        time.sleep(TIMINGS['dashboard'] - 3)
        page.evaluate('window.scrollTo(0, 0)')
        time.sleep(1)
        
        # SECTION 2: Pipeline (10.71s)
        print("Recording Pipeline...")
        page.goto('https://stride-jobs.vercel.app/pipeline')
        page.wait_for_load_state('networkidle')
        time.sleep(1)
        page.evaluate('window.scrollBy(0, 50)')
        time.sleep(TIMINGS['pipeline'] - 1.5)
        time.sleep(0.5)
        
        # SECTION 3: Schedule (8.71s)
        print("Recording Schedule...")
        page.goto('https://stride-jobs.vercel.app/schedule')
        page.wait_for_load_state('networkidle')
        time.sleep(TIMINGS['schedule'])
        
        # SECTION 4: Contacts (11.16s)
        print("Recording Contacts...")
        page.goto('https://stride-jobs.vercel.app/contacts')
        page.wait_for_load_state('networkidle')
        time.sleep(2)
        page.evaluate('window.scrollBy(0, 200)')
        time.sleep(TIMINGS['contacts'] - 3)
        page.evaluate('window.scrollTo(0, 0)')
        time.sleep(1)
        
        # SECTION 5: Companies (8.21s)
        print("Recording Companies...")
        page.goto('https://stride-jobs.vercel.app/companies')
        page.wait_for_load_state('networkidle')
        time.sleep(1)
        page.evaluate('window.scrollBy(0, 150)')
        time.sleep(TIMINGS['companies'] - 1)
        
        # SECTION 6: Back to Dashboard for closing (8.61s)
        print("Recording Closing...")
        page.goto('https://stride-jobs.vercel.app/dashboard')
        page.wait_for_load_state('networkidle')
        time.sleep(TIMINGS['closing'])
        
        print("Finishing...")
        context.close()
        browser.close()
        print("Done! Synced video saved.")

if __name__ == '__main__':
    record_demo()
