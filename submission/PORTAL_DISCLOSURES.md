# CloudCamp Portal Submission Disclosures (Ready-to-Paste Guide)
**Covers all 8 Final Submission Sections & Preliminary Requirements (`Submission Rules v1.1`)**

---

## Section 1: Basics
- **Project Name:** Sampurna AI (সম্পূর্ণা AI)
- **One-Line Pitch:** AI-native molecular, Pareto, and multi-agent formulation platform turning local Bangladeshi crops, mushrooms, and jackfruit fibers into complete, meat-like plant proteins at 69% lower cost and 92% lower CO₂e than chicken.
- **Domain:** FoodSphere AI
- **Challenge:** Future Foods (Innovation in alternative and sustainable foods)
- **Primary Language:** English (official documentation & video) + Bangla-primary bilingual product UI (`বাংলা | EN`).

## Section 2 & 3: Problem Statement & Solution
*(Paste concise summaries from `submission/PRELIM_ONE_PAGER.md` Sections 2 & 3.)*

## Section 4: Demo & Links
- **Live Public Demo URL:** `https://sampurna-ai.jollygrass-e2685ed1.japaneast.azurecontainerapps.io` (single-origin HTTPS on Azure Container Apps, zero login wall, `min-replicas 1`)
- **GitHub Repository URL:** `https://github.com/happinessisreal/sampurna-ai` *(Private — add Judge Access Note if kept private during evaluation)*
- **Figma Design URL:** `https://www.figma.com/design/RMK4SKZQjjE9PGH6wOHLdL`
- **YouTube Demo Video URL (Unlisted, ≤ 3:00):** `<YOUTUBE_UNLISTED_URL>`
- **Link Validator Check:** Ensure all URLs resolve HTTP 200 without sign-in (`PASS`).

## Section 5: Data & AI Provenance
- **Datasets Used (Public, Cited, Non-Personal):**
  1. *USDA FoodData Central* — macronutrient, iron/zinc, and 9-EAA amino acid profiles (mg/g protein) for 14 plant/fungal ingredients and 4 animal baselines.
  2. *FAO (2013) Food & Nutrition Paper 92* & *WHO/FAO/UNU (2007) TRS 935* — official adult DIAAS & PDCAAS indispensable amino acid reference scoring patterns.
  3. *Poore & Nemecek (2018), Science (DOI: 10.1126/science.aaq0216) via Our World in Data* & *Water Footprint Network* — cradle-to-retail GHG emissions (`kg CO₂e/kg`) and freshwater footprint (`L/kg`).
  4. *Dhaka Open Retail & TCB Subsidized Price Lists (Nov 2026)* — yield-adjusted local BDT/kg ingredient costs (transparently flagging unverified dry/LCA proxies with `verified=false`).
  5. *NCBI PubChem PUG-REST* & *10 Open-Access Peer-Reviewed PMC/FAO/Science Papers* — verified molecular CIDs and open-access literature for RAG.
- **Personal Data Handling:** Zero personal or PII data collected or used anywhere in the platform.
- **Foundation Models Called:** **Google Gemini 4 Hydrogen** (`gemini-4-hydrogen`, `thinkingLevel=LOW`, bounded in-memory response cache for cost control) for 4-Agent Bangla constraint parsing, molecular/bilingual synthesis & multimodal prototype Vision; deterministic SciPy HiGHS LP + TF-IDF RAG fallbacks; app hosted on **Azure Container Apps**.

## Section 6: Tooling & IDE Disclosure
- **IDE & AI Coding Assistant:** Antigravity Agentic IDE (with Gemini models for planning, Figma MCP orchestration, backend/frontend engineering, and automated test verification).
- **Frameworks & Scientific Stack:** Python 3.12 (`uv`), FastAPI, SciPy (`linprog` HiGHS), NumPy, Pandas, scikit-learn (TF-IDF), `mcp` (`MCPServer`), Google Gemini API (REST), React 19, Vite, TypeScript, Tailwind CSS v4, Recharts, Docker, Azure Container Apps.
- **Typography Localization:** Official Bangladesh ICT Division / BCC `July` & `Purno` fonts (`bangla.gov.bd/purno`) bundled locally for native Bangla rendering.

## Section 7: MCP Usage Disclosure
- **Figma MCP Server (`figma_figma`):** Used during design phase to build the `Sampurna Tokens` variable collection (26 tokens), 10 reusable components, and 3 Bangla-primary `1440px` UI screens in Figma prior to implementation (`https://www.figma.com/design/RMK4SKZQjjE9PGH6wOHLdL`), visually verified via `get_screenshot`.
- **Sampurna Formulation MCP Server (`sampurna-formulation-mcp` in `backend/mcp_server.py`):** Implemented as part of the product using Python `mcp` SDK (`MCPServer`), exposing 5 deterministic scientific tools (`optimize_protein_blend`, `compute_pareto_frontier`, `analyze_molecular_sensory`, `search_food_literature`, `generate_impact_report`) over stdio so external AI coding assistants and R&D agents can invoke Sampurna directly.

## Section 8: Prompt Library (Curated System Prompts)
1. **Agent 1 — Formulation Strategist (`STRATEGIST_SYSTEM_PROMPT`):** Translates Bangla/Banglish/English user goals into constrained LP parameters (`mode`, `max_budget_bdt`, `min_score`, `excluded_allergens`, `include_ids`, `rag_query`) without fabricating numbers. *(Public)*
2. **Agent 2 & 3 — Molecular Chemist + Bilingual Culinary & Process Engineer (`CHEMIST_CULINARY_SYSTEM_PROMPT`):** Synthesizes PubChem CIDs and DOI-cited RAG excerpts into gram-locked EN/BN recipes and 1,000 kg batch flows while flagging wet-lab hypotheses. *(Public)*
3. **Agent 4 — Responsible-AI Verification Auditor (`AUDITOR_SYSTEM_PROMPT` + deterministic validator):** Cross-checks all quoted values against SciPy outputs, enforces allergen disclosure, and blocks unverified medical claims. *(Public)*
4. **Multimodal Vision Sensory Inspector (`VISION_INSPECTOR_SYSTEM_PROMPT`):** Scores cooked prototype photos on Maillard browning (0–100), fibrous grain (0–100), and moisture while labeling adjustments as *AI Visual Hypothesis*. *(Public)*
