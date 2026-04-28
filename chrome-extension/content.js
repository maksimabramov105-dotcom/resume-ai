function detectATS() {
  const url = window.location.href;
  if (url.includes('boards.greenhouse.io')) return 'greenhouse';
  if (url.includes('jobs.lever.co')) return 'lever';
  if (url.includes('apply.workable.com')) return 'workable';
  if (url.includes('jobs.ashbyhq.com')) return 'ashby';
  return null;
}

async function getUserProfile() {
  return new Promise((resolve) => {
    chrome.storage.local.get(['userProfile'], (result) => {
      resolve(result.userProfile || null);
    });
  });
}

function fillField(selector, value) {
  const el = selector ? document.querySelector(selector) : null;
  if (!el || !value) return false;
  const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
    window.HTMLInputElement.prototype, 'value'
  ).set;
  nativeInputValueSetter.call(el, value);
  el.dispatchEvent(new Event('input', { bubbles: true }));
  el.dispatchEvent(new Event('change', { bubbles: true }));
  return true;
}

function fillGreenhouse(profile) {
  fillField('input[name="first_name"]', profile.firstName);
  fillField('input[name="last_name"]', profile.lastName);
  fillField('input[name="email"]', profile.email);
  fillField('input[name="phone"]', profile.phone);
  fillField('input[name="location"]', profile.location);
  const linkedinField =
    document.querySelector('input[placeholder*="LinkedIn"]') ||
    document.querySelector('input[name*="linkedin"]');
  if (linkedinField && profile.linkedin) {
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    setter.call(linkedinField, profile.linkedin);
    linkedinField.dispatchEvent(new Event('input', { bubbles: true }));
    linkedinField.dispatchEvent(new Event('change', { bubbles: true }));
  }
}

function fillLever(profile) {
  fillField('input[name="name"]', (profile.firstName || '') + ' ' + (profile.lastName || ''));
  fillField('input[name="email"]', profile.email);
  fillField('input[name="phone"]', profile.phone);
  fillField('input[name="location"]', profile.location);
  fillField('input[name="org"]', profile.currentCompany);
  fillField('input[name="urls[LinkedIn]"]', profile.linkedin);
}

function showToast(message) {
  const toast = document.createElement('div');
  toast.style.cssText = `
    position: fixed; top: 20px; right: 20px; z-index: 99999;
    background: #5B73FF; color: white; padding: 12px 20px;
    border-radius: 8px; font-family: Inter, sans-serif; font-size: 14px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.3); max-width: 300px;
  `;
  toast.textContent = message;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 5000);
}

async function main() {
  const ats = detectATS();
  if (!ats) return;

  const profile = await getUserProfile();
  if (!profile) {
    console.log('[ResumeAI] No profile found. Open the extension popup to set up.');
    return;
  }

  setTimeout(() => {
    if (ats === 'greenhouse') fillGreenhouse(profile);
    if (ats === 'lever') fillLever(profile);
    console.log(`[ResumeAI] Auto-filled ${ats} form`);
    showToast('✅ ResumeAI filled your application. Review before submitting.');
  }, 1500);
}

main();
