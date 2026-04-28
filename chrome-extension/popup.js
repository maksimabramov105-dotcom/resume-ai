const FIELDS = ['firstName', 'lastName', 'email', 'phone', 'location', 'currentCompany', 'linkedin'];

function showStatus(msg) {
  const el = document.getElementById('status');
  el.textContent = msg;
  setTimeout(() => { el.textContent = ''; }, 2000);
}

// Load saved profile into form
chrome.storage.local.get(['userProfile'], (result) => {
  const profile = result.userProfile;
  if (!profile) return;
  FIELDS.forEach(key => {
    const el = document.getElementById(key);
    if (el && profile[key]) el.value = profile[key];
  });
});

// Save profile on button click
document.getElementById('saveBtn').addEventListener('click', () => {
  const profile = {};
  FIELDS.forEach(key => {
    const el = document.getElementById(key);
    profile[key] = el ? el.value.trim() : '';
  });

  chrome.storage.local.set({ userProfile: profile }, () => {
    showStatus('✅ Profile saved!');
  });
});
