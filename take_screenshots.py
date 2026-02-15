"""Take uniform feature screenshots from the demo app using Playwright."""
from playwright.sync_api import sync_playwright
import time

BASE = "http://localhost:5002"
OUT = "src/web/static/img/features"
WIDTH = 1280
HEIGHT = 800

# Mock AI analysis HTML using actual template class names
MOCK_AI_ANALYSIS = """
<div class="fit-score-section">
    <div class="fit-score high">92%</div>
    <div class="fit-score-label">Excellent Match</div>
    <p class="fit-summary">Your experience in full-stack development and distributed systems strongly aligns with this role. Your React and Node.js expertise are direct matches, and your leadership experience adds significant value.</p>
</div>
<div class="fit-section">
    <h4>Matching Skills</h4>
    <div class="fit-pills">
        <span class="fit-pill match">React</span>
        <span class="fit-pill match">Node.js</span>
        <span class="fit-pill match">TypeScript</span>
        <span class="fit-pill match">AWS</span>
        <span class="fit-pill match">PostgreSQL</span>
        <span class="fit-pill match">System Design</span>
        <span class="fit-pill match">Team Leadership</span>
    </div>
</div>
<div class="fit-section">
    <h4>Skills to Develop</h4>
    <div class="fit-pills">
        <span class="fit-pill gap">Kubernetes</span>
        <span class="fit-pill gap">GraphQL</span>
        <span class="fit-pill gap">CI/CD Pipelines</span>
    </div>
</div>
<div class="fit-section">
    <h4>Suggestions</h4>
    <div class="suggestions-list">
        <div class="suggestion-item">
            <span class="suggestion-priority" style="background:#16a34a"></span>
            <span class="suggestion-text">Emphasize your experience scaling distributed systems — this is a core requirement.</span>
        </div>
        <div class="suggestion-item">
            <span class="suggestion-priority" style="background:#2563eb"></span>
            <span class="suggestion-text">Add specific metrics to your infrastructure work (e.g., uptime, latency improvements).</span>
        </div>
        <div class="suggestion-item">
            <span class="suggestion-priority" style="background:#f59e0b"></span>
            <span class="suggestion-text">Mention any Kubernetes or container orchestration experience, even if informal.</span>
        </div>
    </div>
</div>
"""

MOCK_COVER_LETTER = """Dear Hiring Team,

I'm excited to apply for the Senior Software Engineer position at Stripe. With 7+ years of experience building scalable web applications and a deep passion for developer tools, I believe I'd be a strong addition to your engineering team.

In my current role, I've led the architecture of a distributed payment processing system handling 50M+ daily transactions — experience that directly maps to Stripe's core challenges. My expertise in React, Node.js, and cloud infrastructure (AWS) has allowed me to ship products that serve millions of users while maintaining 99.99% uptime.

What draws me to Stripe specifically is your commitment to building economic infrastructure for the internet. I've been a Stripe customer and advocate for years, and the opportunity to contribute to products I genuinely believe in is incredibly motivating.

I'd love to discuss how my background in scalable systems and developer experience can contribute to Stripe's mission. Thank you for your consideration.

Best regards,
Sarah Chen"""


def hide_chrome(page):
    """Hide demo banner, sidebar, and expand main content."""
    page.evaluate("""
        document.querySelectorAll('.demo-banner').forEach(el => el.style.display = 'none');
        const sidebar = document.querySelector('.sidebar');
        if (sidebar) sidebar.style.display = 'none';
        const main = document.querySelector('.main-content');
        if (main) { main.style.marginLeft = '0'; main.style.maxWidth = '100%'; }
    """)
    time.sleep(0.3)


def get_main(page):
    """Get the main content element for screenshotting."""
    return page.query_selector(".main-content") or page.query_selector("main") or page


def take_screenshots():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": WIDTH, "height": HEIGHT},
            device_scale_factor=2,
        )
        page = context.new_page()

        # Login via demo with refresh to get fresh data (today's dates for schedule)
        print("Logging into demo (refreshing data)...")
        page.goto(f"{BASE}/demo?refresh=1")
        page.wait_for_load_state("networkidle")
        time.sleep(1)

        # --- Schedule Screenshot ---
        print("Taking schedule screenshot...")
        page.goto(f"{BASE}/schedule")
        page.wait_for_load_state("networkidle")
        time.sleep(0.5)
        hide_chrome(page)

        # Clip to the viewport area showing Today section (not the full scrollable page)
        page.screenshot(
            path=f"{OUT}/schedule.png",
            clip={"x": 0, "y": 0, "width": WIDTH, "height": HEIGHT},
        )
        print(f"  Saved {OUT}/schedule.png")

        # --- Contacts Screenshot ---
        print("Taking contacts screenshot...")
        page.goto(f"{BASE}/contacts")
        page.wait_for_load_state("networkidle")
        time.sleep(0.5)
        hide_chrome(page)
        page.screenshot(
            path=f"{OUT}/contacts.png",
            clip={"x": 0, "y": 0, "width": WIDTH, "height": HEIGHT},
        )
        print(f"  Saved {OUT}/contacts.png")

        # --- AI Analysis Screenshot ---
        print("Taking AI analysis screenshot...")
        page.goto(f"{BASE}/applications")
        page.wait_for_load_state("networkidle")
        time.sleep(0.5)

        # Find the first "View" button in the applications table (not the "Add Lead" button)
        view_btn = page.query_selector("table.data-table a.btn.btn-sm")
        if view_btn:
            href = view_btn.get_attribute("href")
            print(f"  Navigating to {href}")
            page.goto(f"{BASE}{href}")
        else:
            print("  WARNING: Could not find application detail link, trying /applications/1")
            page.goto(f"{BASE}/applications/1")
        page.wait_for_load_state("networkidle")
        time.sleep(0.5)

        # Check we're on a detail page
        page_title = page.query_selector("h1")
        if page_title:
            print(f"  Page title: {page_title.text_content().strip()}")

        hide_chrome(page)

        # Inject mock AI analysis — replace entire card body since AI is disabled
        analysis_html = MOCK_AI_ANALYSIS.replace('`', '\\`').replace('\n', ' ')
        cover_text = MOCK_COVER_LETTER.strip().replace('`', '\\`').replace('\n', '\\n')

        page.evaluate(f"""
            // Replace resume fit card body content (AI may be disabled, so replace the whole body)
            const fitCard = document.querySelector('.resume-fit-card');
            if (fitCard) {{
                const cardBody = fitCard.querySelector('.card-body');
                if (cardBody) {{
                    cardBody.innerHTML = `{analysis_html}`;
                }}
            }}

            // Replace cover letter section content
            // Find the "Cover Letter" h3 heading and replace sibling content
            const detailSections = document.querySelectorAll('.detail-section');
            detailSections.forEach(section => {{
                const h3 = section.querySelector('h3');
                if (h3 && h3.textContent.trim() === 'Cover Letter') {{
                    // Remove empty state, disabled message, and prompts
                    const emptyState = section.querySelector('.empty-state');
                    if (emptyState) emptyState.remove();
                    const aiDisabled = section.querySelector('.ai-disabled');
                    if (aiDisabled) aiDisabled.remove();
                    const prompt = section.querySelector('.cover-letter-prompt');
                    if (prompt) prompt.remove();

                    // Check if cover-letter-content exists, if not create it
                    let content = section.querySelector('.cover-letter-content');
                    if (!content) {{
                        content = document.createElement('div');
                        content.className = 'detail-text cover-letter-content';
                        content.id = 'coverLetterContent';
                        h3.after(content);
                    }}
                    content.textContent = `{cover_text}`;
                    content.style.display = 'block';
                    content.style.whiteSpace = 'pre-wrap';
                }}
            }});

            // Also hide the loading/error elements if they exist
            ['coverLetterLoading', 'coverLetterResult', 'coverLetterError'].forEach(id => {{
                const el = document.getElementById(id);
                if (el) el.style.display = 'none';
            }});
        """)
        time.sleep(0.5)

        # Scroll to show the AI analysis section prominently
        page.evaluate("""
            const fitCard = document.querySelector('.resume-fit-card');
            if (fitCard) fitCard.scrollIntoView({ block: 'start', behavior: 'instant' });
            window.scrollBy(0, -80);
        """)
        time.sleep(0.3)

        page.screenshot(
            path=f"{OUT}/ai-analysis.png",
            clip={"x": 0, "y": 0, "width": WIDTH, "height": HEIGHT},
        )
        print(f"  Saved {OUT}/ai-analysis.png")

        browser.close()
        print("Done!")


if __name__ == "__main__":
    take_screenshots()
