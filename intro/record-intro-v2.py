#!/usr/bin/env python3
"""Record the Apple-style intro v2 - larger logo, slower fades."""

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
        
        page.goto('file:///Users/michaelvicenzino/clawd/stride-feature-branch/intro/intro-apple-v2.html')
        
        # Timing:
        # 0-1s: black
        # 1-4s: logo fading in (3s animation)
        # 5-7.5s: tagline fading in (2.5s animation)
        # 7.5-12s: hold
        # Record 12 seconds total - we'll trim to exact length needed
        time.sleep(12)
        
        context.close()
        browser.close()
        print("Intro v2 recorded!")

if __name__ == '__main__':
    record_intro()
