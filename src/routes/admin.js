const express = require('express');
const router = express.Router();
const db = require('../db');
const shield = require('../services/shield');
const gateway = require('../services/gateway');
const notificationService = require('../services/notificationService');

// GET /api/v1/admin/metrics
router.get('/metrics', (req, res) => {
  const metrics = db.getMetrics();
  const cooldowns = shield.getActiveCooldowns();
  res.json({
    ...metrics,
    activeCooldownsCount: cooldowns.length,
    activeProvider: gateway.getActiveProvider()
  });
});

// GET /api/v1/admin/logs
router.get('/logs', (req, res) => {
  const { limit = 50, status, category, search } = req.query;
  const logs = db.getLogs({
    limit: parseInt(limit, 10),
    status,
    category,
    search
  });
  res.json({ logs });
});

// GET /api/v1/admin/cooldowns
router.get('/cooldowns', (req, res) => {
  const cooldowns = shield.getActiveCooldowns();
  res.json({ cooldowns });
});

// POST /api/v1/admin/test-send
router.post('/test-send', async (req, res) => {
  const { to, templateId, variables, message, category } = req.body;
  const clientIp = req.headers['x-forwarded-for'] || req.socket.remoteAddress;

  const result = await notificationService.dispatchMessage({
    to,
    templateId,
    variables: variables || {},
    customMessage: message,
    category: category || 'TRANSACTIONAL',
    clientIp,
    isPublic: false,
    apiKeyId: 'admin_console'
  });

  res.json(result);
});

// GET /api/v1/admin/settings
router.get('/settings', (req, res) => {
  const shieldCfg = shield.getShieldConfig();
  const gatewayCfg = gateway.getGatewayConfig();
  res.json({
    gatewayProvider: gateway.getActiveProvider(),
    shield: shieldCfg,
    gateway: gatewayCfg
  });
});

// POST /api/v1/admin/settings
router.post('/settings', (req, res) => {
  const { gatewayProvider, shield: shieldUpdates, gateway: gatewayUpdates } = req.body;

  const current = db.getSettings() || {};
  const updated = db.updateSettings({
    gatewayProvider: gatewayProvider !== undefined ? gatewayProvider : current.gatewayProvider,
    shield: { ...(current.shield || {}), ...(shieldUpdates || {}) },
    twilio: { ...(current.twilio || {}), ...(gatewayUpdates?.twilio || {}) },
    customGateway: { ...(current.customGateway || {}), ...(gatewayUpdates?.customGateway || {}) }
  });

  res.json({ success: true, settings: updated });
});

// GET /api/v1/admin/api-keys
router.get('/api-keys', (req, res) => {
  const keys = db.getApiKeys();
  res.json({ apiKeys: keys });
});

// POST /api/v1/admin/api-keys
router.post('/api-keys', (req, res) => {
  const { name } = req.body;
  const created = db.createApiKey(name);
  res.json({ success: true, apiKey: created });
});

// DELETE /api/v1/admin/api-keys/:id
router.delete('/api-keys/:id', (req, res) => {
  const success = db.revokeApiKey(req.params.id);
  res.json({ success });
});

// GET /api/v1/admin/templates
router.get('/templates', (req, res) => {
  res.json({ templates: db.getTemplates() });
});

// POST /api/v1/admin/templates
router.post('/templates', (req, res) => {
  const { id, name, category, body, variables } = req.body;
  if (!name || !body) {
    return res.status(400).json({ error: 'Template name and body are required.' });
  }

  // Extract variables automatically if not provided: {{variable}}
  const extractedVars = variables || (body.match(/{{\s*[\w.-]+\s*}}/g) || []).map(v => v.replace(/[{}]/g, '').trim());

  db.saveTemplate({
    id,
    name,
    category,
    body,
    variables: Array.from(new Set(extractedVars))
  });

  res.json({ success: true, templates: db.getTemplates() });
});

module.exports = router;
