import React, { useEffect, useMemo, useState } from 'react';
import type {
  Component,
  DependencyAnalyzeResponse,
  GraphImpactResponse,
  GraphNeighborsResponse,
  GraphPathResponse,
  GraphSyncResponse,
  HealthResponse,
  MemorySearchResponse,
  ProjectHealthResponse,
  ProjectSummaryResponse,
} from '../types';
import { memoryService, projectService, systemService } from '../services/api';
import { Database, GitBranch, HardDrive, RefreshCw, Search } from 'lucide-react';

interface ProjectDataConsoleProps {
  projectId: string;
  projectSummary: ProjectSummaryResponse | null;
  analyticsRaw: Record<string, unknown> | null;
  projectHealth: ProjectHealthResponse | null;
  dependencyAnalysis: DependencyAnalyzeResponse | null;
  components: Component[];
}

const JsonBlock: React.FC<{ title: string; value: unknown }> = ({ title, value }) => (
  <div className="rounded-lg border border-gray-200 bg-white">
    <div className="border-b border-gray-200 px-4 py-2 text-sm font-semibold text-gray-800">{title}</div>
    <pre className="max-h-72 overflow-auto whitespace-pre-wrap break-all px-4 py-3 text-xs text-gray-700">
      {JSON.stringify(value, null, 2)}
    </pre>
  </div>
);

const ProjectDataConsole: React.FC<ProjectDataConsoleProps> = ({
  projectId,
  projectSummary,
  analyticsRaw,
  projectHealth,
  dependencyAnalysis,
  components,
}) => {
  const [systemHealth, setSystemHealth] = useState<HealthResponse | null>(null);
  const [syncResult, setSyncResult] = useState<GraphSyncResponse | null>(null);
  const [graphImpact, setGraphImpact] = useState<GraphImpactResponse | null>(null);
  const [graphPath, setGraphPath] = useState<GraphPathResponse | null>(null);
  const [graphNeighbors, setGraphNeighbors] = useState<GraphNeighborsResponse | null>(null);
  const [memoryResults, setMemoryResults] = useState<MemorySearchResponse | null>(null);
  const [memoryQuery, setMemoryQuery] = useState('project architecture');
  const [depth, setDepth] = useState(2);
  const [componentId, setComponentId] = useState('');
  const [targetComponentId, setTargetComponentId] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const selectedComponent = useMemo(
    () => components.find((component) => component.id === componentId) || null,
    [components, componentId]
  );

  useEffect(() => {
    if (components.length > 0) {
      setComponentId((prev) => prev || components[0].id);
      setTargetComponentId((prev) => prev || components[Math.min(1, components.length - 1)].id);
    }
  }, [components]);

  useEffect(() => {
    const loadSystemHealth = async () => {
      try {
        const data = await systemService.getHealth();
        setSystemHealth(data);
      } catch (e: any) {
        setSystemHealth({
          status: 'error',
          services: { error: e?.message || 'Failed to load /health' },
        });
      }
    };
    loadSystemHealth();
  }, []);

  const run = async <T,>(name: string, task: () => Promise<T>, setter: (value: T) => void) => {
    try {
      setBusy(name);
      setError(null);
      const value = await task();
      setter(value);
    } catch (e: any) {
      const detail = e?.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : e?.message || `Failed: ${name}`);
    } finally {
      setBusy(null);
    }
  };

  const handleSyncGraph = () =>
    run('sync_graph', () => projectService.syncDependencyGraph(projectId), setSyncResult);

  const handleImpact = () => {
    if (!componentId) return;
    run(
      'graph_impact',
      () => projectService.getGraphImpact(projectId, componentId),
      setGraphImpact
    );
  };

  const handleNeighbors = () => {
    if (!componentId) return;
    run(
      'graph_neighbors',
      () => projectService.getGraphNeighbors(projectId, componentId, depth),
      setGraphNeighbors
    );
  };

  const handlePath = () => {
    if (!componentId || !targetComponentId) return;
    run(
      'graph_path',
      () => projectService.getGraphPath(projectId, componentId, targetComponentId, 15),
      setGraphPath
    );
  };

  const handleMemorySearch = () =>
    run(
      'memory_search',
      () => memoryService.search(memoryQuery, { project_id: projectId }, 20),
      setMemoryResults
    );

  return (
    <div className="space-y-6">
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-gray-800">
            <HardDrive className="h-4 w-4" />
            System Health
          </div>
          <div className="text-sm text-gray-700">{(systemHealth?.status as string) || 'unknown'}</div>
          <div className="mt-2 text-xs text-gray-500">
            services: {Object.keys((systemHealth?.services as Record<string, unknown>) || {}).length}
          </div>
        </div>
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-gray-800">
            <Database className="h-4 w-4" />
            Project Health
          </div>
          <div className="text-sm text-gray-700">
            overall: {Number(projectHealth?.overall_health || 0).toFixed(2)}
          </div>
          <div className="mt-2 text-xs text-gray-500">
            risk_factors: {projectHealth?.risk_factors?.length || 0}
          </div>
        </div>
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-gray-800">
            <GitBranch className="h-4 w-4" />
            Graph Snapshot
          </div>
          <div className="text-sm text-gray-700">
            nodes: {dependencyAnalysis?.nodes || 0} | edges: {dependencyAnalysis?.edges || 0}
          </div>
          <div className="mt-2 text-xs text-gray-500">
            cycles: {dependencyAnalysis?.cycles_detected || 0}
          </div>
        </div>
      </div>

      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <div className="mb-4 text-sm font-semibold text-gray-800">Graph Actions</div>
        <div className="mb-4 grid grid-cols-1 gap-3 md:grid-cols-3">
          <select
            value={componentId}
            onChange={(e) => setComponentId(e.target.value)}
            className="rounded border border-gray-300 px-3 py-2 text-sm"
          >
            {components.map((component) => (
              <option key={component.id} value={component.id}>
                {component.name} ({component.type})
              </option>
            ))}
          </select>
          <select
            value={targetComponentId}
            onChange={(e) => setTargetComponentId(e.target.value)}
            className="rounded border border-gray-300 px-3 py-2 text-sm"
          >
            {components.map((component) => (
              <option key={component.id} value={component.id}>
                {component.name} ({component.type})
              </option>
            ))}
          </select>
          <input
            type="number"
            min={1}
            max={6}
            value={depth}
            onChange={(e) => setDepth(Number(e.target.value || 1))}
            className="rounded border border-gray-300 px-3 py-2 text-sm"
            placeholder="Depth"
          />
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={handleSyncGraph}
            className="inline-flex items-center gap-2 rounded bg-blue-600 px-3 py-2 text-sm text-white hover:bg-blue-700"
            disabled={busy !== null}
          >
            <RefreshCw className={`h-4 w-4 ${busy === 'sync_graph' ? 'animate-spin' : ''}`} />
            Sync Graph
          </button>
          <button
            onClick={handleImpact}
            className="rounded bg-emerald-600 px-3 py-2 text-sm text-white hover:bg-emerald-700"
            disabled={!componentId || busy !== null}
          >
            Impact
          </button>
          <button
            onClick={handleNeighbors}
            className="rounded bg-indigo-600 px-3 py-2 text-sm text-white hover:bg-indigo-700"
            disabled={!componentId || busy !== null}
          >
            Neighbors
          </button>
          <button
            onClick={handlePath}
            className="rounded bg-violet-600 px-3 py-2 text-sm text-white hover:bg-violet-700"
            disabled={!componentId || !targetComponentId || busy !== null}
          >
            Path
          </button>
        </div>
        {selectedComponent && (
          <p className="mt-3 text-xs text-gray-500">
            selected: {selectedComponent.name} ({selectedComponent.id})
          </p>
        )}
      </div>

      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <div className="mb-3 text-sm font-semibold text-gray-800">Memory Search (scoped by project_id)</div>
        <div className="flex flex-col gap-2 md:flex-row">
          <input
            value={memoryQuery}
            onChange={(e) => setMemoryQuery(e.target.value)}
            className="flex-1 rounded border border-gray-300 px-3 py-2 text-sm"
            placeholder="Search query..."
          />
          <button
            onClick={handleMemorySearch}
            className="inline-flex items-center justify-center gap-2 rounded bg-gray-900 px-3 py-2 text-sm text-white hover:bg-black"
            disabled={!memoryQuery.trim() || busy !== null}
          >
            <Search className="h-4 w-4" />
            Search
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <JsonBlock title="Project Summary (/projects/{id}/summary)" value={projectSummary} />
        <JsonBlock title="Project Analytics (/projects/{id}/analytics)" value={analyticsRaw} />
        <JsonBlock title="Project Health (/projects/{id}/health)" value={projectHealth} />
        <JsonBlock title="Dependency Analyze (/projects/dependencies/analyze)" value={dependencyAnalysis} />
        <JsonBlock title="Graph Sync Result" value={syncResult} />
        <JsonBlock title="Graph Impact Result" value={graphImpact} />
        <JsonBlock title="Graph Neighbors Result" value={graphNeighbors} />
        <JsonBlock title="Graph Path Result" value={graphPath} />
        <JsonBlock title="Memory Search Result" value={memoryResults} />
        <JsonBlock title="System Health (/health)" value={systemHealth} />
      </div>
    </div>
  );
};

export default ProjectDataConsole;
