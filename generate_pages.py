# generate_pages.py
import os
import re
import json
import sqlite3
from datetime import datetime, timezone

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "views", "generated")
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.getenv("DB_PATH", "data.db"))
os.makedirs(OUTPUT_DIR, exist_ok=True)


def init_db(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS pages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            faqs TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pages_slug ON pages(slug);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pages_created_at ON pages(created_at DESC);")
    conn.commit()


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")


def fetch_current_trends() -> list[dict]:
    """Generates 100 high-demand, trend-driven programmatic SEO topics across core technology & fintech verticals."""
    featured_trends = [
        {
            "slug": "ai-robo-advisors-2026",
            "title": "Top AI Robo-Advisors for Smart Portfolio Allocation in 2026",
            "category": "Fintech",
            "focus": "algorithmic tax-loss harvesting, dynamic risk rebalancing, and low-fee ETF portfolio automation",
            "benchmark": "0.15%–0.25% annual AUM advisory fee with automated direct indexing",
            "audience": "retail investors, wealth managers, and quantitative fintech builders",
        },
        {
            "slug": "python-automation-workflows",
            "title": "Advanced Python Automation Workflows with GitHub Actions",
            "category": "DevOps",
            "focus": "scheduled cron pipelines, idempotent SQLite/PostgreSQL data ingestion, and automated CI/CD deployments",
            "benchmark": "78% reduction in manual DevOps maintenance overhead across production pipelines",
            "audience": "platform engineers, data scientists, and full-stack automation architects",
        },
        {
            "slug": "nextjs-tailwind-glassmorphism",
            "title": "Building Modern Glassmorphism UIs with Tailwind CSS",
            "category": "Web Dev",
            "focus": "GPU-accelerated backdrop-blur layers, translucent border tokens, and Core Web Vitals optimization",
            "benchmark": "99+ Lighthouse Performance score with sub-1.2s Largest Contentful Paint (LCP)",
            "audience": "frontend engineers, UI/UX design systems teams, and SaaS founders",
        },
        {
            "slug": "postgresql-performance-tuning",
            "title": "Essential PostgreSQL Performance Tuning and Indexing Strategies",
            "category": "Databases",
            "focus": "B-Tree, GIN, and BRIN indexing, query planner cost analysis, and connection pooling with PgBouncer",
            "benchmark": "10x–45x query latency improvement on multi-million-row analytical and transactional tables",
            "audience": "database administrators, backend engineers, and high-scale SaaS architects",
        },
    ]

    domains = [
        {
            "topic": "Enterprise RAG & Vector Database Architecture",
            "category": "AI Engineering",
            "focus": "hybrid semantic + BM25 retrieval, chunking strategies, and sub-50ms embedding search",
            "metric": "$188,000 median architect compensation & 34% enterprise adoption growth",
        },
        {
            "topic": "Zero-Trust Cloud Security & IAM Automation",
            "category": "Cybersecurity",
            "focus": "short-lived OIDC credentials, policy-as-code with OPA, and automated posture management",
            "metric": "$174,000 median security engineer salary & 62% faster incident containment",
        },
        {
            "topic": "Kubernetes FinOps & GPU Cluster Cost Optimization",
            "category": "Cloud Infrastructure",
            "focus": "spot node autoscaling, fractional GPU scheduling, and real-time namespace cost attribution",
            "metric": "38% average cloud bill reduction across multi-tenant production clusters",
        },
        {
            "topic": "Real-Time Streaming Data Pipelines with Rust & Kafka",
            "category": "Data Engineering",
            "focus": "zero-copy serialization, exactly-once stream processing, and low-latency lakehouse ingestion",
            "metric": "$182,000 median staff engineer pay & sub-10ms p99 event processing latency",
        },
        {
            "topic": "Autonomous AI Coding Agents & CI/CD Code Review",
            "category": "Developer Tools",
            "focus": "automated static analysis, deterministic test generation, and pull-request security scanning",
            "metric": "42% faster pull request cycle times across distributed engineering teams",
        },
        {
            "topic": "Serverless Edge Computing & Distributed SQLite",
            "category": "Web Dev",
            "focus": "read-replica edge caching, WebAssembly isolates, and WAL-mode SQLite synchronization",
            "metric": "Sub-25ms global Time to First Byte (TTFB) across 300+ edge locations",
        },
        {
            "topic": "Algorithmic Payment Routing & Real-Time Fraud Detection",
            "category": "Fintech",
            "focus": "ISO 20022 instant settlement, graph neural network anomaly scoring, and multi-acquirer failover",
            "metric": "99.995% payment authorization uptime & 48% reduction in false-positive declines",
        },
        {
            "topic": "LLM Fine-Tuning, Quantization & On-Device Inference",
            "category": "AI Engineering",
            "focus": "LoRA/QLoRA adapters, 4-bit GGUF quantization, and high-throughput vLLM serving",
            "metric": "$192,000 median ML systems compensation & 4.2x token throughput per GPU",
        },
        {
            "topic": "Full-Stack TypeScript Monorepos & Turborepo Caching",
            "category": "Web Dev",
            "focus": "remote build artifact caching, end-to-end type safety, and modular package boundaries",
            "metric": "70% faster CI build times for multi-application enterprise repositories",
        },
        {
            "topic": "Cloud-Native Observability with OpenTelemetry & eBPF",
            "category": "DevOps",
            "focus": "kernel-level distributed tracing, high-cardinality metrics, and automated SLO alerting",
            "metric": "$169,000 median SRE compensation & 55% lower mean time to resolution (MTTR)",
        },
        {
            "topic": "Senior Software Engineer Compensation & Equity Guide",
            "category": "Tech Salaries",
            "focus": "base salary percentiles, RSU vesting schedules, and cost-of-living adjusted take-home pay",
            "metric": "$178,000–$225,000 median base salary band across top US tech hubs",
        },
        {
            "topic": "Machine Learning Engineer Salary & Career Benchmarks",
            "category": "Tech Salaries",
            "focus": "AI infrastructure demand, sign-on bonuses, and senior staff promotion trajectories",
            "metric": "$195,000–$248,000 median base pay with +14.2% year-over-year compensation growth",
        },
    ]

    hubs = [
        {"city": "San Francisco", "region": "Silicon Valley & Bay Area", "tier": "Tier-1 Global AI & Venture Hub"},
        {"city": "New York City", "region": "Northeast Financial Corridor", "tier": "Tier-1 Fintech & Enterprise Hub"},
        {"city": "Seattle", "region": "Pacific Northwest Cloud Hub", "tier": "Hyperscale Cloud & Systems Hub"},
        {"city": "Austin", "region": "Texas Silicon Hills", "tier": "High-Growth Sunbelt Engineering Hub"},
        {"city": "Boston", "region": "New England DeepTech Hub", "tier": "Biotech, Robotics & AI Research Hub"},
        {"city": "Denver", "region": "Rocky Mountain Tech Corridor", "tier": "Cloud, Aerospace & Remote-First Hub"},
        {"city": "London", "region": "UK & European Tech Center", "tier": "Global Fintech & DeepMind AI Hub"},
        {"city": "Toronto", "region": "North American AI Corridor", "tier": "High-Density Machine Learning Hub"},
    ]

    trends = list(featured_trends)
    for d in domains:
        for h in hubs:
            slug = f"{slugify(d['topic'])}-{slugify(h['city'])}-2026"
            title = f"{d['topic']} in {h['city']} (2026 Industry & Benchmark Guide)"
            trends.append(
                {
                    "slug": slug,
                    "title": title,
                    "category": d["category"],
                    "focus": f"{d['focus']} across {h['city']} ({h['region']})",
                    "benchmark": f"{d['metric']} in {h['tier']}",
                    "audience": f"engineering leaders, architects, and technical specialists in {h['city']}",
                }
            )

    return trends[:100]


def generate_page_content(trend: dict) -> dict:
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    title = trend["title"]
    category = trend["category"]
    focus = trend.get("focus", "modern production architecture, automation workflows, and benchmark analysis")
    benchmark = trend.get("benchmark", "top-quartile industry efficiency and verified market performance")
    audience = trend.get("audience", "senior engineers, technical leads, and decision-makers")

    p1 = (
        f"{title} represents one of the fastest-evolving pillars within the {category} ecosystem in 2026. "
        f"Organizations and technical teams focusing on {focus} are consistently achieving {benchmark}. "
        f"As production workloads scale in complexity, engineering and operations leaders require transparent, "
        f"data-backed frameworks to evaluate tooling, architectural trade-offs, and long-term total cost of ownership."
    )

    p2 = (
        f"In this comprehensive programmatic guide tailored for {audience}, we examine the core implementation patterns "
        f"driving measurable ROI. First, modern teams prioritize deterministic automation, observability, and strict "
        f"schema validation across every stage of deployment. Second, integrating {focus} into existing production "
        f"environments requires balancing latency budgets, security guardrails, and developer velocity without "
        f"introducing operational fragility."
    )

    p3 = (
        f"Looking ahead through 2026 and beyond, mastery of {title} directly correlates with both organizational "
        f"resilience and top-tier career advancement in {category}. Whether you are benchmarking compensation, "
        f"auditing production infrastructure, or designing next-generation workflows, applying the verified benchmarks "
        f"({benchmark}) outlined in this report ensures sustainable, high-margin execution."
    )

    full_description = f"{p1}\n\n{p2}\n\n{p3}"

    faqs = [
        {
            "question": f"What are the primary benefits of adopting best practices for {title}?",
            "answer": (
                f"Teams implementing structured workflows for {title} focus on {focus}, resulting in {benchmark} "
                f"alongside stronger reliability, clearer governance, and faster iteration cycles."
            ),
        },
        {
            "question": f"How does {title} impact {category} teams and career benchmarks in 2026?",
            "answer": (
                f"Demand for specialists experienced in {focus} remains exceptionally strong among {audience}, "
                f"driving competitive compensation packages and rapid adoption across enterprise engineering teams."
            ),
        },
        {
            "question": f"What is the recommended first step when implementing {title}?",
            "answer": (
                f"Start by establishing baseline telemetry and performance metrics, then roll out incremental "
                f"automation around {focus} while validating improvements against {benchmark}."
            ),
        },
    ]

    return {
        "title": title,
        "slug": trend["slug"],
        "category": category,
        "date": today_str,
        "benchmark": benchmark,
        "focus": focus,
        "content": full_description,
        "paragraphs": [p1, p2, p3],
        "faqs": faqs,
    }


def render_static_ejs(data: dict) -> str:
    schema_payload = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Article",
                "headline": data["title"],
                "datePublished": data["date"],
                "dateModified": data["date"],
                "articleSection": data["category"],
                "description": data["paragraphs"][0],
                "author": {"@type": "Organization", "name": "TechPay SEO Directory"},
            },
            {
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": f["question"],
                        "acceptedAnswer": {"@type": "Answer", "text": f["answer"]},
                    }
                    for f in data["faqs"]
                ],
            },
        ],
    }

    faqs_html = "\n".join(
        [
            f"""
            <div class="glass-card rounded-xl p-6 border border-slate-800/80">
                <h3 class="text-base sm:text-lg font-bold text-white flex items-start gap-3">
                    <span class="px-2.5 py-0.5 rounded-md bg-indigo-500/20 text-indigo-300 text-xs font-extrabold shrink-0 mt-0.5">Q{idx + 1}</span>
                    <span>{faq['question']}</span>
                </h3>
                <p class="mt-3 text-slate-300 text-sm sm:text-base leading-relaxed pl-9">{faq['answer']}</p>
            </div>
            """
            for idx, faq in enumerate(data["faqs"])
        ]
    )

    paragraphs_html = "\n".join(
        [f'<p class="text-slate-300 leading-relaxed text-base sm:text-lg">{p}</p>' for p in data["paragraphs"]]
    )

    return f"""<!DOCTYPE html>
<html lang="en" class="scroll-smooth">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{data['title']} | TechPay SEO Directory</title>
    <meta name="description" content="{data['paragraphs'][0][:158]}">
    <!-- Google AdSense Auto-Ads Verification Script -->
    <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-4588627708948117" crossorigin="anonymous"></script>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        body {{ font-family: 'Inter', sans-serif; }}
        .glass-card {{ background: rgba(15, 23, 42, 0.65); backdrop-filter: blur(16px); border: 1px solid rgba(255, 255, 255, 0.08); }}
    </style>
    <script type="application/ld+json">
    {json.dumps(schema_payload, ensure_ascii=False)}
    </script>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen flex flex-col selection:bg-indigo-500 selection:text-white">
    <header class="border-b border-slate-800/80 bg-slate-950/80 backdrop-blur-xl sticky top-0 z-30">
        <div class="py-4 px-6 flex justify-between items-center max-w-6xl mx-auto w-full">
            <a href="/" class="text-xl font-extrabold bg-gradient-to-r from-indigo-400 via-sky-400 to-emerald-400 bg-clip-text text-transparent">TechPay Directory</a>
            <nav class="flex flex-wrap items-center gap-5 text-xs sm:text-sm font-medium text-slate-300">
                <a href="/" class="hover:text-white transition">Home</a>
                <a href="/about" class="hover:text-white transition">About Us</a>
                <a href="/contact" class="hover:text-white transition">Contact</a>
                <a href="/privacy" class="hover:text-white transition">Privacy Policy</a>
            </nav>
        </div>
    </header>

    <main class="flex-grow max-w-4xl mx-auto px-6 py-12 w-full space-y-8">
        <article class="glass-card p-8 sm:p-10 rounded-2xl shadow-2xl space-y-6">
            <div class="flex flex-wrap items-center gap-3 text-xs text-indigo-400 font-semibold uppercase tracking-wider">
                <span class="px-3 py-1 rounded-full bg-indigo-500/15 border border-indigo-500/30">{data['category']}</span>
                <span>•</span>
                <span>Updated {data['date']}</span>
            </div>
            <h1 class="text-3xl md:text-4xl font-extrabold tracking-tight text-white leading-tight">{data['title']}</h1>
            <div class="p-4 rounded-xl bg-indigo-950/40 border border-indigo-500/20 text-xs sm:text-sm text-indigo-200">
                <strong>Key Industry Benchmark:</strong> {data['benchmark']}
            </div>
            <div class="space-y-5">
                {paragraphs_html}
            </div>
            <div class="border-t border-slate-800 pt-6 mt-8 flex justify-between items-center text-sm text-slate-400">
                <span>Verified Programmatic SEO Report</span>
                <a href="/" class="text-indigo-400 hover:text-indigo-300 font-semibold">← Back to Directory</a>
            </div>
        </article>

        <section class="space-y-4">
            <h2 class="text-xl sm:text-2xl font-bold text-white">Frequently Asked Questions</h2>
            {faqs_html}
        </section>
    </main>

    <footer class="border-t border-slate-800/80 py-8 px-6 text-xs text-slate-500 max-w-6xl mx-auto w-full flex flex-col sm:flex-row justify-between items-center gap-4">
        <span>&copy; {datetime.now().strftime("%Y")} TechPay SEO Directory. All rights reserved.</span>
        <div class="flex items-center gap-5">
            <a href="/" class="hover:text-slate-300 transition">Home</a>
            <a href="/about" class="hover:text-slate-300 transition">About Us</a>
            <a href="/contact" class="hover:text-slate-300 transition">Contact Us</a>
            <a href="/privacy" class="hover:text-slate-300 transition">Privacy Policy</a>
            <a href="/sitemap.xml" class="hover:text-slate-300 transition">Sitemap</a>
        </div>
    </footer>
</body>
</html>"""


def upsert_to_sqlite(conn: sqlite3.Connection, data: dict) -> None:
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    faqs_json = json.dumps(data["faqs"], ensure_ascii=False)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO pages (slug, title, description, faqs, created_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(slug) DO UPDATE SET
            title = excluded.title,
            description = excluded.description,
            faqs = excluded.faqs,
            created_at = excluded.created_at;
        """,
        (data["slug"], data["title"], data["content"], faqs_json, now_iso),
    )


def main() -> None:
    trends = fetch_current_trends()
    print(f"Generating {len(trends)} high-value trend pages...")

    conn = sqlite3.connect(DB_PATH)
    try:
        init_db(conn)
        for trend in trends:
            data = generate_page_content(trend)
            filename = os.path.join(OUTPUT_DIR, f"{trend['slug']}.ejs")
            page_template = render_static_ejs(data)

            with open(filename, "w", encoding="utf-8") as f:
                f.write(page_template.strip())

            upsert_to_sqlite(conn, data)

        conn.commit()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM pages;")
        total_db_rows = cursor.fetchone()[0]
        print(f"Successfully generated {len(trends)} EJS templates in '{OUTPUT_DIR}'.")
        print(f"Synchronized all pages to SQLite '{DB_PATH}' (Total indexed pages: {total_db_rows}).")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
