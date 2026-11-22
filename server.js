// server.js
require('dotenv').config();
const fs = require('fs');
const path = require('path');
const express = require('express');
const compression = require('compression');
const cookieParser = require('cookie-parser');
const { initializeDatabase } = require('./database');
const { createAdminRouter } = require('./adminRoutes');
const { createApiRouter } = require('./api');

const app = express();
const PORT = process.env.PORT || 3000;
const SITE_URL = (process.env.SITE_URL || `http://localhost:${PORT}`).replace(/\/+$/, '');

const db = initializeDatabase();

app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));
app.set('trust proxy', true);
app.disable('x-powered-by');

app.use(compression());
app.use(express.static(path.join(__dirname, 'public')));
app.use(express.urlencoded({ extended: true }));
app.use(express.json());
app.use(cookieParser());

const insertAnalyticsStmt = db.prepare(`
  INSERT INTO analytics (path, ip_address, date, created_at)
  VALUES (?, ?, ?, ?)
`);

const STATIC_EXT_REGEX = /\.(css|js|mjs|map|ico|png|jpg|jpeg|gif|svg|webp|woff|woff2|ttf|eot|xml|txt|json)$/i;

function extractClientIp(req) {
  const forwarded = req.headers['x-forwarded-for'];
  if (forwarded && typeof forwarded === 'string') {
    return forwarded.split(',')[0].trim();
  }
  return req.ip || (req.socket && req.socket.remoteAddress) || '0.0.0.0';
}

function analyticsTrackerMiddleware(req, res, next) {
  if (req.method !== 'GET') {
    return next();
  }

  const reqPath = req.path || '/';

  if (
    reqPath.startsWith('/admin') ||
    reqPath.startsWith('/api') ||
    reqPath === '/favicon.ico' ||
    reqPath === '/robots.txt' ||
    reqPath === '/sitemap.xml' ||
    STATIC_EXT_REGEX.test(reqPath)
  ) {
    return next();
  }

  res.on('finish', () => {
    if (res.statusCode >= 200 && res.statusCode < 400) {
      try {
        const now = new Date();
        const dateStr = now.toISOString().slice(0, 10);
        const createdAtStr = now.toISOString().replace('T', ' ').slice(0, 19);
        const clientIp = extractClientIp(req);
        insertAnalyticsStmt.run(reqPath, clientIp, dateStr, createdAtStr);
      } catch (err) {
        console.error('Analytics logging error:', err.message);
      }
    }
  });

  return next();
}

app.use(analyticsTrackerMiddleware);

app.use('/api', createApiRouter(db));
app.use('/admin', createAdminRouter(db));

const selectAllPagesStmt = db.prepare(`
  SELECT id, slug, title, description, faqs, meta, created_at
  FROM pages
  ORDER BY id ASC
`);

const searchPagesStmt = db.prepare(`
  SELECT id, slug, title, description, faqs, meta, created_at
  FROM pages
  WHERE title LIKE ? OR slug LIKE ? OR description LIKE ?
  ORDER BY id ASC
`);

const selectPageBySlugStmt = db.prepare(`
  SELECT id, slug, title, description, faqs, meta, created_at
  FROM pages
  WHERE slug = ?
  LIMIT 1
`);

function parseFaqs(faqsText) {
  try {
    const parsed = JSON.parse(faqsText);
    return Array.isArray(parsed) ? parsed : [];
  } catch (_err) {
    return [];
  }
}

function parseMeta(metaText) {
  try {
    const parsed = JSON.parse(metaText || '{}');
    return parsed && typeof parsed === 'object' ? parsed : {};
  } catch (_err) {
    return {};
  }
}

function hydratePageRow(row) {
  const meta = parseMeta(row.meta);
  return {
    ...row,
    faqs: parseFaqs(row.faqs),
    meta,
    category: meta.category || 'Engineering & Compensation',
    city: meta.city || 'Global Benchmark'
  };
}

const CATEGORY_DESCRIPTIONS = {
  'Tech Salaries': 'Localized base salary percentiles (P25/P50/P75), RSU equity vesting, and tax-adjusted take-home pay.',
  'AI Engineering': 'Production RAG vector databases, LoRA fine-tuning, 4-bit AWQ quantization, and vLLM inference scaling.',
  'Cloud Infrastructure': 'Kubernetes FinOps, Karpenter spot node autoscaling, and fractional NVIDIA MIG GPU cluster sharing.',
  'Cybersecurity': 'Zero-Trust IAM, OIDC workload identity federation, SPIFFE/SPIRE mTLS, and OPA policy-as-code.',
  'Fintech': 'Algorithmic multi-acquirer payment routing, ISO 20022 real-time settlement, and ML fraud scoring.',
  'Web Dev': 'Full-stack TypeScript monorepos, Turborepo remote caching, glassmorphism UI, and distributed edge SQLite.',
  'DevOps': 'OpenTelemetry tail-based sampling, kernel eBPF observability, and automated GitHub Actions pipelines.',
  'Data Engineering': 'Zero-GC Rust + Kafka streaming consumers, Apache Arrow/Iceberg lakehouses, and sub-10ms pipelines.',
  'Developer Tools': 'AST-scoped AI code review agents, sandboxed test generation, and deterministic CI static analysis.',
  'Databases': 'PostgreSQL B-Tree/GIN/BRIN indexing, pgvector HNSW tuning, and connection pooling optimization.'
};

app.get('/robots.txt', (_req, res) => {
  res.type('text/plain');
  res.send(`User-agent: *\nAllow: /\nDisallow: /admin\nDisallow: /api\nSitemap: ${SITE_URL}/sitemap.xml\n`);
});

app.get('/sitemap.xml', (_req, res) => {
  try {
    const pages = selectAllPagesStmt.all();
    const urls = pages
      .map((page) => {
        const lastMod = page.created_at
          ? new Date(page.created_at.replace(' ', 'T') + 'Z').toISOString()
          : new Date().toISOString();
        return `
  <url>
    <loc>${SITE_URL}/${encodeURIComponent(page.slug)}</loc>
    <lastmod>${lastMod}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>`;
      })
      .join('');

    const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>${SITE_URL}/</loc>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>${SITE_URL}/about</loc>
    <changefreq>monthly</changefreq>
    <priority>0.6</priority>
  </url>
  <url>
    <loc>${SITE_URL}/contact</loc>
    <changefreq>monthly</changefreq>
    <priority>0.6</priority>
  </url>
  <url>
    <loc>${SITE_URL}/privacy</loc>
    <changefreq>monthly</changefreq>
    <priority>0.5</priority>
  </url>${urls}
</urlset>`;

    res.header('Content-Type', 'application/xml');
    res.send(xml);
  } catch (error) {
    console.error('Error generating sitemap:', error);
    res.status(500).send('Error generating sitemap');
  }
});

function buildHomeContext(rawPages, searchQuery, notFoundSlug = null) {
  const pages = rawPages.map(hydratePageRow);

  const categoryMap = {};
  pages.forEach((p) => {
    const cat = p.category;
    if (!categoryMap[cat]) {
      categoryMap[cat] = {
        name: cat,
        count: 0,
        description: CATEGORY_DESCRIPTIONS[cat] || 'In-depth technical benchmarks and production implementation guides.',
        sampleSlug: p.slug
      };
    }
    categoryMap[cat].count += 1;
  });

  const categories = Object.values(categoryMap).sort((a, b) => b.count - a.count);

  const featuredSlugs = new Set([
    'ai-robo-advisors-2026',
    'python-automation-workflows',
    'nextjs-tailwind-glassmorphism',
    'postgresql-performance-tuning',
    'machine-learning-engineer-salary-in-san-francisco',
    'enterprise-rag-vector-database-architecture-san-francisco-2026'
  ]);
  const featuredPages = pages.filter((p) => featuredSlugs.has(p.slug)).slice(0, 6);

  return {
    pages,
    categories,
    featuredPages: featuredPages.length > 0 ? featuredPages : pages.slice(0, 6),
    searchQuery,
    totalCount: pages.length,
    siteUrl: SITE_URL,
    notFoundSlug
  };
}

app.get('/', (req, res) => {
  try {
    const searchQuery = (req.query.q || '').trim();
    const likePattern = `%${searchQuery}%`;
    const rawPages = searchQuery
      ? searchPagesStmt.all(likePattern, likePattern, likePattern)
      : selectAllPagesStmt.all();

    res.render('home', buildHomeContext(rawPages, searchQuery));
  } catch (error) {
    console.error('Error rendering home route:', error);
    res.status(500).send('Internal Server Error');
  }
});

app.get('/about', (_req, res) => {
  res.render('about', { siteUrl: SITE_URL });
});

app.get('/contact', (req, res) => {
  res.render('contact', {
    siteUrl: SITE_URL,
    submitted: req.query.submitted === '1'
  });
});

app.post('/contact', (_req, res) => {
  res.redirect('/contact?submitted=1');
});

app.get('/privacy', (_req, res) => {
  res.render('privacy', { siteUrl: SITE_URL });
});

app.get('/:slug', (req, res) => {
  try {
    const { slug } = req.params;
    const row = selectPageBySlugStmt.get(slug);

    if (!row) {
      const generatedTemplatePath = path.join(__dirname, 'views', 'generated', `${slug}.ejs`);
      if (fs.existsSync(generatedTemplatePath)) {
        return res.render(`generated/${slug}`, { siteUrl: SITE_URL });
      }

      const allRaw = selectAllPagesStmt.all();
      return res.status(404).render('home', buildHomeContext(allRaw, '', slug));
    }

    const page = hydratePageRow(row);
    const allPages = selectAllPagesStmt.all().map(hydratePageRow);

    // Build contextually relevant related pages (same category or same city, then cross-pillar)
    const sameCategory = allPages.filter((p) => p.slug !== slug && p.category === page.category).slice(0, 4);
    const sameCityOrOther = allPages
      .filter((p) => p.slug !== slug && p.category !== page.category && (p.city === page.city || p.slug.includes('2026')))
      .slice(0, 4);
    const relatedPages = [...sameCategory, ...sameCityOrOther].slice(0, 6);

    return res.render('page', {
      page,
      relatedPages,
      siteUrl: SITE_URL
    });
  } catch (error) {
    console.error('Error rendering dynamic page route:', error);
    return res.status(500).send('Internal Server Error');
  }
});

const server = app.listen(PORT, () => {
  console.log(`Programmatic SEO Directory running at http://localhost:${PORT}`);
  console.log(`Admin Dashboard available at http://localhost:${PORT}/admin`);
  console.log(`Desktop API Endpoint available at http://localhost:${PORT}/api/admin/stats`);
});

process.on('SIGINT', () => {
  server.close(() => {
    db.close();
    process.exit(0);
  });
});

process.on('SIGTERM', () => {
  server.close(() => {
    db.close();
    process.exit(0);
  });
});
