#!/usr/bin/env python3
"""Record a demo video of Stride app walkthrough."""

from playwright.sync_api import sync_playwright
import time

def record_demo():
    with sync_playwright() as p:
        # Launch browser with video recording (headless for server)
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1280, 'height': 720},
            record_video_dir='/Users/michaelvicenzino/clawd/stride-feature-branch/',
            record_video_size={'width': 1280, 'height': 720}
        )
        page = context.new_page()
        
        # Go to demo mode (auto-logs in with sample data)
        print("Opening demo mode...")
        page.goto('https://stride-jobs.vercel.app/demo')
        page.wait_for_load_state('networkidle')
        time.sleep(2.5)
        
        # Dashboard - scroll to show content
        print("Showing dashboard...")
        time.sleep(2)
        page.evaluate('window.scrollBy(0, 300)')
        time.sleep(1.5)
        page.evaluate('window.scrollTo(0, 0)')
        time.sleep(1)
        
        # Navigate to Pipeline via URL
        print("Navigating to Pipeline...")
        page.goto('https://stride-jobs.vercel.app/pipeline')
        page.wait_for_load_state('networkidle')
        time.sleep(3)
        
        # Scroll pipeline to show columns
        page.evaluate('window.scrollBy(0, 100)')
        time.sleep(1.5)
        page.evaluate('window.scrollTo(0, 0)')
        time.sleep(1)
        
        # Navigate to Schedule
        print("Navigating to Schedule...")
        page.goto('https://stride-jobs.vercel.app/schedule')
        page.wait_for_load_state('networkidle')
        time.sleep(2.5)
        
        # Navigate to Contacts
        print("Navigating to Contacts...")
        page.goto('https://stride-jobs.vercel.app/contacts')
        page.wait_for_load_state('networkidle')
        time.sleep(2)
        page.evaluate('window.scrollBy(0, 200)')
        time.sleep(1.5)
        page.evaluate('window.scrollTo(0, 0)')
        time.sleep(1)
        
        # Navigate to Companies
        print("Navigating to Companies...")
        page.goto('https://stride-jobs.vercel.app/companies')
        page.wait_for_load_state('networkidle')
        time.sleep(2)
        page.evaluate('window.scrollBy(0, 200)')
        time.sleep(1.5)
        
        # Back to Dashboard
        print("Back to Dashboard...")
        page.goto('https://stride-jobs.vercel.app/dashboard')
        page.wait_for_load_state('networkidle')
        time.sleep(2)
        
        # Close to save video
        print("Finishing recording...")
        context.close()
        browser.close()
        
        print("Done! Video saved.")

if __name__ == '__main__':
    record_demo()
