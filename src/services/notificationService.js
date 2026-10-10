const shield = require('./shield');
const gateway = require('./gateway');
const templateEngine = require('./templateEngine');
const db = require('../db');

class NotificationService {
  async dispatchMessage({
    to,
    templateId,
    variables = {},
    customMessage,
    category = 'TRANSACTIONAL',
    clientIp,
    isPublic = false,
    apiKeyId = null,
    turnstileToken = null
  }) {
    // 1. Phone number validation
    const phoneValidation = shield.validatePhone(to);
    if (!phoneValidation.valid) {
      db.addLog({
        recipient: shield.maskPhoneNumber(to),
        status: 'FAILED',
        reason: 'INVALID_PHONE_NUMBER',
        category,
        error: phoneValidation.error,
        clientIp,
        apiKeyId
      });
      return { success: false, error: phoneValidation.error, code: 'INVALID_PHONE' };
    }
    const normalizedPhone = phoneValidation.normalized;
    const maskedPhone = shield.maskPhoneNumber(normalizedPhone);

    // 2. CAPTCHA verification (if public endpoint)
    if (isPublic) {
      const captchaResult = await shield.verifyCaptchaToken(turnstileToken, clientIp);
      if (!captchaResult.success) {
        db.addLog({
          recipient: maskedPhone,
          status: 'BLOCKED_ABUSE',
          reason: 'CAPTCHA_FAILED',
          category,
          error: captchaResult.error,
          clientIp,
          apiKeyId
        });
        return { success: false, error: captchaResult.error, code: 'CAPTCHA_FAILED' };
      }
    }

    // 3. Shield Anti-Abuse Checks (Cooldown, Daily Cap, IP Velocity)
    const abuseCheck = shield.checkAbuse({ phone: normalizedPhone, clientIp, isPublic });
    if (!abuseCheck.allowed) {
      const shieldCfg = shield.getShieldConfig();

      db.addLog({
        recipient: maskedPhone,
        status: 'THROTTLED',
        reason: abuseCheck.reason,
        category,
        error: abuseCheck.message,
        clientIp,
        apiKeyId
      });

      // Honeypot / Fake Success behavior if configured:
      if (isPublic && shieldCfg.fakeSuccessOnAbuse) {
        return {
          success: true,
          throttled: true,
          messageId: `fake_${Date.now()}`,
          maskedRecipient: maskedPhone,
          status: 'SENT',
          note: 'Delivered (Shield Protected)'
        };
      }

      return {
        success: false,
        error: abuseCheck.message,
        reason: abuseCheck.reason,
        retryAfter: abuseCheck.retryAfter,
        code: abuseCheck.reason
      };
    }

    // 4. Resolve Message Content
    let finalMessage = '';
    let usedTemplateId = null;

    try {
      if (templateId) {
        const rendered = templateEngine.render(templateId, variables);
        finalMessage = rendered.body;
        usedTemplateId = templateId;
        category = rendered.template.category || category;
      } else if (customMessage && !isPublic) {
        // Custom free-form messages are ONLY allowed for authenticated backend calls or admin
        const validation = templateEngine.validateCustomMessage(customMessage);
        if (!validation.valid) {
          return { success: false, error: validation.error, code: 'INVALID_MESSAGE' };
        }
        finalMessage = validation.text;
      } else {
        return {
          success: false,
          error: 'A valid templateId must be specified for this message.',
          code: 'TEMPLATE_REQUIRED'
        };
      }
    } catch (err) {
      return { success: false, error: err.message, code: 'TEMPLATE_RENDER_ERROR' };
    }

    // 5. Gateway Dispatch
    try {
      const gatewayResponse = await gateway.send({
        to: normalizedPhone,
        message: finalMessage,
        category
      });

      // 6. Record successful dispatch in shield state
      shield.recordAttempt({ phone: normalizedPhone, clientIp, success: true });

      // 7. Audit Logging
      const log = db.addLog({
        recipient: maskedPhone,
        status: gatewayResponse.status || 'DELIVERED',
        category,
        templateId: usedTemplateId,
        message: finalMessage,
        gatewayProvider: gatewayResponse.provider,
        gatewayMessageId: gatewayResponse.gatewayMessageId,
        clientIp,
        apiKeyId
      });

      return {
        success: true,
        messageId: log.id,
        gatewayMessageId: gatewayResponse.gatewayMessageId,
        provider: gatewayResponse.provider,
        status: gatewayResponse.status,
        maskedRecipient: maskedPhone
      };
    } catch (err) {
      // Record failed gateway call
      shield.recordAttempt({ phone: normalizedPhone, clientIp, success: false });

      db.addLog({
        recipient: maskedPhone,
        status: 'FAILED',
        category,
        templateId: usedTemplateId,
        message: finalMessage,
        error: err.message,
        clientIp,
        apiKeyId
      });

      return {
        success: false,
        error: `Gateway dispatch failure: ${err.message}`,
        code: 'GATEWAY_ERROR'
      };
    }
  }

  // Specialized helper for Customer OTP verification flows
  async requestCustomerOtp({ phone, clientIp, turnstileToken }) {
    const phoneValidation = shield.validatePhone(phone);
    if (!phoneValidation.valid) {
      return { success: false, error: phoneValidation.error };
    }
    const normalizedPhone = phoneValidation.normalized;

    // Pre-check abuse BEFORE generating or overwriting any active OTP
    const abuseCheck = shield.checkAbuse({ phone: normalizedPhone, clientIp, isPublic: true });
    if (!abuseCheck.allowed) {
      return {
        success: false,
        error: abuseCheck.message,
        reason: abuseCheck.reason,
        retryAfter: abuseCheck.retryAfter,
        code: abuseCheck.reason
      };
    }

    // Generate random 6-digit code only once verified that request is permitted
    const { code, expiresAt } = shield.generateOtp(normalizedPhone, 6, 5);

    // Dispatch via standardized template
    const dispatchResult = await this.dispatchMessage({
      to: normalizedPhone,
      templateId: 'OTP_VERIFICATION',
      variables: { code },
      category: 'AUTH',
      clientIp,
      isPublic: true,
      turnstileToken
    });

    if (!dispatchResult.success) {
      return dispatchResult;
    }

    return {
      success: true,
      maskedRecipient: dispatchResult.maskedRecipient,
      expiresInSeconds: Math.floor((expiresAt - Date.now()) / 1000)
    };
  }

  verifyCustomerOtp({ phone, code }) {
    const phoneValidation = shield.validatePhone(phone);
    if (!phoneValidation.valid) {
      return { success: false, error: phoneValidation.error };
    }
    return shield.verifyOtp(phoneValidation.normalized, code);
  }
}

const notificationService = new NotificationService();
module.exports = notificationService;
