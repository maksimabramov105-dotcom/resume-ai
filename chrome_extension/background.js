// background.js — Service worker for АвтоОтклик extension
// Polls the API for pending LinkedIn jobs every 10 minutes when on LinkedIn

const API_BASE = 'http://72.56.250.53'; // Will be updated to https://resumeai.bot

// On install: set up alarm
chrome.runtime.onInstalled.addListener(() => {
  chrome.alarms.create('checkPending', { periodInMinutes: 10 });
  console.log('АвтоОтклик extension installed');
});

// Alarm handler: check for pending applications
chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name !== 'checkPending') return;

  const { aa_token, aa_user_id } = await chrome.storage.local.get(['aa_token', 'aa_user_id']);
  if (!aa_token || !aa_user_id) return;

  try {
    const resp = await fetch(`${API_BASE}/api/extension/pending/${aa_user_id}`, {
      headers: { 'Authorization': `Bearer ${aa_token}` }
    });
    if (!resp.ok) return;
    const data = await resp.json();

    if (data.pending && data.pending.length > 0) {
      // Notify content script on active LinkedIn tab
      const tabs = await chrome.tabs.query({ url: 'https://www.linkedin.com/jobs/*', active: true });
      for (const tab of tabs) {
        chrome.tabs.sendMessage(tab.id, { type: 'APPLY_JOBS', jobs: data.pending });
      }
      // Show notification
      chrome.notifications.create({
        type: 'basic',
        iconUrl: 'icons/icon48.png',
        title: 'АвтоОтклик',
        message: `${data.pending.length} вакансий ожидают отклика`
      });
    }
  } catch (e) {
    console.error('Background check failed:', e);
  }
});

// Listen for reports from content script
chrome.runtime.onMessage.addListener(async (msg, sender, sendResponse) => {
  if (msg.type !== 'REPORT_APPLICATION') return;

  const { aa_token } = await chrome.storage.local.get('aa_token');
  if (!aa_token) return;

  try {
    await fetch(`${API_BASE}/api/extension/report`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${aa_token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(msg.data)
    });
  } catch (e) {
    console.error('Failed to report application:', e);
  }
});
