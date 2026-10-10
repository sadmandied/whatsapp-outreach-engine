const config = require('../config');
const db = require('../db');

class ShieldService {
  constructor() {
    // In-memory sliding state for ultra-fast checks
    // phone -> { lastSent: timestamp, history: [timestamps] }
    this.phoneState = new Map();
    // ip -> [timestamps]
    this.ipHistory = new Map();
    // active OTP store for verification: phone -> { code: '123456', expiresAt: timestamp, attempts: 0 }
    this.otpStore = new Map();

    // Periodic garbage collection every 10 minutes
    setInterval(() => this.cleanup(), 10 * 60 * 1000);
  }

  getShieldConfig() {
    const customSettings = db.getSettings() || {};
    return {
      ...config.shield,
      ...(customSettings.shield || {})
    };
  }

  cleanup() {
    const now = Date.now();
    const oneDay = 24 * 60 * 60 * 1000;

    for (const [phone, state] of this.phoneState.entries()) {
      state.history = state.history.filter(ts => now - ts < oneDay);
      if (state.history.length === 0 && now - state.lastSent > oneDay) {
        this.phoneState.delete(phone);
      }
    }

    for (const [ip, history] of this.ipHistory.entries()) {
      const recent = history.filter(ts => now - ts < oneDay);
      if (recent.length === 0) {
        this.ipHistory.delete(ip);
      } else {
        this.ipHistory.set(ip, recent);
      }
    }

    // Clean expired OTPs
    for (const [phone, otpData] of this.otpStore.entries()) {
      if (now > otpData.expiresAt) {
        this.otpStore.delete(phone);
      }
    }
  }

  normalizePhoneNumber(phone) {
    if (!phone) return '';
    let cleaned = phone.replace(/[^\d+]/g, '');
    if (!cleaned.startsWith('+')) {
      // Default to first allowed country code if no '+' prefix
      const shieldCfg = this.getShieldConfig();
      const defaultPrefix = shieldCfg.allowedCountryCodes[0] || '+880';
      cleaned = defaultPrefix + cleaned.replace(/^0+/, '');
    }
    return cleaned;
  }

  maskPhoneNumber(phone) {
    if (!phone || phone.length < 7) return phone;
    const prefix = phone.substring(0, 5);
    const suffix = phone.substring(phone.length - 3);
    const maskedLength = phone.length - 8;
    return `${prefix}${'*'.repeat(Math.max(maskedLength, 3))}${suffix}`;
  }

  validatePhone(phone) {
    const shieldCfg = this.getShieldConfig();
    const normalized = this.normalizePhoneNumber(phone);

    // E.164 check (between 10 and 16 chars, starts with +)
    if (!/^\+[1-9]\d{8,14}$/.test(normalized)) {
      return {
        valid: false,
        error: 'Invalid phone number format. Must follow standard international format (e.g. +8801712345678).'
      };
    }

    // Country code restriction
    if (shieldCfg.allowedCountryCodes && shieldCfg.allowedCountryCodes.length > 0) {
      const matchesAllowed = shieldCfg.allowedCountryCodes.some(prefix => normalized.startsWith(prefix));
      if (!matchesAllowed) {
        return {
          valid: false,
          error: `Phone numbers outside permitted region (${shieldCfg.allowedCountryCodes.join(', ')}) are blocked.`
        };
      }
    }

    return { valid: true, normalized };
  }

  async verifyCaptchaToken(token, clientIp) {
    const shieldCfg = this.getShieldConfig();
    if (!shieldCfg.turnstileSecretKey) {
      // Turnstile not configured, bypass
      return { success: true };
    }

    if (!token) {
      return { success: false, error: 'Human verification token (CAPTCHA) is required.' };
    }

    try {
      const response = await fetch('https://challenges.cloudflare.com/turnstile/v0/siteverify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({
          secret: shieldCfg.turnstileSecretKey,
          response: token,
          remoteip: clientIp || ''
        })
      });
      const data = await response.json();
      if (!data.success) {
        return { success: false, error: 'CAPTCHA verification failed. Please try again.' };
      }
      return { success: true };
    } catch (err) {
      console.error('Turnstile verification error:', err.message);
      return { success: false, error: 'Verification service error' };
    }
  }

  checkAbuse({ phone, clientIp, isPublic = false }) {
    const shieldCfg = this.getShieldConfig();
    const now = Date.now();

    // 1. IP velocity limit
    if (clientIp) {
      const ipTimes = this.ipHistory.get(clientIp) || [];
      const windowMs = shieldCfg.ipWindowMinutes * 60 * 1000;
      const recentIpAttempts = ipTimes.filter(ts => now - ts < windowMs);

      if (recentIpAttempts.length >= shieldCfg.ipMaxRequests) {
        return {
          allowed: false,
          reason: 'IP_VELOCITY_EXCEEDED',
          message: `Too many requests from this IP address. Please wait ${shieldCfg.ipWindowMinutes} minutes.`,
          retryAfter: Math.ceil((windowMs - (now - recentIpAttempts[0])) / 1000)
        };
      }
    }

    // 2. Per-number checks
    const state = this.phoneState.get(phone) || { lastSent: 0, history: [] };

    // Cooldown check
    const cooldownMs = shieldCfg.cooldownSeconds * 1000;
    const elapsedSinceLast = now - state.lastSent;
    if (elapsedSinceLast < cooldownMs) {
      const waitSeconds = Math.ceil((cooldownMs - elapsedSinceLast) / 1000);
      return {
        allowed: false,
        reason: 'COOLDOWN_ACTIVE',
        message: `Please wait ${waitSeconds}s before requesting another message.`,
        retryAfter: waitSeconds
      };
    }

    // 24-hour daily cap check
    const oneDayMs = 24 * 60 * 60 * 1000;
    const recentDayAttempts = state.history.filter(ts => now - ts < oneDayMs);
    if (recentDayAttempts.length >= shieldCfg.dailyLimitPerNumber) {
      return {
        allowed: false,
        reason: 'DAILY_CAP_REACHED',
        message: `Maximum daily messages (${shieldCfg.dailyLimitPerNumber}) reached for this number.`,
        retryAfter: 86400
      };
    }

    return { allowed: true };
  }

  recordAttempt({ phone, clientIp, success = true }) {
    const now = Date.now();

    // Record IP attempt
    if (clientIp) {
      const ipTimes = this.ipHistory.get(clientIp) || [];
      ipTimes.push(now);
      this.ipHistory.set(clientIp, ipTimes);
    }

    // Record Phone attempt if successfully dispatched
    if (success && phone) {
      const state = this.phoneState.get(phone) || { lastSent: 0, history: [] };
      state.lastSent = now;
      state.history.push(now);
      this.phoneState.set(phone, state);
    }
  }

  // OTP generation & store
  generateOtp(phone, length = 6, validityMinutes = 5) {
    const code = Math.floor(100000 + Math.random() * 900000).toString().substring(0, length);
    const expiresAt = Date.now() + validityMinutes * 60 * 1000;

    this.otpStore.set(phone, {
      code,
      expiresAt,
      attempts: 0
    });

    return { code, expiresAt };
  }

  verifyOtp(phone, inputCode) {
    const record = this.otpStore.get(phone);
    if (!record) {
      return { valid: false, error: 'No OTP request found for this number or it has expired.' };
    }

    if (Date.now() > record.expiresAt) {
      this.otpStore.delete(phone);
      return { valid: false, error: 'OTP has expired. Please request a new one.' };
    }

    record.attempts += 1;
    if (record.attempts > 4) {
      this.otpStore.delete(phone);
      return { valid: false, error: 'Too many incorrect attempts. OTP invalidated.' };
    }

    if (record.code === inputCode.trim()) {
      this.otpStore.delete(phone); // Burn after successful use
      return { valid: true };
    }

    return { valid: false, error: `Invalid code. ${5 - record.attempts} attempt(s) remaining.` };
  }

  getActiveCooldowns() {
    const now = Date.now();
    const shieldCfg = this.getShieldConfig();
    const cooldownMs = shieldCfg.cooldownSeconds * 1000;
    const list = [];

    for (const [phone, state] of this.phoneState.entries()) {
      const elapsed = now - state.lastSent;
      if (elapsed < cooldownMs) {
        list.push({
          maskedPhone: this.maskPhoneNumber(phone),
          secondsRemaining: Math.ceil((cooldownMs - elapsed) / 1000),
          dailyTotal: state.history.filter(ts => now - ts < 86400000).length
        });
      }
    }

    return list;
  }
}

const shield = new ShieldService();
module.exports = shield;
