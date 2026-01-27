// Default settings
const DEFAULT_SERVER_URL = 'https://job-hunt-tracker-sand.vercel.app';

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
  const viewContactsLink = document.getElementById('viewContactsLink');

  if (serverUrl && apiKey) {
    statusDot.className = 'status-dot connected';
    statusText.textContent = 'Connected to ' + new URL(serverUrl).hostname;
    viewContactsLink.href = serverUrl + '/contacts';
  } else {
    statusDot.className = 'status-dot disconnected';
    statusText.textContent = serverUrl ? 'API key not set' : 'Not configured';
    viewContactsLink.href = '#';
  }
}

document.addEventListener('DOMContentLoaded', async () => {
  const form = document.getElementById('contactForm');
  const content = document.getElementById('content');
  const notLinkedIn = document.getElementById('notLinkedIn');
  const messageEl = document.getElementById('message');
  const submitBtn = document.getElementById('submitBtn');
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
      settingsMessage.textContent = 'Settings saved. Connection will be tested when adding a contact.';
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

  // Check if we're on a LinkedIn profile page
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

  if (!tab.url || !tab.url.includes('linkedin.com/in/')) {
    content.style.display = 'none';
    notLinkedIn.style.display = 'block';
    return;
  }

  // Get profile data from content script
  try {
    const response = await chrome.tabs.sendMessage(tab.id, { action: 'getProfileData' });
    if (response) {
      document.getElementById('name').value = response.name || '';
      document.getElementById('title').value = response.title || '';
      document.getElementById('company').value = response.company || '';
      document.getElementById('linkedin_url').value = response.linkedin_url || tab.url;
    }
  } catch (error) {
    // Content script might not be loaded yet, just use the URL
    document.getElementById('linkedin_url').value = tab.url.split('?')[0];
    console.log('Could not get profile data:', error);
  }

  // Handle form submission
  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    // Check settings again
    settings = await getSettings();
    if (!settings.serverUrl || !settings.apiKey) {
      messageEl.textContent = 'Please configure the extension in Settings (⚙️) first';
      messageEl.className = 'message error';
      return;
    }

    submitBtn.disabled = true;
    submitBtn.textContent = 'Adding...';
    messageEl.className = 'message';
    messageEl.style.display = 'none';

    const contactData = {
      name: document.getElementById('name').value.trim(),
      title: document.getElementById('title').value.trim(),
      company: document.getElementById('company').value.trim(),
      contact_type: document.getElementById('contact_type').value,
      linkedin_url: document.getElementById('linkedin_url').value,
      notes: document.getElementById('notes').value.trim()
    };

    try {
      const response = await fetch(settings.serverUrl + '/api/contacts', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': settings.apiKey
        },
        body: JSON.stringify(contactData)
      });

      const result = await response.json();

      if (result.success) {
        messageEl.textContent = `✓ ${contactData.name} added to contacts!`;
        messageEl.className = 'message success';
        submitBtn.textContent = 'Added!';

        // Clear form after success
        setTimeout(() => {
          document.getElementById('notes').value = '';
          submitBtn.disabled = false;
          submitBtn.textContent = 'Add Contact';
        }, 2000);
      } else {
        throw new Error(result.error || 'Failed to add contact');
      }
    } catch (error) {
      messageEl.textContent = `✗ ${error.message}`;
      messageEl.className = 'message error';
      submitBtn.disabled = false;
      submitBtn.textContent = 'Add Contact';
    }
  });
});
