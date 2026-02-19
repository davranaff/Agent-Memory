import React from 'react';
import { ProjectAnalytics } from '../types';
import { 
  TrendingUp, 
  Code, 
  FileText, 
  CheckCircle,
  BarChart3,
  PieChart,
  Activity
} from 'lucide-react';

interface ProjectMetricsProps {
  analytics: ProjectAnalytics | null;
  totalLines: number;
  totalFiles: number;
}

const ProjectMetrics: React.FC<ProjectMetricsProps> = ({ 
  analytics, 
  totalLines, 
  totalFiles 
}) => {
  const getComplexityColor = (score: number) => {
    if (score <= 3) return 'text-green-600 bg-green-100';
    if (score <= 7) return 'text-yellow-600 bg-yellow-100';
    return 'text-red-600 bg-red-100';
  };

  const getTestRatioColor = (ratio: number) => {
    if (ratio >= 0.8) return 'text-green-600 bg-green-100';
    if (ratio >= 0.5) return 'text-yellow-600 bg-yellow-100';
    return 'text-red-600 bg-red-100';
  };

  const avgLinesPerFile = totalFiles > 0 ? Math.round(totalLines / totalFiles) : 0;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <div className="flex items-center justify-between mb-4">
            <div className="p-2 bg-blue-100 rounded-lg">
              <FileText className="w-5 h-5 text-blue-600" />
            </div>
            <span className="text-sm text-gray-500">Total</span>
          </div>
          <div className="space-y-1">
            <p className="text-2xl font-bold text-gray-900">{totalFiles.toLocaleString()}</p>
            <p className="text-sm text-gray-600">Files</p>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <div className="flex items-center justify-between mb-4">
            <div className="p-2 bg-green-100 rounded-lg">
              <Code className="w-5 h-5 text-green-600" />
            </div>
            <span className="text-sm text-gray-500">Total</span>
          </div>
          <div className="space-y-1">
            <p className="text-2xl font-bold text-gray-900">{totalLines.toLocaleString()}</p>
            <p className="text-sm text-gray-600">Lines of Code</p>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <div className="flex items-center justify-between mb-4">
            <div className="p-2 bg-purple-100 rounded-lg">
              <BarChart3 className="w-5 h-5 text-purple-600" />
            </div>
            <span className="text-sm text-gray-500">Average</span>
          </div>
          <div className="space-y-1">
            <p className="text-2xl font-bold text-gray-900">{avgLinesPerFile.toLocaleString()}</p>
            <p className="text-sm text-gray-600">Lines per File</p>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <div className="flex items-center justify-between mb-4">
            <div className="p-2 bg-amber-100 rounded-lg">
              <PieChart className="w-5 h-5 text-amber-600" />
            </div>
            <span className="text-sm text-gray-500">Diversity</span>
          </div>
          <div className="space-y-1">
            <p className="text-2xl font-bold text-gray-900">{analytics?.languages_count || 0}</p>
            <p className="text-sm text-gray-600">Languages</p>
          </div>
        </div>
      </div>

      {analytics && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-white p-6 rounded-lg border border-gray-200">
            <div className="flex items-center gap-3 mb-4">
              <Activity className="w-5 h-5 text-gray-600" />
              <h3 className="font-semibold text-gray-900">Complexity Score</h3>
            </div>
            <div className="flex items-center gap-3">
              <div className={`px-3 py-1 rounded-full text-sm font-medium ${getComplexityColor(analytics.complexity_score)}`}>
                {analytics.complexity_score}
              </div>
              <span className="text-sm text-gray-600">
                {analytics.complexity_score <= 3 ? 'Low' : 
                 analytics.complexity_score <= 7 ? 'Medium' : 'High'}
              </span>
            </div>
            <div className="mt-3 text-sm text-gray-600">
              <p>Lower scores indicate simpler, more maintainable code</p>
            </div>
          </div>

          <div className="bg-white p-6 rounded-lg border border-gray-200">
            <div className="flex items-center gap-3 mb-4">
              <CheckCircle className="w-5 h-5 text-gray-600" />
              <h3 className="font-semibold text-gray-900">Test Coverage</h3>
            </div>
            <div className="flex items-center gap-3">
              <div className={`px-3 py-1 rounded-full text-sm font-medium ${getTestRatioColor(analytics.test_ratio)}`}>
                {(analytics.test_ratio * 100).toFixed(1)}%
              </div>
              <span className="text-sm text-gray-600">
                {analytics.test_ratio >= 0.8 ? 'Excellent' : 
                 analytics.test_ratio >= 0.5 ? 'Good' : 'Needs Improvement'}
              </span>
            </div>
            <div className="mt-3 text-sm text-gray-600">
              <p>Ratio of test files to source files</p>
            </div>
          </div>

          <div className="bg-white p-6 rounded-lg border border-gray-200">
            <div className="flex items-center gap-3 mb-4">
              <TrendingUp className="w-5 h-5 text-gray-600" />
              <h3 className="font-semibold text-gray-900">Project Health</h3>
            </div>
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Maintainability</span>
                <span className={`font-medium ${getComplexityColor(analytics.complexity_score)}`}>
                  {analytics.complexity_score <= 3 ? 'High' : 
                   analytics.complexity_score <= 7 ? 'Medium' : 'Low'}
                </span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Test Quality</span>
                <span className={`font-medium ${getTestRatioColor(analytics.test_ratio)}`}>
                  {analytics.test_ratio >= 0.8 ? 'High' : 
                   analytics.test_ratio >= 0.5 ? 'Medium' : 'Low'}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ProjectMetrics;
