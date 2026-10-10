// Global state
let currentTab = 'outreach';
let dispatchMode = 'template'; // 'template' | 'otp' | 'custom'
let templates = [];
let activeSettings = {};
let activeCooldowns = [];
let searchDebounceTimer = null;

// Initialization
document.addEventListener('DOMContentLoaded', () => {
  initOutreachTab();
  loadDashboardData();
  loadSettings();
  loadApiKeys();

  // Refresh metrics and cooldowns every 3 seconds
  setInterval(() => {
    refreshMetricsAndCooldowns();
  }, 3000);
});

// Toast notification helper
function showToast(message, type = 'success') {
  const toast = document.getElementById('toastMessage');
  toast.className = `fixed bottom-6 right-6 z-50 p-4 rounded-xl shadow-2xl text-sm font-medium border flex items-center gap-3 transition-all ${
    type === 'success'
      ? 'bg-emerald-950/90 text-emerald-200 border-emerald-700/60'
      : type === 'warning'
      ? 'bg-amber-950/90 text-amber-200 border-amber-700/60'
      : 'bg-red-950/90 text-red-200 border-red-700/60'
  }`;
  toast.innerHTML = `
    <span>${type === 'success' ? '✓' : type === 'warning' ? '⚠️' : '✕'}</span>
    <span>${message}</span>
  `;
  toast.classList.remove('hidden');

  setTimeout(() => {
    toast.classList.add('hidden');
  }, 4000);
}

// Tab Switching
function switchTab(tabName) {
  currentTab = tabName;
  const sections = ['overview', 'logs', 'shield', 'gateway', 'keys', 'docs', 'outreach'];
  sections.forEach(s => {
    const el = document.getElementById(`section-${s}`);
    const btn = document.getElementById(`tab-${s}`);
    if (el) el.classList.toggle('hidden', s !== tabName);
    if (btn) {
      if (s === tabName) {
        btn.classList.add('text-brand-500', 'border-brand-500');
        btn.classList.remove('text-slate-400', 'border-transparent');
      } else {
        btn.classList.remove('text-brand-500', 'border-brand-500');
        btn.classList.add('text-slate-400', 'border-transparent');
      }
    }
  });

  if (tabName === 'logs') loadLogs();
  if (tabName === 'shield') loadCooldowns();
  if (tabName === 'keys') loadApiKeys();
  if (tabName === 'gateway' || tabName === 'shield') loadSettings();
  if (tabName === 'outreach') initOutreachTab();
}

// Dispatch Mode Toggle
function setDispatchMode(mode) {
  dispatchMode = mode;
  const btnTemplate = document.getElementById('btnModeTemplate');
  const btnOtp = document.getElementById('btnModeOtp');
  const btnCustom = document.getElementById('btnModeCustom');

  const secTemplate = document.getElementById('sectionTemplateSelect');
  const secOtp = document.getElementById('sectionOtpMode');
  const secCustom = document.getElementById('sectionCustomMessage');

  [btnTemplate, btnOtp, btnCustom].forEach(b => {
    b.className = 'px-3 py-1.5 rounded-md font-medium text-slate-400 hover:text-white';
  });

  secTemplate.classList.add('hidden');
  secOtp.classList.add('hidden');
  secCustom.classList.add('hidden');

  if (mode === 'template') {
    btnTemplate.className = 'px-3 py-1.5 rounded-md font-medium bg-brand-600 text-white';
    secTemplate.classList.remove('hidden');
    onTemplateChange();
  } else if (mode === 'otp') {
    btnOtp.className = 'px-3 py-1.5 rounded-md font-medium bg-cyan-600 text-white';
    secOtp.classList.remove('hidden');
    document.getElementById('livePreviewText').innerText =
      'Your verification code is: 123456. Do not share this code with anyone. Valid for 5 minutes.';
  } else if (mode === 'custom') {
    btnCustom.className = 'px-3 py-1.5 rounded-md font-medium bg-amber-600 text-white';
    secCustom.classList.remove('hidden');
    updateCharCount();
  }
}

// Load Dashboard Metrics & Templates
async function loadDashboardData() {
  try {
    const [metricsRes, templatesRes] = await Promise.all([
      fetch('/api/v1/admin/metrics'),
      fetch('/api/v1/admin/templates')
    ]);

    const metrics = await metricsRes.json();
    const templatesData = await templatesRes.json();

    document.getElementById('metricSent').innerText = metrics.sent || 0;
    document.getElementById('metricBlocked').innerText = metrics.blocked || 0;
    document.getElementById('metricCooldowns').innerText = metrics.activeCooldownsCount || 0;
    document.getElementById('metricRate').innerText = `${metrics.successRate || 100}%`;

    const badge = document.getElementById('headerGatewayBadge');
    if (badge && metrics.activeProvider) {
      badge.innerText = metrics.activeProvider.toUpperCase();
    }

    renderRecentActivity(metrics.recentActivity || []);

    templates = templatesData.templates || [];
    renderTemplateSelect();
  } catch (err) {
    console.error('Failed to load dashboard data:', err);
  }
}

// Light refresh for metrics and active cooldowns badge
async function refreshMetricsAndCooldowns() {
  try {
    const res = await fetch('/api/v1/admin/metrics');
    const metrics = await res.json();
    document.getElementById('metricSent').innerText = metrics.sent || 0;
    document.getElementById('metricBlocked').innerText = metrics.blocked || 0;
    document.getElementById('metricCooldowns').innerText = metrics.activeCooldownsCount || 0;
    document.getElementById('metricRate').innerText = `${metrics.successRate || 100}%`;

    if (currentTab === 'shield') {
      loadCooldowns();
    }
  } catch (err) {
    // quiet catch for periodic poll
  }
}

function renderTemplateSelect() {
  const sel = document.getElementById('selectTemplate');
  sel.innerHTML = templates
    .map(t => `<option value="${t.id}">${t.name} (${t.category})</option>`)
    .join('');
  onTemplateChange();
}

function onTemplateChange() {
  if (dispatchMode !== 'template') return;
  const sel = document.getElementById('selectTemplate');
  const selected = templates.find(t => t.id === sel.value);
  if (!selected) return;

  const container = document.getElementById('dynamicVariableInputs');
  container.innerHTML = '';

  const sampleDefaults = {
    code: '849201',
    customerName: 'Sadman',
    orderId: 'ORD-1092',
    amount: '75.00',
    trackingNumber: 'TRK-9921',
    invoiceId: 'INV-4412',
    location: 'Dhaka, Bangladesh'
  };

  if (!selected.variables || selected.variables.length === 0) {
    container.innerHTML = '<span class="text-xs text-slate-400 italic">No variables required.</span>';
  } else {
    selected.variables.forEach(v => {
      const defaultVal = sampleDefaults[v] || 'Sample';
      const div = document.createElement('div');
      div.innerHTML = `
        <label class="block text-[11px] font-medium text-slate-400 mb-0.5">${v}</label>
        <input type="text" data-var="${v}" value="${defaultVal}" placeholder="Enter ${v}" oninput="updateLivePreview()" 
          class="w-full bg-slate-900 border border-borderCol rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none">
      `;
      container.appendChild(div);
    });
  }

  updateLivePreview();
}

function updateLivePreview() {
  if (dispatchMode === 'template') {
    const sel = document.getElementById('selectTemplate');
    const selected = templates.find(t => t.id === sel.value);
    if (!selected) return;

    let body = selected.body;
    const inputs = document.querySelectorAll('#dynamicVariableInputs input');
    inputs.forEach(input => {
      const varName = input.getAttribute('data-var');
      const val = input.value.trim() || `[${varName}]`;
      body = body.replace(new RegExp(`{{\\s*${varName}\\s*}}`, 'g'), val);
    });

    document.getElementById('livePreviewText').innerText = body;
  } else if (dispatchMode === 'custom') {
    const text = document.getElementById('customMessageText').value;
    document.getElementById('livePreviewText').innerText = text.trim() || 'Enter custom alert text...';
  }
}

function updateCharCount() {
  const text = document.getElementById('customMessageText').value;
  const len = text.length;
  const segments = Math.max(1, Math.ceil(len / 160));
  document.getElementById('charCountLabel').innerText = `${len} / 160 chars (${segments} SMS segment${segments > 1 ? 's' : ''})`;
  updateLivePreview();
}

// Render Recent Activity Stream
function renderRecentActivity(logs) {
  const container = document.getElementById('recentActivityList');
  if (!logs || logs.length === 0) {
    container.innerHTML = '<p class="text-xs text-slate-500 text-center py-10">No recent activity recorded yet.</p>';
    return;
  }

  container.innerHTML = logs.map(l => {
    let statusBadge = '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-950 text-emerald-400 border border-emerald-800">DELIVERED</span>';
    if (l.status === 'THROTTLED') {
      statusBadge = '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-950 text-amber-400 border border-amber-800">THROTTLED (60s)</span>';
    } else if (l.status === 'BLOCKED_ABUSE') {
      statusBadge = '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-950 text-rose-400 border border-rose-800">SHIELD BLOCKED</span>';
    } else if (l.status === 'FAILED') {
      statusBadge = '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-red-950 text-red-400 border border-red-800">FAILED</span>';
    }

    const timeAgo = formatTime(l.timestamp);

    return `
      <div class="bg-slate-900/80 border border-borderCol/70 p-3 rounded-xl flex items-start justify-between gap-3 text-xs">
        <div class="space-y-1">
          <div class="flex items-center gap-2">
            <span class="font-mono font-semibold text-white">${l.recipient || 'Unknown'}</span>
            ${statusBadge}
          </div>
          <p class="text-slate-400 line-clamp-1 font-sans text-[11px]">${l.message || l.error || 'Notification dispatched'}</p>
        </div>
        <div class="text-[10px] text-slate-500 whitespace-nowrap">
          ${timeAgo}
        </div>
      </div>
    `;
  }).join('');
}

function formatTime(iso) {
  if (!iso) return '';
  const date = new Date(iso);
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function setSendFeedback(msg, type = 'success') {
  const el = document.getElementById('sendStatusFeedback');
  if (!el) return;
  el.className = `p-3 rounded-xl text-xs font-semibold border transition-all mt-3 ${
    type === 'success'
      ? 'bg-emerald-950/90 text-emerald-300 border-emerald-600 block'
      : type === 'warning'
      ? 'bg-amber-950/90 text-amber-300 border-amber-600 block'
      : 'bg-red-950/90 text-red-300 border-red-600 block'
  }`;
  el.innerHTML = `<span>${type === 'success' ? '✓' : '⚠️'} ${msg}</span>`;
  el.classList.remove('hidden');
}

// Handle Send Notification
async function handleSend(e) {
  e.preventDefault();
  let to = document.getElementById('sendTo').value.trim();
  const btn = document.getElementById('btnSubmitSend');
  btn.disabled = true;
  btn.innerHTML = '<span>Dispatching...</span>';

  // Normalize BD numbers like 017... to +88017...
  if (to.startsWith('01') && to.length === 11) {
    to = '+88' + to;
    document.getElementById('sendTo').value = to;
  }

  try {
    let payload = { to };

    if (dispatchMode === 'otp') {
      const res = await fetch('/api/v1/public/otp/request', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone: to })
      });
      const data = await res.json();
      if (!res.ok) {
        showToast(data.error || 'Failed to dispatch OTP', 'error');
        setSendFeedback(data.error || 'Failed to dispatch OTP', 'error');
      } else {
        const okMsg = `OTP code dispatched to ${data.maskedRecipient}! Valid for 5 minutes.`;
        showToast(okMsg, 'success');
        setSendFeedback(okMsg, 'success');
      }
    } else if (dispatchMode === 'template') {
      const templateId = document.getElementById('selectTemplate').value;
      const variables = {};
      const inputs = document.querySelectorAll('#dynamicVariableInputs input');
      inputs.forEach(inp => {
        variables[inp.getAttribute('data-var')] = inp.value.trim();
      });

      payload.templateId = templateId;
      payload.variables = variables;

      const res = await fetch('/api/v1/admin/test-send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();

      if (!data.success) {
        showToast(data.error || 'Failed to send message', 'warning');
        setSendFeedback(data.error || 'Failed to send message', 'warning');
      } else {
        const okMsg = `Notification successfully dispatched to ${data.maskedRecipient} via ${data.provider.toUpperCase()} gateway!`;
        showToast(okMsg, 'success');
        setSendFeedback(okMsg, 'success');
      }
    } else if (dispatchMode === 'custom') {
      payload.message = document.getElementById('customMessageText').value.trim();

      const res = await fetch('/api/v1/admin/test-send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();

      if (!data.success) {
        showToast(data.error || 'Failed to send custom message', 'warning');
        setSendFeedback(data.error || 'Failed to send custom message', 'warning');
      } else {
        const okMsg = `Custom alert dispatched to ${data.maskedRecipient}!`;
        showToast(okMsg, 'success');
        setSendFeedback(okMsg, 'success');
      }
    }

    await loadDashboardData();
  } catch (err) {
    showToast(`Network error: ${err.message}`, 'error');
    setSendFeedback(`Network error: ${err.message}`, 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<span>Dispatch Notification</span><span>→</span>';
  }
}

// Audit Logs
async function loadLogs() {
  const status = document.getElementById('logStatusFilter').value;
  const search = document.getElementById('logSearchInput').value.trim();

  const url = new URL('/api/v1/admin/logs', window.location.origin);
  if (status) url.searchParams.set('status', status);
  if (search) url.searchParams.set('search', search);

  const res = await fetch(url);
  const data = await res.json();

  const tbody = document.getElementById('logsTableBody');
  if (!data.logs || data.logs.length === 0) {
    tbody.innerHTML = '<tr><td colspan="6" class="py-8 text-center text-slate-500">No logs found matching criteria.</td></tr>';
    return;
  }

  tbody.innerHTML = data.logs.map(l => {
    let badgeClass = 'bg-emerald-950 text-emerald-400 border border-emerald-800';
    if (l.status === 'THROTTLED') badgeClass = 'bg-amber-950 text-amber-400 border border-amber-800';
    if (l.status === 'BLOCKED_ABUSE') badgeClass = 'bg-rose-950 text-rose-400 border border-rose-800';
    if (l.status === 'FAILED') badgeClass = 'bg-red-950 text-red-400 border border-red-800';

    return `
      <tr class="hover:bg-slate-900/50 transition">
        <td class="py-3 px-4 font-mono text-slate-400">${new Date(l.timestamp).toLocaleString()}</td>
        <td class="py-3 px-4 font-mono font-medium text-white">${l.recipient || 'N/A'}</td>
        <td class="py-3 px-4"><span class="px-2 py-0.5 rounded text-[10px] font-bold ${badgeClass}">${l.status}</span></td>
        <td class="py-3 px-4 text-slate-400">${l.category || 'TRANSACTIONAL'}</td>
        <td class="py-3 px-4 text-slate-300 max-w-xs truncate">${l.message || l.error || '-'}</td>
        <td class="py-3 px-4 font-mono text-cyan-400 uppercase">${l.gatewayProvider || 'N/A'}</td>
      </tr>
    `;
  }).join('');
}

function debounceLogSearch() {
  clearTimeout(searchDebounceTimer);
  searchDebounceTimer = setTimeout(loadLogs, 300);
}

// Load Active Cooldowns
async function loadCooldowns() {
  const res = await fetch('/api/v1/admin/cooldowns');
  const data = await res.json();
  const container = document.getElementById('cooldownsList');

  if (!data.cooldowns || data.cooldowns.length === 0) {
    container.innerHTML = '<p class="text-xs text-slate-500 text-center py-8">No numbers currently in cooldown.</p>';
    return;
  }

  container.innerHTML = data.cooldowns.map(c => `
    <div class="bg-slate-900 p-3 rounded-xl border border-borderCol flex items-center justify-between text-xs">
      <div>
        <span class="font-mono font-bold text-white">${c.maskedPhone}</span>
        <span class="text-slate-400 block text-[11px]">Sent ${c.dailyTotal} message(s) in last 24h</span>
      </div>
      <div class="text-right">
        <span class="px-2.5 py-1 rounded-lg text-xs font-mono font-bold bg-cyan-950 text-cyan-400 border border-cyan-800 cooldown-badge">
          ⏳ ${c.secondsRemaining}s left
        </span>
      </div>
    </div>
  `).join('');
}

// Load and Save Settings
async function loadSettings() {
  const res = await fetch('/api/v1/admin/settings');
  activeSettings = await res.json();

  // Shield Form
  const s = activeSettings.shield || {};
  document.getElementById('cfgCooldown').value = s.cooldownSeconds || 60;
  document.getElementById('cfgDailyLimit').value = s.dailyLimitPerNumber || 5;
  document.getElementById('cfgIpWindow').value = s.ipWindowMinutes || 10;
  document.getElementById('cfgIpMax').value = s.ipMaxRequests || 10;
  document.getElementById('cfgCountryCodes').value = (s.allowedCountryCodes || []).join(', ');
  document.getElementById('cfgFakeSuccess').checked = !!s.fakeSuccessOnAbuse;

  // Gateway Form
  const prov = activeSettings.gatewayProvider || 'simulator';
  onProviderSelect(prov);
  const radios = document.getElementsByName('providerOption');
  radios.forEach(r => { if (r.value === prov) r.checked = true; });

  const tw = activeSettings.gateway?.twilio || {};
  document.getElementById('twAccountSid').value = tw.accountSid || '';
  document.getElementById('twAuthToken').value = tw.authToken || '';
  document.getElementById('twFromNumber').value = tw.fromNumber || '';

  const cust = activeSettings.gateway?.customGateway || {};
  document.getElementById('customUrl').value = cust.url || '';
  document.getElementById('customMethod').value = cust.method || 'POST';
  document.getElementById('customBodyTpl').value = cust.bodyTemplate || '';
}

function onProviderSelect(prov) {
  document.getElementById('panelTwilio').classList.toggle('hidden', prov !== 'twilio');
  document.getElementById('panelCustomHttp').classList.toggle('hidden', prov !== 'custom_http');
}

async function handleSaveShield(e) {
  e.preventDefault();
  const payload = {
    shield: {
      cooldownSeconds: parseInt(document.getElementById('cfgCooldown').value, 10),
      dailyLimitPerNumber: parseInt(document.getElementById('cfgDailyLimit').value, 10),
      ipWindowMinutes: parseInt(document.getElementById('cfgIpWindow').value, 10),
      ipMaxRequests: parseInt(document.getElementById('cfgIpMax').value, 10),
      allowedCountryCodes: document.getElementById('cfgCountryCodes').value.split(',').map(c => c.trim()).filter(Boolean),
      fakeSuccessOnAbuse: document.getElementById('cfgFakeSuccess').checked
    }
  };

  const res = await fetch('/api/v1/admin/settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });

  if (res.ok) {
    showToast('Shield rules successfully updated!', 'success');
  } else {
    showToast('Failed to save settings', 'error');
  }
}

async function handleSaveGateway(e) {
  e.preventDefault();
  const selectedRadio = document.querySelector('input[name="providerOption"]:checked');
  const provider = selectedRadio ? selectedRadio.value : 'simulator';

  const payload = {
    gatewayProvider: provider,
    gateway: {
      twilio: {
        accountSid: document.getElementById('twAccountSid').value.trim(),
        authToken: document.getElementById('twAuthToken').value.trim(),
        fromNumber: document.getElementById('twFromNumber').value.trim()
      },
      customGateway: {
        url: document.getElementById('customUrl').value.trim(),
        method: document.getElementById('customMethod').value,
        bodyTemplate: document.getElementById('customBodyTpl').value.trim()
      }
    }
  };

  const res = await fetch('/api/v1/admin/settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });

  if (res.ok) {
    showToast(`Gateway set to ${provider.toUpperCase()}`, 'success');
    document.getElementById('headerGatewayBadge').innerText = provider.toUpperCase();
  } else {
    showToast('Failed to save gateway settings', 'error');
  }
}

// API Keys Management
async function loadApiKeys() {
  const res = await fetch('/api/v1/admin/api-keys');
  const data = await res.json();
  const container = document.getElementById('apiKeysList');

  if (!data.apiKeys || data.apiKeys.length === 0) {
    container.innerHTML = '<p class="text-xs text-slate-500 py-4">No API keys generated yet.</p>';
    return;
  }

  container.innerHTML = data.apiKeys.map(k => `
    <div class="bg-slate-900 border border-borderCol p-4 rounded-xl flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
      <div>
        <div class="font-bold text-white flex items-center gap-2">
          ${k.name}
          ${k.active ? '<span class="text-[10px] bg-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded border border-emerald-500/30">Active</span>' : '<span class="text-[10px] bg-red-500/20 text-red-400 px-2 py-0.5 rounded border border-red-500/30">Revoked</span>'}
        </div>
        <div class="font-mono text-slate-400 mt-1 flex items-center gap-2">
          <span>${k.key}</span>
          <button onclick="copyToClipboard('${k.key}')" class="text-brand-400 hover:underline">Copy</button>
        </div>
        <div class="text-[10px] text-slate-500 mt-1">Created: ${new Date(k.createdAt).toLocaleDateString()} &bull; Last used: ${k.lastUsedAt ? new Date(k.lastUsedAt).toLocaleDateString() : 'Never'}</div>
      </div>
      ${k.active ? `<button onclick="revokeApiKey('${k.id}')" class="text-xs text-rose-400 hover:text-rose-300 font-medium px-3 py-1.5 rounded-lg border border-rose-800/60 bg-rose-950/40">Revoke Key</button>` : ''}
    </div>
  `).join('');
}

async function createNewApiKey() {
  const name = prompt('Enter a label for this API key (e.g. My Website / Mobile App):');
  if (!name) return;

  const res = await fetch('/api/v1/admin/api-keys', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name })
  });

  if (res.ok) {
    showToast('New API key generated!', 'success');
    loadApiKeys();
  }
}

async function revokeApiKey(id) {
  if (!confirm('Are you sure you want to revoke this API key? Applications using this key will immediately stop working.')) return;
  const res = await fetch(`/api/v1/admin/api-keys/${id}`, { method: 'DELETE' });
  if (res.ok) {
    showToast('API key revoked', 'warning');
    loadApiKeys();
  }
}

// Copy to clipboard helper
function copyToClipboard(text) {
  navigator.clipboard.writeText(text);
  showToast('Copied to clipboard!', 'success');
}

function copySnippet(elementId) {
  const text = document.getElementById(elementId).innerText;
  copyToClipboard(text);
}

// ==========================================
// SAFE WHATSAPP OUTREACH IMPLEMENTATION
// ==========================================
const outreachPresets = {
  promo: `Assalamu Alaikum! 🌟\nSpecial limited-time offer for your business: Get an exclusive *25% discount* on our services this week!\n\nCheck our recent work & pricing: [Your Portfolio/Page Link]\nReply to this message if you'd like to claim this offer or have any questions. Have a wonderful day! 😊`,
  service: `Hello there! 🤝\nI came across your business and wanted to reach out. We help companies increase sales and streamline operations through top-tier service.\n\nWould you be open to a quick 5-minute chat to see how we can assist you?\nFeel free to reply here. Thank you!`,
  ecommerce: `Hey there! ✨\nWe have just launched our brand new collection with free delivery nationwide! 📦\n\nBrowse the new arrivals & special deals: [Your Page/Catalog Link]\nLet us know if you need help choosing or placing an order! 🛍️`,
  consulting: `Assalamu Alaikum! 👋\nHope you are having a productive week. We are currently offering a *Free 1-on-1 Strategy Consultation* for selected business owners this month.\n\nNo commitments—just actionable insights to help you grow.\nIf you're interested, reply "YES" and we will schedule a convenient time!`
};

let outreachContacts = [];
let outreachSessionSentCount = 0;

function initOutreachTab() {
  const msgEl = document.getElementById('outreachMessageText');
  if (msgEl && !msgEl.value) {
    selectOutreachPreset();
  }
  const rawNumbers = document.getElementById('outreachRawNumbers');
  if (rawNumbers && !rawNumbers.value.trim()) {
    rawNumbers.value = "01711223344\n01822334455\n01933445566";
  }
  loadOutreachState();
  if (outreachContacts.length === 0) {
    startOutreachQueue();
  }
}

function selectOutreachPreset() {
  const sel = document.getElementById('outreachPitchSelector').value;
  const msgEl = document.getElementById('outreachMessageText');
  if (outreachPresets[sel]) {
    msgEl.value = outreachPresets[sel];
  }
}

function updateOutreachPreview() {
  // Live typing event
}

function normalizeBangladeshNumber(raw) {
  let cleaned = raw.replace(/[^\d+]/g, '');
  if (!cleaned) return null;
  // If starts with 01X (11 digits)
  if (/^01[3-9]\d{8}$/.test(cleaned)) {
    return `880${cleaned.substring(1)}`;
  }
  // If starts with +8801X
  if (/^\+8801[3-9]\d{8}$/.test(cleaned)) {
    return cleaned.replace('+', '');
  }
  // If starts with 8801X
  if (/^8801[3-9]\d{8}$/.test(cleaned)) {
    return cleaned;
  }
  // If international format with +
  if (cleaned.startsWith('+')) {
    return cleaned.replace('+', '');
  }
  return cleaned.length >= 10 ? cleaned : null;
}

function parseOutreachNumbers() {
  const raw = document.getElementById('outreachRawNumbers').value;
  const lines = raw.split(/[\r\n,;]+/);
  const valid = [];

  lines.forEach(l => {
    const norm = normalizeBangladeshNumber(l.trim());
    if (norm && !valid.includes(norm)) {
      valid.push(norm);
    }
  });

  const countEl = document.getElementById('outreachParsedCount');
  if (countEl) countEl.innerText = `${valid.length} valid number(s)`;
  return valid;
}

function startOutreachQueue() {
  const numbers = parseOutreachNumbers();
  const text = document.getElementById('outreachMessageText').value.trim();

  if (numbers.length === 0) {
    showToast('Please enter at least one valid phone number.', 'warning');
    alert('Please enter or paste at least one phone number in the customer list box on the left!');
    return;
  }
  if (!text) {
    showToast('Please write an attractive pitch message.', 'warning');
    alert('Please write or select a pitch message!');
    return;
  }

  // Merge with existing queue or create new
  outreachContacts = numbers.map(num => ({
    phone: num,
    status: 'pending', // 'pending' | 'opened' | 'skipped'
    openedAt: null
  }));

  saveOutreachState();
  renderOutreachQueue();
  showToast(`Loaded ${numbers.length} contacts into queue!`, 'success');
}

function renderOutreachQueue() {
  const container = document.getElementById('outreachQueueContainer');
  if (!container) return;

  if (outreachContacts.length === 0) {
    container.innerHTML = `
      <div class="text-center py-12 text-slate-500 text-xs">
        <span class="text-3xl block mb-2">📋</span>
        Paste phone numbers on the left and click "Load Queue" to begin.
      </div>
    `;
    updateOutreachStats();
    return;
  }

  const messageText = document.getElementById('outreachMessageText').value.trim();
  const encodedText = encodeURIComponent(messageText);

  container.innerHTML = outreachContacts.map((c, idx) => {
    let statusBadge = '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-800 text-slate-400 border border-slate-700">PENDING</span>';
    let rowBorder = 'border-borderCol/70';

    if (c.status === 'opened') {
      statusBadge = '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-950 text-emerald-400 border border-emerald-800">✓ CHAT OPENED</span>';
      rowBorder = 'border-emerald-800/40 bg-emerald-950/10';
    } else if (c.status === 'skipped') {
      statusBadge = '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-900 text-slate-500 border border-slate-800">SKIPPED</span>';
    }

    const waMeUrl = `https://wa.me/${c.phone}?text=${encodedText}`;
    const webUrl = `https://web.whatsapp.com/send?phone=${c.phone}&text=${encodedText}`;

    return `
      <div class="bg-slate-900/90 border ${rowBorder} p-3 rounded-xl flex items-center justify-between gap-3 text-xs transition">
        <div class="flex items-center gap-3">
          <span class="text-[11px] font-mono text-slate-500 w-5">#${idx + 1}</span>
          <div>
            <div class="flex items-center gap-2">
              <span class="font-mono font-bold text-white">+${c.phone}</span>
              ${statusBadge}
            </div>
            <span class="text-[10px] text-slate-500 block">
              ${c.openedAt ? `Opened at ${new Date(c.openedAt).toLocaleTimeString()}` : 'Ready for 1-click dispatch'}
            </span>
          </div>
        </div>

        <div class="flex items-center gap-2">
          <!-- Direct unblockable native link -->
          <a href="${waMeUrl}" target="_blank" rel="noopener noreferrer" onclick="markContactOpened(${idx})" 
            class="bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs px-3 py-1.5 rounded-lg shadow transition flex items-center gap-1">
            <span>💬 Open Chat</span>
          </a>
          <a href="${webUrl}" target="_blank" rel="noopener noreferrer" onclick="markContactOpened(${idx})" 
            class="bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium text-xs px-2 py-1.5 rounded-lg border border-borderCol transition" title="Open directly in WhatsApp Web">
            <span>Web</span>
          </a>
          <button onclick="toggleContactSkip(${idx})" title="Skip this number" class="text-slate-500 hover:text-slate-300 px-1 text-xs">
            ${c.status === 'skipped' ? '↩' : '✕'}
          </button>
        </div>
      </div>
    `;
  }).join('');

  updateOutreachStats();
}

function markContactOpened(index) {
  const contact = outreachContacts[index];
  if (!contact) return;
  contact.status = 'opened';
  contact.openedAt = new Date().toISOString();
  outreachSessionSentCount++;
  saveOutreachState();
  renderOutreachQueue();
  showToast(`Chat opened for +${contact.phone}! Press Enter on WhatsApp.`, 'success');
}

function openNextPendingContact() {
  const nextIdx = outreachContacts.findIndex(c => c.status === 'pending');
  if (nextIdx === -1) {
    showToast('All contacts in queue have already been contacted!', 'success');
    return;
  }
  const contact = outreachContacts[nextIdx];
  const rawMessage = document.getElementById('outreachMessageText').value.trim();
  const encodedText = encodeURIComponent(rawMessage);
  const waUrl = `https://wa.me/${contact.phone}?text=${encodedText}`;

  // Safe programmatic click
  const a = document.createElement('a');
  a.href = waUrl;
  a.target = '_blank';
  a.rel = 'noopener noreferrer';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);

  markContactOpened(nextIdx);
}

function toggleContactSkip(index) {
  const contact = outreachContacts[index];
  if (!contact) return;
  contact.status = contact.status === 'skipped' ? 'pending' : 'skipped';
  saveOutreachState();
  renderOutreachQueue();
}

function clearOutreachQueue() {
  if (confirm('Clear the current outreach queue?')) {
    outreachContacts = [];
    localStorage.removeItem('outreach_queue');
    renderOutreachQueue();
  }
}

function updateOutreachStats() {
  const total = outreachContacts.length;
  const sent = outreachContacts.filter(c => c.status === 'opened').length;
  const remaining = outreachContacts.filter(c => c.status === 'pending').length;

  const totalEl = document.getElementById('outreachTotalStat');
  const sentEl = document.getElementById('outreachSentStat');
  const remEl = document.getElementById('outreachRemainingStat');
  const badgeEl = document.getElementById('outreachPacingBadge');

  if (totalEl) totalEl.innerText = total;
  if (sentEl) sentEl.innerText = sent;
  if (remEl) remEl.innerText = remaining;
  if (badgeEl) {
    badgeEl.innerText = `${outreachSessionSentCount} / 20 Sent`;
    if (outreachSessionSentCount >= 20) {
      badgeEl.className = 'text-sm font-extrabold text-amber-400 animate-pulse';
    }
  }
}

function saveOutreachState() {
  try {
    localStorage.setItem('outreach_queue', JSON.stringify(outreachContacts));
  } catch (e) {}
}

function loadOutreachState() {
  try {
    const saved = localStorage.getItem('outreach_queue');
    if (saved) {
      outreachContacts = JSON.parse(saved);
      renderOutreachQueue();
    }
  } catch (e) {}
}

