#!/usr/bin/env python3
"""Record a mobile demo video of Stride app walkthrough for social media."""

from playwright.sync_api import sync_playwright
import time

def record_demo():
    with sync_playwright() as p:
        # Launch browser with video recording - mobile size (9:16 for socials)
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 390, 'height': 844},
            device_scale_factor=2,
            record_video_dir='/Users/michaelvicenzino/clawd/stride-feature-branch/',
            record_video_size={'width': 390, 'height': 844}
        )
        page = context.new_page()
        
        # Go to demo mode
        print("Opening demo mode...")
        page.goto('https://stride-jobs.vercel.app/demo')
        page.wait_for_load_state('networkidle')
        time.sleep(2.5)
        
        # Dashboard - scroll to show content
        print("Showing dashboard...")
        time.sleep(1.5)
        page.evaluate('window.scrollBy(0, 250)')
        time.sleep(1.5)
        page.evaluate('window.scrollTo(0, 0)')
        time.sleep(1)
        
        # Navigate to Pipeline
        print("Navigating to Pipeline...")
        page.goto('https://stride-jobs.vercel.app/pipeline')
        page.wait_for_load_state('networkidle')
        time.sleep(2.5)
        
        # Navigate to Schedule
        print("Navigating to Schedule...")
        page.goto('https://stride-jobs.vercel.app/schedule')
        page.wait_for_load_state('networkidle')
        time.sleep(2)
        
        # Navigate to Contacts
        print("Navigating to Contacts...")
        page.goto('https://stride-jobs.vercel.app/contacts')
        page.wait_for_load_state('networkidle')
        time.sleep(1.5)
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
        
        print("Done! Mobile video saved.")

if __name__ == '__main__':
    record_demo()
