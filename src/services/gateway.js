const config = require('../config');
const db = require('../db');
const { v4: uuidv4 } = require('uuid');

class GatewayService {
  getActiveProvider() {
    const customSettings = db.getSettings() || {};
    return customSettings.gatewayProvider || config.gatewayProvider || 'simulator';
  }

  getGatewayConfig() {
    const customSettings = db.getSettings() || {};
    return {
      twilio: { ...config.twilio, ...(customSettings.twilio || {}) },
      customGateway: { ...config.customGateway, ...(customSettings.customGateway || {}) }
    };
  }

  async send({ to, message, category = 'TRANSACTIONAL' }) {
    const provider = this.getActiveProvider();

    switch (provider) {
      case 'twilio':
        return await this.sendViaTwilio({ to, message });
      case 'custom_http':
        return await this.sendViaCustomHttp({ to, message });
      case 'simulator':
      default:
        return await this.sendViaSimulator({ to, message, category });
    }
  }

  async sendViaSimulator({ to, message, category }) {
    // Artificial slight network latency (50ms - 150ms) to simulate real telecom round-trip
    await new Promise(r => setTimeout(r, 60));

    const mockId = `sim_msg_${uuidv4().substring(0, 12)}`;
    console.log(`[SIMULATOR SMS DISPATCH] To: ${to} | Category: ${category} | Message: "${message}"`);

    return {
      success: true,
      provider: 'simulator',
      gatewayMessageId: mockId,
      status: 'DELIVERED',
      details: {
        network: 'Simulator Virtual Carrier',
        timestamp: new Date().toISOString(),
        cost: '$0.00 (Mock)'
      }
    };
  }

  async sendViaTwilio({ to, message }) {
    const { twilio } = this.getGatewayConfig();

    if (!twilio.accountSid || !twilio.authToken || !twilio.fromNumber) {
      throw new Error('Twilio credentials (Account SID, Auth Token, From Number) are incomplete.');
    }

    const endpoint = `https://api.twilio.com/2010-04-01/Accounts/${twilio.accountSid}/Messages.json`;
    const authHeader = 'Basic ' + Buffer.from(`${twilio.accountSid}:${twilio.authToken}`).toString('base64');

    const params = new URLSearchParams();
    params.append('To', to);
    params.append('From', twilio.fromNumber);
    params.append('Body', message);

    const response = await fetch(endpoint, {
      method: 'POST',
      headers: {
        'Authorization': authHeader,
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      body: params.toString()
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(`Twilio API Error [${response.status}]: ${data.message || JSON.stringify(data)}`);
    }

    return {
      success: true,
      provider: 'twilio',
      gatewayMessageId: data.sid,
      status: data.status ? data.status.toUpperCase() : 'SENT',
      details: data
    };
  }

  async sendViaCustomHttp({ to, message }) {
    const { customGateway } = this.getGatewayConfig();

    if (!customGateway.url) {
      throw new Error('Custom Gateway URL is not configured.');
    }

    let url = customGateway.url
      .replace(/{{to}}/g, encodeURIComponent(to))
      .replace(/{{message}}/g, encodeURIComponent(message));

    let body = null;
    if (customGateway.method !== 'GET') {
      if (typeof customGateway.bodyTemplate === 'string') {
        const rendered = customGateway.bodyTemplate
          .replace(/{{to}}/g, to)
          .replace(/{{message}}/g, message);
        body = rendered;
      } else {
        body = JSON.stringify({ to, message });
      }
    }

    const response = await fetch(url, {
      method: customGateway.method || 'POST',
      headers: customGateway.headers || { 'Content-Type': 'application/json' },
      body
    });

    const responseText = await response.text();
    let responseData;
    try {
      responseData = JSON.parse(responseText);
    } catch {
      responseData = { raw: responseText };
    }

    if (!response.ok) {
      throw new Error(`Custom Gateway Error [${response.status}]: ${responseText}`);
    }

    return {
      success: true,
      provider: 'custom_http',
      gatewayMessageId: `custom_${Date.now()}`,
      status: 'SENT',
      details: responseData
    };
  }
}

const gateway = new GatewayService();
module.exports = gateway;
