#!/usr/bin/env python3
"""Record the animated intro."""

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
        page.goto('file:///Users/michaelvicenzino/clawd/stride-feature-branch/intro/intro.html')
        
        # Wait for animations to play (3.5 seconds)
        time.sleep(3.5)
        
        context.close()
        browser.close()
        print("Intro recorded!")

if __name__ == '__main__':
    record_intro()
