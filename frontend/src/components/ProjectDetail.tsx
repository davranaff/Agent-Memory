import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  ArrowLeft,
  Code,
  Database,
  FileText,
  FolderOpen,
  GitBranch,
  Package,
  Search,
} from 'lucide-react';
import type {
  Component,
  DependencyAnalyzeResponse,
  Project,
  ProjectAnalytics as ProjectAnalyticsType,
  ProjectHealthResponse,
  ProjectSummaryResponse,
} from '../types';
import { projectService } from '../services/api';
import ComponentDetail from './ComponentDetail';
import DependencyAnalysis from './DependencyAnalysis';
import FileExplorer from './FileExplorer';
import GraphVisualization from './GraphVisualization';
import ProjectAnalytics from './ProjectAnalytics';
import ProjectDataConsole from './ProjectDataConsole';
import ProjectHealth from './ProjectHealth';
import ProjectMetrics from './ProjectMetrics';
import ProjectTimeline from './ProjectTimeline';
import TechnologyStack from './TechnologyStack';

type DetailTab =
  | 'overview'
  | 'timeline'
  | 'health'
  | 'metrics'
  | 'technology'
  | 'analytics'
  | 'dependencies'
  | 'files'
  | 'components'
  | 'graph'
  | 'data';

const ProjectDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [project, setProject] = useState<Project | null>(null);
  const [projectSummary, setProjectSummary] = useState<ProjectSummaryResponse | null>(null);
  const [components, setComponents] = useState<Component[]>([]);
  const [analytics, setAnalytics] = useState<ProjectAnalyticsType | null>(null);
  const [analyticsRaw, setAnalyticsRaw] = useState<Record<string, unknown> | null>(null);
  const [projectHealth, setProjectHealth] = useState<ProjectHealthResponse | null>(null);
  const [dependencyAnalysis, setDependencyAnalysis] = useState<DependencyAnalyzeResponse | null>(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedType, setSelectedType] = useState<string>('all');
  const [activeTab, setActiveTab] = useState<DetailTab>('overview');
  const [selectedComponent, setSelectedComponent] = useState<Component | null>(null);

  useEffect(() => {
    if (id) loadProjectData(id);
  }, [id]);

  const loadProjectData = async (projectId: string) => {
    setLoading(true);
    setError(null);

    const [summaryRes, componentsRes, analyticsRes, analyticsRawRes, healthRes, depsRes] =
      await Promise.allSettled([
        projectService.getProjectSummary(projectId),
        projectService.getProjectComponents(projectId),
        projectService.getProjectAnalytics(projectId),
        projectService.getProjectAnalyticsRaw(projectId),
        projectService.getProjectHealth(projectId),
        projectService.getDependencyAnalysis(projectId),
      ]);

    if (summaryRes.status === 'fulfilled') {
      setProjectSummary(summaryRes.value);
      setProject(summaryRes.value.project);
    } else {
      setError('Failed to load project summary');
    }

    setComponents(componentsRes.status === 'fulfilled' ? componentsRes.value : []);
    setAnalytics(analyticsRes.status === 'fulfilled' ? analyticsRes.value : null);
    setAnalyticsRaw(analyticsRawRes.status === 'fulfilled' ? analyticsRawRes.value : null);
    setProjectHealth(healthRes.status === 'fulfilled' ? healthRes.value : null);
    setDependencyAnalysis(depsRes.status === 'fulfilled' ? depsRes.value : null);
    setLoading(false);
  };

  const filteredComponents = useMemo(
    () =>
      components.filter((component) => {
        const matchesSearch =
          component.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
          component.path.toLowerCase().includes(searchTerm.toLowerCase());
        const matchesType = selectedType === 'all' || component.type === selectedType;
        return matchesSearch && matchesType;
      }),
    [components, searchTerm, selectedType]
  );

  const componentTypes = useMemo(
    () => Array.from(new Set(components.map((component) => component.type))),
    [components]
  );

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="mx-auto max-w-3xl p-6">
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
          {error || 'Project not found'}
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center gap-4">
        <button onClick={() => navigate('/')} className="rounded-lg p-2 hover:bg-gray-100">
          <ArrowLeft className="h-5 w-5" />
        </button>
        <div className="flex items-center gap-2">
          <FolderOpen className="h-6 w-6 text-blue-600" />
          <h1 className="text-3xl font-bold text-gray-900">{project.name}</h1>
        </div>
        <span
          className={`rounded-full px-3 py-1 text-sm ${
            project.analysis_status === 'completed'
              ? 'bg-green-100 text-green-800'
              : 'bg-yellow-100 text-yellow-800'
          }`}
        >
          {project.analysis_status}
        </span>
      </div>

      {error && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="mb-6 rounded-lg bg-white p-6 shadow-md">
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-blue-100 p-3">
              <FileText className="h-6 w-6 text-blue-600" />
            </div>
            <div>
              <p className="text-sm text-gray-600">Files</p>
              <p className="text-2xl font-bold">{project.total_files.toLocaleString()}</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-green-100 p-3">
              <Code className="h-6 w-6 text-green-600" />
            </div>
            <div>
              <p className="text-sm text-gray-600">Lines</p>
              <p className="text-2xl font-bold">{project.total_lines.toLocaleString()}</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-purple-100 p-3">
              <GitBranch className="h-6 w-6 text-purple-600" />
            </div>
            <div>
              <p className="text-sm text-gray-600">Architecture</p>
              <p className="text-lg font-bold capitalize">{project.architecture_type || 'unknown'}</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-amber-100 p-3">
              <Database className="h-6 w-6 text-amber-600" />
            </div>
            <div>
              <p className="text-sm text-gray-600">Components</p>
              <p className="text-2xl font-bold">{components.length.toLocaleString()}</p>
            </div>
          </div>
        </div>
      </div>

      <div className="mb-6 rounded-lg bg-white shadow-md">
        <div className="border-b border-gray-200">
          <nav className="flex gap-8 overflow-x-auto px-6">
            {(
              [
                ['overview', 'Overview'],
                ['timeline', 'Timeline'],
                ['health', 'Health'],
                ['metrics', 'Metrics'],
                ['technology', 'Technology'],
                ['analytics', 'Analytics'],
                ['dependencies', 'Dependencies'],
                ['files', 'Files'],
                ['components', `Components (${components.length})`],
                ['graph', 'Graph'],
                ['data', 'Data Console'],
              ] as Array<[DetailTab, string]>
            ).map(([tab, label]) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`whitespace-nowrap border-b-2 px-1 py-4 text-sm font-medium ${
                  activeTab === tab
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                {label}
              </button>
            ))}
          </nav>
        </div>

        <div className="p-6">
          {selectedComponent ? (
            <ComponentDetail component={selectedComponent} onBack={() => setSelectedComponent(null)} />
          ) : (
            <>
              {activeTab === 'overview' && (
                <div className="space-y-6">
                  <div>
                    <h3 className="mb-4 text-lg font-semibold">Project Summary</h3>
                    <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
                      <div>
                        <h4 className="mb-2 flex items-center gap-2 font-medium text-gray-700">
                          <Package className="h-4 w-4" />
                          Languages
                        </h4>
                        <div className="flex flex-wrap gap-2">
                          {project.languages.map((lang) => (
                            <span key={lang} className="rounded-full bg-blue-100 px-3 py-1 text-sm text-blue-800">
                              {lang}
                            </span>
                          ))}
                        </div>
                      </div>
                      <div>
                        <h4 className="mb-2 flex items-center gap-2 font-medium text-gray-700">
                          <GitBranch className="h-4 w-4" />
                          Frameworks
                        </h4>
                        <div className="flex flex-wrap gap-2">
                          {project.frameworks.map((framework) => (
                            <span
                              key={framework}
                              className="rounded-full bg-green-100 px-3 py-1 text-sm text-green-800"
                            >
                              {framework}
                            </span>
                          ))}
                        </div>
                      </div>
                      <div>
                        <h4 className="mb-2 flex items-center gap-2 font-medium text-gray-700">
                          <Database className="h-4 w-4" />
                          Databases
                        </h4>
                        <div className="flex flex-wrap gap-2">
                          {project.databases.map((db) => (
                            <span key={db} className="rounded-full bg-purple-100 px-3 py-1 text-sm text-purple-800">
                              {db}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>

                  <div>
                    <h3 className="mb-4 text-lg font-semibold">Project Path</h3>
                    <p className="rounded bg-gray-50 p-3 font-mono text-gray-600">{project.path}</p>
                  </div>
                </div>
              )}

              {activeTab === 'timeline' && <ProjectTimeline project={project} />}

              {activeTab === 'health' && (
                <ProjectHealth analytics={analytics} totalFiles={project.total_files} />
              )}

              {activeTab === 'metrics' && (
                <ProjectMetrics analytics={analytics} totalLines={project.total_lines} totalFiles={project.total_files} />
              )}

              {activeTab === 'technology' && <TechnologyStack project={project} />}

              {activeTab === 'analytics' && <ProjectAnalytics analytics={analytics} components={components} />}

              {activeTab === 'dependencies' && <DependencyAnalysis components={components} />}

              {activeTab === 'files' && <FileExplorer components={components} />}

              {activeTab === 'components' && (
                <div>
                  <div className="mb-6 flex gap-4">
                    <div className="relative flex-1">
                      <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                      <input
                        type="text"
                        placeholder="Search components..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="w-full rounded-lg border border-gray-300 py-2 pl-10 pr-4 focus:border-transparent focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                    <select
                      value={selectedType}
                      onChange={(e) => setSelectedType(e.target.value)}
                      className="rounded-lg border border-gray-300 px-4 py-2 focus:border-transparent focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="all">All Types</option>
                      {componentTypes.map((type) => (
                        <option key={type} value={type}>
                          {type}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-gray-200">
                          <th className="px-4 py-3 text-left font-medium text-gray-700">Name</th>
                          <th className="px-4 py-3 text-left font-medium text-gray-700">Type</th>
                          <th className="px-4 py-3 text-left font-medium text-gray-700">Language</th>
                          <th className="px-4 py-3 text-left font-medium text-gray-700">Lines</th>
                          <th className="px-4 py-3 text-left font-medium text-gray-700">Complexity</th>
                          <th className="px-4 py-3 text-left font-medium text-gray-700">Dependencies</th>
                          <th className="px-4 py-3 text-left font-medium text-gray-700">Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {filteredComponents.map((component) => (
                          <tr key={component.id} className="border-b border-gray-100 hover:bg-gray-50">
                            <td className="px-4 py-3">
                              <div>
                                <p className="font-medium">{component.name}</p>
                                <p className="text-xs text-gray-500">{component.path}</p>
                              </div>
                            </td>
                            <td className="px-4 py-3">
                              <span className="rounded bg-blue-100 px-2 py-1 text-xs text-blue-800">{component.type}</span>
                            </td>
                            <td className="px-4 py-3">{component.language}</td>
                            <td className="px-4 py-3">{component.line_count}</td>
                            <td className="px-4 py-3">{component.complexity_score}</td>
                            <td className="px-4 py-3">{component.dependencies.length}</td>
                            <td className="px-4 py-3">
                              <button
                                onClick={() => setSelectedComponent(component)}
                                className="text-sm font-medium text-blue-600 hover:text-blue-800"
                              >
                                View Details
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {activeTab === 'graph' && (
                <div>
                  <h3 className="mb-4 text-lg font-semibold">Dependency Graph Visualization</h3>
                  <GraphVisualization projectId={project.id} components={components} height={600} />
                </div>
              )}

              {activeTab === 'data' && (
                <ProjectDataConsole
                  projectId={project.id}
                  projectSummary={projectSummary}
                  analyticsRaw={analyticsRaw}
                  projectHealth={projectHealth}
                  dependencyAnalysis={dependencyAnalysis}
                  components={components}
                />
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default ProjectDetail;
