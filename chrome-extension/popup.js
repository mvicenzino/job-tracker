// Default settings
const DEFAULT_SERVER_URL = 'https://stride-jobs.vercel.app';

// Get stored settings
async function getSettings() {
  const result = await chrome.storage.sync.get(['serverUrl', 'apiKey']);
  return {
    serverUrl: result.serverUrl || '',
    apiKey: result.apiKey || ''
  };
}

// Save settings
async function saveSettings(serverUrl, apiKey) {
  await chrome.storage.sync.set({ serverUrl, apiKey });
}

// Update connection status display
function updateConnectionStatus(serverUrl, apiKey) {
  const statusDot = document.getElementById('statusDot');
  const statusText = document.getElementById('statusText');

  if (serverUrl && apiKey) {
    statusDot.className = 'status-dot connected';
    statusText.textContent = 'Connected to ' + new URL(serverUrl).hostname;
  } else {
    statusDot.className = 'status-dot disconnected';
    statusText.textContent = serverUrl ? 'API key not set' : 'Not configured';
  }
}

// Update view link based on page type
function updateViewLink(serverUrl, pageType) {
  const viewLink = document.getElementById('viewLink');
  if (!serverUrl) {
    viewLink.href = '#';
    return;
  }

  switch (pageType) {
    case 'contact':
    case 'profile':
      viewLink.href = serverUrl + '/contacts';
      viewLink.textContent = 'View all contacts →';
      break;
    case 'company':
      viewLink.href = serverUrl + '/companies';
      viewLink.textContent = 'View all companies →';
      break;
    case 'job':
      viewLink.href = serverUrl + '/jobs';
      viewLink.textContent = 'View all jobs →';
      break;
    default:
      viewLink.href = serverUrl + '/dashboard';
      viewLink.textContent = 'View dashboard →';
  }
}

// Show the appropriate form and badge based on page type
function showFormForType(pageType) {
  const contactForm = document.getElementById('contactForm');
  const companyForm = document.getElementById('companyForm');
  const jobForm = document.getElementById('jobForm');
  const badge = document.getElementById('pageTypeBadge');

  // Hide all forms
  contactForm.classList.remove('active');
  companyForm.classList.remove('active');
  jobForm.classList.remove('active');

  // Show appropriate form and set badge
  switch (pageType) {
    case 'contact':
    case 'profile':
      contactForm.classList.add('active');
      badge.textContent = 'Contact';
      badge.className = 'page-type-badge badge-contact';
      break;
    case 'company':
      companyForm.classList.add('active');
      badge.textContent = 'Company';
      badge.className = 'page-type-badge badge-company';
      break;
    case 'job':
      jobForm.classList.add('active');
      badge.textContent = 'Job';
      badge.className = 'page-type-badge badge-job';
      break;
    default:
      badge.textContent = '';
      badge.className = 'page-type-badge';
  }
}

// Determine page type from URL
function getPageTypeFromUrl(url) {
  if (!url) return 'unknown';
  if (url.includes('linkedin.com/in/')) return 'profile';
  if (url.includes('linkedin.com/company/')) return 'company';
  if (url.includes('linkedin.com/jobs/view/') || url.includes('linkedin.com/jobs/collections/')) return 'job';
  return 'unknown';
}

document.addEventListener('DOMContentLoaded', async () => {
  const contactForm = document.getElementById('contactForm');
  const companyForm = document.getElementById('companyForm');
  const jobForm = document.getElementById('jobForm');
  const content = document.getElementById('content');
  const notLinkedIn = document.getElementById('notLinkedIn');
  const messageEl = document.getElementById('message');
  const settingsPanel = document.getElementById('settingsPanel');
  const settingsToggle = document.getElementById('settingsToggle');
  const cancelSettings = document.getElementById('cancelSettings');
  const saveSettingsBtn = document.getElementById('saveSettings');
  const settingsMessage = document.getElementById('settingsMessage');

  // Load settings
  let settings = await getSettings();
  updateConnectionStatus(settings.serverUrl, settings.apiKey);

  // Populate settings fields
  document.getElementById('serverUrl').value = settings.serverUrl;
  document.getElementById('apiKey').value = settings.apiKey;

  // Settings toggle
  settingsToggle.addEventListener('click', () => {
    const isSettingsVisible = settingsPanel.style.display === 'block';
    settingsPanel.style.display = isSettingsVisible ? 'none' : 'block';
    content.style.display = isSettingsVisible ? 'block' : 'none';
    notLinkedIn.style.display = 'none';
  });

  // Cancel settings
  cancelSettings.addEventListener('click', async () => {
    settings = await getSettings();
    document.getElementById('serverUrl').value = settings.serverUrl;
    document.getElementById('apiKey').value = settings.apiKey;
    settingsPanel.style.display = 'none';
    content.style.display = 'block';
    settingsMessage.style.display = 'none';
  });

  // Save settings
  saveSettingsBtn.addEventListener('click', async () => {
    const serverUrl = document.getElementById('serverUrl').value.trim().replace(/\/$/, '');
    const apiKey = document.getElementById('apiKey').value.trim();

    if (!serverUrl || !apiKey) {
      settingsMessage.textContent = 'Both Server URL and API Key are required';
      settingsMessage.className = 'message error';
      return;
    }

    // Test the connection
    try {
      settingsMessage.textContent = 'Testing connection...';
      settingsMessage.className = 'message warning';

      const response = await fetch(serverUrl + '/api/contacts', {
        method: 'OPTIONS',
        headers: {
          'X-API-Key': apiKey
        }
      });

      if (response.ok) {
        await saveSettings(serverUrl, apiKey);
        settings = { serverUrl, apiKey };
        updateConnectionStatus(serverUrl, apiKey);
        settingsMessage.textContent = 'Settings saved successfully!';
        settingsMessage.className = 'message success';
        setTimeout(() => {
          settingsPanel.style.display = 'none';
          content.style.display = 'block';
          settingsMessage.style.display = 'none';
        }, 1500);
      } else {
        throw new Error('Could not connect to server');
      }
    } catch (error) {
      // Even if OPTIONS fails, save the settings (some servers don't support OPTIONS)
      await saveSettings(serverUrl, apiKey);
      settings = { serverUrl, apiKey };
      updateConnectionStatus(serverUrl, apiKey);
      settingsMessage.textContent = 'Settings saved. Connection will be tested when adding data.';
      settingsMessage.className = 'message warning';
      setTimeout(() => {
        settingsPanel.style.display = 'none';
        content.style.display = 'block';
        settingsMessage.style.display = 'none';
      }, 2000);
    }
  });

  // Check if settings are configured
  if (!settings.serverUrl || !settings.apiKey) {
    messageEl.textContent = 'Please configure the extension in Settings (⚙️)';
    messageEl.className = 'message warning';
  }

  // Get current tab and determine page type
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const pageType = getPageTypeFromUrl(tab.url);

  if (pageType === 'unknown') {
    content.style.display = 'none';
    notLinkedIn.style.display = 'block';
    return;
  }

  // Show appropriate form
  showFormForType(pageType);
  updateViewLink(settings.serverUrl, pageType);

  // Get data from content script
  try {
    const response = await chrome.tabs.sendMessage(tab.id, { action: 'getData' });
    if (response) {
      populateForm(response);
    }
  } catch (error) {
    console.log('Could not get data from content script:', error);
    // Fallback: populate URL fields
    if (pageType === 'profile') {
      document.getElementById('contact_linkedin_url').value = tab.url.split('?')[0];
    } else if (pageType === 'company') {
      document.getElementById('company_linkedin_url').value = tab.url.split('?')[0];
    } else if (pageType === 'job') {
      document.getElementById('job_url').value = tab.url.split('?')[0];
    }
  }

  // Handle contact form submission
  contactForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    await submitData('contact', {
      name: document.getElementById('contact_name').value.trim(),
      title: document.getElementById('contact_title').value.trim(),
      company: document.getElementById('contact_company').value.trim(),
      contact_type: document.getElementById('contact_type').value,
      linkedin_url: document.getElementById('contact_linkedin_url').value,
      notes: document.getElementById('contact_notes').value.trim()
    }, 'contactSubmitBtn', 'Add Contact');
  });

  // Handle company form submission
  companyForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    await submitData('company', {
      name: document.getElementById('company_name').value.trim(),
      industry: document.getElementById('company_industry').value.trim(),
      size: document.getElementById('company_size').value.trim(),
      location: document.getElementById('company_location').value.trim(),
      website: document.getElementById('company_website').value.trim(),
      description: document.getElementById('company_description').value.trim(),
      linkedin_url: document.getElementById('company_linkedin_url').value
    }, 'companySubmitBtn', 'Add Company');
  });

  // Handle job form submission
  jobForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    await submitData('job', {
      title: document.getElementById('job_title').value.trim(),
      company_name: document.getElementById('job_company').value.trim(),
      location: document.getElementById('job_location').value.trim(),
      remote_type: document.getElementById('job_remote_type').value,
      description: document.getElementById('job_description').value.trim(),
      is_flagged: document.getElementById('job_is_flagged').checked,
      job_url: document.getElementById('job_url').value,
      source: 'LinkedIn'
    }, 'jobSubmitBtn', 'Add Job');
  });

  // Generic submit function
  async function submitData(dataType, data, submitBtnId, submitBtnText) {
    settings = await getSettings();
    if (!settings.serverUrl || !settings.apiKey) {
      messageEl.textContent = 'Please configure the extension in Settings (⚙️) first';
      messageEl.className = 'message error';
      return;
    }

    const submitBtn = document.getElementById(submitBtnId);
    submitBtn.disabled = true;
    submitBtn.textContent = 'Adding...';
    messageEl.className = 'message';
    messageEl.style.display = 'none';

    const endpoints = {
      contact: '/api/contacts',
      company: '/api/companies',
      job: '/api/jobs'
    };

    try {
      const response = await fetch(settings.serverUrl + endpoints[dataType], {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': settings.apiKey
        },
        body: JSON.stringify(data)
      });

      const result = await response.json();

      if (result.success) {
        const itemName = dataType === 'contact' ? data.name : (dataType === 'company' ? data.name : data.title);
        messageEl.textContent = `✓ ${itemName} added!`;
        messageEl.className = 'message success';
        submitBtn.textContent = 'Added!';

        // For jobs, redirect to review page if available
        if (dataType === 'job' && result.application && result.application.review_url) {
          messageEl.textContent = `✓ ${itemName} added! Opening review...`;
          setTimeout(() => {
            chrome.tabs.create({ url: settings.serverUrl + result.application.review_url });
            window.close();
          }, 500);
        } else {
          setTimeout(() => {
            submitBtn.disabled = false;
            submitBtn.textContent = submitBtnText;
          }, 2000);
        }
      } else {
        throw new Error(result.error || `Failed to add ${dataType}`);
      }
    } catch (error) {
      messageEl.textContent = `✗ ${error.message}`;
      messageEl.className = 'message error';
      submitBtn.disabled = false;
      submitBtn.textContent = submitBtnText;
    }
  }

  // Populate form based on data type
  function populateForm(data) {
    if (!data || !data.type) return;

    switch (data.type) {
      case 'contact':
        document.getElementById('contact_name').value = data.name || '';
        document.getElementById('contact_title').value = data.title || '';
        document.getElementById('contact_company').value = data.company || '';
        document.getElementById('contact_linkedin_url').value = data.linkedin_url || tab.url.split('?')[0];
        break;
      case 'company':
        document.getElementById('company_name').value = data.name || '';
        document.getElementById('company_industry').value = data.industry || '';
        document.getElementById('company_size').value = data.size || '';
        document.getElementById('company_location').value = data.location || '';
        document.getElementById('company_website').value = data.website || '';
        document.getElementById('company_description').value = data.description || '';
        document.getElementById('company_linkedin_url').value = data.linkedin_url || tab.url.split('?')[0];
        break;
      case 'job':
        document.getElementById('job_title').value = data.title || '';
        document.getElementById('job_company').value = data.company || '';
        document.getElementById('job_location').value = data.location || '';
        document.getElementById('job_remote_type').value = data.remote_type || '';
        document.getElementById('job_description').value = data.description || '';
        document.getElementById('job_url').value = data.job_url || tab.url.split('?')[0];
        break;
    }
  }
});
