export type Lang = 'bn' | 'en'
export type TabId = 'formulation' | 'molecular' | 'agents' | 'economics' | 'provenance'
export type OptimizationMode = 'cheapest' | 'greenest' | 'most_complete' | 'balanced' | 'meat_analogue'
export type ScoringStandard = 'fao_2013_diaas' | 'who_2007_pdcaas'
export type PriceTier = 'open_market' | 'tcb_subsidized'

export interface Ingredient {
  id: string
  name: string
  name_bn: string
  category: string
  is_baseline: boolean
  protein_g_per_100g: number
  carbs_g_per_100g: number
  fat_g_per_100g: number
  fiber_g_per_100g: number
  iron_mg_per_100g: number
  zinc_mg_per_100g: number
  his: number
  ile: number
  leu: number
  lys: number
  met_cys: number
  phe_tyr: number
  thr: number
  trp: number
  val: number
  digestibility_pdcaas: number
  diaas_ileal_factor: number
  price_bdt_per_kg_open: number
  price_bdt_per_kg_tcb: number
  co2e_kg_per_kg: number
  water_l_per_kg: number
  max_share: number
  allergens: string[]
  functional_role: string
  source_nutrition: string
  source_price: string
  source_co2e: string
  verified: boolean
}

export interface AminoAcidBreakdown {
  code: string
  short_label: string
  name_en: string
  name_bn: string
  blend_mg_per_g_protein: number
  digestible_mg_per_g_protein: number
  reference_mg_per_g_protein: number
  chemical_ratio: number
  digestible_ratio: number
  sufficiency_pct: number
  is_limiting: boolean
}

export interface BlendIngredientItem {
  id: string
  name: string
  name_bn: string
  category: string
  grams: number
  mass_share_pct: number
  protein_g: number
  cost_bdt: number
  co2e_g: number
  water_l: number
  allergens: string[]
  verified: boolean
  unverified_notes: string[]
}

export interface BlendScore {
  epistemic_tier: string
  standard: ScoringStandard
  price_tier: PriceTier
  total_mass_g: number
  total_protein_g: number
  carbs_g: number
  fat_g: number
  fiber_g: number
  iron_mg: number
  zinc_mg: number
  cost_bdt: number
  cost_per_20g_protein_bdt: number
  cost_per_kg_dry_bdt: number
  co2e_g: number
  co2e_per_20g_protein_g: number
  water_l: number
  water_per_20g_protein_l: number
  chemical_aa_score: number
  weighted_digestibility: number
  diaas_score: number
  pdcaas_score: number
  active_quality_score: number
  limiting_aa: string
  limiting_aa_label_en: string
  limiting_aa_label_bn: string
  is_complete_protein: boolean
  amino_acids: AminoAcidBreakdown[]
  items: BlendIngredientItem[]
  allergens_present: string[]
  has_unverified_inputs: boolean
  unverified_ingredients: string[]
}

export interface BaselineComparisonItem {
  baseline_id: string
  name: string
  name_bn: string
  serving_grams_for_20g_protein: number
  cost_bdt: number
  co2e_g: number
  water_l: number
  quality_score: number
  limiting_aa: string
  cost_change_pct: number
  co2e_change_pct: number
  water_change_pct: number
  quality_change_pct: number
  cost_savings_bdt: number
  co2e_savings_g: number
}

export interface MoleculeEvidence {
  key: string
  cid: number
  pubchem_url: string
  name: string
  name_bn: string
  formula: string
  mw: number
  role: string
  sensory_note: string
  sensory_note_bn: string
  mitigation: string
  source_ingredients: string[]
  relative_intensity: number
}

export interface SensoryAnalysis {
  epistemic_tier: string
  beany_off_note_risk_pct: number
  umami_synergy_score: number
  maillard_browning_potential: number
  overall_palatability_index: number
  functional_traits: {
    water_holding: number
    emulsification: number
    gelation: number
    fibrous_anisotropy: number
  }
  detected_molecules: MoleculeEvidence[]
  flavor_bridges_en: string[]
  flavor_bridges_bn: string[]
  process_mitigations_en: string[]
  process_mitigations_bn: string[]
}

export interface EconomicsRequest {
  batch_size_kg: number
  processing_packaging_bdt_per_kg: number
  wholesale_price_bdt_per_kg: number
  daily_servings: number
  operating_days_per_year: number
}

export interface EconomicsReport {
  epistemic_tier: string
  batch_size_kg: number
  servings_per_batch: number
  raw_ingredient_cogs_per_kg_bdt: number
  total_cogs_per_kg_bdt: number
  batch_total_cost_bdt: number
  wholesale_price_bdt_per_kg: number
  gross_margin_pct: number
  batch_gross_profit_bdt: number
  daily_servings: number
  operating_days_per_year: number
  annual_servings: number
  annual_dry_tonnes_required: number
  annual_bdt_saved_vs_chicken: number
  annual_co2e_avoided_tonnes_vs_chicken: number
  annual_water_saved_million_l_vs_chicken: number
  equivalent_cars_removed: number
}

export interface OptimizeRequest {
  mode: OptimizationMode
  standard: ScoringStandard
  price_tier: PriceTier
  min_score: number
  max_budget_bdt: number | null
  max_mass_g: number
  protein_target_g: number
  cost_weight: number
  excluded_allergens: string[]
  include_ids: string[]
  exclude_ids: string[]
  price_overrides: Record<string, number>
  min_fibrous_share: number
  economics?: EconomicsRequest
}

export interface OptimizeResponse {
  feasible: boolean
  mode: OptimizationMode
  message_en: string
  message_bn: string
  grams_by_id: Record<string, number>
  score: BlendScore | null
  diagnostic_hint_en?: string | null
  diagnostic_hint_bn?: string | null
  baselines?: BaselineComparisonItem[]
  sensory?: SensoryAnalysis
  economics?: EconomicsReport
}

export interface ParetoPoint {
  id: string
  cost_bdt: number
  co2e_g: number
  quality_score: number
  total_mass_g: number
  is_knee_point: boolean
  label_en: string
  label_bn: string
  grams_by_id: Record<string, number>
  score: BlendScore
}

export interface ParetoResponse {
  feasible: boolean
  standard: ScoringStandard
  price_tier: PriceTier
  points: ParetoPoint[]
  knee_point_id: string | null
}

export interface RagHit {
  filename: string
  title: string
  citation: string
  pmcid?: string | null
  doi?: string | null
  url?: string | null
  section: string
  excerpt: string
  score: number
}

export interface AgentStepTrace {
  step: number
  agent_name_en: string
  agent_name_bn: string
  model_used: string
  tools_called: string[]
  latency_ms: number
  status: string
  summary_en: string
  summary_bn: string
  cited_dois: string[]
}

export interface FormulateAgentResponse {
  product_name_en: string
  product_name_bn: string
  product_format_en: string
  product_format_bn: string
  target_customer_en: string
  target_customer_bn: string
  ai_provider: string
  audit_passed: boolean
  audit_notes_en: string[]
  audit_notes_bn: string[]
  score: BlendScore
  sensory: SensoryAnalysis
  baselines: BaselineComparisonItem[]
  literature_hits: RagHit[]
  molecular_summary_en: string
  molecular_summary_bn: string
  recipe_steps_en: string[]
  recipe_steps_bn: string[]
  industrial_process_en: string
  industrial_process_bn: string
  hypotheses_to_test_en: string[]
  hypotheses_to_test_bn: string[]
  agent_trace: AgentStepTrace[]
}

export interface VisionInspectResponse {
  epistemic_tier: string
  model_used: string
  maillard_browning_score: number
  fibrous_grain_score: number
  moisture_appearance: string
  visual_assessment_en: string
  visual_assessment_bn: string
  formulation_adjustments_en: string[]
  formulation_adjustments_bn: string[]
}

export interface Preset {
  id: string
  name_bn: string
  name_en: string
  subtitle_bn: string
  subtitle_en: string
  request: OptimizeRequest
  brief_bn: string
  brief_en: string
}

export interface HealthInfo {
  status: string
  app: string
  challenge: string
  ai_foundry: {
    provider: string
    configured: boolean
    model: string
    fast_model: string
    vision_model: string
  }
  dataset: {
    plant_ingredients: number
    verified_ingredients: number
    unverified_proxy_ingredients: number
    baselines: number
    papers: number
  }
  mcp_tools: number
}

export interface McpManifest {
  server_name: string
  transport: string
  command: string
  tool_count: number
  tools: Array<{
    name: string
    description: string
    args: string[]
  }>
}
