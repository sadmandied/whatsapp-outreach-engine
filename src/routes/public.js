const express = require('express');
const router = express.Router();
const notificationService = require('../services/notificationService');

// POST /api/v1/public/otp/request
// Requests an OTP verification code for login or signup
router.post('/otp/request', async (req, res) => {
  const { phone, turnstileToken } = req.body;
  const clientIp = req.headers['x-forwarded-for'] || req.socket.remoteAddress;

  if (!phone) {
    return res.status(400).json({ error: 'Phone number is required.' });
  }

  const result = await notificationService.requestCustomerOtp({
    phone,
    clientIp,
    turnstileToken
  });

  if (!result.success) {
    const statusCode = result.code === 'COOLDOWN_ACTIVE' || result.code === 'DAILY_CAP_REACHED' ? 429 : 400;
    return res.status(statusCode).json(result);
  }

  res.status(200).json(result);
});

// POST /api/v1/public/otp/verify
// Verifies the user-entered code
router.post('/otp/verify', (req, res) => {
  const { phone, code } = req.body;

  if (!phone || !code) {
    return res.status(400).json({ error: 'Both "phone" and "code" are required.' });
  }

  const result = notificationService.verifyCustomerOtp({ phone, code });
  if (!result.valid) {
    return res.status(400).json({ success: false, error: result.error });
  }

  res.status(200).json({
    success: true,
    message: 'Verification successful.'
  });
});

module.exports = router;
