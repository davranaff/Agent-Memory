export interface Project {
  id: string;
  name: string;
  path: string;
  architecture_type: string | null;
  tech_stack?: string[];
  frameworks: string[];
  languages: string[];
  databases: string[];
  build_tools: string[];
  total_files: number;
  total_lines: number;
  analysis_status: string;
  last_analyzed: string | null;
}

export interface Component {
  id: string;
  name: string;
  type: string;
  path: string;
  language: string;
  line_count: number;
  complexity_score: number;
  dependencies: string[];
  exports: string[];
}

export interface GraphNode {
  id: string;
  name: string;
  type: string;
  group: string;
  value?: number;
  color?: string;
  size?: number;
  x?: number;
  y?: number;
  fx?: number;
  fy?: number;
}

export interface GraphLink {
  source: string | GraphNode;
  target: string | GraphNode;
  value: number;
  type?: string;
}

export interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
}

export interface ProjectAnalytics {
  total_files: number;
  total_lines: number;
  languages_count: number;
  complexity_score: number;
  test_ratio: number;
  architecture_type: string | null;
}

export interface ProjectSummaryResponse {
  project: Project;
  components: Record<string, { count: number; avg_complexity: number }>;
  documentation_count: number;
  metadata: Record<string, unknown>;
}

export interface ProjectAnalysisResponse {
  project_id: string;
  project_name: string;
  analysis_status: string;
  analysis_timestamp: string;
  summary: ProjectSummaryResponse;
  metadata: Record<string, unknown>;
}

export interface DependencyAnalyzeResponse {
  graph_statistics: Record<string, unknown>;
  nodes: number;
  edges: number;
  cycles_detected: number;
  strongly_connected_components: number;
  layers: Record<string, unknown>;
  impact_analysis?: Record<string, unknown>;
}

export interface GraphSyncResponse {
  project_id: string;
  backend: string;
  mode: string;
  changed_files_count: number;
  nodes: number;
  edges: number;
  synced_at: string;
}

export interface GraphImpactResponse {
  component_id: string;
  component_name: string;
  direct_impact: number;
  indirect_impact: number;
  total_impact: number;
  affected_components: string[];
  critical_paths: string[][];
  is_critical: boolean;
}

export interface GraphPathResponse {
  project_id: string;
  from_component_id: string;
  to_component_id: string;
  max_depth: number;
  path: string[] | null;
  path_found: boolean;
  path_length: number;
}

export interface GraphNeighborsResponse {
  component_id: string;
  component_name: string;
  depth: number;
  levels: Array<{ depth: number; component_ids: string[]; count: number }>;
  neighbor_component_ids?: string[];
  total_neighbors: number;
}

export interface ProjectHealthResponse {
  overall_health: number;
  health_distribution: Record<string, number>;
  quality_metrics: Record<string, unknown>;
  risk_factors: string[];
  recommendations: Array<string | Record<string, unknown>>;
}

export interface MemoryResult {
  id: string;
  content: string;
  memory_type: string;
  agent_id?: string | null;
  metadata?: Record<string, unknown>;
  importance?: number;
  similarity?: number;
  created_at?: string;
  updated_at?: string;
}

export interface MemorySearchResponse {
  results: MemoryResult[];
  count: number;
}

export interface HealthResponse {
  status: string;
  services: Record<string, unknown>;
}

export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

export interface ApiCatalogItem {
  id: string;
  category: string;
  method: HttpMethod;
  path: string;
  description: string;
  bodyTemplate?: Record<string, unknown>;
  queryTemplate?: Record<string, unknown>;
}
