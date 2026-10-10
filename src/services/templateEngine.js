const db = require('../db');

class TemplateEngine {
  render(templateId, variables = {}) {
    const template = db.getTemplateById(templateId);
    if (!template) {
      throw new Error(`Template not found: ${templateId}`);
    }

    let rendered = template.body;

    for (const [key, value] of Object.entries(variables)) {
      // Basic sanitization: strip excessive newlines or binary chars
      const sanitized = String(value == null ? '' : value)
        .replace(/[\r\n\t]/g, ' ')
        .substring(0, 200); // Prevent gigantic injections
      
      const regex = new RegExp(`{{\\s*${key}\\s*}}`, 'g');
      rendered = rendered.replace(regex, sanitized);
    }

    // Check if any unfilled variables remain like {{something}}
    const missing = rendered.match(/{{\s*[\w.-]+\s*}}/g);
    if (missing) {
      const missingVars = missing.map(m => m.replace(/[{}]/g, '').trim());
      throw new Error(`Missing required template variable(s): ${missingVars.join(', ')}`);
    }

    return {
      template,
      body: rendered.trim()
    };
  }

  validateCustomMessage(text) {
    if (!text || typeof text !== 'string') {
      return { valid: false, error: 'Message body cannot be empty.' };
    }
    const trimmed = text.trim();
    if (trimmed.length < 3) {
      return { valid: false, error: 'Message is too short.' };
    }
    if (trimmed.length > 480) { // Max 3 standard SMS segments
      return { valid: false, error: 'Message exceeds maximum length (480 characters).' };
    }
    return { valid: true, text: trimmed };
  }
}

const templateEngine = new TemplateEngine();
module.exports = templateEngine;
