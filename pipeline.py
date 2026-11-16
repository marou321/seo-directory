# pipeline.py
from __future__ import annotations
import os
import re
import json
import time
import sqlite3
from datetime import datetime, timezone
import requests
import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.getenv("DB_PATH", "data.db"))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


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


def fetch_market_data() -> pd.DataFrame:
    roles = [
        {"role": "Senior Software Engineer", "base_salary": 168000, "yoy_growth": "+6.4%", "demand_level": "Very High"},
        {"role": "Machine Learning Engineer", "base_salary": 185000, "yoy_growth": "+14.2%", "demand_level": "Extreme"},
        {"role": "Cloud DevOps Architect", "base_salary": 162000, "yoy_growth": "+8.1%", "demand_level": "High"},
        {"role": "Lead Data Scientist", "base_salary": 172000, "yoy_growth": "+9.5%", "demand_level": "Very High"},
        {"role": "Cybersecurity Engineer", "base_salary": 158000, "yoy_growth": "+11.3%", "demand_level": "Extreme"},
    ]

    cities = [
        {"city": "San Francisco", "state": "CA", "col_multiplier": 1.25, "tech_hub_tier": "Tier 1 Global Hub"},
        {"city": "New York City", "state": "NY", "col_multiplier": 1.20, "tech_hub_tier": "Tier 1 Financial & Tech Hub"},
        {"city": "Austin", "state": "TX", "col_multiplier": 1.02, "tech_hub_tier": "High-Growth Sunbelt Hub"},
        {"city": "Seattle", "state": "WA", "col_multiplier": 1.15, "tech_hub_tier": "Cloud & Enterprise Giant Hub"},
        {"city": "Denver", "state": "CO", "col_multiplier": 0.98, "tech_hub_tier": "Emerging Mountain Tech Hub"},
    ]

    exchange_multiplier = 0.92
    try:
        response = requests.get("https://open.er-api.com/v6/latest/USD", timeout=10)
        if response.status_code == 200:
            payload = response.json()
            eur_rate = payload.get("rates", {}).get("EUR", 0.92)
            exchange_multiplier = round(float(eur_rate), 4)
    except requests.RequestException:
        exchange_multiplier = 0.92

    records = []
    for r in roles:
        for c in cities:
            localized_salary = int(round(r["base_salary"] * c["col_multiplier"], -2))
            p25_salary = int(round(localized_salary * 0.85, -2))
            p75_salary = int(round(localized_salary * 1.18, -2))
            slug = f"{slugify(r['role'])}-salary-in-{slugify(c['city'])}"
            records.append(
                {
                    "slug": slug,
                    "role": r["role"],
                    "city": c["city"],
                    "state": c["state"],
                    "median_salary": localized_salary,
                    "p25_salary": p25_salary,
                    "p75_salary": p75_salary,
                    "yoy_growth": r["yoy_growth"],
                    "demand_level": r["demand_level"],
                    "tech_hub_tier": c["tech_hub_tier"],
                    "usd_to_eur_rate": exchange_multiplier,
                }
            )

    return pd.DataFrame(records)


def generate_fallback_seo_content(row: pd.Series) -> dict:
    year = datetime.now().year
    role = row["role"]
    city = row["city"]
    state = row["state"]
    median = f"${row['median_salary']:,}"
    p25 = f"${row['p25_salary']:,}"
    p75 = f"${row['p75_salary']:,}"

    title = f"{role} Salary in {city}, {state} ({year} Guide) — {median} Avg"

    p1 = (
        f"Professionals working as a {role} in {city}, {state} command a median annual base salary of {median} USD, "
        f"positioning this market as a {row['tech_hub_tier']}. According to current compensation benchmarks, the 25th "
        f"percentile starts at {p25} for mid-level contributors, while top-quartile specialists at the 75th percentile "
        f"earn upwards of {p75} in base pay alone. With year-over-year compensation growth tracking at {row['yoy_growth']} "
        f"and local hiring demand rated as {row['demand_level']}, {city} continues to attract both venture-backed "
        f"scale-ups and Fortune 500 engineering centers."
    )
    p2 = (
        f"Beyond base salary, total compensation packages for a {role} in {city} frequently include annual performance "
        f"bonuses ranging from 10% to 20%, alongside multi-year restricted stock units (RSUs) or early-stage equity grants. "
        f"When evaluating offers in {city}, {state}, candidates should weigh local cost-of-living dynamics, state tax "
        f"implications, and hybrid-work flexibility. Employers across cloud infrastructure, fintech, healthcare AI, and "
        f"enterprise SaaS are actively competing for senior technical talent able to architect resilient production systems."
    )
    p3 = (
        f"To maximize earning potential as a {role} in {city}, candidates should highlight measurable production impact, "
        f"distributed systems scalability, and cross-functional technical leadership during compensation negotiations. "
        f"Benchmarking competing offers against the {p25} to {p75} band ensures you capture fair market value in {year}."
    )

    faqs = [
        {
            "question": f"What is the average {role} salary in {city}, {state}?",
            "answer": (
                f"The median base salary for a {role} in {city}, {state} is {median} per year, with most experienced "
                f"professionals earning between {p25} (25th percentile) and {p75} (75th percentile) before equity and bonuses."
            ),
        },
        {
            "question": f"Is hiring demand high for {role} roles in {city}?",
            "answer": (
                f"Yes, market demand for {role} talent in {city} is currently classified as {row['demand_level']}, "
                f"supported by {row['yoy_growth']} year-over-year salary growth across local technology employers."
            ),
        },
        {
            "question": f"How can I negotiate a top-tier {role} offer in {city}?",
            "answer": (
                f"Target the 75th percentile benchmark of {p75} by demonstrating domain expertise, production ownership, "
                f"and competing offers from other {row['tech_hub_tier']} employers."
            ),
        },
    ]

    return {
        "title": title,
        "description": f"{p1}\n\n{p2}\n\n{p3}",
        "faqs": faqs,
    }


def generate_seo_content(client: OpenAI | None, row: pd.Series) -> dict:
    if client is None:
        return generate_fallback_seo_content(row)

    system_prompt = (
        "You are an expert Programmatic SEO Strategist and Tech Compensation Analyst. "
        "Return strictly valid JSON matching the requested schema with no markdown code fences."
    )

    user_prompt = f"""
Generate comprehensive, authoritative, SEO-optimized content for the following role and location combination:
- Role: {row['role']}
- Location: {row['city']}, {row['state']} ({row['tech_hub_tier']})
- Median Base Salary: ${row['median_salary']:,} USD (25th Percentile: ${row['p25_salary']:,} | 75th Percentile: ${row['p75_salary']:,})
- YoY Compensation Growth: {row['yoy_growth']}
- Market Hiring Demand: {row['demand_level']}

Requirements:
1. "title": A compelling, high-CTR SEO title (55-70 characters) containing the role, city, median salary, and current year.
2. "description": A detailed, deeply informative 300-word SEO article divided into 3 clear paragraphs separated by double newlines (\\n\\n). Discuss compensation benchmarks, local cost-of-living adjustments in {row['city']}, top hiring sectors, equity/bonus structures, and career trajectory.
3. "faqs": An array of exactly 3 specific, high-intent FAQ objects, each containing "question" and "answer" keys tailored specifically to working as a {row['role']} in {row['city']}, {row['state']}.

Return a JSON object with keys: "title", "description", and "faqs".
"""

    for attempt in range(3):
        try:
            completion = client.chat.completions.create(
                model=OPENAI_MODEL,
                response_format={"type": "json_object"},
                temperature=0.6,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            raw_content = completion.choices[0].message.content
            parsed = json.loads(raw_content)

            title = str(parsed.get("title", "")).strip()
            description = str(parsed.get("description", "")).strip()
            faqs = parsed.get("faqs", [])

            if not title or not description or not isinstance(faqs, list) or len(faqs) < 3:
                raise ValueError("Incomplete JSON structure returned from OpenAI.")

            normalized_faqs = []
            for item in faqs[:3]:
                normalized_faqs.append(
                    {
                        "question": str(item.get("question", "")).strip(),
                        "answer": str(item.get("answer", "")).strip(),
                    }
                )

            return {
                "title": title,
                "description": description,
                "faqs": normalized_faqs,
            }
        except Exception as err:
            if attempt == 2:
                print(f"OpenAI API call failed ({err}); using structured fallback generator for {row['slug']}.")
                return generate_fallback_seo_content(row)
            time.sleep(2 ** attempt)


def upsert_page(conn: sqlite3.Connection, slug: str, title: str, description: str, faqs: list) -> None:
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    faqs_json = json.dumps(faqs, ensure_ascii=False)
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
        (slug, title, description, faqs_json, now_iso),
    )
    conn.commit()


def main() -> None:
    has_valid_key = bool(OPENAI_API_KEY) and not OPENAI_API_KEY.startswith("sk-proj-your-")
    client = OpenAI(api_key=OPENAI_API_KEY) if has_valid_key else None

    if not has_valid_key:
        print("Notice: No live OPENAI_API_KEY configured in .env. Using built-in SEO generator so you can test immediately.")

    conn = sqlite3.connect(DB_PATH)

    try:
        init_db(conn)
        df = fetch_market_data()
        total = len(df)
        print(f"Loaded {total} role-city combinations into Pandas DataFrame.")

        for idx, row in df.iterrows():
            slug = row["slug"]
            print(f"[{idx + 1}/{total}] Generating page: {slug} ...")
            seo_payload = generate_seo_content(client, row)
            upsert_page(
                conn=conn,
                slug=slug,
                title=seo_payload["title"],
                description=seo_payload["description"],
                faqs=seo_payload["faqs"],
            )

        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM pages;")
        count = cursor.fetchone()[0]
        print(f"Salary benchmark pipeline completed. Rows in '{DB_PATH}': {count}")
    finally:
        conn.close()

    try:
        import generate_pages
        generate_pages.main()
    except Exception as gen_err:
        print(f"Warning: generate_pages synchronization encountered an issue: {gen_err}")


if __name__ == "__main__":
    main()
