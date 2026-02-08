#!/usr/bin/env python3
"""Record demo with NO white screens - pre-load pages before recording."""

from playwright.sync_api import sync_playwright
import time

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
        
        # Pre-load all pages first (no recording)
        print("Pre-loading pages...")
        ctx_preload = browser.new_context(viewport={'width': 1280, 'height': 720})
        pg = ctx_preload.new_page()
        
        for url in ['/demo', '/dashboard', '/pipeline', '/schedule', '/contacts', '/companies']:
            pg.goto(f'https://stride-jobs.vercel.app{url}')
            pg.wait_for_load_state('networkidle')
            time.sleep(0.5)
        ctx_preload.close()
        
        # Now record with warm cache
        print("Starting recording...")
        context = browser.new_context(
            viewport={'width': 1280, 'height': 720},
            record_video_dir='/Users/michaelvicenzino/clawd/stride-feature-branch/nowhite/',
            record_video_size={'width': 1280, 'height': 720}
        )
        page = context.new_page()
        
        # Dashboard - go and wait for content
        print("Dashboard...")
        page.goto('https://stride-jobs.vercel.app/dashboard')
        page.wait_for_load_state('networkidle')
        page.wait_for_timeout(500)  # Brief settle
        time.sleep(TIMINGS['dashboard'] - 0.5)
        
        # Pipeline
        print("Pipeline...")
        page.goto('https://stride-jobs.vercel.app/pipeline')
        page.wait_for_load_state('networkidle')
        page.wait_for_timeout(300)
        time.sleep(TIMINGS['pipeline'] - 0.3)
        
        # Schedule
        print("Schedule...")
        page.goto('https://stride-jobs.vercel.app/schedule')
        page.wait_for_load_state('networkidle')
        page.wait_for_timeout(300)
        time.sleep(TIMINGS['schedule'] - 0.3)
        
        # Contacts
        print("Contacts...")
        page.goto('https://stride-jobs.vercel.app/contacts')
        page.wait_for_load_state('networkidle')
        page.wait_for_timeout(300)
        page.evaluate('window.scrollBy(0, 150)')
        time.sleep(TIMINGS['contacts'] - 0.8)
        page.evaluate('window.scrollTo(0, 0)')
        time.sleep(0.5)
        
        # Companies
        print("Companies...")
        page.goto('https://stride-jobs.vercel.app/companies')
        page.wait_for_load_state('networkidle')
        page.wait_for_timeout(300)
        page.evaluate('window.scrollBy(0, 150)')
        time.sleep(TIMINGS['companies'] - 0.3)
        
        # Back to Dashboard for closing
        print("Closing...")
        page.goto('https://stride-jobs.vercel.app/dashboard')
        page.wait_for_load_state('networkidle')
        page.wait_for_timeout(300)
        time.sleep(TIMINGS['closing'] - 0.3)
        
        print("Done!")
        context.close()
        browser.close()

if __name__ == '__main__':
    record_demo()
