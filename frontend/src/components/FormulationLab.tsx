import { useState } from 'react'
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Lock,
  Play,
  SlidersHorizontal,
  Sparkles,
} from 'lucide-react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from 'recharts'
import { ALLERGEN_OPTIONS, COPY, MODE_OPTIONS, bnNum } from '../i18n'
import type {
  Ingredient,
  Lang,
  OptimizeRequest,
  OptimizeResponse,
  ParetoPoint,
  ParetoResponse,
} from '../types'

interface Props {
  lang: Lang
  req: OptimizeRequest
  setReq: React.Dispatch<React.SetStateAction<OptimizeRequest>>
  result: OptimizeResponse | null
  pareto: ParetoResponse | null
  ingredients: Ingredient[]
  loading: boolean
  onRunOptimize: (override?: OptimizeRequest) => void
  onSelectParetoPoint: (pt: ParetoPoint) => void
}

export function FormulationLab({
  lang,
  req,
  setReq,
  result,
  pareto,
  ingredients,
  loading,
  onRunOptimize,
  onSelectParetoPoint,
}: Props) {
  const t = COPY[lang]
  const [showIngDrawer, setShowIngDrawer] = useState(false)
  const [selectedParetoId, setSelectedParetoId] = useState<string | null>(null)

  const score = result?.score ?? null
  const sensory = result?.sensory ?? null
  const baselines = result?.baselines ?? []
  const chicken = baselines.find((b) => b.baseline_id === 'chicken_broiler')
  const beef = baselines.find((b) => b.baseline_id === 'beef_boneless')
  const lentil = baselines.find((b) => b.baseline_id === 'red_lentil')

  const toggleAllergen = (id: string) => {
    setReq((prev) => {
      const exists = prev.excluded_allergens.includes(id)
      return {
        ...prev,
        excluded_allergens: exists
          ? prev.excluded_allergens.filter((a) => a !== id)
          : [...prev.excluded_allergens, id],
      }
    })
  }

  const togglePin = (id: string) => {
    setReq((prev) => {
      const pinned = prev.include_ids.includes(id)
      const excluded = prev.exclude_ids.filter((x) => x !== id)
      return {
        ...prev,
        exclude_ids: excluded,
        include_ids: pinned ? prev.include_ids.filter((x) => x !== id) : [...prev.include_ids, id],
      }
    })
  }

  const toggleExclude = (id: string) => {
    setReq((prev) => {
      const ex = prev.exclude_ids.includes(id)
      return {
        ...prev,
        include_ids: prev.include_ids.filter((x) => x !== id),
        exclude_ids: ex ? prev.exclude_ids.filter((x) => x !== id) : [...prev.exclude_ids, id],
      }
    })
  }

  const paretoData = (pareto?.points ?? []).map((p) => ({
    x: p.cost_bdt,
    y: p.co2e_g,
    z: p.quality_score * 100,
    point: p,
  }))

  const activeParetoId = selectedParetoId ?? pareto?.knee_point_id ?? null

  return (
    <div className="grid grid-cols-1 gap-6 md:grid-cols-12">
      {/* Left Sidebar Controls (Figma Screen 01 Left Rail) */}
      <aside className="rounded-2xl border border-[#DCE5DF] bg-white p-5 shadow-xs md:col-span-4 xl:col-span-3">
        <div className="mb-4">
          <h2 className="text-lg font-bold text-[#0F231B]">{t.controls_title}</h2>
          <p className="text-xs text-[#6B8077]">{t.controls_sub}</p>
        </div>

        {/* Goal Modes */}
        <div className="mb-4 space-y-2">
          <label className="block text-xs font-semibold text-[#3D554B]">{t.goal_label}</label>
          {MODE_OPTIONS.map((m) => {
            const active = req.mode === m.id
            return (
              <button
                key={m.id}
                type="button"
                onClick={() => {
                  const next = { ...req, mode: m.id }
                  setReq(next)
                  onRunOptimize(next)
                }}
                className={`w-full rounded-xl border px-3 py-2 text-left transition ${
                  active
                    ? 'border-[#0B5D42] bg-[#E3F4EC] text-[#0B5D42]'
                    : 'border-[#DCE5DF] bg-[#F5F7F5] text-[#0F231B] hover:border-[#B8CAC0]'
                }`}
              >
                <div className="text-xs font-bold">{lang === 'bn' ? m.title_bn : m.title_en}</div>
                <div className="text-[11px] text-[#3D554B]">{lang === 'bn' ? m.sub_bn : m.sub_en}</div>
              </button>
            )
          })}
        </div>

        {/* Protein Standard Toggle */}
        <div className="mb-4">
          <label className="mb-1.5 block text-xs font-semibold text-[#3D554B]">
            {t.standard_label}
          </label>
          <div className="grid grid-cols-2 gap-1 rounded-xl bg-[#EEF3EF] p-1">
            {(
              [
                ['fao_2013_diaas', 'FAO 2013 DIAAS'],
                ['who_2007_pdcaas', 'WHO 2007 PDCAAS'],
              ] as const
            ).map(([val, lbl]) => (
              <button
                key={val}
                type="button"
                onClick={() => {
                  const next = { ...req, standard: val }
                  setReq(next)
                  onRunOptimize(next)
                }}
                className={`font-mono-tech rounded-lg py-1.5 text-[11px] font-bold transition ${
                  req.standard === val
                    ? 'bg-white text-[#0B5D42] shadow-xs'
                    : 'text-[#3D554B] hover:text-[#0F231B]'
                }`}
              >
                {lbl}
              </button>
            ))}
          </div>
        </div>

        {/* Sliders */}
        <div className="mb-4 space-y-3">
          <div>
            <div className="mb-1 flex items-center justify-between text-xs">
              <span className="font-semibold text-[#3D554B]">{t.min_score_label}</span>
              <span className="font-mono-tech font-bold text-[#0B5D42]">
                {req.min_score.toFixed(2)}
              </span>
            </div>
            <input
              type="range"
              min={0.75}
              max={1.15}
              step={0.05}
              value={req.min_score}
              onChange={(e) => setReq({ ...req, min_score: parseFloat(e.target.value) })}
              className="w-full accent-[#0B5D42]"
            />
          </div>

          <div>
            <div className="mb-1 flex items-center justify-between text-xs">
              <span className="font-semibold text-[#3D554B]">{t.budget_label}</span>
              <span className="font-mono-tech font-bold text-[#0B5D42]">
                {req.max_budget_bdt === null
                  ? t.no_budget
                  : `৳ ${bnNum(req.max_budget_bdt.toFixed(0), lang)}`}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="range"
                min={8}
                max={45}
                step={1}
                value={req.max_budget_bdt ?? 45}
                onChange={(e) => {
                  const v = parseFloat(e.target.value)
                  setReq({ ...req, max_budget_bdt: v >= 45 ? null : v })
                }}
                className="w-full accent-[#0B5D42]"
              />
              {req.max_budget_bdt !== null && (
                <button
                  type="button"
                  onClick={() => setReq({ ...req, max_budget_bdt: null })}
                  className="rounded border border-[#DCE5DF] px-1.5 py-0.5 text-[10px] text-[#3D554B]"
                >
                  ∞
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Market Price Tier */}
        <div className="mb-4">
          <label className="mb-1.5 block text-xs font-semibold text-[#3D554B]">
            {t.price_tier_label}
          </label>
          <div className="grid grid-cols-2 gap-1 rounded-xl bg-[#EEF3EF] p-1">
            {(
              [
                ['open_market', t.open_market],
                ['tcb_subsidized', t.tcb_subsidized],
              ] as const
            ).map(([val, lbl]) => (
              <button
                key={val}
                type="button"
                onClick={() => {
                  const next = { ...req, price_tier: val }
                  setReq(next)
                  onRunOptimize(next)
                }}
                className={`rounded-lg py-1.5 text-xs font-bold transition ${
                  req.price_tier === val
                    ? 'bg-white text-[#0B5D42] shadow-xs'
                    : 'text-[#3D554B] hover:text-[#0F231B]'
                }`}
              >
                {lbl}
              </button>
            ))}
          </div>
        </div>

        {/* Allergens */}
        <div className="mb-4">
          <label className="mb-1.5 block text-xs font-semibold text-[#3D554B]">
            {t.allergens_label}
          </label>
          <div className="flex flex-wrap gap-1.5">
            {ALLERGEN_OPTIONS.map((al) => {
              const active = req.excluded_allergens.includes(al.id)
              return (
                <button
                  key={al.id}
                  type="button"
                  onClick={() => toggleAllergen(al.id)}
                  className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold transition ${
                    active
                      ? 'border-[#0D9488] bg-[#E0F5F3] text-[#0D9488]'
                      : 'border-[#B8CAC0] bg-[#F5F7F5] text-[#3D554B]'
                  }`}
                >
                  {lang === 'bn' ? al.bn : al.en} {active ? '✓' : ''}
                </button>
              )
            })}
          </div>
        </div>

        {/* Collapsible Pin / Price Override Drawer */}
        <div className="mb-4 rounded-xl border border-[#DCE5DF] bg-[#F5F7F5] p-2.5">
          <button
            type="button"
            onClick={() => setShowIngDrawer((s) => !s)}
            className="flex w-full items-center justify-between text-xs font-semibold text-[#3D554B]"
          >
            <span className="flex items-center gap-1.5">
              <SlidersHorizontal className="h-3.5 w-3.5 text-[#0B5D42]" />
              {t.customize_ing}
            </span>
            {showIngDrawer ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </button>
          {showIngDrawer && (
            <div className="mt-2.5 max-h-56 space-y-1.5 overflow-y-auto pr-1">
              {ingredients.map((ing) => {
                const pinned = req.include_ids.includes(ing.id)
                const excluded = req.exclude_ids.includes(ing.id)
                const priceVal =
                  req.price_overrides[ing.id] ??
                  (req.price_tier === 'tcb_subsidized'
                    ? ing.price_bdt_per_kg_tcb
                    : ing.price_bdt_per_kg_open)
                return (
                  <div
                    key={ing.id}
                    className="flex items-center justify-between gap-1.5 rounded-lg bg-white px-2 py-1 text-[11px]"
                  >
                    <span className="truncate font-medium text-[#0F231B]">
                      {lang === 'bn' ? ing.name_bn : ing.name.split(' (')[0]}
                    </span>
                    <div className="flex shrink-0 items-center gap-1">
                      <input
                        type="number"
                        min={10}
                        max={2000}
                        value={priceVal}
                        onChange={(e) => {
                          const v = parseFloat(e.target.value)
                          if (!Number.isNaN(v) && v > 0) {
                            setReq({
                              ...req,
                              price_overrides: { ...req.price_overrides, [ing.id]: v },
                            })
                          }
                        }}
                        className="font-mono-tech w-14 rounded border border-[#DCE5DF] px-1 py-0.5 text-right text-[10px]"
                        title="BDT/kg"
                      />
                      <button
                        type="button"
                        onClick={() => togglePin(ing.id)}
                        className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${
                          pinned ? 'bg-[#0B5D42] text-white' : 'bg-[#EEF3EF] text-[#3D554B]'
                        }`}
                        title="Pin >= 5%"
                      >
                        <Lock className="inline h-2.5 w-2.5" />
                      </button>
                      <button
                        type="button"
                        onClick={() => toggleExclude(ing.id)}
                        className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${
                          excluded ? 'bg-[#C2410C] text-white' : 'bg-[#EEF3EF] text-[#3D554B]'
                        }`}
                        title="Exclude"
                      >
                        ✕
                      </button>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* Optimize CTA */}
        <button
          type="button"
          disabled={loading}
          onClick={() => {
            setSelectedParetoId(null)
            onRunOptimize()
          }}
          className="flex w-full items-center justify-center gap-2 rounded-xl bg-[#0B5D42] px-4 py-3 text-sm font-bold text-white shadow-sm transition hover:bg-[#094934] disabled:opacity-60"
        >
          <Play className="h-4 w-4" />
          {loading ? t.optimizing : t.optimize_cta}
        </button>
      </aside>

      {/* Right Analytics Canvas */}
      <section className="space-y-5 md:col-span-8 xl:col-span-9">
        {/* Infeasible Diagnostic Alert */}
        {result && !result.feasible && (
          <div className="rounded-2xl border border-[#C2410C] bg-[#FFEDD5] p-4 text-[#7C2D12]">
            <div className="flex items-start gap-2.5">
              <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-[#C2410C]" />
              <div>
                <div className="text-sm font-bold">
                  {lang === 'bn' ? result.message_bn : result.message_en}
                </div>
                <p className="mt-1 text-xs">
                  {lang === 'bn' ? result.diagnostic_hint_bn : result.diagnostic_hint_en}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Row 1: 4 Verified KPI Cards */}
        {score && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-2xl border border-[#DCE5DF] bg-white p-4 shadow-xs">
              <div className="text-xs font-medium text-[#3D554B]">{t.kpi_cost}</div>
              <div className="mt-1 text-2xl font-bold text-[#0F231B]">
                ৳ {bnNum(score.cost_per_20g_protein_bdt.toFixed(2), lang)}
              </div>
              {chicken && (
                <span className="mt-2 inline-block rounded-full bg-[#E3F4EC] px-2.5 py-0.5 text-[11px] font-semibold text-[#0B5D42]">
                  ▼ {bnNum(Math.abs(chicken.cost_change_pct).toFixed(1), lang)}%{' '}
                  {lang === 'bn' ? 'মুরগির চেয়ে কম' : 'vs Chicken'}
                </span>
              )}
            </div>

            <div className="rounded-2xl border border-[#DCE5DF] bg-white p-4 shadow-xs">
              <div className="text-xs font-medium text-[#3D554B]">{t.kpi_co2}</div>
              <div className="mt-1 text-2xl font-bold text-[#0F231B]">
                {bnNum(score.co2e_per_20g_protein_g.toFixed(0), lang)}{' '}
                <span className="text-base font-medium">{lang === 'bn' ? 'গ্রাম CO₂e' : 'g CO₂e'}</span>
              </div>
              {chicken && beef && (
                <span className="mt-2 inline-block rounded-full bg-[#E3F4EC] px-2.5 py-0.5 text-[11px] font-semibold text-[#0B5D42]">
                  ▼ {bnNum(Math.abs(chicken.co2e_change_pct).toFixed(0), lang)}%{' '}
                  {lang === 'bn' ? 'মুরগি' : 'Chkn'} · ▼{' '}
                  {bnNum(Math.abs(beef.co2e_change_pct).toFixed(0), lang)}%{' '}
                  {lang === 'bn' ? 'গরু' : 'Beef'}
                </span>
              )}
            </div>

            <div className="rounded-2xl border border-[#DCE5DF] bg-white p-4 shadow-xs">
              <div className="text-xs font-medium text-[#3D554B]">
                {t.kpi_quality} ({score.standard === 'fao_2013_diaas' ? 'FAO DIAAS' : 'PDCAAS'})
              </div>
              <div className="mt-1 text-2xl font-bold text-[#0F231B]">
                {bnNum(score.active_quality_score.toFixed(2), lang)}{' '}
                <span className="text-sm font-semibold text-[#0D9488]">
                  ({score.is_complete_protein
                    ? lang === 'bn'
                      ? 'সম্পূর্ণ'
                      : 'Complete'
                    : lang === 'bn'
                      ? 'আংশিক'
                      : 'Partial'}
                  )
                </span>
              </div>
              {lentil && (
                <span className="mt-2 inline-block rounded-full bg-[#E0F5F3] px-2.5 py-0.5 text-[11px] font-semibold text-[#0D9488]">
                  ▲ {bnNum(Math.max(0, lentil.quality_change_pct).toFixed(0), lang)}%{' '}
                  {lang === 'bn' ? 'শুধু মসুরের চেয়ে' : 'vs Lentil'}
                </span>
              )}
            </div>

            <div className="rounded-2xl border border-[#DCE5DF] bg-white p-4 shadow-xs">
              <div className="text-xs font-medium text-[#3D554B]">{t.kpi_palatability}</div>
              <div className="mt-1 text-2xl font-bold text-[#0F231B]">
                {sensory ? bnNum(sensory.overall_palatability_index.toFixed(0), lang) : '—'} /{' '}
                {bnNum(100, lang)}
              </div>
              {sensory && (
                <span className="mt-2 inline-block rounded-full bg-[#E0F5F3] px-2.5 py-0.5 text-[11px] font-semibold text-[#0D9488]">
                  {lang === 'bn'
                    ? `হেক্সানাল ঝুঁকি: ${bnNum(sensory.beany_off_note_risk_pct.toFixed(0), lang)}%`
                    : `Beany risk: ${sensory.beany_off_note_risk_pct.toFixed(0)}%`}
                </span>
              )}
            </div>
          </div>
        )}

        {/* Row 2: Dark-Lab Pareto Scatter Plot + 9-EAA Chart */}
        {score && (
          <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
            {/* Dark-Lab Pareto Frontier */}
            <div className="rounded-2xl bg-[#0D1F18] p-5 text-white shadow-sm">
              <div className="mb-3 flex flex-wrap items-start justify-between gap-2">
                <div>
                  <h3 className="text-base font-bold">{t.pareto_title}</h3>
                  <p className="text-xs text-[#9BB7AA]">{t.pareto_sub}</p>
                </div>
                <span className="rounded-full bg-[#0D9488]/25 px-2.5 py-1 text-[11px] font-semibold text-[#5EEAD4]">
                  {bnNum(paretoData.length, lang)}{' '}
                  {lang === 'bn' ? 'টি অপ্টিমাল ব্লেন্ড' : 'Pareto blends'}
                </span>
              </div>

              <div className="h-56 w-full rounded-xl bg-[#132A21] p-2">
                <ResponsiveContainer width="100%" height="100%">
                  <ScatterChart margin={{ top: 12, right: 16, bottom: 8, left: 0 }}>
                    <CartesianGrid stroke="#1E3B2F" strokeDasharray="4 4" />
                    <XAxis
                      type="number"
                      dataKey="x"
                      name={lang === 'bn' ? 'খরচ (৳)' : 'Cost (BDT)'}
                      stroke="#9BB7AA"
                      fontSize={11}
                      tickFormatter={(v) => `৳${v}`}
                    />
                    <YAxis
                      type="number"
                      dataKey="y"
                      name="CO₂e (g)"
                      stroke="#9BB7AA"
                      fontSize={11}
                      tickFormatter={(v) => `${v}g`}
                    />
                    <ZAxis type="number" dataKey="z" range={[70, 170]} />
                    <Tooltip
                      cursor={{ strokeDasharray: '3 3', stroke: '#5EEAD4' }}
                      content={({ active, payload }) => {
                        if (!active || !payload?.length) return null
                        const item = payload[0].payload as { point: ParetoPoint }
                        const pt = item.point
                        return (
                          <div className="rounded-xl border border-[#2DD4BF]/40 bg-[#0D1F18] p-2.5 text-xs text-white shadow-lg">
                            <div className="font-bold text-[#5EEAD4]">
                              {lang === 'bn' ? pt.label_bn : pt.label_en}
                            </div>
                            <div className="font-mono-tech mt-1 text-[11px]">
                              ৳{pt.cost_bdt.toFixed(2)} · {pt.co2e_g.toFixed(0)}g CO₂e · Score{' '}
                              {pt.quality_score.toFixed(2)}
                            </div>
                            <div className="mt-1 text-[10px] text-[#9BB7AA]">
                              {lang === 'bn' ? 'ক্লিক করে লোড করুন' : 'Click dot to load blend'}
                            </div>
                          </div>
                        )
                      }}
                    />
                    <Scatter
                      data={paretoData}
                      onClick={(d) => {
                        if (d && d.point) {
                          setSelectedParetoId(d.point.id)
                          onSelectParetoPoint(d.point)
                        }
                      }}
                    >
                      {paretoData.map((entry) => {
                        const isSel = entry.point.id === activeParetoId
                        return (
                          <Cell
                            key={entry.point.id}
                            cursor="pointer"
                            fill={isSel ? '#34D399' : '#2DD4BF'}
                            stroke={isSel ? '#FFFFFF' : '#0D1F18'}
                            strokeWidth={isSel ? 2.5 : 1}
                          />
                        )
                      })}
                    </Scatter>
                  </ScatterChart>
                </ResponsiveContainer>
              </div>

              <div className="mt-3 flex flex-wrap items-center gap-3 text-[11px] text-[#CBE2D6]">
                <span className="flex items-center gap-1.5">
                  <span className="h-2.5 w-2.5 rounded-full bg-[#34D399]" />
                  {lang === 'bn' ? 'নির্বাচিত / ব্যালান্সড' : 'Selected / Knee Optimal'}
                </span>
                {chicken && (
                  <span className="text-[#FDBA74]">
                    ● {lang === 'bn' ? 'মুরগি:' : 'Chicken:'} ৳{bnNum(chicken.cost_bdt.toFixed(1), lang)} ·{' '}
                    {bnNum(chicken.co2e_g.toFixed(0), lang)}g CO₂e
                  </span>
                )}
              </div>
            </div>

            {/* 9 Essential Amino Acids Bar Chart */}
            <div className="rounded-2xl border border-[#DCE5DF] bg-white p-5 shadow-xs">
              <div className="mb-3 flex flex-wrap items-start justify-between gap-2">
                <div>
                  <h3 className="text-base font-bold text-[#0F231B]">{t.eaa_title}</h3>
                  <p className="text-xs text-[#6B8077]">{t.eaa_sub}</p>
                </div>
                <span className="rounded-full bg-[#E0F5F3] px-2.5 py-1 text-[11px] font-semibold text-[#0D9488]">
                  {lang === 'bn' ? 'সীমাবদ্ধ: ' : 'Limiting: '}
                  {score.amino_acids.find((a) => a.is_limiting)?.short_label} ·{' '}
                  {bnNum(
                    (score.amino_acids.find((a) => a.is_limiting)?.sufficiency_pct ?? 0).toFixed(0),
                    lang
                  )}
                  %
                </span>
              </div>

              <div className="h-56 w-full rounded-xl bg-[#F5F7F5] p-2">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={score.amino_acids}
                    margin={{ top: 14, right: 12, left: -16, bottom: 4 }}
                  >
                    <CartesianGrid stroke="#DCE5DF" strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="short_label" fontSize={11} stroke="#3D554B" />
                    <YAxis fontSize={11} stroke="#6B8077" domain={[0, 'dataMax + 20']} />
                    <ReferenceLine y={100} stroke="#0D9488" strokeDasharray="4 4" strokeWidth={1.5} />
                    <Tooltip
                      formatter={(val: number) => [`${val.toFixed(1)}%`, lang === 'bn' ? 'পূর্ণতা' : 'Sufficiency']}
                    />
                    <Bar dataKey="sufficiency_pct" radius={[6, 6, 0, 0]}>
                      {score.amino_acids.map((aa) => (
                        <Cell
                          key={aa.code}
                          fill={aa.is_limiting ? '#0D9488' : '#0B5D42'}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <div className="mt-2.5 flex items-center gap-1.5 text-xs font-medium text-[#0B5D42]">
                <CheckCircle2 className="h-4 w-4 shrink-0" />
                <span>
                  {score.is_complete_protein
                    ? lang === 'bn'
                      ? 'সব ৯টি অত্যাবশ্যকীয় অ্যামিনো অ্যাসিড ১০০% পূর্ণ করেছে।'
                      : 'All 9 essential amino acids meet or exceed the 100% completeness threshold.'
                    : lang === 'bn'
                      ? 'সীমাবদ্ধ অ্যামিনো অ্যাসিড ১০০%-এর নিচে (আংশিক প্রোটিন)।'
                      : 'Limiting amino acid below 100% threshold.'}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Row 3: Ingredient Sheet + Baseline Comparisons */}
        {score && (
          <div className="grid grid-cols-1 gap-5 xl:grid-cols-12">
            {/* Ingredient Sheet */}
            <div className="rounded-2xl border border-[#DCE5DF] bg-white p-5 shadow-xs xl:col-span-7">
              <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                <h3 className="text-sm font-bold text-[#0F231B]">
                  {t.ing_table_title} ({bnNum(score.total_mass_g.toFixed(1), lang)}{' '}
                  {lang === 'bn' ? 'গ্রাম = ২০g প্রোটিন' : 'g = 20g protein'})
                </h3>
                <div className="flex items-center gap-2 text-[11px] font-semibold">
                  <span className="text-[#0B5D42]">
                    {lang === 'bn'
                      ? `ফাইবার ${bnNum(score.fiber_g.toFixed(1), lang)}g · আয়রন ${bnNum(score.iron_mg.toFixed(1), lang)}mg`
                      : `Fiber ${score.fiber_g.toFixed(1)}g · Iron ${score.iron_mg.toFixed(1)}mg`}
                  </span>
                </div>
              </div>

              {score.has_unverified_inputs && (
                <div className="mb-3 flex items-center gap-2 rounded-xl border border-[#B45309]/30 bg-[#FEF3C7] px-3 py-2 text-[11px] text-[#92400E]">
                  <Sparkles className="h-4 w-4 shrink-0" />
                  <span>
                    {lang === 'bn'
                      ? `স্বচ্ছতা সতর্কতা: ${score.unverified_ingredients.join(', ')}-এর শুকনো দর/LCA আনুমানিক প্রক্সি।`
                      : `Transparency notice: dry-price/LCA estimates used for ${score.unverified_ingredients.join(', ')}.`}
                  </span>
                </div>
              )}

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="rounded-lg bg-[#EEF3EF] text-[#3D554B]">
                      <th className="rounded-l-lg px-3 py-2 font-semibold">{t.col_ing}</th>
                      <th className="px-2 py-2 font-semibold">{t.col_grams}</th>
                      <th className="px-2 py-2 font-semibold">{t.col_protein}</th>
                      <th className="px-2 py-2 font-semibold">{t.col_cost}</th>
                      <th className="rounded-r-lg px-2 py-2 text-right font-semibold">
                        {t.col_status}
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#DCE5DF]">
                    {score.items.map((item) => (
                      <tr key={item.id} className="hover:bg-[#F5F7F5]/60">
                        <td className="px-3 py-2.5 font-semibold text-[#0F231B]">
                          {lang === 'bn' ? item.name_bn : item.name}
                          <span className="ml-1.5 text-[10px] font-normal text-[#6B8077]">
                            ({bnNum(item.mass_share_pct.toFixed(0), lang)}%)
                          </span>
                        </td>
                        <td className="px-2 py-2.5 text-[#3D554B]">
                          {bnNum(item.grams.toFixed(1), lang)} {lang === 'bn' ? 'গ্রা.' : 'g'}
                        </td>
                        <td className="px-2 py-2.5 font-medium text-[#0D9488]">
                          {bnNum(item.protein_g.toFixed(1), lang)} {lang === 'bn' ? 'গ্রা.' : 'g'}
                        </td>
                        <td className="px-2 py-2.5 font-bold text-[#0F231B]">
                          ৳ {bnNum(item.cost_bdt.toFixed(2), lang)}
                        </td>
                        <td className="px-2 py-2.5 text-right">
                          <span
                            className={`inline-block rounded-full px-2 py-0.5 text-[10px] font-bold ${
                              item.verified
                                ? 'bg-[#E3F4EC] text-[#0B5D42]'
                                : 'bg-[#FEF3C7] text-[#B45309]'
                            }`}
                          >
                            {item.verified ? t.verified_ok : t.proxy_warn}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Baseline Comparisons */}
            <div className="rounded-2xl border border-[#DCE5DF] bg-white p-5 shadow-xs xl:col-span-5">
              <h3 className="text-sm font-bold text-[#0F231B]">{t.baseline_title}</h3>
              <p className="mb-3 text-[11px] text-[#6B8077]">{t.baseline_sub}</p>

              <div className="space-y-3">
                {/* Active Blend Bar */}
                <div>
                  <div className="flex items-center justify-between text-xs font-semibold">
                    <span className="text-[#0B5D42]">
                      {lang === 'bn' ? 'সম্পূর্ণা ব্লেন্ড (আমাদের সমাধান)' : 'Sampurna Optimized Blend'}
                    </span>
                    <span className="font-mono-tech text-[#0B5D42]">
                      DIAAS {score.active_quality_score.toFixed(2)}
                    </span>
                  </div>
                  <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-[#EEF3EF]">
                    <div
                      className="h-full rounded-full bg-[#0B5D42]"
                      style={{
                        width: `${Math.min(100, Math.max(10, (score.cost_per_20g_protein_bdt / 75) * 100))}%`,
                      }}
                    />
                  </div>
                  <div className="mt-0.5 text-[10px] text-[#6B8077]">
                    ৳{bnNum(score.cost_per_20g_protein_bdt.toFixed(2), lang)} ·{' '}
                    {bnNum(score.co2e_per_20g_protein_g.toFixed(0), lang)}g CO₂e
                  </div>
                </div>

                {baselines.slice(0, 5).map((b) => {
                  const barPct = Math.min(100, Math.max(12, (b.cost_bdt / 75) * 100))
                  const isAnimal = b.baseline_id !== 'red_lentil' && b.baseline_id !== 'white_rice'
                  return (
                    <div key={b.baseline_id}>
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-semibold text-[#0F231B]">
                          {lang === 'bn' ? b.name_bn : b.name}
                        </span>
                        <span className="font-bold text-[#0D9488]">
                          {b.cost_change_pct < 0
                            ? `${bnNum(b.cost_change_pct.toFixed(0), lang)}% ${lang === 'bn' ? 'খরচ' : 'cost'}`
                            : `+${bnNum(b.quality_change_pct.toFixed(0), lang)}% ${lang === 'bn' ? 'মান' : 'qual'}`}
                        </span>
                      </div>
                      <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-[#EEF3EF]">
                        <div
                          className={`h-full rounded-full ${
                            isAnimal ? 'bg-[#C2410C]' : 'bg-[#6B8077]'
                          }`}
                          style={{ width: `${barPct}%` }}
                        />
                      </div>
                      <div className="mt-0.5 text-[10px] text-[#6B8077]">
                        ৳{bnNum(b.cost_bdt.toFixed(2), lang)} ·{' '}
                        {bnNum(b.co2e_g.toFixed(0), lang)}g CO₂e · Score{' '}
                        {b.quality_score.toFixed(2)}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>
        )}
      </section>
    </div>
  )
}
