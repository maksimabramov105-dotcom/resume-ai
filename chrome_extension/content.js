// content.js — LinkedIn Easy Apply automation
// Only runs when triggered by background.js with APPLY_JOBS message

let isApplying = false;
const APPLY_DELAY_MS = 3000; // 3s between form steps
const JOB_DELAY_BASE = 120000; // 2 min base
const JOB_DELAY_RAND = 60000;  // +up to 1 min random jitter

// Receive job list from background
chrome.runtime.onMessage.addListener(async (msg, sender, sendResponse) => {
  if (msg.type !== 'APPLY_JOBS' || isApplying) return;
  isApplying = true;

  const jobs = msg.jobs; // [{vacancy_url, vacancy_id, user_profile}]

  for (const job of jobs) {
    try {
      const result = await applyToJob(job);
      chrome.runtime.sendMessage({
        type: 'REPORT_APPLICATION',
        data: {
          vacancy_url: job.vacancy_url,
          vacancy_id:  job.vacancy_id,
          status:      result.success ? 'sent' : 'failed',
          error:       result.error || null
        }
      });
      // Wait between applications to avoid detection
      const delay = JOB_DELAY_BASE + Math.random() * JOB_DELAY_RAND;
      await sleep(delay);
    } catch (e) {
      chrome.runtime.sendMessage({
        type: 'REPORT_APPLICATION',
        data: {
          vacancy_url: job.vacancy_url,
          vacancy_id:  job.vacancy_id,
          status: 'failed',
          error: e.message
        }
      });
    }
  }

  isApplying = false;
});

async function applyToJob(job) {
  // Navigate to job page
  window.location.href = job.vacancy_url;
  await sleep(3500); // extra buffer for navigation

  // Find Easy Apply button — LinkedIn uses several selectors across versions
  const easyApplyBtn = (
    document.querySelector('button[aria-label*="Easy Apply"]') ||
    document.querySelector('.jobs-apply-button--top-card button') ||
    document.querySelector('button.jobs-apply-button')
  );

  if (!easyApplyBtn) {
    return { success: false, error: 'No Easy Apply button found' };
  }

  easyApplyBtn.click();
  await sleep(APPLY_DELAY_MS);

  // Handle multi-step form — LinkedIn Easy Apply usually has 2-4 steps
  let steps = 0;
  const MAX_STEPS = 10;

  while (steps < MAX_STEPS) {
    await sleep(1500);

    // Check if form modal is still open
    const modal = document.querySelector('.jobs-easy-apply-modal, [data-test-modal]');
    if (!modal) break;

    // Submit button — final step
    const submitBtn = (
      document.querySelector('button[aria-label="Submit application"]') ||
      document.querySelector('footer button[data-easy-apply-next-button]') ||
      findButtonByText('Submit application')
    );
    if (submitBtn && !submitBtn.disabled) {
      submitBtn.click();
      await sleep(2500);
      return { success: true };
    }

    // Try to fill any required text inputs that are empty
    const textInputs = modal.querySelectorAll('input[type="text"]:not([value]), input[type="number"]:not([value])');
    textInputs.forEach(inp => {
      if (!inp.value || inp.value === '') {
        // Use placeholder hint or safe default
        if (inp.placeholder && inp.placeholder.length < 10) {
          inp.value = inp.placeholder;
        } else if (inp.type === 'number') {
          inp.value = '1';
        }
        // Trigger change event so React/Angular picks it up
        inp.dispatchEvent(new Event('input', { bubbles: true }));
        inp.dispatchEvent(new Event('change', { bubbles: true }));
      }
    });

    // "Review" step
    const reviewBtn = (
      document.querySelector('button[aria-label="Review your application"]') ||
      findButtonByText('Review')
    );
    if (reviewBtn && !reviewBtn.disabled) {
      reviewBtn.click();
      await sleep(APPLY_DELAY_MS);
      steps++;
      continue;
    }

    // "Next" step
    const nextBtn = (
      document.querySelector('button[aria-label="Continue to next step"]') ||
      document.querySelector('button[data-easy-apply-next-button]') ||
      findButtonByText('Next')
    );
    if (nextBtn && !nextBtn.disabled) {
      nextBtn.click();
      await sleep(APPLY_DELAY_MS);
      steps++;
      continue;
    }

    // No known button found — bail
    break;
  }

  // Try to dismiss modal if still open
  const dismissBtn = document.querySelector('button[aria-label="Dismiss"], button[data-test-modal-close-btn]');
  if (dismissBtn) {
    dismissBtn.click();
    await sleep(1000);
    // Confirm discard if prompted
    const discardBtn = document.querySelector('button[data-test-dialog-primary-btn]');
    if (discardBtn) discardBtn.click();
  }

  return { success: false, error: `Completed ${steps} steps but could not submit` };
}

function findButtonByText(text) {
  const buttons = document.querySelectorAll('button');
  for (const btn of buttons) {
    if (btn.textContent.trim().toLowerCase() === text.toLowerCase()) return btn;
  }
  return null;
}

function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}
