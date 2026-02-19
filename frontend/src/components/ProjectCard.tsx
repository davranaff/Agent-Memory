import React from 'react';
import { Link } from 'react-router-dom';
import { Project } from '../types';
import { 
  FolderOpen, 
  Code, 
  FileText, 
  ArrowRight,
  Clock,
  CheckCircle,
  AlertTriangle
} from 'lucide-react';

interface ProjectCardProps {
  project: Project;
}

const ProjectCard: React.FC<ProjectCardProps> = ({ project }) => {
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-3 h-3" />;
      case 'in_progress':
        return <Clock className="w-3 h-3" />;
      case 'failed':
        return <AlertTriangle className="w-3 h-3" />;
      default:
        return <Clock className="w-3 h-3" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'in_progress':
        return 'bg-yellow-100 text-yellow-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'Never';
    try {
      const date = new Date(dateString);
      if (Number.isNaN(date.getTime())) return 'Unknown';
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
      const diffDays = Math.floor(diffHours / 24);

      if (diffHours < 1) return 'Just now';
      if (diffHours < 24) return `${diffHours}h ago`;
      if (diffDays < 7) return `${diffDays}d ago`;
      return date.toLocaleDateString();
    } catch {
      return 'Unknown';
    }
  };

  const getComplexityIndicator = (totalFiles: number, totalLines: number) => {
    const avgLinesPerFile = totalFiles > 0 ? totalLines / totalFiles : 0;
    
    if (avgLinesPerFile > 500) return { color: 'text-red-600', label: 'Complex' };
    if (avgLinesPerFile > 200) return { color: 'text-yellow-600', label: 'Moderate' };
    return { color: 'text-green-600', label: 'Simple' };
  };

  const complexity = getComplexityIndicator(project.total_files, project.total_lines);

  return (
    <Link
      to={`/project/${project.id}`}
      className="block bg-white rounded-lg shadow-md hover:shadow-xl transition-all duration-300 border border-gray-200 hover:border-blue-300 group overflow-hidden"
    >
      <div className="p-6">
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-2 flex-1 min-w-0">
            <FolderOpen className="w-5 h-5 text-blue-600 flex-shrink-0" />
            <h3 className="text-lg font-semibold text-gray-900 truncate group-hover:text-blue-600 transition-colors">
              {project.name}
            </h3>
          </div>
          <div className={`flex items-center gap-1 px-2 py-1 text-xs rounded-full ${getStatusColor(project.analysis_status)}`}>
            {getStatusIcon(project.analysis_status)}
            <span className="capitalize">{project.analysis_status.replace('_', ' ')}</span>
          </div>
        </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-2 gap-3 mb-4">
          <div className="flex items-center gap-2 text-sm text-gray-600">
            <FileText className="w-4 h-4 text-blue-500" />
            <span>{project.total_files.toLocaleString()} files</span>
          </div>
          <div className="flex items-center gap-2 text-sm text-gray-600">
            <Code className="w-4 h-4 text-green-500" />
            <span>{project.total_lines.toLocaleString()} lines</span>
          </div>
        </div>

        {/* Architecture and Complexity */}
        <div className="flex items-center justify-between mb-4 p-3 bg-gray-50 rounded-lg">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-gray-700">Architecture:</span>
            <span className="text-sm text-gray-900 capitalize">{project.architecture_type || 'unknown'}</span>
          </div>
          <div className={`flex items-center gap-1 text-sm ${complexity.color}`}>
            <span className="font-medium">{complexity.label}</span>
          </div>
        </div>

        {/* Languages */}
        <div className="mb-4">
          <div className="flex flex-wrap gap-1">
            {project.languages.slice(0, 4).map((lang) => (
              <span
                key={lang}
                className="px-2 py-1 bg-blue-50 text-blue-700 text-xs rounded border border-blue-200"
              >
                {lang}
              </span>
            ))}
            {project.languages.length > 4 && (
              <span className="px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded">
                +{project.languages.length - 4}
              </span>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="pt-4 border-t border-gray-200">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs text-gray-500">
              <Clock className="w-3 h-3" />
              <span>{formatDate(project.last_analyzed)}</span>
            </div>
            <div className="flex items-center gap-1 text-blue-600 opacity-0 group-hover:opacity-100 transition-all duration-200 transform translate-x-1 group-hover:translate-x-0">
              <span className="text-xs font-medium">View Details</span>
              <ArrowRight className="w-3 h-3" />
            </div>
          </div>
          
          {/* Project Path */}
          <div className="mt-2">
            <p className="text-xs text-gray-500 font-mono truncate bg-gray-50 px-2 py-1 rounded">
              {project.path}
            </p>
          </div>
        </div>
      </div>
    </Link>
  );
};

export default ProjectCard;
