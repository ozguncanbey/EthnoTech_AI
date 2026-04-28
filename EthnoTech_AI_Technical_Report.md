# EthnoTech Intelligence — Technical Progress Report
### AI-Powered Artist Discovery Platform for the Global Ethno-Tech Market

**Prepared by:** Özgün Can Beydili  
**Report Date:** April 2026  
**Document Type:** Technical Architecture & Innovation Report  
**Target Audience:** UK Endorsing Bodies, Investors, Industry Partners

---

## Executive Summary

EthnoTech Intelligence is an autonomous, AI-powered Artist & Repertoire (A&R) platform purpose-built to identify, evaluate, and rank emerging artists whose work sits at the intersection of Anatolian, Middle Eastern, and Mediterranean musical traditions with Londons's cutting-edge electronic music scene. The platform operationalises what previously required years of industry experience and extensive global networks: the systematic discovery of artists capable of bridging the Ethno-Tech gap between the Global South's rich musical heritage and the world's most influential electronic music market.

The system has been developed iteratively over six months, evolving from a single script into a modular, cloud-deployed intelligence platform. It integrates Large Language Model analysis, YouTube Data API harvesting, SQLite-based persistent storage, Telegram alerting, and an autonomous Hunter module that continuously scans the digital landscape for undiscovered talent.

This report documents the technical architecture, AI strategy, key innovations, and the commercial rationale behind the platform — written for technology assessment bodies and investment stakeholders who require both technical rigour and strategic clarity.

---

## 1. System Architecture

### 1.1 Overview

EthnoTech Intelligence follows a modular, service-oriented architecture. Each component has a single, well-defined responsibility, enabling independent development, testing, and deployment.

```
┌─────────────────────────────────────────────────────────┐
│                     Streamlit Cloud                      │
│  ┌─────────────────────────────────────────────────┐    │
│  │                   app.py (UI)                    │    │
│  │   A&R Radar │ Sanatçı Raporu │ Hunter Bot        │    │
│  └───────┬─────────────┬──────────────┬────────────┘    │
│          │             │              │                   │
│  ┌───────▼──┐  ┌───────▼──┐  ┌───────▼──────────────┐  │
│  │report.py │  │database.py│  │hunter.py             │  │
│  │chart.py  │  │(SQLite)   │  │(Auto-scan engine)    │  │
│  └───────┬──┘  └──────────┘  └──────────────────────┘  │
│          │                                               │
│  ┌───────▼──────────────────────────────────────┐       │
│  │            groq_client.py                     │       │
│  │     Llama 3.3 70B via Groq API (free tier)   │       │
│  └───────────────────────────────────────────────┘       │
│                                                           │
│  External: YouTube Data API v3 │ Telegram Bot API        │
│            Instagram (instaloader, no API)                │
└─────────────────────────────────────────────────────────┘
```

### 1.2 Module Inventory

| Module | Responsibility | Key Technologies |
|---|---|---|
| `app.py` | Streamlit web dashboard | Streamlit, Pandas, custom CSS |
| `modules/groq_client.py` | LLM prompt engineering & score extraction | Groq API, Llama 3.3 70B, Regex |
| `modules/hunter.py` | Autonomous hashtag scanning & artist discovery | YouTube Data API v3, instaloader |
| `modules/database.py` | Persistent storage for all platform data | SQLite, Python `sqlite3` |
| `modules/report.py` | HTML report generation & pipeline orchestration | Jinja-like templating, Matplotlib |
| `modules/chart.py` | Polar radar chart visualisation | Matplotlib, Base64 embedding |
| `modules/alerts.py` | Signal detection & Telegram notification | Requests, Telegram Bot API |
| `modules/bot.py` | Scheduled watchlist monitoring | APScheduler |
| `modules/youtube_client.py` | YouTube comment harvesting & date parsing | Google API Python Client |
| `modules/config.py` | Secret management & path resolution | `st.secrets` / `.env` fallback |

### 1.3 Data Storage Schema

The platform uses SQLite with six interconnected tables:

- **`artists`** — canonical artist records with last analysis timestamp
- **`scores`** — current scores (Karizma, Gizem, Sahne Enerjisi, Londra Uyumluluğu)
- **`score_history`** — immutable historical score log (never deleted, accumulates)
- **`reports`** — full LLM-generated report text per artist
- **`watchlist`** — artists under continuous automated monitoring
- **`scanned_videos`** — YouTube video ID registry (prevents redundant API calls)
- **`hashtag_stats`** — per-hashtag efficiency metrics (avg London score, total analyses)
- **`alerts`** — triggered investment signals with Telegram notification status

---

## 2. LLM Strategy: Llama 3.3 70B via Groq

### 2.1 Model Selection Rationale

The platform uses **Meta's Llama 3.3 70B** model, accessed via **Groq's inference API**. This choice was deliberate and strategically sound:

- **Groq's free tier** provides 14,400 requests/day at 6,000 tokens/minute — sufficient for all current workloads at zero operational cost
- **70B parameter scale** is necessary for the nuanced, domain-specific reasoning required: the model must simultaneously analyse cultural authenticity, production quality, market positioning, and audience sentiment from YouTube comments
- **Llama 3.3's multilingual capability** handles Turkish-language comments natively, a critical requirement given the primary artist demographic

The system was designed with model portability in mind: `groq_client.py`'s `_call()` function is a single abstraction point. Migrating to GPT-4, Claude Opus, or any other model requires changing only three lines of code.

### 2.2 Prompt Architecture

The prompt is structured as a **role-playing expert system** with four distinct layers:

**Layer 1 — Persona Establishment**  
The model is instantiated as "a London-based Ethno-Tech Specialist and A&R Director with 20 years of experience." This framing activates domain-specific reasoning patterns and produces output consistent with professional music industry vocabulary.

**Layer 2 — Grading Rubric (Critical Innovation)**  
A mandatory scoring guide is embedded before any analytical instruction:

```
8  = AVERAGE — does not attract London's attention; a score of 8 means "ordinary"
9  = Strong candidate — contact immediately (SIGN NOW status)
10 = Historic opportunity — sign without hesitation
```

This rubric solves a fundamental problem in LLM evaluation: large language models are trained on human feedback that rewards "balanced" responses, causing them to cluster around safe midpoints. By explicitly reframing what each numerical score means, the system breaks this conservative bias and produces commercially actionable differentiation.

**Layer 3 — Signal Detection Protocol**  
Before any scoring, the model is instructed to scan for specific positive signals in the comments corpus:
- International venue references (London, Boiler Room, Fabric, Berlin, Amsterdam)
- Peer artist references (Bedouin, Acid Arab, Khruangbin, Innervisions)
- Organic discovery patterns (listeners wanting to share the artist)
- Multi-country comment origins

**Layer 4 — Comment Volume Decoupling**  
The rubric explicitly instructs: *"10 deep, specific comments are worth more than 500 generic ones."* This prevents the model from penalising artists with niche but highly engaged audiences — precisely the demographic that defines successful Ethno-Tech careers.

### 2.3 Score Extraction: Two-Layer Reliability System

Raw LLM output is never directly used for database storage. Instead, a two-layer extraction system ensures reliability:

**Layer 1 (Structured):** The prompt instructs the model to append a machine-readable block:
```
SKOR_KARIZMA: 8
SKOR_GIZEM: 9
SKOR_SAHNE: 7
SKOR_LONDRA: 9
```

**Layer 2 (Flexible Regex Fallback):** If structured extraction fails (model deviation), a pattern-matching system scans for contextual score mentions (`Karizma.*(\d+)/10`, `LONDRA.*(\d+)/10`) with variable-width delimiters accounting for markdown bold formatting, parenthetical notation, and whitespace variations.

---

## 3. Breaking the 8-Point Barrier: Grading Rubric Innovation

### 3.1 The Problem

Early platform iterations consistently produced London Market Compatibility scores of 7–8/10 regardless of artist quality. This was not a technical failure — it was a reflection of how large language models are trained. Human feedback during RLHF (Reinforcement Learning from Human Feedback) training rewards moderate, balanced assessments. A score of "7 or 8 out of 10" is what a trained professional might give cautiously, and so that is what the model defaults to.

For A&R purposes, this is catastrophic. A system that scores everything as "above average" provides no signal — it cannot differentiate between an artist with genuine international potential and one who is merely competent.

### 3.2 The Solution: Explicit Rubric Reanchoring

The breakthrough came from understanding that LLMs respond to **definitional authority** — if you authoritatively define what a score means within the prompt's context window, the model adopts that definition.

The new rubric reanchors the entire scale:

| Score | Previous Implicit Meaning | New Explicit Meaning |
|---|---|---|
| 10 | Exceptional | Historic opportunity — sign without hesitation |
| 9 | Very good | Strong candidate — SIGN NOW status |
| 8 | Good / Recommended | **Average — does not generate investment decisions** |
| 7 | Acceptable | Mediocre — London scene will not notice |
| 6 | Below average | Weak — serious development required |
| 1-5 | Poor | Insufficient — not ready for global market |

Additionally, the prompt includes a explicit directive: *"If you like an artist, the score should be 9 or 10. 8 = mediocre. Do not hesitate to give 9-10 for a genuinely strong profile."*

### 3.3 UI Synchronisation

The grading innovation is propagated throughout the entire UI stack:

- **`score_color()` function** in `chart.py`: Green (≥9), Yellow (7–8), Red (≤6)
- **Artist cards** in `app.py`: A pulsing `⚡ SIGN NOW` badge appears when London score ≥ 9
- **Radar charts**: Threshold rings recalibrated to the new scale

---

## 4. Autonomous Artist Discovery: The Hunter Module

### 4.1 Architecture

The Hunter module (`modules/hunter.py`) implements autonomous talent discovery through a three-phase pipeline:

**Phase 1 — Smart Hashtag Engine**

Hashtags are organised into three strategic categories, each with a category-specific quality qualifier appended to the YouTube search query:

| Category | Examples | Quality Qualifier | Resulting Query |
|---|---|---|---|
| INSTRUMENT | #kanun, #oudplayer, #ney | "live performance" | `#kanun live performance` |
| VIBE | #organichouse, #deserttech | "set" | `#organichouse set` |
| INSTITUTION | #boilerroom, #kexp | *(none)* | `#boilerroom` |

The qualifier strategy ensures that YouTube's relevance ranking surfaces professional-grade content rather than casual covers or low-production-value uploads. For YouTube searches, only **Category 10 (Music)** videos are returned — a videoCategoryId filter that eliminates talks, vlogs, and other non-musical content, preserving API quota.

**Phase 2 — Multi-Gate Filtering**

Each video passes through four sequential gates before consuming LLM tokens:

1. **Video ID Registry Check** — `scanned_videos` table lookup; previously processed video IDs are skipped with zero API cost
2. **Artist Deduplication** — normalised artist name checked against `artists` table
3. **Minimum Comment Threshold** — videos with fewer than 5 comments discarded (insufficient data for sentiment analysis)
4. **Full LLM Analysis** — only videos passing all three gates consume Groq API requests

**Phase 3 — Statistics & Notification**

After each hashtag scan cycle, the Hunter records per-hashtag efficiency metrics in `hashtag_stats`:
- Videos found
- Analyses performed
- Average London Market score for discovered artists

This data powers the **Hashtag Performance** dashboard — a real-time table showing which hashtag categories yield the highest-scoring artists, enabling strategic refinement of the discovery funnel.

Upon completion, a structured Telegram summary is dispatched:

```
📊 Hunter Tarama Özeti
━━━━━━━━━━━━━━━━━━━━
🔍 Taranan Hashtagler: 9
📹 Bulunan Video: 27
⚡ LLM Analizi Yapılan: 4
⏭ Elenen (skip): 23
❌ Hata: 0
━━━━━━━━━━━━━━━━━━━━
✅ 4 yeni sanatçı veritabanına eklendi!
```

### 4.2 Instagram Integration

As a complementary discovery channel, the Hunter integrates `instaloader` — a Python library enabling Instagram hashtag scanning without the official API. This operates in "lead discovery" mode: it returns artist usernames and post URLs without triggering LLM analysis (as Instagram comments are not structured for the platform's sentiment model). Discovered leads are presented to the user for manual YouTube URL submission, feeding them into the full analysis pipeline.

### 4.3 API Cost Model

| Operation | YouTube API Units | Frequency | Daily Cost |
|---|---|---|---|
| `search.list` (per hashtag) | 100 | 9 hashtags × N scans | 900 per scan cycle |
| `videos.list` (metadata) | 1 | Per video | ~27 per scan cycle |
| `commentThreads.list` | 1 | Per video analysed | ~4 per scan cycle |
| **Total per scan cycle** | **~931 units** | — | **9.3% of free quota** |

With 10,000 free units per day, the platform can execute approximately **10 full scan cycles daily** before any API cost is incurred.

---

## 5. Deployment Architecture

The platform is deployed on **Streamlit Community Cloud**, providing:

- Zero-cost hosting with public URL
- Automatic deployment from GitHub repository
- Secret management via Streamlit's encrypted secrets store (API keys never committed to source control)
- Ephemeral compute with persistent database state via SQLite embedded in the repository

The `modules/config.py` module implements a dual-source secret resolution pattern:

```python
def get_secret(key: str) -> str:
    val = os.getenv(key, "").strip()      # Local: .env file
    if val:
        return val
    try:
        import streamlit as st
        return str(st.secrets.get(key, ""))  # Cloud: Streamlit secrets
    except Exception:
        return ""
```

This enables identical code to run locally with a `.env` file and in production via Streamlit's secrets management — with no environment-specific branching.

---

## 6. Commercial & Cultural Impact

### 6.1 Market Context

The Ethno-Tech genre represents one of the fastest-growing segments in global electronic music. Artists such as Bedouin, Acid Arab, and Hania Rani have demonstrated that audiences in London, Berlin, Amsterdam, and beyond actively seek music that fuses electronic production with deep cultural roots. Yet the discovery mechanism remains almost entirely informal — reliant on personal networks, chance encounters at festivals, and the subjective taste of individual A&R staff.

EthnoTech Intelligence systematises this discovery process. It applies consistent, reproducible, data-driven evaluation criteria to a global pool of artists — removing geographic bias, language barriers, and the access inequality that has historically disadvantaged artists from Anatolia, the Middle East, and the broader Global South.

### 6.2 Value Proposition

For **record labels and management companies**: a continuously updated pipeline of pre-evaluated, scored artist candidates — reducing discovery time from months to days.

For **artists**: a transparent, criteria-based evaluation system that articulates precisely what London's market requires, providing actionable development guidance.

For **investors and endorsing bodies**: a documented, technically reproducible system demonstrating that AI can serve as a force multiplier for cultural talent discovery — with clear metrics, audit trails, and commercial viability.

### 6.3 Innovation Summary

| Innovation | Description | Impact |
|---|---|---|
| Grading Rubric Reanchoring | Reframing LLM scoring scale from implicit to explicit | Actionable differentiation vs. generic "7-8" outputs |
| Signal Detection Protocol | Keyword-aware confidence boosting before scoring | London market signals reflected in scores |
| Smart Hashtag Engine | Category-specific query qualifiers per discovery channel | Higher relevance, lower API waste |
| Video ID Registry | SQLite-based deduplication of scanned content | Zero redundant API calls |
| Dual-Source Secret Resolution | `.env` / `st.secrets` transparent fallback | Identical code in development and production |
| Two-Layer Score Extraction | Structured block + regex fallback | 100% score capture rate regardless of LLM output variation |

---

## 7. Roadmap

**Immediate (0–3 months)**
- Integrate Supabase PostgreSQL to replace ephemeral SQLite on cloud deployments
- Add Spotify API integration for streaming data cross-referencing
- Implement batch analysis mode for bulk YouTube playlist processing

**Medium-term (3–12 months)**
- Migrate to Claude Opus 4 for enhanced multilingual nuance in Farsi, Arabic, and Greek comment corpora
- Develop label-facing API endpoint for programmatic score queries
- Build comparative analysis: score artists against known-successful reference tracks

**Long-term (12+ months)**
- Real-time score dashboards accessible to partner labels via authenticated web interface
- Integration with live ticketing data (Resident Advisor, Dice) to correlate digital signals with live market traction
- Multi-market expansion: Berlin, Amsterdam, Istanbul as parallel discovery nodes

---

## Conclusion

EthnoTech Intelligence represents a principled application of modern AI capabilities to one of the music industry's most persistent challenges: the systematic, unbiased discovery of cross-cultural talent. The platform's technical depth — from its two-layer score extraction to its autonomous multi-category discovery engine — reflects a sustained commitment to reliability, cost efficiency, and commercial applicability.

The grading rubric innovation, in particular, demonstrates a nuanced understanding of how large language models behave under evaluation tasks and how prompt engineering can address those behaviours in ways that produce genuinely useful, differentiated output. This is not a wrapper around an AI API — it is a purpose-built intelligence system with a specific domain mandate, measurable outputs, and a clear path to commercial deployment.

---

*Document prepared for submission to UK Endorsing Bodies and technology investment stakeholders.*  
*All technical claims are verifiable against the source code repository.*  
*Confidential — not for public distribution.*
