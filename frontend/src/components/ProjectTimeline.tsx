import React from 'react';
import { Project } from '../types';
import { Clock, Calendar, Activity, TrendingUp } from 'lucide-react';

interface ProjectTimelineProps {
  project: Project;
}

const ProjectTimeline: React.FC<ProjectTimelineProps> = ({ project }) => {
  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'Never';
    try {
      const date = new Date(dateString);
      if (Number.isNaN(date.getTime())) return 'Unknown';
      return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return 'Unknown';
    }
  };

  const getTimeSinceAnalysis = (dateString: string | null) => {
    if (!dateString) return 'Never analyzed';
    try {
      const analyzed = new Date(dateString);
      if (Number.isNaN(analyzed.getTime())) return 'Unknown';
      const now = new Date();
      const diffMs = now.getTime() - analyzed.getTime();
      const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
      const diffDays = Math.floor(diffHours / 24);

      if (diffHours < 1) return 'Just now';
      if (diffHours < 24) return `${diffHours} hours ago`;
      if (diffDays < 7) return `${diffDays} days ago`;
      return formatDate(dateString);
    } catch {
      return 'Unknown';
    }
  };

  const getAnalysisStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'in_progress':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'failed':
        return 'bg-red-100 text-red-800 border-red-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Project Timeline</h3>
        
        <div className="space-y-4">
          <div className="flex items-start gap-4">
            <div className="flex-shrink-0 w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
              <Calendar className="w-5 h-5 text-blue-600" />
            </div>
            <div className="flex-1">
              <h4 className="font-medium text-gray-900">Last Analysis</h4>
              <p className="text-sm text-gray-600">{getTimeSinceAnalysis(project.last_analyzed)}</p>
              <p className="text-xs text-gray-500 mt-1">{formatDate(project.last_analyzed)}</p>
            </div>
          </div>

          <div className="flex items-start gap-4">
            <div className="flex-shrink-0 w-10 h-10 bg-green-100 rounded-full flex items-center justify-center">
              <Activity className="w-5 h-5 text-green-600" />
            </div>
            <div className="flex-1">
              <h4 className="font-medium text-gray-900">Analysis Status</h4>
              <div className="mt-1">
                <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium border ${getAnalysisStatusColor(project.analysis_status)}`}>
                  {project.analysis_status.replace('_', ' ').toUpperCase()}
                </span>
              </div>
            </div>
          </div>

          <div className="flex items-start gap-4">
            <div className="flex-shrink-0 w-10 h-10 bg-purple-100 rounded-full flex items-center justify-center">
              <TrendingUp className="w-5 h-5 text-purple-600" />
            </div>
            <div className="flex-1">
              <h4 className="font-medium text-gray-900">Project Scale</h4>
              <div className="mt-2 grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-gray-600">Files:</span>
                  <span className="ml-2 font-medium">{project.total_files.toLocaleString()}</span>
                </div>
                <div>
                  <span className="text-gray-600">Lines:</span>
                  <span className="ml-2 font-medium">{project.total_lines.toLocaleString()}</span>
                </div>
              </div>
            </div>
          </div>

          <div className="flex items-start gap-4">
            <div className="flex-shrink-0 w-10 h-10 bg-amber-100 rounded-full flex items-center justify-center">
              <Clock className="w-5 h-5 text-amber-600" />
            </div>
            <div className="flex-1">
              <h4 className="font-medium text-gray-900">Project Information</h4>
              <div className="mt-2 space-y-1 text-sm">
                <div className="flex">
                  <span className="text-gray-600 w-20">Name:</span>
                  <span className="font-medium">{project.name}</span>
                </div>
                <div className="flex">
                  <span className="text-gray-600 w-20">Type:</span>
                  <span className="font-medium capitalize">{project.architecture_type || 'unknown'}</span>
                </div>
                <div className="flex">
                  <span className="text-gray-600 w-20">Languages:</span>
                  <span className="font-medium">{project.languages.length}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Analysis Details</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h4 className="font-medium text-gray-700 mb-3">Technical Metrics</h4>
            <div className="space-y-2">
              <div className="flex justify-between py-2 border-b border-gray-100">
                <span className="text-sm text-gray-600">Total Files</span>
                <span className="text-sm font-medium">{project.total_files.toLocaleString()}</span>
              </div>
              <div className="flex justify-between py-2 border-b border-gray-100">
                <span className="text-sm text-gray-600">Total Lines</span>
                <span className="text-sm font-medium">{project.total_lines.toLocaleString()}</span>
              </div>
              <div className="flex justify-between py-2 border-b border-gray-100">
                <span className="text-sm text-gray-600">Avg Lines/File</span>
                <span className="text-sm font-medium">
                  {project.total_files > 0 ? Math.round(project.total_lines / project.total_files) : 0}
                </span>
              </div>
              <div className="flex justify-between py-2">
                <span className="text-sm text-gray-600">Languages</span>
                <span className="text-sm font-medium">{project.languages.length}</span>
              </div>
            </div>
          </div>

          <div>
            <h4 className="font-medium text-gray-700 mb-3">Technology Stack</h4>
            <div className="space-y-2">
              <div className="flex justify-between py-2 border-b border-gray-100">
                <span className="text-sm text-gray-600">Frameworks</span>
                <span className="text-sm font-medium">{project.frameworks.length}</span>
              </div>
              <div className="flex justify-between py-2 border-b border-gray-100">
                <span className="text-sm text-gray-600">Databases</span>
                <span className="text-sm font-medium">{project.databases.length}</span>
              </div>
              <div className="flex justify-between py-2 border-b border-gray-100">
                <span className="text-sm text-gray-600">Build Tools</span>
                <span className="text-sm font-medium">{project.build_tools?.length || 0}</span>
              </div>
              <div className="flex justify-between py-2">
                <span className="text-sm text-gray-600">Architecture</span>
                <span className="text-sm font-medium capitalize">{project.architecture_type || 'unknown'}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProjectTimeline;
