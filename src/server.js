const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const path = require('path');
const config = require('./config');

const apiRoutes = require('./routes/api');
const publicRoutes = require('./routes/public');
const adminRoutes = require('./routes/admin');

const app = express();

// Clean local server - no cross-origin restrictions on external links

app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Disable caching for live development & log requests
app.use((req, res, next) => {
  res.set('Cache-Control', 'no-store, no-cache, must-revalidate, private');
  console.log(`[REQ ${new Date().toLocaleTimeString()}] ${req.method} ${req.url}`);
  next();
});

// Serve frontend static files
app.use(express.static(path.join(__dirname, 'public'), { etag: false, maxAge: 0 }));

// Health Check
app.get('/health', (req, res) => {
  res.json({
    status: 'ok',
    timestamp: new Date().toISOString(),
    service: 'secure-notify-service',
    version: '1.0.0'
  });
});

// Mount Routes
app.use('/api/v1', apiRoutes);
app.use('/api/v1/public', publicRoutes);
app.use('/api/v1/admin', adminRoutes);

// Favicon handler
app.get('/favicon.ico', (req, res) => res.status(204).end());

// Fallback to dashboard for SPA
app.use((req, res) => {
  res.sendFile('index.html', { root: path.join(__dirname, 'public') });
});

// Error handling middleware
app.use((err, req, res, next) => {
  console.error('[UNHANDLED SERVER ERROR]', err);
  res.status(500).json({
    error: 'Internal Server Error',
    message: err.message
  });
});

const PORT = config.port;
const server = app.listen(PORT, '0.0.0.0', () => {
  console.log(`=======================================================`);
  console.log(`🛡️  Secure Customer Notification Service is LIVE!`);
  console.log(`🌐 Dashboard:    http://localhost:${PORT}`);
  console.log(`📡 Backend API:  http://localhost:${PORT}/api/v1/messages/send`);
  console.log(`🔐 Public OTP:   http://localhost:${PORT}/api/v1/public/otp/request`);
  console.log(`⚙️  SMS Gateway:  ${config.gatewayProvider.toUpperCase()}`);
  console.log(`🛡️  Shield:       ACTIVE (Anti-Abuse, Rate-Limiter, Cooldown)`);
  console.log(`=======================================================`);
});

module.exports = { app, server };
