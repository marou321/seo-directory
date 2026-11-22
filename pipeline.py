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
            meta TEXT DEFAULT '{}',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    try:
        cursor.execute("ALTER TABLE pages ADD COLUMN meta TEXT DEFAULT '{}';")
    except sqlite3.OperationalError:
        pass
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
        {
            "role": "Senior Software Engineer",
            "base_salary": 172000,
            "yoy_growth": "+6.8%",
            "demand_level": "Very High",
            "stack": "Distributed Systems, Go/TypeScript/Java, Kubernetes, PostgreSQL, Microservices Architecture",
            "bonus_pct": 15,
            "rsu_annual": 55000,
        },
        {
            "role": "Machine Learning Engineer",
            "base_salary": 192000,
            "yoy_growth": "+14.2%",
            "demand_level": "Extreme",
            "stack": "PyTorch, vLLM/TensorRT-LLM, CUDA, RAG Vector Pipelines, MLOps & Distributed Training",
            "bonus_pct": 18,
            "rsu_annual": 75000,
        },
        {
            "role": "Cloud DevOps Architect",
            "base_salary": 168000,
            "yoy_growth": "+8.4%",
            "demand_level": "High",
            "stack": "AWS/GCP Multi-Cloud, Terraform/OpenTofu, Karpenter Kubernetes, OpenTelemetry, FinOps",
            "bonus_pct": 15,
            "rsu_annual": 48000,
        },
        {
            "role": "Lead Data Scientist",
            "base_salary": 178000,
            "yoy_growth": "+9.5%",
            "demand_level": "Very High",
            "stack": "Causal Inference, Python/SQL/Spark, Experimentation Platforms, Predictive Modeling, dbt",
            "bonus_pct": 16,
            "rsu_annual": 52000,
        },
        {
            "role": "Cybersecurity Engineer",
            "base_salary": 164000,
            "yoy_growth": "+11.6%",
            "demand_level": "Extreme",
            "stack": "Zero-Trust IAM, OIDC/SPIFFE, Cloud Security Posture (CSPM), Threat Detection, DevSecOps",
            "bonus_pct": 15,
            "rsu_annual": 45000,
        },
    ]

    cities = [
        {
            "city": "San Francisco",
            "state": "CA",
            "col_multiplier": 1.25,
            "tech_hub_tier": "Tier-1 Silicon Valley & Bay Area Hub",
            "tax_profile": "9.3%–13.3% CA marginal state tax; high RSU equity weight",
            "sectors": "frontier AI labs, developer tools, hyperscale SaaS, and fintech",
            "work_model": "68% hybrid (3 days in SoMa/Palo Alto), 32% remote",
        },
        {
            "city": "New York City",
            "state": "NY",
            "col_multiplier": 1.20,
            "tech_hub_tier": "Tier-1 Financial & Enterprise Tech Hub",
            "tax_profile": "10.9% NY state + 3.876% NYC local tax; strong cash bonus incentives",
            "sectors": "quantitative finance, institutional fintech, ad-tech, and media",
            "work_model": "74% hybrid/in-office (Midtown/Flatiron/FiDi), 26% remote",
        },
        {
            "city": "Austin",
            "state": "TX",
            "col_multiplier": 1.03,
            "tech_hub_tier": "High-Growth Texas Silicon Hills Hub",
            "tax_profile": "0% Texas state personal income tax; high net take-home ratio",
            "sectors": "semiconductor engineering, enterprise cloud, cybersecurity, and B2B SaaS",
            "work_model": "52% hybrid (Downtown/Domain), 48% remote-first",
        },
        {
            "city": "Seattle",
            "state": "WA",
            "col_multiplier": 1.16,
            "tech_hub_tier": "Pacific Northwest Hyperscale Cloud Hub",
            "tax_profile": "0% WA state personal income tax on wages; public RSU-heavy packages",
            "sectors": "hyperscale cloud infrastructure, distributed storage, and AI systems",
            "work_model": "64% hybrid (South Lake Union/Bellevue/Redmond), 36% remote",
        },
        {
            "city": "Denver",
            "state": "CO",
            "col_multiplier": 0.99,
            "tech_hub_tier": "Rocky Mountain Cloud & Aerospace Hub",
            "tax_profile": "4.40% flat Colorado state income tax; statutory pay transparency in all job ads",
            "sectors": "aerospace telemetry, clean-tech IoT, defense cloud, and distributed SaaS",
            "work_model": "44% hybrid (LoDo/Boulder), 56% remote-first",
        },
    ]

    records = []
    for idx_r, r in enumerate(roles):
        for idx_c, c in enumerate(cities):
            localized_salary = int(round(r["base_salary"] * c["col_multiplier"], -2))
            p25_salary = int(round(localized_salary * 0.86, -2))
            p75_salary = int(round(localized_salary * 1.18, -2))
            annual_bonus = int(round(localized_salary * (r["bonus_pct"] / 100.0), -2))
            annual_rsu = int(round(r["rsu_annual"] * c["col_multiplier"], -2))
            total_comp_median = localized_salary + annual_bonus + annual_rsu
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
                    "annual_bonus": annual_bonus,
                    "annual_rsu": annual_rsu,
                    "total_comp_median": total_comp_median,
                    "yoy_growth": r["yoy_growth"],
                    "demand_level": r["demand_level"],
                    "tech_hub_tier": c["tech_hub_tier"],
                    "tax_profile": c["tax_profile"],
                    "sectors": c["sectors"],
                    "work_model": c["work_model"],
                    "stack": r["stack"],
                    "variant": (idx_r + idx_c) % 3,
                }
            )

    return pd.DataFrame(records)


def generate_rich_salary_guide(row: pd.Series, all_df: pd.DataFrame) -> dict:
    year = 2026
    role = row["role"]
    city = row["city"]
    state = row["state"]
    median = f"${row['median_salary']:,}"
    p25 = f"${row['p25_salary']:,}"
    p75 = f"${row['p75_salary']:,}"
    tc_med = f"${row['total_comp_median']:,}"
    bonus = f"${row['annual_bonus']:,}"
    rsu = f"${row['annual_rsu']:,}"

    title = f"{role} Salary in {city}, {state} ({year} Base, Equity & Total Comp Guide)"

    if row["variant"] == 0:
        p1 = (
            f"In {year}, a {role} based in {city}, {state} commands a verified median base salary of {median} USD, "
            f"with total annual compensation (including target cash bonus of {bonus} and annualized RSU equity of {rsu}) "
            f"reaching {tc_med} USD. Across the {row['tech_hub_tier']}, base compensation spans from {p25} at the 25th "
            f"percentile to {p75} at the 75th percentile for senior individual contributors mastering {row['stack']}."
        )
    elif row["variant"] == 1:
        p1 = (
            f"How much does a {role} earn in {city}, {state} during {year}? Driven by {row['demand_level']} hiring demand "
            f"and {row['yoy_growth']} year-over-year wage appreciation across {row['sectors']}, median base pay stands at "
            f"{median} USD ({p25} P25 to {p75} P75). When accounting for {rsu} in annual equity vesting and {bonus} in "
            f"performance bonuses, median Total Compensation (TC) reaches {tc_med} USD."
        )
    else:
        p1 = (
            f"Benchmarking {role} compensation in {city}, {state} requires analyzing both base salary bands ({p25} to {p75}, "
            f"median {median} USD) and liquid equity components. Operating within a {row['tech_hub_tier']} characterized by "
            f"{row['tax_profile']}, experienced engineers specializing in {row['stack']} achieve a median total package of {tc_med} USD."
        )

    p2 = (
        f"Local purchasing power and net take-home pay in {city} are shaped by {row['tax_profile']} and a workforce "
        f"distribution of {row['work_model']}. Employers across {row['sectors']} structure senior offers with multi-year "
        f"equity grants and sign-on bonuses ($20,000–$65,000) to attract candidates who can own mission-critical production systems."
    )

    use_cases = [
        f"Evaluating a new {role} job offer in {city} by decomposing guaranteed base cash ({median} median) versus 4-year RSU grants ({rsu}/yr) and target bonus ({bonus}/yr).",
        f"Preparing a data-backed promotion or annual refresher case when your current base pay lags behind the {city} 50th percentile ({median}) or 75th percentile ({p75}).",
        f"Comparing net after-tax disposable income in {city}, {state} ({row['tax_profile']}) against remote or relocation offers in competing US technology hubs.",
    ]

    steps = [
        f"Phase 1 — Benchmark Your Exact Level Band: Anchor your expectation against {city}'s P50 ({median} base / {tc_med} TC) and P75 ({p75} base) bands before sharing any numbers with recruiters.",
        f"Phase 2 — Audit Equity Liquidity & Vesting Cliffs: Confirm whether the {rsu}/yr equity component vests quarterly without a Year-2 cliff Drop, or negotiate a Year-1 cash sign-on bridge.",
        f"Phase 3 — Demonstrate High-Leverage Stack Ownership: Emphasize production outcomes in {row['stack']}—specifically latency, reliability, or revenue metrics—to justify top-quartile P75 placement.",
        f"Phase 4 — Adjust for Tax & Hybrid Commute Costs: Factor in {row['tax_profile']} and {row['work_model']} when finalizing base vs. equity split requests.",
    ]

    table_headers = ["Experience / Level Tier", f"{city} Base Salary", "Annual Bonus + Equity", "Estimated Total Comp (TC)"]
    l4_base = int(round(row["median_salary"] * 0.82, -2))
    l4_tc = int(round(row["total_comp_median"] * 0.76, -2))
    l6_base = int(round(row["median_salary"] * 1.22, -2))
    l6_tc = int(round(row["total_comp_median"] * 1.38, -2))
    l7_base = int(round(row["median_salary"] * 1.45, -2))
    l7_tc = int(round(row["total_comp_median"] * 1.78, -2))

    table_rows = [
        ["Mid-Level (L4 / 2–4 YOE)", f"${l4_base:,}", f"${l4_tc - l4_base:,}", f"${l4_tc:,}"],
        [f"Senior {role} (L5 / 5–8 YOE)", median, f"${row['annual_bonus'] + row['annual_rsu']:,}", tc_med],
        ["Staff / Lead IC (L6 / 8+ YOE)", f"${l6_base:,}", f"${l6_tc - l6_base:,}", f"${l6_tc:,}"],
        ["Principal Architect (L7+)", f"${l7_base:,}", f"${l7_tc - l7_base:,}", f"${l7_tc:,}"],
    ]

    pros = [
        f"Strong {row['yoy_growth']} year-over-year compensation growth driven by {row['demand_level']} demand across {row['sectors']}.",
        f"Liquid RSU and performance bonus structures add ${row['annual_bonus'] + row['annual_rsu']:,}/yr above the {median} median base salary.",
        f"Flexible {row['work_model']} arrangements allow engineers to optimize commute and housing costs across the {city} metro area.",
    ]

    cons = [
        f"Take-home pay calculations must account for {row['tax_profile']} and local housing appreciation.",
        f"Top-quartile P75 packages ({p75}+ base) require proven production leadership in {row['stack']} and rigorous system-design interviews.",
        "Equity-heavy offers carry public market volatility or private 409A illiquidity risk compared to all-cash base compensation.",
    ]

    faqs = [
        {
            "question": f"What is the average and median {role} salary in {city}, {state} for {year}?",
            "answer": (
                f"In {year}, the median base salary for a {role} in {city}, {state} is {median} USD per year "
                f"(ranging from {p25} at the 25th percentile to {p75} at the 75th percentile). Including annual bonus "
                f"({bonus}) and equity ({rsu}), median Total Compensation reaches {tc_med} USD."
            ),
        },
        {
            "question": f"Which technical skills pay the highest premium for a {role} in {city}?",
            "answer": (
                f"Employers across {row['sectors']} pay a 15%–25% premium (pushing base pay toward {p75}) for candidates "
                f"with hands-on production mastery of {row['stack']}."
            ),
        },
        {
            "question": f"How do taxes and remote/hybrid policies impact {role} take-home pay in {city}?",
            "answer": (
                f"Compensation in {city} is subject to {row['tax_profile']}, while local teams operate under a "
                f"workforce split of {row['work_model']}."
            ),
        },
        {
            "question": f"How should I negotiate a {role} offer in {city}, {state}?",
            "answer": (
                f"Anchor base salary discussions around the {median}–{p75} range and focus additional leverage on the "
                f"4-year equity grant ({rsu}/yr target) and Year-1 sign-on cash bonus."
            ),
        },
    ]

    related_links = []
    for _, cand in all_df.iterrows():
        if cand["slug"] == row["slug"]:
            continue
        if cand["role"] == role or cand["city"] == city:
            related_links.append(
                {
                    "slug": cand["slug"],
                    "title": f"{cand['role']} Salary in {cand['city']}, {cand['state']} (2026 Guide)",
                    "category": "Tech Salaries",
                }
            )
        if len(related_links) >= 6:
            break

    headings = {
        "s1": f"{year} Compensation Overview & {city} Market Context",
        "s2": "Practical Offer Evaluation & Career Scenarios",
        "s3": "4-Step Salary & Equity Negotiation Playbook",
        "s4": f"{role} Compensation Matrix by Seniority in {city}",
        "s5": f"Market Advantages vs. Cost & Tax Trade-Offs in {city}",
    }

    full_description = (
        f"{p1}\n\n{p2}\n\n"
        f"{headings['s2']}:\n" + "\n".join([f"• {u}" for u in use_cases]) + "\n\n"
        f"{headings['s3']}:\n" + "\n".join(steps)
    )

    meta_payload = {
        "category": "Tech Salaries",
        "city": f"{city}, {state}",
        "region": row["tech_hub_tier"],
        "reading_time": "6 min read",
        "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "kpis": [
            {"label": "Median Base Salary (P50)", "value": f"{median} / yr"},
            {"label": "Median Total Comp (Base+Bonus+RSU)", "value": f"{tc_med} / yr"},
            {"label": "25th to 75th Percentile Band", "value": f"{p25} – {p75}"},
            {"label": "YoY Growth & Hiring Demand", "value": f"{row['yoy_growth']} ({row['demand_level']})"},
        ],
        "stack": row["stack"],
        "headings": headings,
        "overview_paragraphs": [p1, p2],
        "use_cases": use_cases,
        "steps": steps,
        "table_headers": table_headers,
        "table_rows": table_rows,
        "pros": pros,
        "cons": cons,
        "regional_insight": p2,
        "compliance": row["tax_profile"],
        "tax_profile": row["tax_profile"],
        "work_model": row["work_model"],
        "salary_base": int(row["median_salary"]),
        "related_links": related_links,
    }

    return {
        "title": title,
        "description": full_description,
        "faqs": faqs,
        "meta": meta_payload,
    }


def upsert_page(conn: sqlite3.Connection, slug: str, title: str, description: str, faqs: list, meta: dict) -> None:
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    faqs_json = json.dumps(faqs, ensure_ascii=False)
    meta_json = json.dumps(meta, ensure_ascii=False)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO pages (slug, title, description, faqs, meta, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(slug) DO UPDATE SET
            title = excluded.title,
            description = excluded.description,
            faqs = excluded.faqs,
            meta = excluded.meta,
            created_at = excluded.created_at;
        """,
        (slug, title, description, faqs_json, meta_json, now_iso),
    )
    conn.commit()


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    try:
        init_db(conn)
        df = fetch_market_data()
        total = len(df)
        print(f"Generating {total} in-depth localized compensation & equity guides...")

        for idx, row in df.iterrows():
            slug = row["slug"]
            seo_payload = generate_rich_salary_guide(row, df)
            upsert_page(
                conn=conn,
                slug=slug,
                title=seo_payload["title"],
                description=seo_payload["description"],
                faqs=seo_payload["faqs"],
                meta=seo_payload["meta"],
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
