// database.js
const path = require('path');

const DB_PATH = path.resolve(__dirname, process.env.DB_PATH || 'data.db');

function createDatabaseConnection(filePath) {
  try {
    const BetterSqlite3 = require('better-sqlite3');
    const db = new BetterSqlite3(filePath);
    return db;
  } catch (_err) {
    const { DatabaseSync } = require('node:sqlite');
    const db = new DatabaseSync(filePath);
    db.pragma = function pragma(statement) {
      db.exec(`PRAGMA ${statement};`);
    };
    return db;
  }
}

function initializeDatabase() {
  const db = createDatabaseConnection(DB_PATH);

  db.exec('PRAGMA journal_mode = WAL;');
  db.exec('PRAGMA synchronous = NORMAL;');
  db.exec('PRAGMA foreign_keys = ON;');

  const createPagesTableSQL = `
    CREATE TABLE IF NOT EXISTS pages (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      slug TEXT NOT NULL UNIQUE,
      title TEXT NOT NULL,
      description TEXT NOT NULL,
      faqs TEXT NOT NULL,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
  `;

  const createAnalyticsTableSQL = `
    CREATE TABLE IF NOT EXISTS analytics (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      path TEXT NOT NULL,
      ip_address TEXT NOT NULL,
      date TEXT NOT NULL,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
  `;

  const createIndexesSQL = `
    CREATE INDEX IF NOT EXISTS idx_pages_slug ON pages(slug);
    CREATE INDEX IF NOT EXISTS idx_pages_created_at ON pages(created_at DESC);
    CREATE INDEX IF NOT EXISTS idx_analytics_date ON analytics(date);
    CREATE INDEX IF NOT EXISTS idx_analytics_path ON analytics(path);
    CREATE INDEX IF NOT EXISTS idx_analytics_created_at ON analytics(created_at DESC);
  `;

  db.exec(createPagesTableSQL);
  db.exec(createAnalyticsTableSQL);
  db.exec(createIndexesSQL);

  return db;
}

if (require.main === module) {
  try {
    const db = initializeDatabase();
    const pagesCount = db.prepare('SELECT COUNT(*) AS count FROM pages').get();
    const analyticsCount = db.prepare('SELECT COUNT(*) AS count FROM analytics').get();
    console.log(`Database initialized successfully at: ${DB_PATH}`);
    console.log(`Current records in 'pages': ${pagesCount.count}`);
    console.log(`Current records in 'analytics': ${analyticsCount.count}`);
    db.close();
  } catch (error) {
    console.error('Failed to initialize SQLite database:', error);
    process.exit(1);
  }
}

module.exports = {
  initializeDatabase,
  DB_PATH
};
