import { useEffect, useState } from 'react'
import { Download, Factory, FileText, Printer } from 'lucide-react'
import { api } from '../api'
import { COPY, bnNum } from '../i18n'
import type { EconomicsRequest, Lang, OptimizeResponse } from '../types'

interface Props {
  lang: Lang
  result: OptimizeResponse | null
  economicsReq: EconomicsRequest
  setEconomicsReq: (next: EconomicsRequest) => void
  onRecalculateEconomics: (next: EconomicsRequest) => void
}

export function EconomicsReport({
  lang,
  result,
  economicsReq,
  setEconomicsReq,
  onRecalculateEconomics,
}: Props) {
  const t = COPY[lang]
  const econ = result?.economics
  const score = result?.score
  const [markdown, setMarkdown] = useState('')
  const [loadingMd, setLoadingMd] = useState(false)

  useEffect(() => {
    if (!score || !result?.grams_by_id) return
    let cancelled = false
    setLoadingMd(true)
    api
      .reportMarkdown({
        product_name:
          lang === 'bn' ? 'ঢাকা সম্পূর্ণা প্রোটিন ব্লেন্ড' : 'Dhaka Sampurna Protein Blend',
        product_format: 'Dry-mix / Hydrated plant-fungal formulation',
        target_customer: 'Dhaka households & RMG factory canteens',
        grams_by_id: result.grams_by_id,
        standard: score.standard,
        price_tier: score.price_tier,
        price_overrides: {},
        economics: economicsReq,
      })
      .then((res) => {
        if (!cancelled) setMarkdown(res.markdown)
      })
      .finally(() => {
        if (!cancelled) setLoadingMd(false)
      })
    return () => {
      cancelled = true
    }
  }, [score, result?.grams_by_id, economicsReq, lang])

  const updateSlider = (patch: Partial<EconomicsRequest>) => {
    const next = { ...economicsReq, ...patch }
    setEconomicsReq(next)
    onRecalculateEconomics(next)
  }

  const downloadMd = () => {
    const blob = new Blob([markdown], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'SAMPURNA_IMPACT_REPORT.md'
    a.click()
    URL.revokeObjectURL(url)
  }

  if (!econ || !score) {
    return (
      <div className="rounded-2xl border border-[#DCE5DF] bg-white p-8 text-center text-sm text-[#3D554B]">
        {lang === 'bn'
          ? 'প্রথমে ফর্মুলেশন ল্যাব থেকে একটি ব্লেন্ড তৈরি করুন।'
          : 'Optimize a formulation first to simulate factory economics.'}
      </div>
    )
  }

  const bdtCrore = econ.annual_bdt_saved_vs_chicken / 10_000_000

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
      {/* Left: Factory & RMG Canteen Scale Simulator + B2B GTM */}
      <section className="space-y-5 lg:col-span-6">
        <div className="rounded-2xl border border-[#DCE5DF] bg-white p-5 shadow-xs">
          <div className="mb-4 flex flex-wrap items-start justify-between gap-2">
            <div>
              <h2 className="flex items-center gap-2 text-base font-bold text-[#0F231B]">
                <Factory className="h-4 w-4 text-[#0B5D42]" />
                {t.econ_title}
              </h2>
              <p className="text-xs text-[#6B8077]">{t.econ_sub}</p>
            </div>
            <span className="rounded-full bg-[#E3F4EC] px-2.5 py-1 text-[10px] font-bold text-[#0B5D42]">
              VERIFIED COMPUTED
            </span>
          </div>

          {/* 3 Mini Slider Cards */}
          <div className="mb-5 grid grid-cols-1 gap-3 sm:grid-cols-3">
            <div className="rounded-xl border border-[#DCE5DF] bg-[#F5F7F5] p-3">
              <div className="text-[11px] font-semibold text-[#3D554B]">
                {lang === 'bn' ? 'দৈনিক সার্ভিং (RMG)' : 'Daily RMG Servings'}
              </div>
              <div className="mt-0.5 text-sm font-bold text-[#0B5D42]">
                {bnNum(economicsReq.daily_servings.toLocaleString(), lang)}{' '}
                {lang === 'bn' ? 'জন' : 'ppl'}
              </div>
              <input
                type="range"
                min={1000}
                max={50000}
                step={1000}
                value={economicsReq.daily_servings}
                onChange={(e) => updateSlider({ daily_servings: parseInt(e.target.value, 10) })}
                className="mt-2 w-full accent-[#0B5D42]"
              />
            </div>

            <div className="rounded-xl border border-[#DCE5DF] bg-[#F5F7F5] p-3">
              <div className="text-[11px] font-semibold text-[#3D554B]">
                {lang === 'bn' ? 'প্রসেসিং ও প্যাকিং' : 'Processing + Pack'}
              </div>
              <div className="mt-0.5 text-sm font-bold text-[#0B5D42]">
                ৳ {bnNum(economicsReq.processing_packaging_bdt_per_kg, lang)} /{' '}
                {lang === 'bn' ? 'কেজি' : 'kg'}
              </div>
              <input
                type="range"
                min={5}
                max={60}
                step={1}
                value={economicsReq.processing_packaging_bdt_per_kg}
                onChange={(e) =>
                  updateSlider({ processing_packaging_bdt_per_kg: parseFloat(e.target.value) })
                }
                className="mt-2 w-full accent-[#0B5D42]"
              />
            </div>

            <div className="rounded-xl border border-[#DCE5DF] bg-[#F5F7F5] p-3">
              <div className="text-[11px] font-semibold text-[#3D554B]">
                {lang === 'bn' ? 'B2B পাইকারি দাম' : 'B2B Wholesale Price'}
              </div>
              <div className="mt-0.5 text-sm font-bold text-[#0B5D42]">
                ৳ {bnNum(economicsReq.wholesale_price_bdt_per_kg, lang)} /{' '}
                {lang === 'bn' ? 'কেজি' : 'kg'}
              </div>
              <input
                type="range"
                min={160}
                max={450}
                step={5}
                value={economicsReq.wholesale_price_bdt_per_kg}
                onChange={(e) =>
                  updateSlider({ wholesale_price_bdt_per_kg: parseFloat(e.target.value) })
                }
                className="mt-2 w-full accent-[#0B5D42]"
              />
            </div>
          </div>

          {/* 3 Economics KPI Cards */}
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <div className="rounded-xl border border-[#DCE5DF] bg-white p-3.5">
              <div className="text-[11px] text-[#3D554B]">
                {lang === 'bn' ? 'ব্যাচ খরচ (১,০০০ কেজি)' : '1,000 kg Batch Cost'}
              </div>
              <div className="mt-1 text-xl font-bold text-[#0F231B]">
                ৳ {bnNum(Math.round(econ.batch_total_cost_bdt).toLocaleString(), lang)}
              </div>
              <span className="mt-2 inline-block rounded-full bg-[#E3F4EC] px-2 py-0.5 text-[10px] font-bold text-[#0B5D42]">
                {lang === 'bn' ? 'মার্জিন: ' : 'Margin: '}
                {bnNum(econ.gross_margin_pct.toFixed(1), lang)}%
              </span>
            </div>

            <div className="rounded-xl border border-[#DCE5DF] bg-white p-3.5">
              <div className="text-[11px] text-[#3D554B]">
                {lang === 'bn' ? 'বার্ষিক ক্যান্টিন সাশ্রয়' : 'Annual Savings vs Chicken'}
              </div>
              <div className="mt-1 text-xl font-bold text-[#0F231B]">
                {lang === 'bn'
                  ? `৳ ${bnNum(bdtCrore.toFixed(2), lang)} কোটি`
                  : `BDT ${(econ.annual_bdt_saved_vs_chicken / 1_000_000).toFixed(1)}M`}
              </div>
              <span className="mt-2 inline-block rounded-full bg-[#E3F4EC] px-2 py-0.5 text-[10px] font-bold text-[#0B5D42]">
                {bnNum(economicsReq.daily_servings.toLocaleString(), lang)} ×{' '}
                {bnNum(economicsReq.operating_days_per_year, lang)}d
              </span>
            </div>

            <div className="rounded-xl border border-[#DCE5DF] bg-white p-3.5">
              <div className="text-[11px] text-[#3D554B]">
                {lang === 'bn' ? 'বার্ষিক কার্বন হ্রাস' : 'Annual CO₂e Avoided'}
              </div>
              <div className="mt-1 text-xl font-bold text-[#0F231B]">
                {bnNum(Math.round(econ.annual_co2e_avoided_tonnes_vs_chicken).toLocaleString(), lang)}{' '}
                {lang === 'bn' ? 'টন' : 't CO₂e'}
              </div>
              <span className="mt-2 inline-block rounded-full bg-[#E0F5F3] px-2 py-0.5 text-[10px] font-bold text-[#0D9488]">
                ≈ {bnNum(econ.equivalent_cars_removed, lang)}{' '}
                {lang === 'bn' ? 'টি গাড়ি সমতুল্য' : 'cars off road'}
              </span>
            </div>
          </div>
        </div>

        {/* B2B Commercialization Roadmap */}
        <div className="rounded-2xl border border-[#DCE5DF] bg-white p-5 shadow-xs">
          <h3 className="mb-3 text-sm font-bold text-[#0F231B]">
            {lang === 'bn'
              ? 'বাণিজ্যিক রোডম্যাপ ও বৈশ্বিক স্কেল (Business Model & Global Readiness)'
              : 'Commercialization & Global Readiness Model'}
          </h3>
          <div className="space-y-2.5 text-xs">
            {[
              {
                t_bn: '১. B2B R&D SaaS ও API কোপাইলট',
                t_en: '1. B2B R&D Formulation SaaS & MCP API',
                s_bn: 'PRAN, ACI, Kazi Farms ও গ্লোবাল ফুড ব্র্যান্ড',
                s_en: 'Local CPGs (PRAN, ACI) & global alt-protein startups',
                r_bn: '৳ ৭৫,০০০ / মাস + এন্টারপ্রাইজ API',
                r_en: '$750/mo + Usage Licensing',
              },
              {
                t_bn: '২. প্রাতিষ্ঠানিক প্রিমিক্স (RMG ক্যান্টিন ও NGO)',
                t_en: '2. Institutional Premix (4M RMG Workers & WFP)',
                s_bn: '৪০ লক্ষ গার্মেন্টস কর্মী ক্যান্টিন ও পুষ্টি কর্মসূচি',
                s_en: 'Factory canteens, BRAC, WFP emergency nutrition',
                r_bn: `৳ ${bnNum(economicsReq.wholesale_price_bdt_per_kg, lang)} / কেজি (${bnNum(econ.gross_margin_pct.toFixed(0), lang)}% মার্জিন)`,
                r_en: `BDT ${economicsReq.wholesale_price_bdt_per_kg}/kg (${econ.gross_margin_pct.toFixed(0)}% margin)`,
              },
              {
                t_bn: '৩. হালাল রপ্তানি অল্ট-প্রোটিন লাইসেন্সিং',
                t_en: '3. Global Halal Alt-Protein IP Licensing',
                s_bn: 'মধ্যপ্রাচ্য, মালয়েশিয়া ও প্রবাসী বাজার',
                s_en: 'MENA, ASEAN & NRB diaspora retail export',
                r_bn: 'ফর্মুলেশন লাইসেন্সিং + ৩–৫% রয়্যালটি',
                r_en: 'Formulation IP + 3–5% Royalty',
              },
            ].map((row) => (
              <div
                key={row.t_en}
                className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-[#DCE5DF] bg-[#F5F7F5] px-3.5 py-2.5"
              >
                <div>
                  <div className="font-bold text-[#0F231B]">
                    {lang === 'bn' ? row.t_bn : row.t_en}
                  </div>
                  <div className="text-[11px] text-[#3D554B]">
                    {lang === 'bn' ? row.s_bn : row.s_en}
                  </div>
                </div>
                <div className="font-bold text-[#0B5D42]">
                  {lang === 'bn' ? row.r_bn : row.r_en}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Right: Rendered Impact Report + Download */}
      <section className="lg:col-span-6">
        <div className="rounded-2xl border border-[#DCE5DF] bg-white p-5 shadow-xs">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-[#0B5D42]" />
              <h3 className="text-base font-bold text-[#0F231B]">{t.report_title}</h3>
            </div>
            <div className="no-print flex items-center gap-2">
              <button
                type="button"
                onClick={downloadMd}
                disabled={!markdown}
                className="inline-flex items-center gap-1.5 rounded-xl bg-[#0B5D42] px-3.5 py-2 text-xs font-bold text-white hover:bg-[#094934] disabled:opacity-60"
              >
                <Download className="h-3.5 w-3.5" />
                {t.download_md}
              </button>
              <button
                type="button"
                onClick={() => window.print()}
                className="inline-flex items-center gap-1.5 rounded-xl border border-[#B8CAC0] bg-[#EEF3EF] px-3.5 py-2 text-xs font-bold text-[#0F231B] hover:bg-[#DCE5DF]"
              >
                <Printer className="h-3.5 w-3.5" />
                {t.print_pdf}
              </button>
            </div>
          </div>

          <pre className="font-mono-tech max-h-[600px] overflow-auto whitespace-pre-wrap rounded-xl border border-[#DCE5DF] bg-[#F5F7F5] p-4 text-[11px] leading-relaxed text-[#0F231B]">
            {loadingMd ? 'Generating deterministic report...' : markdown}
          </pre>
        </div>
      </section>
    </div>
  )
}
