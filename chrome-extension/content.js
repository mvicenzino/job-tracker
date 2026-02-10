// Content script to extract LinkedIn data

// Detect page type
function getPageType() {
  const url = window.location.href;
  if (url.includes('linkedin.com/in/')) return 'profile';
  if (url.includes('linkedin.com/company/')) return 'company';
  if (url.includes('linkedin.com/jobs/view/') || url.includes('linkedin.com/jobs/collections/')) return 'job';
  return 'unknown';
}

// Helper: try multiple selectors, return first match text
function getText(selectors) {
  for (const sel of selectors) {
    try {
      const el = document.querySelector(sel);
      if (el && el.textContent.trim()) {
        return el.textContent.trim();
      }
    } catch (e) {}
  }
  return '';
}

// Extract LinkedIn profile data (contacts)
function extractProfileData() {
  const data = {
    type: 'contact',
    name: '',
    title: '',
    company: '',
    linkedin_url: window.location.href.split('?')[0],
    location: ''
  };

  // Extract name - multiple fallback selectors
  data.name = getText([
    'h1.text-heading-xlarge',
    'h1[class*="text-heading-xlarge"]',
    '.pv-top-card h1',
    '.ph5 h1',
    '.pv-text-details__left-panel h1',
    'section.pv-top-card h1',
    '[data-generated-suggestion-target="urn:li:fsu_profileActionDelegate"] h1',
    'main h1',
    'h1'
  ]);

  // Extract headline/title
  data.title = getText([
    '.text-body-medium.break-words',
    'div.text-body-medium.break-words',
    '.pv-top-card .text-body-medium',
    '.ph5 .text-body-medium',
    '.pv-text-details__left-panel .text-body-medium',
    '[data-generated-suggestion-target] + div',
    'main section .text-body-medium'
  ]);

  // Extract current company - try multiple approaches
  // Approach 1: From experience section
  const expSection = document.querySelector('#experience, section[id*="experience"], [id*="profilePagedListComponent"][id*="EXPERIENCE"]');
  if (expSection) {
    const section = expSection.closest('section') || expSection.parentElement || expSection;
    const firstExp = section.querySelector('li, [class*="pvs-entity"]');
    if (firstExp) {
      const companyEl = firstExp.querySelector('span[aria-hidden="true"]') ||
                        firstExp.querySelector('.t-14.t-normal') ||
                        firstExp.querySelector('[class*="t-normal"]');
      if (companyEl) {
        const text = companyEl.textContent.trim();
        data.company = text.split('·')[0].split('•')[0].trim();
      }
    }
  }

  // Approach 2: Company link in top card
  if (!data.company) {
    const companyLinks = document.querySelectorAll('a[href*="/company/"]');
    for (const link of companyLinks) {
      // Skip if it's in footer or nav
      if (link.closest('footer') || link.closest('nav')) continue;
      const text = link.textContent.trim();
      if (text && text.length > 1 && text.length < 100) {
        data.company = text;
        break;
      }
    }
  }

  // Approach 3: Extract from headline ("Title at Company")
  if (!data.company && data.title) {
    const atMatch = data.title.match(/(?:\bat\b|\s@\s)\s*([^|·•,]+)/i);
    if (atMatch) {
      data.company = atMatch[1].trim();
    }
  }

  // Extract location
  data.location = getText([
    '.text-body-small.inline.t-black--light.break-words',
    '.pv-top-card .pb2.pv-text-details__left-panel span.text-body-small',
    '.pv-text-details__left-panel span.text-body-small',
    '.ph5 span.text-body-small',
    'main span.text-body-small.inline'
  ]);

  // Clean up location if it includes connection info
  if (data.location && data.location.includes('connection')) {
    data.location = data.location.split(/\d+\s*(connections?|followers?)/i)[0].trim();
  }

  console.log('[Stride Extension] Extracted profile:', data);
  return data;
}

// Helper: find a dt/dd pair in the About section by label text
function getDDByLabel(label) {
  const dtElements = document.querySelectorAll('dt');
  for (const dt of dtElements) {
    if (dt.textContent.trim().toLowerCase().includes(label.toLowerCase())) {
      const dd = dt.nextElementSibling;
      if (dd && dd.tagName === 'DD') {
        return dd.textContent.trim();
      }
    }
  }
  return '';
}

// Extract LinkedIn company data
function extractCompanyData() {
  const data = {
    type: 'company',
    name: '',
    industry: '',
    size: '',
    location: '',
    website: '',
    description: '',
    linkedin_url: window.location.href.split('?')[0]
  };

  // Company name
  data.name = getText([
    'h1.org-top-card-summary__title',
    'h1[class*="org-top-card"]',
    '.org-top-card-summary h1',
    'h1[class*="top-card"] span',
    '[data-test-id="org-name"]',
    'main h1',
    'h1'
  ]);

  // Industry
  data.industry = getDDByLabel('industry') || getText([
    '.org-top-card-summary-info-list__info-item',
    '[class*="org-top-card"] .text-body-small',
    '[data-test-id="about-us__industry"] dd'
  ]);

  // Company size
  const rawSize = getDDByLabel('company size') || getText([
    'dd.org-about-company-module__company-size-definition-text',
    '[data-test-id="about-us__size"] dd'
  ]);
  if (rawSize) {
    const rangeMatch = rawSize.match(/[\d,]+-?[\d,]*/);
    data.size = rangeMatch ? rangeMatch[0] : rawSize.split('\n')[0].trim();
  }

  // Location/Headquarters
  data.location = getDDByLabel('headquarters') || getText([
    '[data-test-id="about-us__headquarters"] dd'
  ]);
  if (!data.location) {
    const locationEls = document.querySelectorAll('.org-top-card-summary-info-list__info-item');
    for (const el of locationEls) {
      const text = el.textContent.trim();
      if (text.includes(',') && !text.includes('employees')) {
        data.location = text;
        break;
      }
    }
  }

  // Website
  const websiteDDText = getDDByLabel('website');
  if (websiteDDText) {
    const dtElements = document.querySelectorAll('dt');
    for (const dt of dtElements) {
      if (dt.textContent.trim().toLowerCase().includes('website')) {
        const dd = dt.nextElementSibling;
        if (dd && dd.tagName === 'DD') {
          const link = dd.querySelector('a');
          data.website = link ? link.href : websiteDDText;
          break;
        }
      }
    }
  }
  if (!data.website) {
    const websiteEl = document.querySelector('a[data-test-id="about-us__website"]') ||
                      document.querySelector('.org-about-company-module__company-page-url a');
    if (websiteEl) {
      data.website = websiteEl.href || websiteEl.textContent.trim();
    }
  }

  // Description
  data.description = getDDByLabel('overview') || getText([
    '[class*="org-about-us"] p',
    '.org-about-company-module__description',
    'section[class*="about"] p',
    '.org-top-card-summary__tagline'
  ]);

  console.log('[Stride Extension] Extracted company:', data);
  return data;
}

// Extract LinkedIn job posting data
function extractJobData() {
  const data = {
    type: 'job',
    title: '',
    company: '',
    location: '',
    remote_type: '',
    description: '',
    job_url: window.location.href.split('?')[0],
    source: 'LinkedIn'
  };

  // Job title
  data.title = getText([
    'h1.job-details-jobs-unified-top-card__job-title',
    'h1.jobs-unified-top-card__job-title',
    '.job-details-jobs-unified-top-card__job-title',
    'h1[class*="job-title"]',
    '.jobs-details h1',
    'h1.t-24',
    'main h1',
    'h1'
  ]);

  // Company name
  data.company = getText([
    '.job-details-jobs-unified-top-card__company-name a',
    '.jobs-unified-top-card__company-name a',
    'a[data-tracking-control-name="public_jobs_topcard-org-name"]',
    '.job-details-jobs-unified-top-card__company-name',
    '[class*="jobs-unified-top-card__company-name"]',
    '.jobs-details [class*="company"]'
  ]);

  // Location
  data.location = getText([
    '.job-details-jobs-unified-top-card__primary-description-container .tvm__text',
    '.jobs-unified-top-card__bullet',
    '.job-details-jobs-unified-top-card__primary-description span',
    '.tvm__text--positive',
    '[class*="job-details"] [class*="location"]'
  ]);

  // Remote type
  const workplaceText = getText([
    '.job-details-jobs-unified-top-card__workplace-type',
    '[class*="workplace-type"]'
  ]).toLowerCase();
  
  if (workplaceText.includes('remote')) data.remote_type = 'remote';
  else if (workplaceText.includes('hybrid')) data.remote_type = 'hybrid';
  else if (workplaceText.includes('on-site') || workplaceText.includes('onsite')) data.remote_type = 'onsite';
  
  // Check location for remote indicators
  if (!data.remote_type && data.location) {
    const locLower = data.location.toLowerCase();
    if (locLower.includes('remote')) data.remote_type = 'remote';
    else if (locLower.includes('hybrid')) data.remote_type = 'hybrid';
  }

  // Job description - try multiple selectors
  const descSelectors = [
    '.jobs-description__content',
    '.jobs-description-content',
    '.jobs-description-content__text',
    '#job-details',
    '[class*="jobs-description"]',
    '[class*="description__text"]',
    '.job-details-about-the-job-module__description',
    'article[class*="jobs-description"]',
    '.jobs-box__html-content'
  ];
  
  for (const selector of descSelectors) {
    try {
      const el = document.querySelector(selector);
      if (el && el.textContent.trim().length > 50) {
        data.description = el.textContent.trim().substring(0, 5000);
        console.log('[Stride Extension] Found description with selector:', selector);
        break;
      }
    } catch (e) {}
  }
  
  // Fallback: try to find any large text block in the main content
  if (!data.description) {
    const mainContent = document.querySelector('main') || document.body;
    const textBlocks = mainContent.querySelectorAll('p, div, section');
    for (const block of textBlocks) {
      const text = block.textContent.trim();
      if (text.length > 200 && text.length < 10000 && !block.closest('nav') && !block.closest('header')) {
        data.description = text.substring(0, 5000);
        console.log('[Stride Extension] Found description via fallback');
        break;
      }
    }
  }

  console.log('[Stride Extension] Extracted job:', data);
  return data;
}

// Main extraction function
function extractData() {
  const pageType = getPageType();
  console.log('[Stride Extension] Page type:', pageType);

  switch (pageType) {
    case 'profile':
      return extractProfileData();
    case 'company':
      return extractCompanyData();
    case 'job':
      return extractJobData();
    default:
      return { type: 'unknown', pageType };
  }
}

// Listen for messages from popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log('[Stride Extension] Received message:', request.action);
  if (request.action === 'getProfileData' || request.action === 'getData') {
    const data = extractData();
    sendResponse(data);
  }
  if (request.action === 'getPageType') {
    sendResponse({ pageType: getPageType() });
  }
  return true;
});
