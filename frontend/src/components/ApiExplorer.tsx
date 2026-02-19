import React, { useMemo, useState } from 'react';
import { Filter, Send, Server } from 'lucide-react';
import { apiClient } from '../services/api';
import type { ApiCatalogItem, HttpMethod } from '../types';

const API_CATALOG: ApiCatalogItem[] = [
  { id: 'health', category: 'system', method: 'GET', path: '/health', description: 'Backend health' },
  { id: 'projects-list', category: 'projects', method: 'GET', path: '/projects/', description: 'List projects' },
  {
    id: 'projects-analyze',
    category: 'projects',
    method: 'POST',
    path: '/projects/analyze',
    description: 'Analyze project path',
    bodyTemplate: {
      project_path: '/Users/davranaff/Desktop/agents memory',
      project_name: 'Agent Memory',
      force_reindex: true,
      analysis_options: {},
    },
  },
  {
    id: 'project-summary',
    category: 'projects',
    method: 'GET',
    path: '/projects/{project_id}/summary',
    description: 'Project summary',
  },
  {
    id: 'project-components',
    category: 'projects',
    method: 'GET',
    path: '/projects/{project_id}/components',
    description: 'Project components',
    queryTemplate: { limit: 200, offset: 0 },
  },
  {
    id: 'project-analytics',
    category: 'projects',
    method: 'GET',
    path: '/projects/{project_id}/analytics',
    description: 'Project analytics',
  },
  {
    id: 'project-health',
    category: 'projects',
    method: 'GET',
    path: '/projects/{project_id}/health',
    description: 'Project health',
  },
  {
    id: 'components-search',
    category: 'projects',
    method: 'POST',
    path: '/projects/components/search',
    description: 'Search components',
    bodyTemplate: { query: 'memory', search_type: 'fuzzy', filters: {}, limit: 50, offset: 0 },
  },
  {
    id: 'components-analyze',
    category: 'projects',
    method: 'POST',
    path: '/projects/components/analyze',
    description: 'Detailed component analysis',
    bodyTemplate: {
      component_id: '{component_id}',
      include_comparisons: true,
      include_recommendations: true,
    },
  },
  {
    id: 'dependencies-analyze',
    category: 'graph',
    method: 'POST',
    path: '/projects/dependencies/analyze',
    description: 'Dependency graph analysis',
    bodyTemplate: {
      project_id: '{project_id}',
      include_impact_analysis: false,
      component_id: null,
    },
  },
  {
    id: 'dependencies-sync',
    category: 'graph',
    method: 'POST',
    path: '/projects/dependencies/sync',
    description: 'Sync dependency graph to graph DB',
    bodyTemplate: { project_id: '{project_id}', changed_files: [] },
  },
  {
    id: 'graph-impact',
    category: 'graph',
    method: 'GET',
    path: '/projects/{project_id}/graph/impact',
    description: 'Impact analysis for component',
    queryTemplate: { component_id: '{component_id}' },
  },
  {
    id: 'graph-path',
    category: 'graph',
    method: 'GET',
    path: '/projects/{project_id}/graph/path',
    description: 'Path between two components',
    queryTemplate: {
      from_component_id: '{from_component_id}',
      to_component_id: '{to_component_id}',
      max_depth: 15,
    },
  },
  {
    id: 'graph-neighbors',
    category: 'graph',
    method: 'GET',
    path: '/projects/{project_id}/graph/neighbors',
    description: 'Graph neighbors by component',
    queryTemplate: { component_id: '{component_id}', depth: 2 },
  },
  {
    id: 'technology-analyze',
    category: 'projects',
    method: 'POST',
    path: '/projects/technology/analyze',
    description: 'Technology stack analysis',
    bodyTemplate: { project_id: '{project_id}', include_recommendations: true, export_format: 'json' },
  },
  {
    id: 'patterns-detect',
    category: 'projects',
    method: 'POST',
    path: '/projects/patterns/detect',
    description: 'Architecture patterns detection',
    bodyTemplate: { project_id: '{project_id}', include_recommendations: true },
  },
  {
    id: 'project-compare',
    category: 'projects',
    method: 'POST',
    path: '/projects/compare',
    description: 'Compare projects',
    bodyTemplate: { project_ids: ['{project_id_1}', '{project_id_2}'] },
  },
  {
    id: 'files-parse',
    category: 'projects',
    method: 'POST',
    path: '/projects/files/parse',
    description: 'Parse single file',
    bodyTemplate: { file_path: '/host-projects/agents memory/app/main.py', include_dependencies: true },
  },
  {
    id: 'project-delete',
    category: 'projects',
    method: 'DELETE',
    path: '/projects/{project_id}',
    description: 'Delete project index',
  },
  {
    id: 'memory-search',
    category: 'memory',
    method: 'POST',
    path: '/memory/search',
    description: 'Search vector memory',
    bodyTemplate: { query: 'project architecture', metadata_filters: { project_id: '{project_id}' }, top_k: 20 },
  },
  {
    id: 'memory-store',
    category: 'memory',
    method: 'POST',
    path: '/memory/store',
    description: 'Store memory item',
    bodyTemplate: { content: 'Project summary', memory_type: 'project_summary', metadata: { project_id: '{project_id}' } },
  },
  {
    id: 'memory-get',
    category: 'memory',
    method: 'GET',
    path: '/memory/{memory_id}',
    description: 'Get memory by id',
  },
  {
    id: 'memory-delete',
    category: 'memory',
    method: 'DELETE',
    path: '/memory/{memory_id}',
    description: 'Delete memory by id',
  },
  {
    id: 'agents-create',
    category: 'agents',
    method: 'POST',
    path: '/agents',
    description: 'Create agent',
    bodyTemplate: { name: 'frontend-agent', role: 'analyst', system_prompt: 'Analyze project context' },
  },
  {
    id: 'agent-get',
    category: 'agents',
    method: 'GET',
    path: '/agents/{agent_id}',
    description: 'Get agent',
  },
  {
    id: 'agent-run',
    category: 'agents',
    method: 'POST',
    path: '/agents/{agent_id}/run',
    description: 'Run agent task',
    bodyTemplate: { input: 'Summarize project architecture', session_id: null },
  },
  {
    id: 'sessions-create',
    category: 'sessions',
    method: 'POST',
    path: '/sessions',
    description: 'Create session',
    bodyTemplate: { agent_id: '{agent_id}', title: 'frontend-session' },
  },
  {
    id: 'session-get',
    category: 'sessions',
    method: 'GET',
    path: '/sessions/{session_id}',
    description: 'Get session',
  },
  {
    id: 'orchestration-run',
    category: 'orchestration',
    method: 'POST',
    path: '/orchestration/run',
    description: 'Run workflow',
    bodyTemplate: { workflow_name: 'project-analysis', input_data: { project_id: '{project_id}' } },
  },
  {
    id: 'orchestration-get',
    category: 'orchestration',
    method: 'GET',
    path: '/orchestration/{run_id}',
    description: 'Get workflow run status',
  },
  {
    id: 'orchestration-list',
    category: 'orchestration',
    method: 'GET',
    path: '/orchestration/workflows/list',
    description: 'List workflows',
  },
  {
    id: 'semantic-emb-code',
    category: 'semantic',
    method: 'POST',
    path: '/semantic/embeddings/code',
    description: 'Create code embedding',
    bodyTemplate: { content: 'def hello():\n  return 1', metadata: { project_id: '{project_id}' } },
  },
  {
    id: 'semantic-emb-pattern',
    category: 'semantic',
    method: 'POST',
    path: '/semantic/embeddings/pattern',
    description: 'Create pattern embedding',
    bodyTemplate: { pattern_data: { name: 'Repository Pattern' }, metadata: { project_id: '{project_id}' } },
  },
  {
    id: 'semantic-emb-doc',
    category: 'semantic',
    method: 'POST',
    path: '/semantic/embeddings/documentation',
    description: 'Create documentation embedding',
    bodyTemplate: { title: 'Architecture', content: 'Project architecture summary', metadata: { project_id: '{project_id}' } },
  },
  {
    id: 'semantic-emb-usage',
    category: 'semantic',
    method: 'POST',
    path: '/semantic/embeddings/usage',
    description: 'Create usage embedding',
    bodyTemplate: { query: 'how to analyze project', response: 'use /projects/analyze', metadata: { project_id: '{project_id}' } },
  },
  {
    id: 'semantic-search',
    category: 'semantic',
    method: 'POST',
    path: '/semantic/search',
    description: 'General semantic search',
    bodyTemplate: { query: 'project architecture', search_type: 'all', limit: 10, min_similarity: 0.0 },
  },
  {
    id: 'semantic-search-code',
    category: 'semantic',
    method: 'POST',
    path: '/semantic/search/code',
    description: 'Semantic code search',
    bodyTemplate: { query: 'dependency graph', language: 'python', limit: 10 },
  },
  {
    id: 'semantic-search-pattern',
    category: 'semantic',
    method: 'POST',
    path: '/semantic/search/pattern',
    description: 'Search architecture patterns',
    bodyTemplate: { query: 'repository pattern', limit: 10 },
  },
  {
    id: 'semantic-search-examples',
    category: 'semantic',
    method: 'POST',
    path: '/semantic/search/examples',
    description: 'Search usage examples',
    bodyTemplate: { query: 'project analyze', limit: 10 },
  },
  {
    id: 'semantic-search-analytics',
    category: 'semantic',
    method: 'GET',
    path: '/semantic/search/analytics',
    description: 'Semantic search analytics',
  },
  {
    id: 'semantic-emb-stats',
    category: 'semantic',
    method: 'GET',
    path: '/semantic/embeddings/statistics',
    description: 'Embeddings statistics',
  },
  {
    id: 'semantic-patterns-detect',
    category: 'semantic',
    method: 'POST',
    path: '/semantic/patterns/detect',
    description: 'Detect semantic patterns',
    bodyTemplate: { project_id: '{project_id}', include_examples: true },
  },
  {
    id: 'semantic-doc-search',
    category: 'semantic',
    method: 'POST',
    path: '/semantic/documentation/search',
    description: 'Semantic documentation search',
    bodyTemplate: { query: 'graph database', limit: 10 },
  },
  {
    id: 'semantic-usage-similar',
    category: 'semantic',
    method: 'POST',
    path: '/semantic/usage/similar',
    description: 'Find similar usage',
    bodyTemplate: { usage_id: '{usage_id}', limit: 10 },
  },
  {
    id: 'semantic-emb-clear',
    category: 'semantic',
    method: 'DELETE',
    path: '/semantic/embeddings/clear',
    description: 'Clear embeddings',
  },
  {
    id: 'enhanced-project-analyze',
    category: 'enhanced',
    method: 'POST',
    path: '/enhanced/projects/analyze',
    description: 'Enhanced project analysis',
    bodyTemplate: { project_path: '/host-projects/agents memory', project_name: 'Agent Memory', options: {} },
  },
  {
    id: 'enhanced-search-code',
    category: 'enhanced',
    method: 'POST',
    path: '/enhanced/search/code',
    description: 'Enhanced code search',
    bodyTemplate: { query: 'memory store', project_id: '{project_id}', limit: 20 },
  },
  {
    id: 'enhanced-pattern-suggest',
    category: 'enhanced',
    method: 'POST',
    path: '/enhanced/patterns/suggest',
    description: 'Suggest architecture patterns',
    bodyTemplate: { project_id: '{project_id}', context: 'service layer' },
  },
  {
    id: 'enhanced-code-review',
    category: 'enhanced',
    method: 'POST',
    path: '/enhanced/code/review',
    description: 'Review code snippet',
    bodyTemplate: { code: 'def test():\n  pass', language: 'python', focus: ['bugs'] },
  },
  {
    id: 'enhanced-git-precommit',
    category: 'enhanced',
    method: 'POST',
    path: '/enhanced/git/precommit',
    description: 'Run pre-commit checks',
    bodyTemplate: { project_path: '/host-projects/agents memory', files: [] },
  },
  {
    id: 'enhanced-git-review',
    category: 'enhanced',
    method: 'POST',
    path: '/enhanced/git/review',
    description: 'Review git diff',
    bodyTemplate: { project_path: '/host-projects/agents memory', base_ref: 'main', head_ref: 'HEAD' },
  },
  {
    id: 'enhanced-git-status',
    category: 'enhanced',
    method: 'GET',
    path: '/enhanced/git/status',
    description: 'Git status',
    queryTemplate: { project_path: '/host-projects/agents memory' },
  },
  {
    id: 'enhanced-git-commits',
    category: 'enhanced',
    method: 'GET',
    path: '/enhanced/git/commits',
    description: 'Git commits',
    queryTemplate: { project_path: '/host-projects/agents memory', limit: 20 },
  },
  {
    id: 'enhanced-hooks-install',
    category: 'enhanced',
    method: 'POST',
    path: '/enhanced/git/hooks/install',
    description: 'Install git hooks',
    bodyTemplate: { project_path: '/host-projects/agents memory' },
  },
  {
    id: 'enhanced-hooks-uninstall',
    category: 'enhanced',
    method: 'POST',
    path: '/enhanced/git/hooks/uninstall',
    description: 'Uninstall git hooks',
    bodyTemplate: { project_path: '/host-projects/agents memory' },
  },
  {
    id: 'enhanced-hooks-config',
    category: 'enhanced',
    method: 'GET',
    path: '/enhanced/git/hooks/config',
    description: 'Get hooks config',
    queryTemplate: { project_path: '/host-projects/agents memory' },
  },
  {
    id: 'advanced-autocomplete-suggest',
    category: 'advanced',
    method: 'POST',
    path: '/advanced/autocomplete/suggestions',
    description: 'Autocomplete suggestions',
    bodyTemplate: { prefix: 'def analy', language: 'python', max_suggestions: 5 },
  },
  {
    id: 'advanced-autocomplete-context',
    category: 'advanced',
    method: 'POST',
    path: '/advanced/autocomplete/context',
    description: 'Autocomplete context analysis',
    bodyTemplate: { content: 'class Service:\n  def run(self):\n    ', language: 'python' },
  },
  {
    id: 'advanced-cache-stats',
    category: 'advanced',
    method: 'GET',
    path: '/advanced/autocomplete/cache/stats',
    description: 'Autocomplete cache stats',
  },
  {
    id: 'advanced-cache-clear',
    category: 'advanced',
    method: 'POST',
    path: '/advanced/autocomplete/cache/clear',
    description: 'Clear autocomplete cache',
  },
  {
    id: 'advanced-error-analyze',
    category: 'advanced',
    method: 'POST',
    path: '/advanced/error-prevention/analyze',
    description: 'Analyze possible errors',
    bodyTemplate: { code: 'for i in range(10)\n  print(i)', language: 'python' },
  },
  {
    id: 'advanced-error-rules',
    category: 'advanced',
    method: 'GET',
    path: '/advanced/error-prevention/rules',
    description: 'List error prevention rules',
  },
  {
    id: 'advanced-error-enable',
    category: 'advanced',
    method: 'POST',
    path: '/advanced/error-prevention/rules/enable',
    description: 'Enable error rule',
    bodyTemplate: { rule_id: '{rule_id}' },
  },
  {
    id: 'advanced-error-disable',
    category: 'advanced',
    method: 'POST',
    path: '/advanced/error-prevention/rules/disable',
    description: 'Disable error rule',
    bodyTemplate: { rule_id: '{rule_id}' },
  },
  {
    id: 'advanced-error-stats',
    category: 'advanced',
    method: 'GET',
    path: '/advanced/error-prevention/rules/statistics',
    description: 'Error prevention statistics',
  },
  {
    id: 'advanced-error-autofix',
    category: 'advanced',
    method: 'POST',
    path: '/advanced/error-prevention/autofix',
    description: 'Auto-fix code issues',
    bodyTemplate: { code: 'x == None', language: 'python' },
  },
  {
    id: 'advanced-code-analysis',
    category: 'advanced',
    method: 'POST',
    path: '/advanced/code/analysis',
    description: 'Advanced code analysis',
    bodyTemplate: { code: 'def handler(x): return x', language: 'python', context: {} },
  },
];

const METHOD_STYLES: Record<HttpMethod, string> = {
  GET: 'bg-emerald-100 text-emerald-800',
  POST: 'bg-blue-100 text-blue-800',
  PUT: 'bg-amber-100 text-amber-800',
  PATCH: 'bg-violet-100 text-violet-800',
  DELETE: 'bg-red-100 text-red-800',
};

const prettyJson = (value: unknown) => JSON.stringify(value, null, 2);

const parseJsonInput = (raw: string, label: string): Record<string, unknown> | undefined => {
  const trimmed = raw.trim();
  if (!trimmed) return undefined;
  let parsed: unknown;
  try {
    parsed = JSON.parse(trimmed);
  } catch {
    throw new Error(`${label} must be valid JSON`);
  }
  if (parsed === null) return undefined;
  if (typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new Error(`${label} must be a JSON object`);
  }
  return parsed as Record<string, unknown>;
};

const ApiExplorer: React.FC = () => {
  const [search, setSearch] = useState('');
  const [activeId, setActiveId] = useState(API_CATALOG[0].id);
  const [method, setMethod] = useState<HttpMethod>(API_CATALOG[0].method);
  const [path, setPath] = useState(API_CATALOG[0].path);
  const [queryJson, setQueryJson] = useState(prettyJson(API_CATALOG[0].queryTemplate || {}));
  const [bodyJson, setBodyJson] = useState(prettyJson(API_CATALOG[0].bodyTemplate || {}));
  const [responseStatus, setResponseStatus] = useState<number | null>(null);
  const [responseData, setResponseData] = useState<unknown>(null);
  const [responseError, setResponseError] = useState<string | null>(null);
  const [durationMs, setDurationMs] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);

  const filteredCatalog = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return API_CATALOG;
    return API_CATALOG.filter((item) => {
      return (
        item.path.toLowerCase().includes(term) ||
        item.description.toLowerCase().includes(term) ||
        item.category.toLowerCase().includes(term) ||
        item.method.toLowerCase().includes(term)
      );
    });
  }, [search]);

  const selectEndpoint = (item: ApiCatalogItem) => {
    setActiveId(item.id);
    setMethod(item.method);
    setPath(item.path);
    setQueryJson(prettyJson(item.queryTemplate || {}));
    setBodyJson(prettyJson(item.bodyTemplate || {}));
    setResponseError(null);
  };

  const runRequest = async () => {
    setLoading(true);
    setResponseError(null);
    setResponseStatus(null);
    setDurationMs(null);

    try {
      const params = parseJsonInput(queryJson, 'Query params');
      const data = parseJsonInput(bodyJson, 'Request body');
      const start = Date.now();
      const response = await apiClient.request(method, path, { params, data });
      setDurationMs(Date.now() - start);
      setResponseStatus(response.status);
      setResponseData(response.data);
    } catch (e: any) {
      const detail = e?.response?.data?.detail;
      setResponseStatus(e?.response?.status || null);
      setResponseError(typeof detail === 'string' ? detail : e?.message || 'Request failed');
      setResponseData(e?.response?.data || null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto grid max-w-7xl grid-cols-1 gap-6 p-6 xl:grid-cols-12">
      <section className="rounded-lg border border-gray-200 bg-white xl:col-span-4">
        <div className="border-b border-gray-200 p-4">
          <div className="mb-3 flex items-center gap-2">
            <Server className="h-4 w-4 text-gray-700" />
            <h2 className="text-sm font-semibold text-gray-900">API Catalog</h2>
          </div>
          <div className="relative">
            <Filter className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Filter by path/category"
              className="w-full rounded border border-gray-300 py-2 pl-9 pr-3 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
            />
          </div>
        </div>

        <div className="max-h-[72vh] overflow-auto p-2">
          {filteredCatalog.map((item) => (
            <button
              key={item.id}
              onClick={() => selectEndpoint(item)}
              className={`mb-2 w-full rounded border p-3 text-left transition ${
                activeId === item.id
                  ? 'border-blue-300 bg-blue-50'
                  : 'border-gray-200 bg-white hover:border-gray-300 hover:bg-gray-50'
              }`}
            >
              <div className="mb-1 flex items-center justify-between gap-2">
                <span className={`rounded px-2 py-0.5 text-xs font-semibold ${METHOD_STYLES[item.method]}`}>
                  {item.method}
                </span>
                <span className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600">{item.category}</span>
              </div>
              <div className="truncate font-mono text-xs text-gray-800">{item.path}</div>
              <div className="mt-1 text-xs text-gray-500">{item.description}</div>
            </button>
          ))}
          {filteredCatalog.length === 0 && (
            <div className="p-3 text-sm text-gray-500">No endpoints matched the filter</div>
          )}
        </div>
      </section>

      <section className="space-y-4 rounded-lg border border-gray-200 bg-white p-4 xl:col-span-8">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-5">
          <select
            value={method}
            onChange={(e) => setMethod(e.target.value as HttpMethod)}
            className="rounded border border-gray-300 px-3 py-2 text-sm"
          >
            <option value="GET">GET</option>
            <option value="POST">POST</option>
            <option value="PUT">PUT</option>
            <option value="PATCH">PATCH</option>
            <option value="DELETE">DELETE</option>
          </select>
          <input
            value={path}
            onChange={(e) => setPath(e.target.value)}
            className="rounded border border-gray-300 px-3 py-2 font-mono text-sm md:col-span-4"
            placeholder="/projects/{project_id}/summary"
          />
        </div>

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <div>
            <label className="mb-2 block text-xs font-semibold uppercase tracking-wide text-gray-600">Query Params JSON</label>
            <textarea
              value={queryJson}
              onChange={(e) => setQueryJson(e.target.value)}
              className="h-44 w-full rounded border border-gray-300 p-3 font-mono text-xs focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
            />
          </div>
          <div>
            <label className="mb-2 block text-xs font-semibold uppercase tracking-wide text-gray-600">Request Body JSON</label>
            <textarea
              value={bodyJson}
              onChange={(e) => setBodyJson(e.target.value)}
              className="h-44 w-full rounded border border-gray-300 p-3 font-mono text-xs focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
            />
          </div>
        </div>

        <div className="flex items-center justify-between gap-3">
          <p className="text-xs text-gray-500">
            Replace placeholders manually in path/body/query: <code>{'{project_id}'}</code>, <code>{'{component_id}'}</code>.
          </p>
          <button
            onClick={runRequest}
            disabled={loading || !path.trim()}
            className="inline-flex items-center gap-2 rounded bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-black disabled:cursor-not-allowed disabled:opacity-60"
          >
            <Send className="h-4 w-4" />
            {loading ? 'Running...' : 'Send Request'}
          </button>
        </div>

        <div className="rounded-lg border border-gray-200">
          <div className="flex flex-wrap items-center gap-3 border-b border-gray-200 px-4 py-2 text-sm">
            <span className="font-medium text-gray-700">Response</span>
            {responseStatus !== null && (
              <span className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-700">status: {responseStatus}</span>
            )}
            {durationMs !== null && (
              <span className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-700">{durationMs} ms</span>
            )}
            {responseError && <span className="text-xs text-red-700">{responseError}</span>}
          </div>
          <pre className="max-h-[42vh] overflow-auto whitespace-pre-wrap break-all p-4 font-mono text-xs text-gray-800">
            {responseData ? prettyJson(responseData) : 'No response yet'}
          </pre>
        </div>
      </section>
    </div>
  );
};

export default ApiExplorer;
