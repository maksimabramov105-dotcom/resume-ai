// content.js — Multi-ATS auto-apply automation
// Supports: LinkedIn Easy Apply, Greenhouse, Lever, Workable, Ashby

let isApplying = false;
const APPLY_DELAY_MS = 3000;
const JOB_DELAY_BASE = 120000;
const JOB_DELAY_RAND = 60000;

chrome.runtime.onMessage.addListener(async (msg, sender, sendResponse) => {
  if (msg.type === 'APPLY_JOBS') {
    if (isApplying) return;
    isApplying = true;
    const jobs = msg.jobs;

    for (const job of jobs) {
      try {
        const result = await applyToJob(job);
        chrome.runtime.sendMessage({
          type: 'REPORT_APPLICATION',
          data: {
            vacancy_url: job.vacancy_url,
            vacancy_id: job.vacancy_id,
            status: result.success ? 'sent' : 'failed',
            error: result.error || null
          }
        });
        const delay = JOB_DELAY_BASE + Math.random() * JOB_DELAY_RAND;
        await sleep(delay);
      } catch (e) {
        chrome.runtime.sendMessage({
          type: 'REPORT_APPLICATION',
          data: { vacancy_url: job.vacancy_url, vacancy_id: job.vacancy_id, status: 'failed', error: e.message }
        });
      }
    }
    isApplying = false;
  }

  if (msg.type === 'FILL_FORM') {
    // Direct fill request from popup (no navigation)
    const ats = detectATS();
    const profile = msg.profile;
    let result = { success: false, error: 'Unknown ATS' };
    if (ats === 'greenhouse') result = fillGreenhouse(profile);
    else if (ats === 'lever') result = fillLever(profile);
    else if (ats === 'workable') result = fillWorkable(profile);
    else if (ats === 'ashby') result = fillAshby(profile);
    else if (ats === 'linkedin') result = { success: false, error: 'LinkedIn requires navigation flow' };
    chrome.runtime.sendMessage({ type: 'FILL_RESULT', data: result });
  }
});

// ─── ATS Detection ───────────────────────────────────────────────────────────

function detectATS() {
  const host = window.location.hostname;
  const path = window.location.pathname;
  if (host.includes('linkedin.com')) return 'linkedin';
  if (host.includes('greenhouse.io')) return 'greenhouse';
  if (host.includes('lever.co')) return 'lever';
  if (host.includes('workable.com')) return 'workable';
  if (host.includes('ashbyhq.com')) return 'ashby';
  // Embedded boards (company sites hosting ATS iframe)
  if (document.querySelector('form[action*="greenhouse"]') || document.querySelector('#application_form')) return 'greenhouse';
  if (document.querySelector('[data-qa="apply-form"]')) return 'lever';
  return null;
}

// ─── Toast notification ───────────────────────────────────────────────────────

function showToast(message, type = 'info') {
  const existing = document.getElementById('resumeai-toast');
  if (existing) existing.remove();

  const toast = document.createElement('div');
  toast.id = 'resumeai-toast';
  toast.textContent = message;
  Object.assign(toast.style, {
    position: 'fixed', top: '20px', right: '20px', zIndex: '999999',
    background: type === 'success' ? '#16a34a' : type === 'error' ? '#dc2626' : '#1d4ed8',
    color: '#fff', padding: '12px 20px', borderRadius: '8px',
    fontFamily: 'system-ui, sans-serif', fontSize: '14px',
    boxShadow: '0 4px 12px rgba(0,0,0,0.3)', maxWidth: '320px',
    transition: 'opacity 0.3s'
  });
  document.body.appendChild(toast);
  setTimeout(() => { toast.style.opacity = '0'; setTimeout(() => toast.remove(), 300); }, 4000);
}

// ─── Helper: set input value triggering React/Vue/Angular events ──────────────

function setNativeValue(el, value) {
  const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')?.set;
  const nativeTextareaSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value')?.set;
  if (el.tagName === 'TEXTAREA' && nativeTextareaSetter) {
    nativeTextareaSetter.call(el, value);
  } else if (nativeInputValueSetter) {
    nativeInputValueSetter.call(el, value);
  } else {
    el.value = value;
  }
  el.dispatchEvent(new Event('input', { bubbles: true }));
  el.dispatchEvent(new Event('change', { bubbles: true }));
}

function fillByLabel(labelText, value, root = document) {
  const labels = root.querySelectorAll('label');
  for (const label of labels) {
    if (label.textContent.trim().toLowerCase().includes(labelText.toLowerCase())) {
      const forId = label.getAttribute('for');
      const input = forId
        ? root.getElementById(forId)
        : label.querySelector('input, textarea, select');
      if (input && !input.value) {
        setNativeValue(input, value);
        return true;
      }
    }
  }
  return false;
}

// ─── Greenhouse ───────────────────────────────────────────────────────────────
// boards.greenhouse.io/companyname/jobs/12345

function fillGreenhouse(profile) {
  try {
    const form = document.querySelector('#application_form, form.application-form, [data-provides="greenhouse-job-board"]');
    if (!form) return { success: false, error: 'Greenhouse form not found' };

    const fields = {
      first_name: profile.first_name || profile.name?.split(' ')[0] || '',
      last_name: profile.last_name || profile.name?.split(' ').slice(1).join(' ') || '',
      email: profile.email || '',
      phone: profile.phone || '',
      location: profile.city || profile.location || '',
      resume_text: profile.resume_text || '',
    };

    // Standard Greenhouse input IDs
    const mappings = {
      'input#first_name': fields.first_name,
      'input#last_name': fields.last_name,
      'input#email': fields.email,
      'input#phone': fields.phone,
      'input#job_application_location': fields.location,
      'input#job_application_resume_text': fields.resume_text,
    };

    let filled = 0;
    for (const [selector, value] of Object.entries(mappings)) {
      const el = form.querySelector(selector);
      if (el && value && !el.value) {
        setNativeValue(el, value);
        filled++;
      }
    }

    // Cover letter textarea
    const coverEl = form.querySelector('textarea#cover_letter, textarea[name="job_application[cover_letter_text]"]');
    if (coverEl && profile.cover_letter && !coverEl.value) {
      setNativeValue(coverEl, profile.cover_letter);
      filled++;
    }

    // LinkedIn URL field
    const liField = form.querySelector('input[name*="linkedin"], input[id*="linkedin"]');
    if (liField && profile.linkedin_url && !liField.value) {
      setNativeValue(liField, profile.linkedin_url);
      filled++;
    }

    // Website / portfolio
    const webField = form.querySelector('input[name*="website"], input[id*="website"], input[name*="portfolio"]');
    if (webField && profile.website && !webField.value) {
      setNativeValue(webField, profile.website);
      filled++;
    }

    showToast(`ResumeAI: заполнено ${filled} полей (Greenhouse)`, 'success');
    return { success: true, fields_filled: filled };
  } catch (e) {
    showToast('ResumeAI: ошибка заполнения формы', 'error');
    return { success: false, error: e.message };
  }
}

// ─── Lever ────────────────────────────────────────────────────────────────────
// jobs.lever.co/companyname/job-id/apply

function fillLever(profile) {
  try {
    const form = document.querySelector('form.application-form, [data-qa="apply-form"], form');
    if (!form) return { success: false, error: 'Lever form not found' };

    const nameParts = (profile.name || '').split(' ');
    const fields = {
      name: profile.name || '',
      email: profile.email || '',
      phone: profile.phone || '',
      org: profile.current_company || profile.company || '',
      urls_linkedin: profile.linkedin_url || '',
      urls_github: profile.github_url || '',
      urls_portfolio: profile.website || '',
      location: profile.city || profile.location || '',
      summary: profile.cover_letter || profile.bio || '',
    };

    // Lever uses input[name="..."] attributes
    const nameMap = {
      'name': fields.name,
      'email': fields.email,
      'phone': fields.phone,
      'org': fields.org,
      'urls[LinkedIn]': fields.urls_linkedin,
      'urls[GitHub]': fields.urls_github,
      'urls[Portfolio]': fields.urls_portfolio,
      'location': fields.location,
    };

    let filled = 0;
    for (const [name, value] of Object.entries(nameMap)) {
      const el = form.querySelector(`input[name="${name}"], textarea[name="${name}"]`);
      if (el && value && !el.value) {
        setNativeValue(el, value);
        filled++;
      }
    }

    // Summary / cover letter textarea
    const summaryEl = form.querySelector('textarea[name="comments"], textarea[name="summary"], textarea[placeholder*="cover"]');
    if (summaryEl && fields.summary && !summaryEl.value) {
      setNativeValue(summaryEl, fields.summary);
      filled++;
    }

    showToast(`ResumeAI: заполнено ${filled} полей (Lever)`, 'success');
    return { success: true, fields_filled: filled };
  } catch (e) {
    showToast('ResumeAI: ошибка заполнения формы', 'error');
    return { success: false, error: e.message };
  }
}

// ─── Workable ─────────────────────────────────────────────────────────────────
// apply.workable.com/companyname/j/JOBID/

function fillWorkable(profile) {
  try {
    const form = document.querySelector('form[data-ui="application-form"], form.application, form');
    if (!form) return { success: false, error: 'Workable form not found' };

    const labelMap = {
      'first name': profile.first_name || profile.name?.split(' ')[0] || '',
      'last name': profile.last_name || profile.name?.split(' ').slice(1).join(' ') || '',
      'email': profile.email || '',
      'phone': profile.phone || '',
      'city': profile.city || profile.location || '',
      'linkedin': profile.linkedin_url || '',
      'website': profile.website || '',
      'summary': profile.cover_letter || profile.bio || '',
    };

    let filled = 0;
    for (const [label, value] of Object.entries(labelMap)) {
      if (value && fillByLabel(label, value, form)) filled++;
    }

    // Workable React inputs sometimes need direct attribute targeting
    const emailEl = form.querySelector('input[name="email"], input[type="email"]');
    if (emailEl && profile.email && !emailEl.value) {
      setNativeValue(emailEl, profile.email);
      filled++;
    }

    showToast(`ResumeAI: заполнено ${filled} полей (Workable)`, 'success');
    return { success: true, fields_filled: filled };
  } catch (e) {
    showToast('ResumeAI: ошибка заполнения формы', 'error');
    return { success: false, error: e.message };
  }
}

// ─── Ashby ────────────────────────────────────────────────────────────────────
// jobs.ashbyhq.com/companyname/job-id

function fillAshby(profile) {
  try {
    const form = document.querySelector('form[data-testid="application-form"], form.ashby-application-form, form');
    if (!form) return { success: false, error: 'Ashby form not found' };

    const labelMap = {
      'first name': profile.first_name || profile.name?.split(' ')[0] || '',
      'last name': profile.last_name || profile.name?.split(' ').slice(1).join(' ') || '',
      'email': profile.email || '',
      'phone': profile.phone || '',
      'linkedin': profile.linkedin_url || '',
      'website': profile.website || profile.github_url || '',
      'cover letter': profile.cover_letter || '',
      'city': profile.city || profile.location || '',
    };

    let filled = 0;
    for (const [label, value] of Object.entries(labelMap)) {
      if (value && fillByLabel(label, value, form)) filled++;
    }

    // Ashby also uses data-testid attributes
    const testIdMap = {
      'first-name-input': profile.first_name || profile.name?.split(' ')[0] || '',
      'last-name-input': profile.last_name || profile.name?.split(' ').slice(1).join(' ') || '',
      'email-input': profile.email || '',
      'phone-input': profile.phone || '',
    };
    for (const [testId, value] of Object.entries(testIdMap)) {
      const el = form.querySelector(`[data-testid="${testId}"]`);
      if (el && value && !el.value) {
        setNativeValue(el, value);
        filled++;
      }
    }

    showToast(`ResumeAI: заполнено ${filled} полей (Ashby)`, 'success');
    return { success: true, fields_filled: filled };
  } catch (e) {
    showToast('ResumeAI: ошибка заполнения формы', 'error');
    return { success: false, error: e.message };
  }
}

// ─── LinkedIn Easy Apply ──────────────────────────────────────────────────────

async function applyToJob(job) {
  window.location.href = job.vacancy_url;
  await sleep(3500);

  const ats = detectATS();

  if (ats === 'greenhouse') return fillGreenhouse(job.user_profile || {});
  if (ats === 'lever') return fillLever(job.user_profile || {});
  if (ats === 'workable') return fillWorkable(job.user_profile || {});
  if (ats === 'ashby') return fillAshby(job.user_profile || {});

  // Default: LinkedIn Easy Apply flow
  const easyApplyBtn = (
    document.querySelector('button[aria-label*="Easy Apply"]') ||
    document.querySelector('.jobs-apply-button--top-card button') ||
    document.querySelector('button.jobs-apply-button')
  );

  if (!easyApplyBtn) return { success: false, error: 'No Easy Apply button found' };

  easyApplyBtn.click();
  await sleep(APPLY_DELAY_MS);

  let steps = 0;
  const MAX_STEPS = 10;

  while (steps < MAX_STEPS) {
    await sleep(1500);
    const modal = document.querySelector('.jobs-easy-apply-modal, [data-test-modal]');
    if (!modal) break;

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

    const textInputs = modal.querySelectorAll('input[type="text"]:not([value]), input[type="number"]:not([value])');
    textInputs.forEach(inp => {
      if (!inp.value || inp.value === '') {
        if (inp.type === 'number') inp.value = '1';
        inp.dispatchEvent(new Event('input', { bubbles: true }));
        inp.dispatchEvent(new Event('change', { bubbles: true }));
      }
    });

    const reviewBtn = document.querySelector('button[aria-label="Review your application"]') || findButtonByText('Review');
    if (reviewBtn && !reviewBtn.disabled) {
      reviewBtn.click(); await sleep(APPLY_DELAY_MS); steps++; continue;
    }

    const nextBtn = (
      document.querySelector('button[aria-label="Continue to next step"]') ||
      document.querySelector('button[data-easy-apply-next-button]') ||
      findButtonByText('Next')
    );
    if (nextBtn && !nextBtn.disabled) {
      nextBtn.click(); await sleep(APPLY_DELAY_MS); steps++; continue;
    }
    break;
  }

  const dismissBtn = document.querySelector('button[aria-label="Dismiss"], button[data-test-modal-close-btn]');
  if (dismissBtn) {
    dismissBtn.click(); await sleep(1000);
    const discardBtn = document.querySelector('button[data-test-dialog-primary-btn]');
    if (discardBtn) discardBtn.click();
  }

  return { success: false, error: `Completed ${steps} steps but could not submit` };
}

function findButtonByText(text) {
  for (const btn of document.querySelectorAll('button')) {
    if (btn.textContent.trim().toLowerCase() === text.toLowerCase()) return btn;
  }
  return null;
}

function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}
