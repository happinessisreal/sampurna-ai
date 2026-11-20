import { useEffect, useState } from 'react'
import { api } from './api'
import { AgentCopilot } from './components/AgentCopilot'
import { EconomicsReport } from './components/EconomicsReport'
import { FormulationLab } from './components/FormulationLab'
import { MolecularLab } from './components/MolecularLab'
import { ProvenanceView } from './components/ProvenanceView'
import { COPY } from './i18n'
import type {
  EconomicsRequest,
  FormulateAgentResponse,
  HealthInfo,
  Ingredient,
  Lang,
  OptimizeRequest,
  OptimizeResponse,
  ParetoPoint,
  ParetoResponse,
  Preset,
  TabId,
} from './types'

const DEFAULT_ECON: EconomicsRequest = {
  batch_size_kg: 1000,
  processing_packaging_bdt_per_kg: 18,
  wholesale_price_bdt_per_kg: 245,
  daily_servings: 10000,
  operating_days_per_year: 250,
}

const DEFAULT_REQ: OptimizeRequest = {
  mode: 'meat_analogue',
  standard: 'fao_2013_diaas',
  price_tier: 'open_market',
  min_score: 1.0,
  max_budget_bdt: 16.0,
  max_mass_g: 250.0,
  protein_target_g: 20.0,
  cost_weight: 0.55,
  excluded_allergens: ['peanut'],
  include_ids: ['red_lentil', 'oyster_mushroom', 'green_jackfruit'],
  exclude_ids: [],
  price_overrides: {},
  min_fibrous_share: 0.35,
  economics: DEFAULT_ECON,
}

export function App() {
  const [lang, setLang] = useState<Lang>('bn')
  const [activeTab, setActiveTab] = useState<TabId>('formulation')
  const [health, setHealth] = useState<HealthInfo | null>(null)
  const [presets, setPresets] = useState<Preset[]>([])
  const [activePresetId, setActivePresetId] = useState<string>('dhaka_keema')
  const [plantIngs, setPlantIngs] = useState<Ingredient[]>([])
  const [baselines, setBaselines] = useState<Ingredient[]>([])
  const [req, setReq] = useState<OptimizeRequest>(DEFAULT_REQ)
  const [econReq, setEconReq] = useState<EconomicsRequest>(DEFAULT_ECON)
  const [optResult, setOptResult] = useState<OptimizeResponse | null>(null)
  const [pareto, setPareto] = useState<ParetoResponse | null>(null)
  const [optLoading, setOptLoading] = useState(false)
  const [agentResult, setAgentResult] = useState<FormulateAgentResponse | null>(null)
  const [agentLoading, setAgentLoading] = useState(false)

  const t = COPY[lang]

  const runOptimize = async (overrideReq?: OptimizeRequest) => {
    const payload = { ...(overrideReq ?? req), economics: econReq }
    setOptLoading(true)
    try {
      const [optRes, parRes] = await Promise.all([api.optimize(payload), api.pareto(payload)])
      setOptResult(optRes)
      setPareto(parRes)
    } finally {
      setOptLoading(false)
    }
  }

  useEffect(() => {
    api.health().then(setHealth)
    api.presets().then(setPresets)
    api.ingredients().then((d) => {
      setPlantIngs(d.plant_ingredients)
      setBaselines(d.baselines)
    })
    runOptimize(DEFAULT_REQ)
  }, [])

  const applyPreset = (p: Preset) => {
    setActivePresetId(p.id)
    const next: OptimizeRequest = {
      ...DEFAULT_REQ,
      ...p.request,
      price_overrides: p.request.price_overrides ?? {},
      economics: econReq,
    }
    setReq(next)
    runOptimize(next)
  }

  const handleSelectPareto = async (pt: ParetoPoint) => {
    setOptLoading(true)
    try {
      const res = await api.scoreDirect(
        pt.grams_by_id,
        req.standard,
        req.price_tier,
        req.price_overrides,
        econReq
      )
      setOptResult(res)
    } finally {
      setOptLoading(false)
    }
  }

  const handleRecalcEcon = async (nextEcon: EconomicsRequest) => {
    if (!optResult?.grams_by_id) return
    const res = await api.scoreDirect(
      optResult.grams_by_id,
      req.standard,
      req.price_tier,
      req.price_overrides,
      nextEcon
    )
    setOptResult(res)
  }

  const handleRunAgent = async (brief: string) => {
    setAgentLoading(true)
    try {
      const res = await api.runAgents(brief, req.standard, req.price_tier, lang)
      setAgentResult(res)
      // Sync active blend with the 4-Agent Copilot result
      const synced = await api.scoreDirect(
        Object.fromEntries(res.score.items.map((i) => [i.id, i.grams])),
        req.standard,
        req.price_tier,
        req.price_overrides,
        econReq
      )
      setOptResult(synced)
    } finally {
      setAgentLoading(false)
    }
  }

  const tabs: Array<{ id: TabId; label: string }> = [
    { id: 'formulation', label: t.tab_formulation },
    { id: 'molecular', label: t.tab_molecular },
    { id: 'agents', label: t.tab_agents },
    { id: 'economics', label: t.tab_economics },
    { id: 'provenance', label: t.tab_provenance },
  ]

  return (
    <div className="min-h-screen bg-[#F5F7F5] text-[#0F231B]">
      {/* Top Navigation Bar matching Figma */}
      <header className="sticky top-0 z-30 border-b border-[#DCE5DF] bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-[1440px] flex-wrap items-center justify-between gap-4 px-4 py-3 sm:px-8">
          {/* Botanical Molecule Logo */}
          <div className="flex items-center gap-2.5">
            <svg width="36" height="36" viewBox="0 0 36 36" fill="none" aria-hidden="true">
              <rect width="36" height="36" rx="10" fill="#0B5D42" />
              <circle cx="18" cy="11" r="3" fill="#5EEAD4" />
              <circle cx="11" cy="23" r="3" fill="#A7F3D0" />
              <circle cx="25" cy="23" r="3" fill="#A7F3D0" />
              <path
                d="M18 14V18M18 18L13.5 21.5M18 18L22.5 21.5"
                stroke="#FFFFFF"
                strokeWidth="2"
                strokeLinecap="round"
              />
              <circle cx="18" cy="18" r="2.2" fill="#FFFFFF" />
            </svg>
            <div>
              <div className="text-lg font-bold leading-tight text-[#0F231B]">{t.brand}</div>
              <div className="font-mono-tech text-[10px] font-medium text-[#0D9488]">
                {t.subbrand}
              </div>
            </div>
          </div>

          {/* Primary Navigation Tabs */}
          <nav className="flex flex-wrap items-center gap-1">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id)}
                className={`rounded-xl px-3.5 py-2 text-xs font-bold transition sm:text-sm ${
                  activeTab === tab.id
                    ? 'bg-[#E3F4EC] text-[#0B5D42]'
                    : 'text-[#3D554B] hover:bg-[#EEF3EF]'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </nav>

          {/* Status Badges & বাংলা | EN Language Switch */}
          <div className="flex items-center gap-2.5">
            <span className="hidden items-center gap-1.5 rounded-full bg-[#E3F4EC] px-3 py-1 text-[11px] font-semibold text-[#0B5D42] md:inline-flex">
              <span className="h-2 w-2 rounded-full bg-[#0B5D42]" />
              {health?.ai_foundry.configured
                ? `${health.ai_foundry.provider === 'nebius' ? 'Nebius' : health.ai_foundry.provider === 'gemini' ? 'Gemini' : 'Foundry'} · ${health.ai_foundry.model.replace(/^[^/]+\//, '')}`
                : lang === 'bn'
                  ? 'Nebius · Kimi K3.1 প্রস্তুত'
                  : 'AI · Deterministic'}
            </span>
            <span className="font-mono-tech hidden rounded-full bg-[#E0F5F3] px-3 py-1 text-[11px] font-medium text-[#0D9488] sm:inline-block">
              MCP · {health?.mcp_tools ?? 5} Tools
            </span>

            <div className="flex items-center rounded-full border border-[#B8CAC0] bg-[#EEF3EF] p-0.5">
              <button
                type="button"
                onClick={() => setLang('bn')}
                className={`rounded-full px-3 py-1 text-xs font-bold transition ${
                  lang === 'bn' ? 'bg-[#0B5D42] text-white' : 'text-[#3D554B]'
                }`}
              >
                বাংলা
              </button>
              <button
                type="button"
                onClick={() => setLang('en')}
                className={`font-mono-tech rounded-full px-3 py-1 text-xs font-bold transition ${
                  lang === 'en' ? 'bg-[#0B5D42] text-white' : 'text-[#3D554B]'
                }`}
              >
                EN
              </button>
            </div>
          </div>
        </div>

        {/* Preset Strip Bar */}
        <div className="border-t border-[#DCE5DF] bg-[#EEF3EF]/80">
          <div className="mx-auto flex max-w-[1440px] flex-wrap items-center justify-between gap-3 px-4 py-2.5 sm:px-8">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-semibold text-[#3D554B]">{t.preset_label}</span>
              {presets.map((p) => {
                const active = activePresetId === p.id
                return (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() => applyPreset(p)}
                    className={`rounded-full border px-3.5 py-1 text-xs font-semibold transition ${
                      active
                        ? 'border-[#0B5D42] bg-[#0B5D42] text-white'
                        : 'border-[#B8CAC0] bg-white text-[#0F231B] hover:border-[#0B5D42]'
                    }`}
                  >
                    {lang === 'bn' ? p.name_bn : p.name_en}
                  </button>
                )
              })}
            </div>
            <span className="hidden items-center gap-1.5 rounded-full bg-[#E3F4EC] px-3 py-1 text-[11px] font-semibold text-[#0B5D42] xl:inline-flex">
              <span className="h-1.5 w-1.5 rounded-full bg-[#0B5D42]" />
              {t.verified_badge}
            </span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="mx-auto max-w-[1440px] px-4 py-6 sm:px-8">
        {activeTab === 'formulation' && (
          <FormulationLab
            lang={lang}
            req={req}
            setReq={setReq}
            result={optResult}
            pareto={pareto}
            ingredients={plantIngs}
            loading={optLoading}
            onRunOptimize={runOptimize}
            onSelectParetoPoint={handleSelectPareto}
          />
        )}
        {activeTab === 'molecular' && <MolecularLab lang={lang} result={optResult} />}
        {activeTab === 'agents' && (
          <AgentCopilot
            lang={lang}
            presets={presets}
            agentResult={agentResult}
            loading={agentLoading}
            onRunAgent={handleRunAgent}
          />
        )}
        {activeTab === 'economics' && (
          <EconomicsReport
            lang={lang}
            result={optResult}
            economicsReq={econReq}
            setEconomicsReq={setEconReq}
            onRecalculateEconomics={handleRecalcEcon}
          />
        )}
        {activeTab === 'provenance' && (
          <ProvenanceView lang={lang} plantIngredients={plantIngs} baselines={baselines} />
        )}
      </main>
    </div>
  )
}

export default App
