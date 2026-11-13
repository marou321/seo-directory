// adminRoutes.js
const path = require('path');
const crypto = require('crypto');
const { exec } = require('child_process');
const express = require('express');

const RPM_RATE = parseFloat(process.env.RPM_RATE || '5.00');
const ADMIN_COOKIE_NAME = 'seo_admin_session';

function getAdminPassword() {
  return process.env.ADMIN_PASSWORD || 'admin123';
}

function getSigningSecret() {
  return process.env.COOKIE_SECRET || `seo-directory-secret-${getAdminPassword()}`;
}

function createSignedToken(payload) {
  const data = Buffer.from(JSON.stringify(payload)).toString('base64url');
  const signature = crypto
    .createHmac('sha256', getSigningSecret())
    .update(data)
    .digest('base64url');
  return `${data}.${signature}`;
}

function verifySignedToken(token) {
  if (!token || typeof token !== 'string' || !token.includes('.')) {
    return null;
  }
  const [data, signature] = token.split('.');
  const expectedSig = crypto
    .createHmac('sha256', getSigningSecret())
    .update(data)
    .digest('base64url');

  const sigBuffer = Buffer.from(signature);
  const expectedBuffer = Buffer.from(expectedSig);
  if (sigBuffer.length !== expectedBuffer.length) {
    return null;
  }
  if (!crypto.timingSafeEqual(sigBuffer, expectedBuffer)) {
    return null;
  }

  try {
    const parsed = JSON.parse(Buffer.from(data, 'base64url').toString('utf8'));
    if (!parsed.exp || Date.now() > parsed.exp) {
      return null;
    }
    return parsed;
  } catch (_err) {
    return null;
  }
}

function safeComparePassword(inputPassword, expectedPassword) {
  const inputHash = crypto.createHash('sha256').update(String(inputPassword || '')).digest();
  const expectedHash = crypto.createHash('sha256').update(String(expectedPassword || '')).digest();
  return crypto.timingSafeEqual(inputHash, expectedHash);
}

function requireAdminAuth(req, res, next) {
  const token = req.cookies ? req.cookies[ADMIN_COOKIE_NAME] : null;
  const session = verifySignedToken(token);

  if (!session || session.role !== 'admin') {
    if (req.xhr || (req.headers.accept && req.headers.accept.includes('application/json'))) {
      return res.status(401).json({ success: false, message: 'Unauthorized. Please log in again.' });
    }
    return res.redirect('/admin/login');
  }

  req.admin = session;
  return next();
}

function createAdminRouter(db) {
  const router = express.Router();

  const countPagesStmt = db.prepare(`SELECT COUNT(*) AS count FROM pages`);
  const countAllViewsStmt = db.prepare(`SELECT COUNT(*) AS count FROM analytics`);
  const countTodayViewsStmt = db.prepare(`SELECT COUNT(*) AS count FROM analytics WHERE date = ?`);
  const countUniqueVisitorsStmt = db.prepare(`SELECT COUNT(DISTINCT ip_address) AS count FROM analytics`);

  const topPagesStmt = db.prepare(`
    SELECT
      a.path,
      COUNT(*) AS views,
      COUNT(DISTINCT a.ip_address) AS unique_ips,
      MAX(a.created_at) AS last_viewed,
      p.title
    FROM analytics a
    LEFT JOIN pages p ON ('/' || p.slug) = a.path
    GROUP BY a.path
    ORDER BY views DESC
    LIMIT 10
  `);

  const dailyTrafficStmt = db.prepare(`
    SELECT date, COUNT(*) AS views
    FROM analytics
    GROUP BY date
    ORDER BY date DESC
    LIMIT 7
  `);

  const recentLogsStmt = db.prepare(`
    SELECT id, path, ip_address, date, created_at
    FROM analytics
    ORDER BY id DESC
    LIMIT 15
  `);

  const recentPagesStmt = db.prepare(`
    SELECT id, slug, title, created_at
    FROM pages
    ORDER BY id DESC
    LIMIT 10
  `);

  let isPipelineRunning = false;

  router.get('/login', (req, res) => {
    const token = req.cookies ? req.cookies[ADMIN_COOKIE_NAME] : null;
    if (verifySignedToken(token)) {
      return res.redirect('/admin');
    }
    return res.render('login', {
      error: null
    });
  });

  router.post('/login', (req, res) => {
    const { password } = req.body;
    const expectedPassword = getAdminPassword();

    if (!safeComparePassword(password, expectedPassword)) {
      return res.status(401).render('login', {
        error: 'Invalid administrator password. Please check your credentials.'
      });
    }

    const token = createSignedToken({
      role: 'admin',
      iat: Date.now(),
      exp: Date.now() + 1000 * 60 * 60 * 24 * 7
    });

    res.cookie(ADMIN_COOKIE_NAME, token, {
      httpOnly: true,
      sameSite: 'lax',
      secure: process.env.NODE_ENV === 'production',
      maxAge: 1000 * 60 * 60 * 24 * 7,
      path: '/'
    });

    return res.redirect('/admin');
  });

  router.post('/logout', (_req, res) => {
    res.clearCookie(ADMIN_COOKIE_NAME, { path: '/' });
    return res.redirect('/admin/login');
  });

  router.use(requireAdminAuth);

  router.get('/', (req, res) => {
    try {
      const todayIso = new Date().toISOString().slice(0, 10);

      const totalPages = countPagesStmt.get().count || 0;
      const totalViews = countAllViewsStmt.get().count || 0;
      const todayViews = countTodayViewsStmt.get(todayIso).count || 0;
      const uniqueVisitors = countUniqueVisitorsStmt.get().count || 0;

      const estimatedEarningsAllTime = ((totalViews / 1000) * RPM_RATE).toFixed(2);
      const estimatedEarningsToday = ((todayViews / 1000) * RPM_RATE).toFixed(2);

      const topPages = topPagesStmt.all().map((row) => ({
        ...row,
        estimated_revenue: ((row.views / 1000) * RPM_RATE).toFixed(2)
      }));

      const dailyTraffic = dailyTrafficStmt.all().reverse();
      const recentLogs = recentLogsStmt.all();
      const recentPages = recentPagesStmt.all();

      return res.render('admin', {
        stats: {
          totalPages,
          totalViews,
          todayViews,
          uniqueVisitors,
          rpm: RPM_RATE.toFixed(2),
          estimatedEarningsAllTime,
          estimatedEarningsToday
        },
        topPages,
        dailyTraffic,
        recentLogs,
        recentPages,
        isPipelineRunning,
        flashMessage: req.query.msg || null,
        flashStatus: req.query.status || null
      });
    } catch (error) {
      console.error('Error loading admin dashboard:', error);
      return res.status(500).send('Failed to load Admin Dashboard');
    }
  });

  router.post('/run-pipeline', (req, res) => {
    const wantsJson =
      req.xhr ||
      (req.headers.accept && req.headers.accept.includes('application/json')) ||
      req.headers['content-type'] === 'application/json';

    if (isPipelineRunning) {
      const msg = 'The AI Pipeline is already running in the background. Please wait for it to finish.';
      if (wantsJson) {
        return res.status(409).json({ success: false, message: msg });
      }
      return res.redirect(`/admin?status=error&msg=${encodeURIComponent(msg)}`);
    }

    isPipelineRunning = true;
    const scriptPath = path.resolve(__dirname, 'pipeline.py');
    const defaultWinPython = path.join(
      process.env.LOCALAPPDATA || 'C:\\Users\\LEGION\\AppData\\Local',
      'Programs',
      'Python',
      'Python311',
      'python.exe'
    );
    const fs = require('fs');
    const pythonExecutable =
      process.env.PYTHON_BIN || (fs.existsSync(defaultWinPython) ? defaultWinPython : 'python');
    const command = `"${pythonExecutable}" "${scriptPath}"`;

    exec(
      command,
      {
        cwd: __dirname,
        env: { ...process.env },
        timeout: 1000 * 60 * 10,
        maxBuffer: 1024 * 1024 * 5
      },
      (error, stdout, stderr) => {
        isPipelineRunning = false;

        if (error) {
          const errorOutput = (stderr || error.message || 'Unknown pipeline error').trim();
          if (wantsJson) {
            return res.status(500).json({
              success: false,
              message: 'Pipeline execution failed.',
              details: errorOutput,
              stdout: (stdout || '').trim()
            });
          }
          return res.redirect(
            `/admin?status=error&msg=${encodeURIComponent(`Pipeline failed: ${errorOutput.slice(0, 220)}`)}`
          );
        }

        const cleanStdout = (stdout || 'Pipeline completed successfully.').trim();
        if (wantsJson) {
          return res.json({
            success: true,
            message: 'AI Data Pipeline executed successfully and updated data.db.',
            stdout: cleanStdout
          });
        }

        return res.redirect(
          `/admin?status=success&msg=${encodeURIComponent('AI Data Pipeline completed successfully!')}`
        );
      }
    );
  });

  return router;
}

module.exports = {
  createAdminRouter,
  requireAdminAuth
};
