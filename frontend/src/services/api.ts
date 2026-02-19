import axios from 'axios';
import type {
  Component,
  DependencyAnalyzeResponse,
  GraphImpactResponse,
  GraphNeighborsResponse,
  GraphPathResponse,
  GraphSyncResponse,
  HealthResponse,
  HttpMethod,
  MemorySearchResponse,
  Project,
  ProjectAnalysisResponse,
  ProjectAnalytics,
  ProjectHealthResponse,
  ProjectSummaryResponse,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:10001';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 60000,
});

const normalizeProject = (raw: Partial<Project> & Record<string, unknown>): Project => ({
  id: String(raw.id || ''),
  name: String(raw.name || ''),
  path: String(raw.path || ''),
  architecture_type: (raw.architecture_type as string | null) ?? null,
  tech_stack: Array.isArray(raw.tech_stack) ? (raw.tech_stack as string[]) : [],
  frameworks: Array.isArray(raw.frameworks) ? (raw.frameworks as string[]) : [],
  languages: Array.isArray(raw.languages) ? (raw.languages as string[]) : [],
  databases: Array.isArray(raw.databases) ? (raw.databases as string[]) : [],
  build_tools: Array.isArray(raw.build_tools) ? (raw.build_tools as string[]) : [],
  total_files: Number(raw.total_files || 0),
  total_lines: Number(raw.total_lines || 0),
  analysis_status: String(raw.analysis_status || 'unknown'),
  last_analyzed: (raw.last_analyzed as string | null) ?? null,
});

const normalizeProjectSummary = (raw: Record<string, any>): ProjectSummaryResponse => ({
  project: normalizeProject(raw.project || {}),
  components: raw.components || {},
  documentation_count: Number(raw.documentation_count || 0),
  metadata: raw.metadata || {},
});

const normalizeAnalytics = (
  raw: Record<string, any>,
  project: Project
): ProjectAnalytics => {
  const metrics = raw?.metrics || {};
  const complexityMetrics = metrics?.complexity_metrics || {};
  const testingMetrics = metrics?.testing_metrics || {};
  const summary = raw?.summary || {};
  const dependencyAnalysis = raw?.dependency_analysis || {};

  const complexity =
    Number(complexityMetrics.average_cyclomatic_complexity) ||
    Number(summary.average_complexity) ||
    Number(dependencyAnalysis.average_dependencies) ||
    0;

  const testRatio =
    Number(testingMetrics.average_test_coverage) > 1
      ? Number(testingMetrics.average_test_coverage) / 100
      : Number(testingMetrics.average_test_coverage || 0);

  return {
    total_files: project.total_files,
    total_lines: project.total_lines,
    languages_count: project.languages.length,
    complexity_score: Number.isFinite(complexity) ? Number(complexity.toFixed(2)) : 0,
    test_ratio: Number.isFinite(testRatio) ? testRatio : 0,
    architecture_type: project.architecture_type,
  };
};

export const apiClient = {
  request: async <T = unknown>(
    method: HttpMethod,
    path: string,
    options?: {
      params?: Record<string, unknown>;
      data?: unknown;
    }
  ): Promise<{ status: number; data: T }> => {
    const response = await api.request<T>({
      method,
      url: path,
      params: options?.params,
      data: options?.data,
    });
    return {
      status: response.status,
      data: response.data,
    };
  },
};

export const projectService = {
  getProjects: async (): Promise<Project[]> => {
    const response = await api.get('/projects/');
    return (response.data || []).map((project: any) => normalizeProject(project));
  },

  getProjectSummary: async (id: string): Promise<ProjectSummaryResponse> => {
    const response = await api.get(`/projects/${id}/summary`);
    return normalizeProjectSummary(response.data || {});
  },

  getProjectComponents: async (
    id: string,
    filters?: Record<string, unknown>
  ): Promise<Component[]> => {
    const response = await api.get(`/projects/${id}/components`, { params: filters });
    return response.data || [];
  },

  getProjectAnalyticsRaw: async (id: string): Promise<Record<string, unknown>> => {
    const response = await api.get(`/projects/${id}/analytics`);
    return response.data || {};
  },

  getProjectAnalytics: async (id: string): Promise<ProjectAnalytics> => {
    const [summary, rawAnalytics] = await Promise.all([
      projectService.getProjectSummary(id),
      projectService.getProjectAnalyticsRaw(id),
    ]);
    return normalizeAnalytics(rawAnalytics as Record<string, any>, summary.project);
  },

  getProjectHealth: async (id: string): Promise<ProjectHealthResponse> => {
    const response = await api.get(`/projects/${id}/health`);
    return response.data;
  },

  analyzeProject: async (
    projectPath: string,
    projectName?: string,
    forceReindex = false
  ): Promise<ProjectAnalysisResponse> => {
    const response = await api.post('/projects/analyze', {
      project_path: projectPath,
      project_name: projectName,
      force_reindex: forceReindex,
      analysis_options: {},
    });
    return response.data;
  },

  getDependencyAnalysis: async (
    projectId: string,
    componentId?: string
  ): Promise<DependencyAnalyzeResponse> => {
    const response = await api.post('/projects/dependencies/analyze', {
      project_id: projectId,
      include_impact_analysis: Boolean(componentId),
      component_id: componentId || null,
    });
    return response.data;
  },

  syncDependencyGraph: async (
    projectId: string,
    changedFiles: string[] = []
  ): Promise<GraphSyncResponse> => {
    const response = await api.post('/projects/dependencies/sync', {
      project_id: projectId,
      changed_files: changedFiles,
    });
    return response.data;
  },

  getGraphImpact: async (
    projectId: string,
    componentId: string
  ): Promise<GraphImpactResponse> => {
    const response = await api.get(`/projects/${projectId}/graph/impact`, {
      params: { component_id: componentId },
    });
    return response.data;
  },

  getGraphPath: async (
    projectId: string,
    fromComponentId: string,
    toComponentId: string,
    maxDepth = 15
  ): Promise<GraphPathResponse> => {
    const response = await api.get(`/projects/${projectId}/graph/path`, {
      params: {
        from_component_id: fromComponentId,
        to_component_id: toComponentId,
        max_depth: maxDepth,
      },
    });
    return response.data;
  },

  getGraphNeighbors: async (
    projectId: string,
    componentId: string,
    depth = 1
  ): Promise<GraphNeighborsResponse> => {
    const response = await api.get(`/projects/${projectId}/graph/neighbors`, {
      params: { component_id: componentId, depth },
    });
    return response.data;
  },

  searchComponents: async (
    query: string,
    filters?: Record<string, unknown>
  ): Promise<Record<string, unknown>> => {
    const response = await api.post('/projects/components/search', { query, ...(filters || {}) });
    return response.data;
  },
};

export const systemService = {
  getHealth: async (): Promise<HealthResponse> => {
    const response = await api.get('/health');
    return response.data;
  },
};

export const memoryService = {
  search: async (
    query: string,
    metadataFilters?: Record<string, unknown>,
    topK = 20
  ): Promise<MemorySearchResponse> => {
    const response = await api.post('/memory/search', {
      query,
      metadata_filters: metadataFilters || null,
      top_k: topK,
    });
    return response.data;
  },

  store: async (payload: Record<string, unknown>): Promise<Record<string, unknown>> => {
    const response = await api.post('/memory/store', payload);
    return response.data;
  },
};

export default api;
