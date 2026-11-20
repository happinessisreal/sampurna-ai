import type {
  EconomicsRequest,
  FormulateAgentResponse,
  HealthInfo,
  Ingredient,
  McpManifest,
  OptimizeRequest,
  OptimizeResponse,
  ParetoResponse,
  Preset,
  RagHit,
  VisionInspectResponse,
} from './types'

async function jsonReq<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init)
  if (!res.ok) {
    const txt = await res.text()
    throw new Error(`HTTP ${res.status}: ${txt}`)
  }
  return (await res.json()) as T
}

export const api = {
  health: () => jsonReq<HealthInfo>('/api/health'),
  presets: () => jsonReq<Preset[]>('/api/presets'),
  ingredients: () =>
    jsonReq<{ plant_ingredients: Ingredient[]; baselines: Ingredient[] }>('/api/ingredients'),
  mcpManifest: () => jsonReq<McpManifest>('/api/mcp-manifest'),
  papers: (q?: string) =>
    jsonReq<{ papers?: Array<Record<string, string | null>>; hits?: RagHit[] }>(
      q ? `/api/papers?q=${encodeURIComponent(q)}&top_k=4` : '/api/papers'
    ),
  optimize: (req: OptimizeRequest) =>
    jsonReq<OptimizeResponse>('/api/optimize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    }),
  scoreDirect: (
    grams_by_id: Record<string, number>,
    standard: string,
    price_tier: string,
    price_overrides: Record<string, number>,
    economics: EconomicsRequest
  ) =>
    jsonReq<OptimizeResponse>('/api/score', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ grams_by_id, standard, price_tier, price_overrides, economics }),
    }),
  pareto: (req: OptimizeRequest) =>
    jsonReq<ParetoResponse>('/api/pareto', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    }),
  runAgents: (brief: string, standard: string, price_tier: string, language: string) =>
    jsonReq<FormulateAgentResponse>('/api/agent/formulate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ brief, standard, price_tier, language }),
    }),
  inspectVision: async (sampleId: string, blendContext: string, file?: File | null) => {
    const fd = new FormData()
    fd.append('sample_id', sampleId)
    fd.append('blend_context', blendContext)
    if (file) fd.append('file', file)
    return jsonReq<VisionInspectResponse>('/api/vision/inspect', { method: 'POST', body: fd })
  },
  reportMarkdown: (payload: {
    product_name: string
    product_format: string
    target_customer: string
    grams_by_id: Record<string, number>
    standard: string
    price_tier: string
    price_overrides: Record<string, number>
    economics: EconomicsRequest
  }) =>
    jsonReq<{ markdown: string }>('/api/report', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),
}
