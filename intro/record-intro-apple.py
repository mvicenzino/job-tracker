#!/usr/bin/env python3
"""Record the Apple-style animated intro - slow and elegant."""

from playwright.sync_api import sync_playwright
import time

def record_intro():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1280, 'height': 720},
            record_video_dir='/Users/michaelvicenzino/clawd/stride-feature-branch/intro/',
            record_video_size={'width': 1280, 'height': 720}
        )
        page = context.new_page()
        
        # Load the intro
        page.goto('file:///Users/michaelvicenzino/clawd/stride-feature-branch/intro/intro-apple.html')
        
        # Wait for slow animations to complete + hold time
        # Logo: 0.5s delay + 2s animation = 2.5s
        # Tagline: 3s delay + 2s animation = 5s
        # Hold for 3 more seconds = 8s total
        time.sleep(8)
        
        context.close()
        browser.close()
        print("Apple-style intro recorded!")

if __name__ == '__main__':
    record_intro()
