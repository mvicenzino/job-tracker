const API_URL = 'https://job-hunt-tracker-sand.vercel.app/api/contacts';

document.addEventListener('DOMContentLoaded', async () => {
  const form = document.getElementById('contactForm');
  const content = document.getElementById('content');
  const notLinkedIn = document.getElementById('notLinkedIn');
  const messageEl = document.getElementById('message');
  const submitBtn = document.getElementById('submitBtn');

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
      const response = await fetch(API_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
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
        }, 1000);
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
