require('dotenv').config();

const config = {
  port: parseInt(process.env.PORT || '3000', 10),
  adminSecretKey: process.env.ADMIN_SECRET_KEY || 'admin12345',
  
  // Active Gateway: "simulator" | "twilio" | "custom_http"
  gatewayProvider: process.env.SMS_GATEWAY_PROVIDER || 'simulator',
  
  // Twilio settings
  twilio: {
    accountSid: process.env.TWILIO_ACCOUNT_SID || '',
    authToken: process.env.TWILIO_AUTH_TOKEN || '',
    fromNumber: process.env.TWILIO_FROM_NUMBER || '',
  },

  // Custom HTTP gateway settings
  customGateway: {
    url: process.env.CUSTOM_GATEWAY_URL || '',
    method: (process.env.CUSTOM_GATEWAY_METHOD || 'POST').toUpperCase(),
    headers: process.env.CUSTOM_GATEWAY_HEADERS ? JSON.parse(process.env.CUSTOM_GATEWAY_HEADERS) : { 'Content-Type': 'application/json' },
    bodyTemplate: process.env.CUSTOM_GATEWAY_BODY_TEMPLATE || '{"to": "{{to}}", "message": "{{message}}"}',
  },

  // Shield / Anti-Abuse engine settings
  shield: {
    cooldownSeconds: parseInt(process.env.COOLDOWN_SECONDS || '60', 10),
    dailyLimitPerNumber: parseInt(process.env.DAILY_LIMIT_PER_NUMBER || '5', 10),
    ipWindowMinutes: parseInt(process.env.IP_WINDOW_MINUTES || '10', 10),
    ipMaxRequests: parseInt(process.env.IP_MAX_REQUESTS || '10', 10),
    allowedCountryCodes: (process.env.ALLOWED_COUNTRY_CODES || '+880,+1,+44')
      .split(',')
      .map(c => c.trim())
      .filter(Boolean),
    fakeSuccessOnAbuse: process.env.FAKE_SUCCESS_ON_ABUSE === 'true',
    turnstileSecretKey: process.env.TURNSTILE_SECRET_KEY || '',
    turnstileSiteKey: process.env.TURNSTILE_SITE_KEY || '',
  }
};

module.exports = config;
