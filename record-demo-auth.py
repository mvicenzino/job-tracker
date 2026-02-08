#!/usr/bin/env python3
"""Record demo - authenticate first via /demo route."""

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
        
        # Create context that will maintain session
        context = browser.new_context(
            viewport={'width': 1280, 'height': 720},
            record_video_dir='/Users/michaelvicenzino/clawd/stride-feature-branch/auth/',
            record_video_size={'width': 1280, 'height': 720}
        )
        page = context.new_page()
        
        # First authenticate via /demo (this logs us in)
        print("Authenticating via /demo...")
        page.goto('https://stride-jobs.vercel.app/demo')
        page.wait_for_load_state('networkidle')
        time.sleep(2)  # Let it fully load and redirect
        
        # Now we're logged in - navigate to dashboard
        print("Dashboard...")
        page.goto('https://stride-jobs.vercel.app/dashboard')
        page.wait_for_load_state('networkidle')
        time.sleep(0.5)
        page.evaluate('window.scrollBy(0, 200)')
        time.sleep(TIMINGS['dashboard'] - 1)
        page.evaluate('window.scrollTo(0, 0)')
        time.sleep(0.5)
        
        # Pipeline
        print("Pipeline...")
        page.goto('https://stride-jobs.vercel.app/pipeline')
        page.wait_for_load_state('networkidle')
        time.sleep(0.3)
        time.sleep(TIMINGS['pipeline'] - 0.3)
        
        # Schedule
        print("Schedule...")
        page.goto('https://stride-jobs.vercel.app/schedule')
        page.wait_for_load_state('networkidle')
        time.sleep(TIMINGS['schedule'])
        
        # Contacts
        print("Contacts...")
        page.goto('https://stride-jobs.vercel.app/contacts')
        page.wait_for_load_state('networkidle')
        time.sleep(0.5)
        page.evaluate('window.scrollBy(0, 150)')
        time.sleep(TIMINGS['contacts'] - 1)
        page.evaluate('window.scrollTo(0, 0)')
        time.sleep(0.5)
        
        # Companies
        print("Companies...")
        page.goto('https://stride-jobs.vercel.app/companies')
        page.wait_for_load_state('networkidle')
        time.sleep(0.3)
        page.evaluate('window.scrollBy(0, 150)')
        time.sleep(TIMINGS['companies'] - 0.3)
        
        # Back to Dashboard for closing
        print("Closing...")
        page.goto('https://stride-jobs.vercel.app/dashboard')
        page.wait_for_load_state('networkidle')
        time.sleep(TIMINGS['closing'])
        
        print("Done!")
        context.close()
        browser.close()

if __name__ == '__main__':
    record_demo()
