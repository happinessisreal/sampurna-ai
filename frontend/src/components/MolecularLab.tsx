import { useState } from 'react'
import { ExternalLink, Eye, FlaskConical, Loader2, Sparkles, Upload } from 'lucide-react'
import { api } from '../api'
import { COPY, bnNum } from '../i18n'
import type { Lang, OptimizeResponse, VisionInspectResponse } from '../types'

interface Props {
  lang: Lang
  result: OptimizeResponse | null
}

export function MolecularLab({ lang, result }: Props) {
  const t = COPY[lang]
  const sensory = result?.sensory
  const score = result?.score

  const [sampleId, setSampleId] = useState<'keema_prototype' | 'khichuri_prototype'>('keema_prototype')
  const [vision, setVision] = useState<VisionInspectResponse | null>(null)
  const [visionLoading, setVisionLoading] = useState(false)

  const runVision = async (file?: File | null, targetSample = sampleId) => {
    setVisionLoading(true)
    try {
      const ctx = score
        ? score.items.map((i) => `${i.name} (${i.grams}g)`).join(', ')
        : 'Sampurna Plant Protein Blend'
      const res = await api.inspectVision(targetSample, ctx, file)
      setVision(res)
    } finally {
      setVisionLoading(false)
    }
  }

  if (!sensory) {
    return (
      <div className="rounded-2xl border border-[#DCE5DF] bg-white p-8 text-center text-sm text-[#3D554B]">
        {lang === 'bn'
          ? 'প্রথমে ফর্মুলেশন ল্যাব থেকে একটি ব্লেন্ড অপ্টিমাইজ করুন।'
          : 'Optimize a blend in the Formulation Lab first.'}
      </div>
    )
  }

  const traits = [
    {
      label_bn: 'পানি ধারণ ক্ষমতা (Water Holding Capacity)',
      label_en: 'Water Holding Capacity',
      val: sensory.functional_traits.water_holding,
    },
    {
      label_bn: 'ইমালসিফিকেশন ও বাইন্ডিং (Emulsification)',
      label_en: 'Emulsification & Binding',
      val: sensory.functional_traits.emulsification,
    },
    {
      label_bn: 'জেলেশন শক্তি (Gelation Network)',
      label_en: 'Gelation Network',
      val: sensory.functional_traits.gelation,
    },
    {
      label_bn: 'ফাইব্রাস স্ট্রাকচার / অ্যানাইসোট্রপি (Fibrousness)',
      label_en: 'Fibrous Structural Anisotropy',
      val: sensory.functional_traits.fibrous_anisotropy,
    },
  ]

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
      {/* Left: PubChem Flavor & Functional Chemistry */}
      <section className="space-y-5 lg:col-span-7">
        <div className="rounded-2xl border border-[#DCE5DF] bg-white p-5 shadow-xs">
          <div className="mb-4 flex flex-wrap items-start justify-between gap-2">
            <div>
              <h2 className="text-lg font-bold text-[#0F231B]">{t.mol_title}</h2>
              <p className="text-xs text-[#6B8077]">{t.mol_sub}</p>
            </div>
            <span className="inline-flex items-center gap-1.5 rounded-full bg-[#E0F5F3] px-3 py-1 text-[11px] font-semibold text-[#0D9488]">
              <FlaskConical className="h-3.5 w-3.5" />
              {t.model_badge}
            </span>
          </div>

          {/* 3 Sensory Gauges */}
          <div className="mb-5 grid grid-cols-1 gap-3 sm:grid-cols-3">
            <div className="rounded-xl bg-[#E3F4EC] p-3">
              <div className="text-[11px] font-semibold text-[#3D554B]">
                {lang === 'bn' ? 'ডাল-গন্ধ (Hexanal) ঝুঁকি' : 'Beany (Hexanal) Risk'}
              </div>
              <div className="mt-1 text-2xl font-bold text-[#0B5D42]">
                {bnNum(sensory.beany_off_note_risk_pct.toFixed(1), lang)}%
              </div>
              <div className="text-[10px] text-[#3D554B]">
                {sensory.beany_off_note_risk_pct < 30
                  ? lang === 'bn'
                    ? 'উমামি ও তাপে দমিত'
                    : 'Well masked by umami'
                  : lang === 'bn'
                    ? '৮৫°C ব্লাঞ্চিং সুপারিশকৃত'
                    : '85°C blanching advised'}
              </div>
            </div>

            <div className="rounded-xl bg-[#E0F5F3] p-3">
              <div className="text-[11px] font-semibold text-[#3D554B]">
                {lang === 'bn' ? 'উমামি সিনার্জি সূচক' : 'Umami Synergy Index'}
              </div>
              <div className="mt-1 text-2xl font-bold text-[#0D9488]">
                {bnNum(sensory.umami_synergy_score.toFixed(0), lang)} / {bnNum(100, lang)}
              </div>
              <div className="font-mono-tech text-[10px] text-[#3D554B]">
                L-Glu + 5&apos;-GMP
              </div>
            </div>

            <div className="rounded-xl bg-[#E0F5F3] p-3">
              <div className="text-[11px] font-semibold text-[#3D554B]">
                {lang === 'bn' ? 'মেইলার্ড ব্রাউনিং সম্ভাবনা' : 'Maillard Browning Potential'}
              </div>
              <div className="mt-1 text-2xl font-bold text-[#0D9488]">
                {bnNum(sensory.maillard_browning_potential.toFixed(0), lang)} / {bnNum(100, lang)}
              </div>
              <div className="font-mono-tech text-[10px] text-[#3D554B]">
                Cys + Xylose &gt;140°C
              </div>
            </div>
          </div>

          {/* PubChem Compounds List */}
          <div className="space-y-3">
            {sensory.detected_molecules.slice(0, 6).map((mol) => {
              const isOff = mol.role === 'beany_off_note'
              return (
                <div
                  key={mol.key}
                  className="rounded-xl border border-[#DCE5DF] bg-[#F5F7F5]/60 p-3.5"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span
                        className={`h-2.5 w-2.5 rounded-full ${
                          isOff ? 'bg-[#C2410C]' : 'bg-[#0B5D42]'
                        }`}
                      />
                      <span className="text-sm font-bold text-[#0F231B]">
                        {lang === 'bn' ? mol.name_bn : mol.name}
                      </span>
                      <span className="font-mono-tech rounded bg-white px-1.5 py-0.5 text-[10px] text-[#3D554B]">
                        {mol.formula}
                      </span>
                    </div>
                    <a
                      href={mol.pubchem_url}
                      target="_blank"
                      rel="noreferrer"
                      className="font-mono-tech inline-flex items-center gap-1 text-xs font-bold text-[#0D9488] hover:underline"
                    >
                      PubChem CID {mol.cid}
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  </div>
                  <p className="mt-1.5 text-xs text-[#3D554B]">
                    {lang === 'bn' ? mol.sensory_note_bn : mol.sensory_note}
                  </p>
                  <div className="mt-1.5 flex flex-wrap items-center justify-between gap-2 text-[11px] text-[#6B8077]">
                    <span>
                      {lang === 'bn' ? 'উৎস: ' : 'Sources: '}
                      {mol.source_ingredients.join(', ')}
                    </span>
                    <span className="text-[#0B5D42]">{mol.mitigation}</span>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </section>

      {/* Right: Functional Matrix + Flavor Bridges + Foundry Vision Inspector */}
      <section className="space-y-5 lg:col-span-5">
        <div className="rounded-2xl border border-[#DCE5DF] bg-white p-5 shadow-xs">
          <h3 className="mb-3 text-sm font-bold text-[#0F231B]">
            {lang === 'bn'
              ? 'ফাংশনাল প্রোটিন প্রোপার্টি (ম্যাট্রিক্স স্কোর)'
              : 'Functional Protein Matrix Traits'}
          </h3>
          <div className="space-y-3">
            {traits.map((tr) => (
              <div key={tr.label_en}>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-[#3D554B]">
                    {lang === 'bn' ? tr.label_bn : tr.label_en}
                  </span>
                  <span className="font-mono-tech font-bold text-[#0B5D42]">
                    {bnNum(tr.val.toFixed(0), lang)}%
                  </span>
                </div>
                <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-[#EEF3EF]">
                  <div
                    className="h-full rounded-full bg-[#0D9488]"
                    style={{ width: `${Math.min(100, tr.val)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>

          <div className="mt-5 space-y-2 border-t border-[#DCE5DF] pt-4">
            <h4 className="text-xs font-bold text-[#0F231B]">
              {lang === 'bn' ? 'সনাক্তকৃত ফ্লেভার-ব্রিজ ও প্রসেসিং' : 'Flavor Bridges & Mitigations'}
            </h4>
            {(lang === 'bn' ? sensory.flavor_bridges_bn : sensory.flavor_bridges_en).map((b, i) => (
              <p key={i} className="rounded-lg bg-[#E3F4EC]/70 px-3 py-2 text-xs text-[#0B5D42]">
                {b}
              </p>
            ))}
            {(lang === 'bn' ? sensory.process_mitigations_bn : sensory.process_mitigations_en).map(
              (m, i) => (
                <p key={i} className="rounded-lg bg-[#F5F7F5] px-3 py-2 text-xs text-[#3D554B]">
                  • {m}
                </p>
              )
            )}
          </div>
        </div>

        {/* Dark-Lab Foundry Claude Vision Inspector */}
        <div className="rounded-2xl bg-[#0D1F18] p-5 text-white shadow-sm">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <Eye className="h-4 w-4 text-[#5EEAD4]" />
              <h3 className="text-sm font-bold">{t.vision_title}</h3>
            </div>
            <span className="rounded-full bg-[#FEF3C7] px-2.5 py-0.5 text-[10px] font-bold text-[#B45309]">
              {t.hypo_badge}
            </span>
          </div>

          <p className="mb-3 text-xs text-[#9BB7AA]">
            {lang === 'bn'
              ? 'রান্না করা কিমা বা প্যাটি প্রোটোটাইপের ছবি আপলোড করুন অথবা নমুনা প্রোটোটাইপ পরীক্ষা করুন:'
              : 'Upload a cooked prototype photo or evaluate a built-in reference sample:'}
          </p>

          <div className="mb-3 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => {
                setSampleId('keema_prototype')
                runVision(null, 'keema_prototype')
              }}
              className="rounded-lg border border-[#2DD4BF]/40 bg-[#132A21] px-3 py-1.5 text-xs font-semibold text-[#5EEAD4] hover:bg-[#1A382C]"
            >
              {lang === 'bn' ? 'নমুনা: ঢাকা কিমা বিশ্লেষণ' : 'Test Sample: Keema'}
            </button>
            <button
              type="button"
              onClick={() => {
                setSampleId('khichuri_prototype')
                runVision(null, 'khichuri_prototype')
              }}
              className="rounded-lg border border-[#2DD4BF]/40 bg-[#132A21] px-3 py-1.5 text-xs font-semibold text-[#5EEAD4] hover:bg-[#1A382C]"
            >
              {lang === 'bn' ? 'নমুনা: খিচুড়ি প্রিমিক্স' : 'Test Sample: Khichuri'}
            </button>
            <label className="inline-flex cursor-pointer items-center gap-1.5 rounded-lg bg-[#0B5D42] px-3 py-1.5 text-xs font-bold text-white hover:bg-[#094934]">
              <Upload className="h-3.5 w-3.5" />
              {lang === 'bn' ? 'ছবি আপলোড' : 'Upload Photo'}
              <input
                type="file"
                accept="image/*"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0]
                  if (file) runVision(file)
                }}
              />
            </label>
          </div>

          {visionLoading && (
            <div className="flex items-center gap-2 py-4 text-xs text-[#5EEAD4]">
              <Loader2 className="h-4 w-4 animate-spin" />
              {lang === 'bn' ? 'ভিশন মডেল বিশ্লেষণ চলছে...' : 'Running Vision inspection...'}
            </div>
          )}

          {vision && !visionLoading && (
            <div className="space-y-2.5 rounded-xl bg-[#132A21] p-3.5 text-xs">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="font-mono-tech text-[11px] text-[#5EEAD4]">{vision.model_used}</span>
                <span className="font-mono-tech text-[11px] text-white">
                  Maillard {bnNum(vision.maillard_browning_score, lang)}/100 · Grain{' '}
                  {bnNum(vision.fibrous_grain_score, lang)}/100
                </span>
              </div>
              <p className="text-[#E2EFE8]">
                {lang === 'bn' ? vision.visual_assessment_bn : vision.visual_assessment_en}
              </p>
              <div className="space-y-1 border-t border-[#284A3C] pt-2 text-[11px] text-[#FDE68A]">
                {(lang === 'bn'
                  ? vision.formulation_adjustments_bn
                  : vision.formulation_adjustments_en
                ).map((adj, idx) => (
                  <div key={idx} className="flex items-start gap-1.5">
                    <Sparkles className="mt-0.5 h-3 w-3 shrink-0" />
                    <span>{adj}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </section>
    </div>
  )
}
