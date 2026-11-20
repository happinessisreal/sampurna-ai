import { useState } from 'react'
import { Bot, CheckCircle2, Clock, Loader2, ShieldCheck, Sparkles } from 'lucide-react'
import { COPY, bnNum } from '../i18n'
import type { FormulateAgentResponse, Lang, Preset } from '../types'

interface Props {
  lang: Lang
  presets: Preset[]
  agentResult: FormulateAgentResponse | null
  loading: boolean
  onRunAgent: (brief: string) => void
}

export function AgentCopilot({ lang, presets, agentResult, loading, onRunAgent }: Props) {
  const t = COPY[lang]
  const [brief, setBrief] = useState(
    'ঢাকার মধ্যবিত্ত পরিবারের জন্য ১৬ টাকার মধ্যে ডাল-গন্ধহীন সম্পূর্ণ প্রোটিন উদ্ভিজ্জ কিমা ও বাংলা রেসিপি তৈরি করো'
  )

  return (
    <div className="space-y-6">
      {/* Prompt Input Card */}
      <div className="rounded-2xl border border-[#DCE5DF] bg-white p-5 shadow-xs">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Bot className="h-5 w-5 text-[#0B5D42]" />
            <h2 className="text-lg font-bold text-[#0F231B]">{t.agent_title}</h2>
          </div>
          <span className="rounded-full bg-[#E3F4EC] px-3 py-1 text-[11px] font-semibold text-[#0B5D42]">
            {t.verified_badge}
          </span>
        </div>

        <div className="flex flex-col gap-3 sm:flex-row">
          <input
            type="text"
            value={brief}
            onChange={(e) => setBrief(e.target.value)}
            placeholder={
              lang === 'bn'
                ? 'বাংলা বা ইংরেজিতে পণ্যের চাহিদা লিখুন...'
                : 'Describe your target protein SKU, budget, or dietary goal...'
            }
            className="flex-1 rounded-xl border-2 border-[#0B5D42] bg-[#F5F7F5] px-4 py-3 text-sm text-[#0F231B] outline-none focus:bg-white"
          />
          <button
            type="button"
            disabled={loading || !brief.trim()}
            onClick={() => onRunAgent(brief)}
            className="flex items-center justify-center gap-2 rounded-xl bg-[#0B5D42] px-6 py-3 text-sm font-bold text-white shadow-sm transition hover:bg-[#094934] disabled:opacity-60"
          >
            {loading && <Loader2 className="h-4 w-4 animate-spin" />}
            {loading ? t.agent_running : t.agent_run}
          </button>
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-2">
          <span className="text-[11px] font-semibold text-[#6B8077]">
            {lang === 'bn' ? 'নমুনা প্রম্পট:' : 'Quick briefs:'}
          </span>
          {presets.map((p) => (
            <button
              key={p.id}
              type="button"
              onClick={() => {
                const text = lang === 'bn' ? p.brief_bn : p.brief_en
                setBrief(text)
                onRunAgent(text)
              }}
              className="rounded-full border border-[#DCE5DF] bg-[#F5F7F5] px-3 py-1 text-[11px] font-medium text-[#3D554B] hover:border-[#0B5D42] hover:text-[#0B5D42]"
            >
              {lang === 'bn' ? p.name_bn : p.name_en}
            </button>
          ))}
        </div>
      </div>

      {agentResult && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
          {/* Left: 4-Agent Execution Trace */}
          <div className="space-y-3 lg:col-span-5">
            <div className="flex items-center justify-between text-xs text-[#6B8077]">
              <span className="font-semibold text-[#0F231B]">
                {lang === 'bn' ? 'লাইভ এজেন্ট এক্সিকিউশন ট্রেস' : 'Live 4-Agent Execution Trace'}
              </span>
              <span className="font-mono-tech">{agentResult.ai_provider}</span>
            </div>

            {agentResult.agent_trace.map((step) => (
              <div
                key={step.step}
                className="rounded-2xl border border-[#DCE5DF] bg-white p-4 shadow-xs"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-sm font-bold text-[#0F231B]">
                    {lang === 'bn' ? step.agent_name_bn : step.agent_name_en}
                  </span>
                  <span className="font-mono-tech inline-flex items-center gap-1 rounded-full bg-[#E3F4EC] px-2.5 py-0.5 text-[10px] font-bold text-[#0B5D42]">
                    <Clock className="h-3 w-3" />
                    {bnNum(step.latency_ms, lang)}ms · {step.status}
                  </span>
                </div>
                <p className="mt-1.5 text-xs text-[#3D554B]">
                  {lang === 'bn' ? step.summary_bn : step.summary_en}
                </p>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {step.tools_called.map((tool) => (
                    <span
                      key={tool}
                      className="font-mono-tech rounded bg-[#EEF3EF] px-2 py-0.5 text-[10px] text-[#3D554B]"
                    >
                      {tool}()
                    </span>
                  ))}
                  {step.cited_dois.map((doi) => (
                    <a
                      key={doi}
                      href={`https://doi.org/${doi}`}
                      target="_blank"
                      rel="noreferrer"
                      className="font-mono-tech rounded bg-[#E0F5F3] px-2 py-0.5 text-[10px] font-semibold text-[#0D9488] hover:underline"
                    >
                      DOI:{doi}
                    </a>
                  ))}
                </div>
              </div>
            ))}

            {/* Audit Box */}
            <div className="rounded-2xl border border-[#0B5D42]/30 bg-[#E3F4EC]/70 p-4">
              <div className="flex items-center gap-2 text-xs font-bold text-[#0B5D42]">
                <ShieldCheck className="h-4 w-4" />
                {lang === 'bn'
                  ? 'রেসপনসিবল-AI অডিটর রিপোর্ট'
                  : 'Responsible-AI Auditor Verification'}
              </div>
              <ul className="mt-2 space-y-1 text-xs text-[#0F231B]">
                {(lang === 'bn' ? agentResult.audit_notes_bn : agentResult.audit_notes_en).map(
                  (note, i) => (
                    <li key={i} className="flex items-start gap-1.5">
                      <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#0B5D42]" />
                      <span>{note}</span>
                    </li>
                  )
                )}
              </ul>
            </div>
          </div>

          {/* Right: Strict Epistemic Split (Computed Recipe vs AI Hypotheses) */}
          <div className="space-y-5 lg:col-span-7">
            {/* Verified Formulation & Recipe */}
            <div className="rounded-2xl border-2 border-[#0B5D42] bg-white p-5 shadow-xs">
              <div className="mb-3 flex flex-wrap items-start justify-between gap-2">
                <div>
                  <span className="rounded-full bg-[#E3F4EC] px-2.5 py-0.5 text-[10px] font-bold text-[#0B5D42]">
                    {lang === 'bn'
                      ? 'গণিত লকড · SciPy LP গ্রাম ওজন অপরিবর্তিত'
                      : 'MATH-LOCKED · Exact SciPy LP Gram Weights'}
                  </span>
                  <h3 className="mt-2 text-lg font-bold text-[#0B5D42]">
                    {lang === 'bn' ? agentResult.product_name_bn : agentResult.product_name_en}
                  </h3>
                  <p className="text-xs text-[#3D554B]">
                    {lang === 'bn' ? agentResult.product_format_bn : agentResult.product_format_en} ·{' '}
                    {lang === 'bn'
                      ? agentResult.target_customer_bn
                      : agentResult.target_customer_en}
                  </p>
                </div>
                <div className="rounded-xl bg-[#F5F7F5] px-3 py-2 text-right text-xs">
                  <div className="font-bold text-[#0F231B]">
                    ৳ {bnNum(agentResult.score.cost_per_20g_protein_bdt.toFixed(2), lang)} ·{' '}
                    {bnNum(agentResult.score.co2e_per_20g_protein_g.toFixed(0), lang)}g CO₂e
                  </div>
                  <div className="font-mono-tech text-[11px] text-[#0D9488]">
                    Score {agentResult.score.active_quality_score.toFixed(2)} (
                    {agentResult.score.total_mass_g.toFixed(1)}g)
                  </div>
                </div>
              </div>

              <div className="mb-4 rounded-xl bg-[#F5F7F5] p-3 text-xs text-[#3D554B]">
                <strong className="text-[#0F231B]">
                  {lang === 'bn' ? 'মলিকুলার সারসংক্ষেপ: ' : 'Molecular Summary: '}
                </strong>
                {lang === 'bn' ? agentResult.molecular_summary_bn : agentResult.molecular_summary_en}
              </div>

              <h4 className="mb-2 text-sm font-bold text-[#0F231B]">{t.recipe_title}</h4>
              <ol className="space-y-2 text-xs text-[#0F231B]">
                {(lang === 'bn' ? agentResult.recipe_steps_bn : agentResult.recipe_steps_en).map(
                  (step, idx) => (
                    <li key={idx} className="flex gap-2 rounded-lg bg-[#F5F7F5]/60 px-3 py-2">
                      <span className="font-bold text-[#0B5D42]">{bnNum(idx + 1, lang)}.</span>
                      <span>{step}</span>
                    </li>
                  )
                )}
              </ol>

              <div className="mt-4 rounded-xl border border-[#DCE5DF] bg-[#EEF3EF]/60 p-3 text-xs text-[#3D554B]">
                <strong className="text-[#0F231B]">
                  {lang === 'bn' ? 'কারখানা প্রসেস (১,০০০ কেজি): ' : 'Industrial Process (1,000 kg): '}
                </strong>
                {lang === 'bn'
                  ? agentResult.industrial_process_bn
                  : agentResult.industrial_process_en}
              </div>
            </div>

            {/* Amber Epistemic Box: AI Hypotheses to Test */}
            <div className="rounded-2xl border-2 border-[#B45309] bg-[#FEF3C7]/70 p-5">
              <div className="mb-2 flex items-center justify-between gap-2">
                <h3 className="flex items-center gap-2 text-sm font-bold text-[#B45309]">
                  <Sparkles className="h-4 w-4" />
                  {t.hypo_title}
                </h3>
                <span className="rounded-full bg-[#B45309] px-2.5 py-0.5 text-[10px] font-bold text-white">
                  {lang === 'bn' ? 'AI হাইপোথিসিস' : 'AI HYPOTHESIS'}
                </span>
              </div>
              <ul className="space-y-1.5 text-xs text-[#78350F]">
                {(lang === 'bn'
                  ? agentResult.hypotheses_to_test_bn
                  : agentResult.hypotheses_to_test_en
                ).map((h, i) => (
                  <li key={i}>• {h}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
