const express = require('express');
const router = express.Router();
const db = require('../db');
const notificationService = require('../services/notificationService');

// Middleware to authenticate Backend API calls
function requireApiKey(req, res, next) {
  const headerKey = req.headers['x-api-key'] || 
    (req.headers.authorization && req.headers.authorization.startsWith('Bearer ') ? req.headers.authorization.slice(7) : null);

  if (!headerKey) {
    return res.status(401).json({
      error: 'Unauthorized. Missing API key.',
      hint: 'Provide your API key in the X-API-Key header or Authorization: Bearer <key> header.'
    });
  }

  const validKey = db.verifyApiKey(headerKey);
  if (!validKey) {
    return res.status(403).json({
      error: 'Forbidden. Invalid or revoked API key.'
    });
  }

  req.apiKey = validKey;
  next();
}

// POST /api/v1/messages/send
// Dispatches a notification to a customer phone number
router.post('/messages/send', requireApiKey, async (req, res) => {
  const { to, templateId, variables, message, category } = req.body;
  const clientIp = req.headers['x-forwarded-for'] || req.socket.remoteAddress;

  if (!to) {
    return res.status(400).json({ error: 'Recipient phone number "to" is required.' });
  }

  if (!templateId && !message) {
    return res.status(400).json({
      error: 'Either "templateId" (with optional "variables") or "message" must be provided.'
    });
  }

  const result = await notificationService.dispatchMessage({
    to,
    templateId,
    variables: variables || {},
    customMessage: message,
    category: category || 'TRANSACTIONAL',
    clientIp,
    isPublic: false,
    apiKeyId: req.apiKey.id
  });

  if (!result.success) {
    const statusCode = result.code === 'COOLDOWN_ACTIVE' || result.code === 'DAILY_CAP_REACHED' ? 429 : 400;
    return res.status(statusCode).json(result);
  }

  return res.status(200).json(result);
});

// GET /api/v1/templates
// Lists available templates for backend consumption
router.get('/templates', requireApiKey, (req, res) => {
  const templates = db.getTemplates();
  res.json({ templates });
});

// GET /api/v1/messages/status/:id
// Retrieves audit log status for a message
router.get('/messages/status/:id', requireApiKey, (req, res) => {
  const logs = db.getLogs({ limit: 100 });
  const found = logs.find(l => l.id === req.params.id || l.gatewayMessageId === req.params.id);
  if (!found) {
    return res.status(404).json({ error: 'Message ID not found.' });
  }
  res.json({ message: found });
});

module.exports = router;
