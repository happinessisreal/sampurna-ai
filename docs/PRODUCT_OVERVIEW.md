# Sampurna AI — Product & Architecture Overview

## 1. Identity
- **Product Name:** **Sampurna AI** (*সম্পূর্ণা AI*)
- **Summary:** A zero-hallucination molecular and Pareto AI formulation platform that turns affordable Bangladeshi crops, mushrooms, and jackfruit by-products into complete, meat-like plant proteins at 69% lower cost and 92% lower carbon than chicken.
- **Localization:** Full **Bangla-primary (`বাংলা`)** web experience with an instant **`বাংলা | EN`** toggle.

## 2. Problem & Target Users
Bangladesh ranks near the bottom globally in quality animal-protein intake (**~186th out of 189 countries**, at **~4.5–5 kg of meat/person/year** or **~12 g/day**) because edible broiler chicken costs `৳32.08` and beef `৳73.17` per 20 g protein (emitting `931 g – 9,705 g CO₂e`). Families rely on the cereal "rice trap", where single staples are incomplete proteins (red lentil is sulfur-amino-acid limited at `0.610` FAO DIAAS; white rice is lysine limited at `0.623`)—contributing to **~24% child stunting** and **>40% anemia** among women and RMG garment workers. Meanwhile, local food processors (PRAN, ACI, cloud kitchens) and factory canteens lack accessible R&D tools to solve legume *hexanal* beany off-notes and fibrous texture without expensive lab trial-and-error.

## 3. AI-Native System Architecture
1. **3D Pareto & SciPy HiGHS LP Optimizer (`backend/core/optimizer.py`):** Optimizes across 14 locally available ingredients and 9 indispensable amino acids (`FAO 2013 DIAAS` & `WHO 2007 PDCAAS`), generating 15–20 non-dominated Cost × Carbon × Quality blends with allergen and TCB-subsidized pricing controls.
2. **PubChem Molecular Flavor-Bridge Engine (`backend/core/chemistry.py`):** Maps volatile off-notes (*Hexanal* CID `6184`) against fungal umami (*L-Glutamic Acid* CID `33032` + *5'-GMP* CID `135398631`) and Maillard precursors (*L-Cysteine* CID `5862` + *D-Xylose* CID `135191`).
3. **4-Agent Collaborative R&D Copilot (`backend/agent/orchestrator.py`):**
   - *Agent 1 (Formulation Strategist)* parses Bangla/EN briefs into LP constraints.
   - *Agent 2 (Molecular Chemist)* combines PubChem chemistry with TF-IDF RAG over **10 real open-access PMC/FAO/Science papers**.
   - *Agent 3 (Bilingual Culinary & Process Engineer)* outputs exact gram-locked EN/BN recipes + 1,000 kg batch processing flows.
   - *Agent 4 (Responsible-AI Verification Auditor)* programmatically verifies every quoted number, attaches allergen labels, and separates *Verified Computed* figures from *AI Hypotheses* needing wet-lab testing.
4. **Multimodal Prototype Vision Inspector + Live MCP Server (`backend/mcp_server.py`):** Inspects cooked prototype photos for Maillard browning/texture and exposes all 5 core tools via standard Model Context Protocol (`sampurna-formulation-mcp`).

## 4. Measurable Impact & Business Model
- **Verified Prototype Output (*Dhaka Sampurna Plant-Protein Keema*, 20 g complete protein):** `55.1 g` dry blend (`50%` Soy TVP, `27.3%` Chickpea, `10%` Oyster Mushroom, `7.7%` Red Lentil, `5%` Green Jackfruit Fiber) delivering **`FAO DIAAS 1.000`** at **`৳9.86`** (**−69.3% cost** vs. edible chicken) and **`73.9 g CO₂e`** (**−92.1% GHG** vs. chicken, **−99.2%** vs. beef).
- **Business Model & Scale:** B2B R&D formulation SaaS (`৳75,000/mo`) + institutional premix licensing for Bangladesh's 4M-worker RMG canteens (a single 10,000-worker canteen saves **৳5.13 crore/year** and avoids **2,133 tonnes CO₂e/year**).
- **Next-Phase Roadmap:** Real Dhaka bazaar sourcing, 20-person blind hedonic sensory trials closing the loop into the optimizer, live PubChem/USDA API enrichment, and B2B pilot deployments.
