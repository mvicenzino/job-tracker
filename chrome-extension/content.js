// Content script to extract LinkedIn profile data
function extractProfileData() {
  const data = {
    name: '',
    title: '',
    company: '',
    linkedin_url: window.location.href.split('?')[0],
    location: ''
  };

  // Extract name
  const nameEl = document.querySelector('h1.text-heading-xlarge') ||
                 document.querySelector('h1[class*="text-heading"]') ||
                 document.querySelector('.pv-top-card h1');
  if (nameEl) {
    data.name = nameEl.textContent.trim();
  }

  // Extract headline/title
  const headlineEl = document.querySelector('.text-body-medium.break-words') ||
                     document.querySelector('[data-generated-suggestion-target]') ||
                     document.querySelector('.pv-top-card .text-body-medium');
  if (headlineEl) {
    data.title = headlineEl.textContent.trim();
  }

  // Extract current company from experience or headline
  const experienceSection = document.querySelector('#experience');
  if (experienceSection) {
    const currentRole = experienceSection.closest('section')?.querySelector('li');
    if (currentRole) {
      const companyEl = currentRole.querySelector('.t-14.t-normal span[aria-hidden="true"]') ||
                        currentRole.querySelector('.t-14.t-normal');
      if (companyEl) {
        // Company name is usually in format "Company Name · Full-time"
        const companyText = companyEl.textContent.trim();
        data.company = companyText.split('·')[0].trim();
      }
    }
  }

  // Fallback: try to extract company from headline
  if (!data.company && data.title) {
    const atMatch = data.title.match(/(?:at|@)\s+([^|·]+)/i);
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

// Listen for messages from popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'getProfileData') {
    const data = extractProfileData();
    sendResponse(data);
  }
  return true;
});
