// api.js
const crypto = require('crypto');
const express = require('express');

const RPM_RATE = parseFloat(process.env.RPM_RATE || '5.00');

function getConfiguredApiKey() {
  return process.env.API_KEY || process.env.NODE_API_KEY || 'seo-secret-api-key-2026';
}

function safeCompareKey(providedKey, expectedKey) {
  const providedHash = crypto.createHash('sha256').update(String(providedKey || '')).digest();
  const expectedHash = crypto.createHash('sha256').update(String(expectedKey || '')).digest();
  return crypto.timingSafeEqual(providedHash, expectedHash);
}

function requireApiKey(req, res, next) {
  const headerKey =
    req.headers['api_key'] ||
    req.headers['x-api-key'] ||
    (req.headers.authorization && req.headers.authorization.startsWith('Bearer ')
      ? req.headers.authorization.slice(7).trim()
      : null);

  if (!headerKey || !safeCompareKey(headerKey, getConfiguredApiKey())) {
    return res.status(401).json({
      success: false,
      error: 'Unauthorized: Invalid or missing API_KEY header.'
    });
  }

  return next();
}

function createApiRouter(db) {
  const router = express.Router();

  const countPagesStmt = db.prepare(`SELECT COUNT(*) AS count FROM pages`);
  const countAllViewsStmt = db.prepare(`SELECT COUNT(*) AS count FROM analytics`);
  const countTodayViewsStmt = db.prepare(`SELECT COUNT(*) AS count FROM analytics WHERE date = ?`);

  router.get('/admin/stats', requireApiKey, (_req, res) => {
    try {
      const todayIso = new Date().toISOString().slice(0, 10);

      const totalPages = countPagesStmt.get().count || 0;
      const totalViews = countAllViewsStmt.get().count || 0;
      const todayViews = countTodayViewsStmt.get(todayIso).count || 0;
      const estimatedEarnings = Number(((totalViews / 1000) * RPM_RATE).toFixed(2));

      return res.status(200).json({
        success: true,
        total_pages: totalPages,
        total_views: totalViews,
        today_views: todayViews,
        rpm: RPM_RATE,
        estimated_earnings: estimatedEarnings,
        formatted_earnings: `$${estimatedEarnings.toFixed(2)}`,
        timestamp: new Date().toISOString()
      });
    } catch (error) {
      console.error('Error in GET /api/admin/stats:', error);
      return res.status(500).json({
        success: false,
        error: 'Internal server error while querying SQLite stats.'
      });
    }
  });

  return router;
}

module.exports = {
  createApiRouter,
  requireApiKey
};
