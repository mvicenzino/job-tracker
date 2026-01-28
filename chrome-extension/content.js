// Content script to extract LinkedIn profile data
function extractProfileData() {
  const data = {
    name: '',
    title: '',
    company: '',
    linkedin_url: window.location.href.split('?')[0],
    location: ''
  };

  // Extract name - try multiple selectors
  const nameEl = document.querySelector('h1.text-heading-xlarge') ||
                 document.querySelector('h1[class*="text-heading"]') ||
                 document.querySelector('.pv-top-card h1') ||
                 document.querySelector('.ph5 h1') ||
                 document.querySelector('h1');
  if (nameEl) {
    data.name = nameEl.textContent.trim();
  }

  // Extract headline/title - try multiple selectors
  const headlineEl = document.querySelector('.text-body-medium.break-words') ||
                     document.querySelector('[data-generated-suggestion-target]') ||
                     document.querySelector('.pv-top-card .text-body-medium') ||
                     document.querySelector('.ph5 .text-body-medium') ||
                     document.querySelector('.pv-text-details__left-panel .text-body-medium');
  if (headlineEl) {
    data.title = headlineEl.textContent.trim();
  }

  // Extract current company from experience section
  const experienceSection = document.querySelector('#experience') ||
                            document.querySelector('section[id*="experience"]');
  if (experienceSection) {
    const section = experienceSection.closest('section') || experienceSection;
    const currentRole = section.querySelector('li');
    if (currentRole) {
      // Try multiple patterns for company name
      const companyEl = currentRole.querySelector('.t-14.t-normal span[aria-hidden="true"]') ||
                        currentRole.querySelector('.t-14.t-normal') ||
                        currentRole.querySelector('[class*="t-normal"] span[aria-hidden="true"]');
      if (companyEl) {
        const companyText = companyEl.textContent.trim();
        data.company = companyText.split('·')[0].trim();
      }
    }
  }

  // Fallback: try to get company from the top card subtitle area
  if (!data.company) {
    const topCardLinks = document.querySelectorAll('.pv-top-card a[href*="/company/"], .ph5 a[href*="/company/"]');
    if (topCardLinks.length > 0) {
      data.company = topCardLinks[0].textContent.trim();
    }
  }

  // Fallback: try to extract company from headline
  if (!data.company && data.title) {
    const atMatch = data.title.match(/(?:at|@)\s+([^|·,]+)/i);
    if (atMatch) {
      data.company = atMatch[1].trim();
    }
  }

  // Extract location
  const locationEl = document.querySelector('.text-body-small.inline.t-black--light.break-words') ||
                     document.querySelector('.pv-top-card .pb2.pv-text-details__left-panel span') ||
                     document.querySelector('.ph5 .text-body-small');
  if (locationEl) {
    data.location = locationEl.textContent.trim();
  }

  return data;
}

// Listen for messages from popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'getProfileData') {
    const data = extractProfileData();
    sendResponse(data);
  }
  return true;
});
