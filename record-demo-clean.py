#!/usr/bin/env python3
"""Record demo - wait for content to be visible before starting video capture."""

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
        
        # First, load the page WITHOUT recording to let it fully render
        context_preload = browser.new_context(viewport={'width': 1280, 'height': 720})
        page_preload = context_preload.new_page()
        page_preload.goto('https://stride-jobs.vercel.app/demo')
        page_preload.wait_for_load_state('networkidle')
        page_preload.wait_for_selector('text=Dashboard', timeout=10000)
        time.sleep(1)  # Extra settle time
        context_preload.close()
        
        # Now start recording with a fresh context
        context = browser.new_context(
            viewport={'width': 1280, 'height': 720},
            record_video_dir='/Users/michaelvicenzino/clawd/stride-feature-branch/clean/',
            record_video_size={'width': 1280, 'height': 720}
        )
        page = context.new_page()
        
        # SECTION 1: Dashboard
        print("Recording Dashboard...")
        page.goto('https://stride-jobs.vercel.app/dashboard')
        page.wait_for_load_state('networkidle')
        page.wait_for_selector('text=Dashboard', timeout=10000)
        time.sleep(0.3)  # Brief settle
        page.evaluate('window.scrollBy(0, 250)')
        time.sleep(TIMINGS['dashboard'] - 1)
        page.evaluate('window.scrollTo(0, 0)')
        time.sleep(0.7)
        
        # SECTION 2: Pipeline
        print("Recording Pipeline...")
        page.goto('https://stride-jobs.vercel.app/pipeline')
        page.wait_for_load_state('networkidle')
        time.sleep(0.3)
        page.evaluate('window.scrollBy(0, 50)')
        time.sleep(TIMINGS['pipeline'] - 0.3)
        
        # SECTION 3: Schedule
        print("Recording Schedule...")
        page.goto('https://stride-jobs.vercel.app/schedule')
        page.wait_for_load_state('networkidle')
        time.sleep(TIMINGS['schedule'])
        
        # SECTION 4: Contacts
        print("Recording Contacts...")
        page.goto('https://stride-jobs.vercel.app/contacts')
        page.wait_for_load_state('networkidle')
        time.sleep(1)
        page.evaluate('window.scrollBy(0, 200)')
        time.sleep(TIMINGS['contacts'] - 2)
        page.evaluate('window.scrollTo(0, 0)')
        time.sleep(1)
        
        # SECTION 5: Companies
        print("Recording Companies...")
        page.goto('https://stride-jobs.vercel.app/companies')
        page.wait_for_load_state('networkidle')
        time.sleep(0.5)
        page.evaluate('window.scrollBy(0, 150)')
        time.sleep(TIMINGS['companies'] - 0.5)
        
        # SECTION 6: Closing
        print("Recording Closing...")
        page.goto('https://stride-jobs.vercel.app/dashboard')
        page.wait_for_load_state('networkidle')
        time.sleep(TIMINGS['closing'])
        
        print("Finishing...")
        context.close()
        browser.close()
        print("Clean demo recorded!")

if __name__ == '__main__':
    record_demo()
