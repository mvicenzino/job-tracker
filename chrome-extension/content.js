// Content script to extract LinkedIn data

// Detect page type
function getPageType() {
  const url = window.location.href;
  if (url.includes('linkedin.com/in/')) return 'profile';
  if (url.includes('linkedin.com/company/')) return 'company';
  if (url.includes('linkedin.com/jobs/view/') || url.includes('linkedin.com/jobs/collections/')) return 'job';
  return 'unknown';
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

  // Extract name
  const nameEl = document.querySelector('h1.text-heading-xlarge') ||
                 document.querySelector('h1[class*="text-heading"]') ||
                 document.querySelector('.pv-top-card h1') ||
                 document.querySelector('.ph5 h1') ||
                 document.querySelector('h1');
  if (nameEl) {
    data.name = nameEl.textContent.trim();
  }

  // Extract headline/title
  const headlineEl = document.querySelector('.text-body-medium.break-words') ||
                     document.querySelector('[data-generated-suggestion-target]') ||
                     document.querySelector('.pv-top-card .text-body-medium') ||
                     document.querySelector('.ph5 .text-body-medium');
  if (headlineEl) {
    data.title = headlineEl.textContent.trim();
  }

  // Extract current company from experience
  const experienceSection = document.querySelector('#experience') ||
                            document.querySelector('section[id*="experience"]');
  if (experienceSection) {
    const section = experienceSection.closest('section') || experienceSection;
    const currentRole = section.querySelector('li');
    if (currentRole) {
      const companyEl = currentRole.querySelector('.t-14.t-normal span[aria-hidden="true"]') ||
                        currentRole.querySelector('.t-14.t-normal');
      if (companyEl) {
        const companyText = companyEl.textContent.trim();
        data.company = companyText.split('·')[0].trim();
      }
    }
  }

  // Fallback: try to get company from top card
  if (!data.company) {
    const topCardLinks = document.querySelectorAll('.pv-top-card a[href*="/company/"], .ph5 a[href*="/company/"]');
    if (topCardLinks.length > 0) {
      data.company = topCardLinks[0].textContent.trim();
    }
  }

  // Fallback: extract from headline
  if (!data.company && data.title) {
    const atMatch = data.title.match(/(?:at|@)\s+([^|·,]+)/i);
    if (atMatch) {
      data.company = atMatch[1].trim();
    }
  }

  // Extract location
  const locationEl = document.querySelector('.text-body-small.inline.t-black--light.break-words') ||
                     document.querySelector('.pv-top-card .pb2.pv-text-details__left-panel span');
  if (locationEl) {
    data.location = locationEl.textContent.trim();
  }

  return data;
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
  const nameEl = document.querySelector('h1.org-top-card-summary__title') ||
                 document.querySelector('h1[class*="org-top-card"]') ||
                 document.querySelector('.org-top-card-summary h1') ||
                 document.querySelector('h1');
  if (nameEl) {
    data.name = nameEl.textContent.trim();
  }

  // Industry
  const industryEl = document.querySelector('.org-top-card-summary-info-list__info-item') ||
                     document.querySelector('[class*="org-top-card"] .text-body-small');
  if (industryEl) {
    data.industry = industryEl.textContent.trim();
  }

  // Company size - look in about section
  const sizeEl = document.querySelector('dd.org-about-company-module__company-size-definition-text') ||
                 document.querySelector('[data-test-id="about-us__size"] dd');
  if (sizeEl) {
    data.size = sizeEl.textContent.trim().split(' ')[0]; // Get just the number range
  }

  // Location
  const locationEls = document.querySelectorAll('.org-top-card-summary-info-list__info-item');
  locationEls.forEach(el => {
    const text = el.textContent.trim();
    if (text.includes(',') && !text.includes('employees')) {
      data.location = text;
    }
  });

  // Website
  const websiteEl = document.querySelector('a[data-test-id="about-us__website"] span') ||
                    document.querySelector('.org-about-company-module__company-page-url a');
  if (websiteEl) {
    data.website = websiteEl.closest('a')?.href || websiteEl.textContent.trim();
  }

  // Description
  const descEl = document.querySelector('.org-top-card-summary__tagline') ||
                 document.querySelector('p[class*="org-about-us"]');
  if (descEl) {
    data.description = descEl.textContent.trim();
  }

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
  const titleEl = document.querySelector('h1.job-details-jobs-unified-top-card__job-title') ||
                  document.querySelector('h1.jobs-unified-top-card__job-title') ||
                  document.querySelector('.job-details-jobs-unified-top-card__job-title') ||
                  document.querySelector('h1[class*="job-title"]') ||
                  document.querySelector('.jobs-details h1') ||
                  document.querySelector('h1');
  if (titleEl) {
    data.title = titleEl.textContent.trim();
  }

  // Company name
  const companyEl = document.querySelector('.job-details-jobs-unified-top-card__company-name a') ||
                    document.querySelector('.jobs-unified-top-card__company-name a') ||
                    document.querySelector('a[data-tracking-control-name="public_jobs_topcard-org-name"]') ||
                    document.querySelector('.job-details-jobs-unified-top-card__company-name') ||
                    document.querySelector('[class*="company-name"]');
  if (companyEl) {
    data.company = companyEl.textContent.trim();
  }

  // Location
  const locationEl = document.querySelector('.job-details-jobs-unified-top-card__primary-description-container .tvm__text') ||
                     document.querySelector('.jobs-unified-top-card__bullet') ||
                     document.querySelector('.job-details-jobs-unified-top-card__primary-description span') ||
                     document.querySelector('[class*="job-details"] [class*="location"]');
  if (locationEl) {
    data.location = locationEl.textContent.trim();
  }

  // Remote type - check for remote/hybrid/onsite indicators
  const workplaceEl = document.querySelector('.job-details-jobs-unified-top-card__workplace-type') ||
                      document.querySelector('[class*="workplace-type"]');
  if (workplaceEl) {
    const text = workplaceEl.textContent.toLowerCase();
    if (text.includes('remote')) data.remote_type = 'remote';
    else if (text.includes('hybrid')) data.remote_type = 'hybrid';
    else if (text.includes('on-site') || text.includes('onsite')) data.remote_type = 'onsite';
  }

  // Check location text for remote indicators
  if (!data.remote_type && data.location) {
    const locLower = data.location.toLowerCase();
    if (locLower.includes('remote')) data.remote_type = 'remote';
    else if (locLower.includes('hybrid')) data.remote_type = 'hybrid';
  }

  // Job description
  const descEl = document.querySelector('.jobs-description__content') ||
                 document.querySelector('.job-details-jobs-unified-top-card__job-insight') ||
                 document.querySelector('[class*="description"]');
  if (descEl) {
    data.description = descEl.textContent.trim().substring(0, 2000); // Limit length
  }

  return data;
}

// Main extraction function
function extractData() {
  const pageType = getPageType();

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
  if (request.action === 'getProfileData' || request.action === 'getData') {
    const data = extractData();
    sendResponse(data);
  }
  if (request.action === 'getPageType') {
    sendResponse({ pageType: getPageType() });
  }
  return true;
});
