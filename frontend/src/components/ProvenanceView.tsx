import { useEffect, useState } from 'react'
import { BookOpen, Cpu, Database, ExternalLink, Search, ShieldAlert } from 'lucide-react'
import { api } from '../api'
import { COPY, bnNum } from '../i18n'
import type { Ingredient, Lang, McpManifest, RagHit } from '../types'

interface Props {
  lang: Lang
  plantIngredients: Ingredient[]
  baselines: Ingredient[]
}

export function ProvenanceView({ lang, plantIngredients, baselines }: Props) {
  const t = COPY[lang]
  const [filter, setFilter] = useState('')
  const [ragQuery, setRagQuery] = useState('hexanal beany off-flavor oyster mushroom jackfruit texture')
  const [ragHits, setRagHits] = useState<RagHit[]>([])
  const [allPapers, setAllPapers] = useState<Array<Record<string, string | null>>>([])
  const [mcp, setMcp] = useState<McpManifest | null>(null)

  useEffect(() => {
    api.papers().then((d) => setAllPapers(d.papers ?? []))
    api.papers(ragQuery).then((d) => setRagHits(d.hits ?? []))
    api.mcpManifest().then(setMcp)
  }, [])

  const runRag = () => {
    api.papers(ragQuery).then((d) => setRagHits(d.hits ?? []))
  }

  const allItems = [...plantIngredients, ...baselines].filter((item) => {
    const q = filter.toLowerCase()
    return (
      !q ||
      item.name.toLowerCase().includes(q) ||
      item.name_bn.includes(filter) ||
      item.category.toLowerCase().includes(q)
    )
  })

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        {/* Left: Dark-Lab Live MCP Server Inspector */}
        <section className="rounded-2xl bg-[#0D1F18] p-5 text-white shadow-sm lg:col-span-5">
          <div className="mb-3 flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <Cpu className="h-4 w-4 text-[#5EEAD4]" />
              <h2 className="text-base font-bold">{t.mcp_title}</h2>
            </div>
            <span className="font-mono-tech rounded-full bg-[#0D9488]/30 px-2.5 py-0.5 text-[11px] text-[#5EEAD4]">
              {mcp ? `${mcp.tool_count} Tools` : 'FastMCP'}
            </span>
          </div>

          <p className="mb-3 text-xs text-[#9BB7AA]">
            {lang === 'bn'
              ? 'বাহ্যিক AI এজেন্ট সরাসরি স্ট্যান্ডার্ড Model Context Protocol (MCP)-এর মাধ্যমে সম্পূর্ণা AI-এর অপ্টিমাইজার, কেমিস্ট্রি ও ইমপ্যাক্ট রিপোর্ট কল করতে পারে।'
              : 'External AI coding agents and enterprise copilots invoke Sampurna deterministic engines directly over standard MCP.'}
          </p>

          {mcp && (
            <div className="space-y-2">
              {mcp.tools.map((tool) => (
                <div
                  key={tool.name}
                  className="rounded-xl border border-[#2DD4BF]/30 bg-[#132A21] p-2.5"
                >
                  <div className="font-mono-tech text-xs font-bold text-[#5EEAD4]">
                    ⚡ {tool.name}({tool.args.join(', ')})
                  </div>
                  <p className="mt-1 text-[11px] text-[#CBE2D6]">{tool.description}</p>
                </div>
              ))}
              <div className="mt-3 rounded-xl bg-[#08130E] p-3">
                <div className="mb-1 text-[10px] font-bold uppercase tracking-wide text-[#9BB7AA]">
                  Claude / Cursor MCP Client Config
                </div>
                <pre className="font-mono-tech overflow-x-auto text-[10px] text-[#A7F3D0]">
                  {JSON.stringify(
                    {
                      mcpServers: {
                        'sampurna-formulation-mcp': {
                          command: 'uv',
                          args: ['run', 'python', '-m', 'backend.mcp_server'],
                        },
                      },
                    },
                    null,
                    2
                  )}
                </pre>
              </div>
            </div>
          )}
        </section>

        {/* Right: Scientific Literature RAG Search */}
        <section className="rounded-2xl border border-[#DCE5DF] bg-white p-5 shadow-xs lg:col-span-7">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <h2 className="flex items-center gap-2 text-base font-bold text-[#0F231B]">
              <BookOpen className="h-4 w-4 text-[#0B5D42]" />
              {t.rag_title}
            </h2>
            <span className="rounded-full bg-[#E3F4EC] px-2.5 py-0.5 text-[11px] font-semibold text-[#0B5D42]">
              {bnNum(allPapers.length, lang)} {lang === 'bn' ? 'টি পেপার · শূন্য প্লেসহোল্ডার' : 'Real DOIs · Zero Placeholders'}
            </span>
          </div>

          <div className="mb-4 flex gap-2">
            <input
              type="text"
              value={ragQuery}
              onChange={(e) => setRagQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && runRag()}
              className="flex-1 rounded-xl border border-[#B8CAC0] bg-[#F5F7F5] px-3 py-2 text-xs text-[#0F231B]"
            />
            <button
              type="button"
              onClick={runRag}
              className="inline-flex items-center gap-1.5 rounded-xl bg-[#0B5D42] px-4 py-2 text-xs font-bold text-white hover:bg-[#094934]"
            >
              <Search className="h-3.5 w-3.5" />
              {lang === 'bn' ? 'খুঁজুন' : 'Search'}
            </button>
          </div>

          <div className="space-y-2.5">
            {ragHits.map((hit) => (
              <div
                key={`${hit.filename}-${hit.section}`}
                className="rounded-xl border border-[#DCE5DF] bg-[#F5F7F5]/60 p-3"
              >
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="text-xs font-bold text-[#0F231B]">{hit.title}</div>
                  <span className="font-mono-tech rounded bg-[#E0F5F3] px-2 py-0.5 text-[10px] font-bold text-[#0D9488]">
                    Score {hit.score.toFixed(2)}
                  </span>
                </div>
                <div className="mt-1 flex flex-wrap items-center gap-2 text-[11px] text-[#3D554B]">
                  <span>{hit.citation}</span>
                  {hit.pmcid && <span className="font-mono-tech font-semibold">{hit.pmcid}</span>}
                  {hit.doi && (
                    <a
                      href={`https://doi.org/${hit.doi}`}
                      target="_blank"
                      rel="noreferrer"
                      className="font-mono-tech inline-flex items-center gap-1 text-[#0B5D42] hover:underline"
                    >
                      DOI:{hit.doi}
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  )}
                </div>
                <p className="mt-1.5 text-[11px] leading-relaxed text-[#3D554B]">{hit.excerpt}</p>
              </div>
            ))}
          </div>
        </section>
      </div>

      {/* Full Verified Ingredient & Baseline Provenance Table */}
      <section className="rounded-2xl border border-[#DCE5DF] bg-white p-5 shadow-xs">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="flex items-center gap-2 text-base font-bold text-[#0F231B]">
              <Database className="h-4 w-4 text-[#0B5D42]" />
              {lang === 'bn'
                ? 'সম্পূর্ণ উপাদান ও বেসলাইন ডেটাবেস (১৮টি আইটেম · সোর্স ও যাচাইকরণ)'
                : 'Complete Ingredient & Baseline Provenance Matrix (18 Curated Items)'}
            </h2>
            <p className="text-xs text-[#6B8077]">
              {lang === 'bn'
                ? 'USDA FoodData Central · FAO (2013) · Poore & Nemecek (2018) · ঢাকা TCB/খোলা বাজার (নভেম্বর ২০২৬)'
                : 'USDA FDC · FAO 2013 · Poore & Nemecek 2018 OWID · Dhaka Open Retail & TCB (Nov 2026)'}
            </p>
          </div>
          <input
            type="text"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            placeholder={lang === 'bn' ? 'উপাদান খুঁজুন...' : 'Filter ingredients...'}
            className="rounded-xl border border-[#B8CAC0] bg-[#F5F7F5] px-3 py-1.5 text-xs"
          />
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-[11px]">
            <thead>
              <tr className="bg-[#EEF3EF] text-[#3D554B]">
                <th className="px-2.5 py-2">{lang === 'bn' ? 'উপাদান' : 'Ingredient'}</th>
                <th className="px-2 py-2">{lang === 'bn' ? 'প্রোটিন/১০০g' : 'Protein %'}</th>
                <th className="px-2 py-2">{lang === 'bn' ? 'খোলা/TCB (৳/kg)' : 'Open / TCB (BDT/kg)'}</th>
                <th className="px-2 py-2">CO₂e (kg/kg)</th>
                <th className="px-2 py-2">DIAAS Factor</th>
                <th className="px-2 py-2">{lang === 'bn' ? 'পুষ্টি ও কার্বন সোর্স' : 'Citations'}</th>
                <th className="px-2 py-2 text-right">{lang === 'bn' ? 'অবস্থা' : 'Verified'}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#DCE5DF]">
              {allItems.map((ing) => (
                <tr key={ing.id} className={ing.is_baseline ? 'bg-[#FFEDD5]/25' : ''}>
                  <td className="px-2.5 py-2 font-bold text-[#0F231B]">
                    {lang === 'bn' ? ing.name_bn : ing.name}
                    {ing.is_baseline && (
                      <span className="ml-1.5 rounded bg-[#C2410C]/15 px-1.5 py-0.5 text-[9px] font-bold text-[#C2410C]">
                        BASELINE
                      </span>
                    )}
                  </td>
                  <td className="font-mono-tech px-2 py-2">{ing.protein_g_per_100g.toFixed(1)}g</td>
                  <td className="font-mono-tech px-2 py-2">
                    ৳{ing.price_bdt_per_kg_open.toFixed(0)} / ৳{ing.price_bdt_per_kg_tcb.toFixed(0)}
                  </td>
                  <td className="font-mono-tech px-2 py-2">{ing.co2e_kg_per_kg.toFixed(2)}</td>
                  <td className="font-mono-tech px-2 py-2">{ing.diaas_ileal_factor.toFixed(2)}</td>
                  <td className="px-2 py-2 text-[10px] text-[#3D554B]">
                    <div>{ing.source_nutrition}</div>
                    <div className="text-[#6B8077]">
                      {ing.source_price} · {ing.source_co2e}
                    </div>
                  </td>
                  <td className="px-2 py-2 text-right">
                    {ing.verified ? (
                      <span className="rounded-full bg-[#E3F4EC] px-2 py-0.5 text-[10px] font-bold text-[#0B5D42]">
                        VERIFIED
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 rounded-full bg-[#FEF3C7] px-2 py-0.5 text-[10px] font-bold text-[#B45309]">
                        <ShieldAlert className="h-3 w-3" />
                        ESTIMATE
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
