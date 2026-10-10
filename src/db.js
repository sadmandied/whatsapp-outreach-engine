const fs = require('fs');
const path = require('path');
const { v4: uuidv4 } = require('uuid');

const DATA_DIR = path.join(__dirname, '..', 'data');
const DB_FILE = path.join(DATA_DIR, 'db.json');

// Ensure data directory exists
if (!fs.existsSync(DATA_DIR)) {
  fs.mkdirSync(DATA_DIR, { recursive: true });
}

const DEFAULT_TEMPLATES = [
  {
    id: 'OTP_VERIFICATION',
    name: 'OTP Verification Code',
    category: 'AUTH',
    body: 'Your verification code is: {{code}}. Do not share this code with anyone. Valid for 5 minutes.',
    variables: ['code'],
    isSystem: true
  },
  {
    id: 'ORDER_CONFIRMATION',
    name: 'Order Confirmation',
    category: 'ORDERS',
    body: 'Hi {{customerName}}, your order #{{orderId}} of ${{amount}} is confirmed and being prepared!',
    variables: ['customerName', 'orderId', 'amount'],
    isSystem: true
  },
  {
    id: 'SHIPPING_UPDATE',
    name: 'Shipping / Out for Delivery',
    category: 'ORDERS',
    body: 'Great news {{customerName}}! Your package #{{trackingNumber}} is out for delivery today.',
    variables: ['customerName', 'trackingNumber'],
    isSystem: true
  },
  {
    id: 'PAYMENT_RECEIPT',
    name: 'Payment Receipt',
    category: 'BILLING',
    body: 'Payment received! We received ${{amount}} for invoice #{{invoiceId}}. Thank you for your business.',
    variables: ['amount', 'invoiceId'],
    isSystem: true
  },
  {
    id: 'SECURITY_ALERT',
    name: 'Account Security Alert',
    category: 'SECURITY',
    body: 'Security Alert: A new login to your account was detected from {{location}}. If this was not you, secure your account immediately.',
    variables: ['location'],
    isSystem: true
  }
];

const DEFAULT_STATE = {
  apiKeys: [
    {
      id: 'key_default_1',
      name: 'Primary Backend Integration Key',
      key: 'sec_live_demo_key_998877',
      createdAt: new Date().toISOString(),
      lastUsedAt: null,
      active: true,
      permissions: ['messages:send', 'templates:read']
    }
  ],
  templates: DEFAULT_TEMPLATES,
  logs: [],
  settings: null // loaded from config or user overrides
};

class Database {
  constructor() {
    this.data = this.load();
  }

  load() {
    try {
      if (fs.existsSync(DB_FILE)) {
        const raw = fs.readFileSync(DB_FILE, 'utf-8');
        const parsed = JSON.parse(raw);
        return {
          ...DEFAULT_STATE,
          ...parsed,
          templates: parsed.templates && parsed.templates.length ? parsed.templates : DEFAULT_TEMPLATES
        };
      }
    } catch (err) {
      console.error('Failed to load existing db.json, initializing fresh store:', err.message);
    }
    const initial = { ...DEFAULT_STATE };
    this.saveDirect(initial);
    return initial;
  }

  save() {
    try {
      const tempPath = `${DB_FILE}.tmp`;
      fs.writeFileSync(tempPath, JSON.stringify(this.data, null, 2), 'utf-8');
      fs.renameSync(tempPath, DB_FILE);
    } catch (err) {
      console.error('Failed to save db.json:', err.message);
    }
  }

  saveDirect(data) {
    fs.writeFileSync(DB_FILE, JSON.stringify(data, null, 2), 'utf-8');
  }

  // --- API Keys ---
  getApiKeys() {
    return this.data.apiKeys;
  }

  createApiKey(name, permissions = ['messages:send']) {
    const newKey = {
      id: `key_${uuidv4().substring(0, 8)}`,
      name: name || 'New Backend Key',
      key: `sec_live_${uuidv4().replace(/-/g, '')}`,
      createdAt: new Date().toISOString(),
      lastUsedAt: null,
      active: true,
      permissions
    };
    this.data.apiKeys.push(newKey);
    this.save();
    return newKey;
  }

  revokeApiKey(keyId) {
    const key = this.data.apiKeys.find(k => k.id === keyId || k.key === keyId);
    if (key) {
      key.active = false;
      this.save();
      return true;
    }
    return false;
  }

  verifyApiKey(rawKey) {
    if (!rawKey) return false;
    const found = this.data.apiKeys.find(k => k.key === rawKey && k.active);
    if (found) {
      found.lastUsedAt = new Date().toISOString();
      this.save();
      return found;
    }
    return null;
  }

  // --- Audit Logs ---
  addLog(entry) {
    const log = {
      id: `log_${uuidv4()}`,
      timestamp: new Date().toISOString(),
      ...entry
    };
    this.data.logs.unshift(log); // newest first
    // keep max 500 logs in storage
    if (this.data.logs.length > 500) {
      this.data.logs = this.data.logs.slice(0, 500);
    }
    this.save();
    return log;
  }

  getLogs({ limit = 50, status, category, search } = {}) {
    let result = this.data.logs;
    if (status) {
      result = result.filter(l => l.status === status);
    }
    if (category) {
      result = result.filter(l => l.category === category);
    }
    if (search) {
      const q = search.toLowerCase();
      result = result.filter(l => 
        (l.recipient && l.recipient.includes(q)) ||
        (l.message && l.message.toLowerCase().includes(q)) ||
        (l.templateId && l.templateId.toLowerCase().includes(q))
      );
    }
    return result.slice(0, limit);
  }

  // --- Templates ---
  getTemplates() {
    return this.data.templates;
  }

  getTemplateById(id) {
    return this.data.templates.find(t => t.id === id);
  }

  saveTemplate({ id, name, category, body, variables }) {
    const existing = this.data.templates.find(t => t.id === id);
    if (existing) {
      existing.name = name || existing.name;
      existing.category = category || existing.category;
      existing.body = body || existing.body;
      existing.variables = variables || existing.variables;
    } else {
      this.data.templates.push({
        id: id || `TPL_${Date.now()}`,
        name,
        category: category || 'CUSTOM',
        body,
        variables: variables || [],
        isSystem: false
      });
    }
    this.save();
  }

  // --- Dynamic Settings ---
  getSettings() {
    return this.data.settings;
  }

  updateSettings(settings) {
    this.data.settings = { ...this.data.settings, ...settings };
    this.save();
    return this.data.settings;
  }

  // --- Aggregate Metrics ---
  getMetrics() {
    const total = this.data.logs.length;
    const delivered = this.data.logs.filter(l => l.status === 'DELIVERED').length;
    const sent = this.data.logs.filter(l => l.status === 'SENT' || l.status === 'DELIVERED').length;
    const blocked = this.data.logs.filter(l => l.status === 'BLOCKED_ABUSE' || l.status === 'THROTTLED').length;
    const failed = this.data.logs.filter(l => l.status === 'FAILED').length;
    
    return {
      total,
      sent,
      delivered,
      blocked,
      failed,
      successRate: sent > 0 ? Math.round((delivered / sent) * 100) : 100,
      recentActivity: this.data.logs.slice(0, 10)
    };
  }
}

const db = new Database();
module.exports = db;
