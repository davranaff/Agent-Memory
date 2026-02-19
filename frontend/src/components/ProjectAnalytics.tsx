import React from 'react';
import type { ProjectAnalytics, Component } from '../types';
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  AreaChart,
  Area
} from 'recharts';
import { TrendingUp, FileText, Code, CheckCircle } from 'lucide-react';

interface ProjectAnalyticsProps {
  analytics: ProjectAnalytics | null;
  components: Component[];
}

const ProjectAnalytics: React.FC<ProjectAnalyticsProps> = ({ analytics, components }) => {
  if (!analytics) {
    return (
      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <div className="text-center text-gray-500 py-8">
          <TrendingUp className="w-12 h-12 mx-auto mb-4 text-gray-300" />
          <p>No analytics data available</p>
        </div>
      </div>
    );
  }

  // Component type distribution
  const componentTypeData = components.reduce((acc, component) => {
    const type = component.type;
    acc[type] = (acc[type] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const componentTypeChartData = Object.entries(componentTypeData).map(([type, count]) => ({
    name: type,
    value: count,
    percentage: ((count / components.length) * 100).toFixed(1)
  }));

  // Language distribution
  const languageData = components.reduce((acc, component) => {
    const lang = component.language;
    acc[lang] = (acc[lang] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const languageChartData = Object.entries(languageData).map(([lang, count]) => ({
    name: lang,
    value: count,
    percentage: ((count / components.length) * 100).toFixed(1)
  }));

  // Complexity distribution
  const complexityRanges = [
    { range: '0-5', min: 0, max: 5, count: 0, color: '#10b981' },
    { range: '6-10', min: 6, max: 10, count: 0, color: '#f59e0b' },
    { range: '11-20', min: 11, max: 20, count: 0, color: '#ef4444' },
    { range: '20+', min: 21, max: Infinity, count: 0, color: '#dc2626' }
  ];

  components.forEach(component => {
    const range = complexityRanges.find(r => component.complexity_score >= r.min && component.complexity_score <= r.max);
    if (range) range.count++;
  });

  const complexityChartData = complexityRanges.map(range => ({
    name: range.range,
    value: range.count,
    color: range.color
  }));

  // Line count distribution
  const lineRanges = [
    { range: '0-50', min: 0, max: 50, count: 0 },
    { range: '51-100', min: 51, max: 100, count: 0 },
    { range: '101-200', min: 101, max: 200, count: 0 },
    { range: '201-500', min: 201, max: 500, count: 0 },
    { range: '500+', min: 501, max: Infinity, count: 0 }
  ];

  components.forEach(component => {
    const range = lineRanges.find(r => component.line_count >= r.min && component.line_count <= r.max);
    if (range) range.count++;
  });

  const lineChartData = lineRanges.map(range => ({
    name: range.range,
    value: range.count
  }));

  const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16'];

  const getComplexityLevel = (score: number) => {
    if (score <= 5) return { level: 'Low', color: 'text-green-600' };
    if (score <= 10) return { level: 'Medium', color: 'text-yellow-600' };
    return { level: 'High', color: 'text-red-600' };
  };

  const getTestCoverageLevel = (ratio: number) => {
    if (ratio >= 0.8) return { level: 'Excellent', color: 'text-green-600' };
    if (ratio >= 0.6) return { level: 'Good', color: 'text-yellow-600' };
    if (ratio >= 0.4) return { level: 'Fair', color: 'text-orange-600' };
    return { level: 'Poor', color: 'text-red-600' };
  };

  const complexityLevel = getComplexityLevel(analytics.complexity_score);
  const testCoverageLevel = getTestCoverageLevel(analytics.test_ratio);

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <div className="flex items-center justify-between mb-4">
            <div className="p-2 bg-blue-100 rounded-lg">
              <FileText className="w-5 h-5 text-blue-600" />
            </div>
            <span className="text-sm text-gray-500">Total</span>
          </div>
          <div className="space-y-1">
            <p className="text-2xl font-bold text-gray-900">{analytics.total_files.toLocaleString()}</p>
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
            <p className="text-2xl font-bold text-gray-900">{analytics.total_lines.toLocaleString()}</p>
            <p className="text-sm text-gray-600">Lines of Code</p>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <div className="flex items-center justify-between mb-4">
            <div className={`p-2 rounded-lg ${complexityLevel.color.replace('text', 'bg')?.replace('-600', '-100')}`}>
              <TrendingUp className="w-5 h-5" />
            </div>
            <span className="text-sm text-gray-500">Average</span>
          </div>
          <div className="space-y-1">
            <p className={`text-2xl font-bold ${complexityLevel.color}`}>{analytics.complexity_score}</p>
            <p className="text-sm text-gray-600">Complexity ({complexityLevel.level})</p>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <div className="flex items-center justify-between mb-4">
            <div className={`p-2 rounded-lg ${testCoverageLevel.color.replace('text', 'bg')?.replace('-600', '-100')}`}>
              <CheckCircle className="w-5 h-5" />
            </div>
            <span className="text-sm text-gray-500">Coverage</span>
          </div>
          <div className="space-y-1">
            <p className={`text-2xl font-bold ${testCoverageLevel.color}`}>{(analytics.test_ratio * 100).toFixed(1)}%</p>
            <p className="text-sm text-gray-600">Test Ratio ({testCoverageLevel.level})</p>
          </div>
        </div>
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Component Types Distribution */}
        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Component Types</h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={componentTypeChartData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percentage }) => `${name}: ${percentage}%`}
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
              >
                {componentTypeChartData.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Language Distribution */}
        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Language Distribution</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={languageChartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="value" fill="#3b82f6" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Complexity Distribution */}
        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Complexity Distribution</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={complexityChartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="value" fill="#8884d8">
                {complexityChartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Line Count Distribution */}
        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Lines per File Distribution</h3>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={lineChartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Area type="monotone" dataKey="value" stroke="#8b5cf6" fill="#8b5cf6" fillOpacity={0.6} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Detailed Metrics */}
      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Detailed Metrics</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <div>
            <h4 className="font-medium text-gray-700 mb-3">Project Statistics</h4>
            <div className="space-y-2">
              <div className="flex justify-between py-2 border-b border-gray-100">
                <span className="text-sm text-gray-600">Total Components</span>
                <span className="text-sm font-medium">{components.length}</span>
              </div>
              <div className="flex justify-between py-2 border-b border-gray-100">
                <span className="text-sm text-gray-600">Total Files</span>
                <span className="text-sm font-medium">{analytics.total_files}</span>
              </div>
              <div className="flex justify-between py-2 border-b border-gray-100">
                <span className="text-sm text-gray-600">Total Lines</span>
                <span className="text-sm font-medium">{analytics.total_lines.toLocaleString()}</span>
              </div>
              <div className="flex justify-between py-2">
                <span className="text-sm text-gray-600">Languages</span>
                <span className="text-sm font-medium">{analytics.languages_count}</span>
              </div>
            </div>
          </div>

          <div>
            <h4 className="font-medium text-gray-700 mb-3">Quality Metrics</h4>
            <div className="space-y-2">
              <div className="flex justify-between py-2 border-b border-gray-100">
                <span className="text-sm text-gray-600">Test Coverage</span>
                <span className={`text-sm font-medium ${testCoverageLevel.color}`}>
                  {(analytics.test_ratio * 100).toFixed(1)}%
                </span>
              </div>
              <div className="flex justify-between py-2 border-b border-gray-100">
                <span className="text-sm text-gray-600">Complexity Score</span>
                <span className={`text-sm font-medium ${complexityLevel.color}`}>
                  {analytics.complexity_score}
                </span>
              </div>
              <div className="flex justify-between py-2 border-b border-gray-100">
                <span className="text-sm text-gray-600">Avg Lines/File</span>
                <span className="text-sm font-medium">
                  {analytics.total_files > 0 ? Math.round(analytics.total_lines / analytics.total_files) : 0}
                </span>
              </div>
              <div className="flex justify-between py-2">
                <span className="text-sm text-gray-600">Architecture</span>
                <span className="text-sm font-medium capitalize">{analytics.architecture_type || 'unknown'}</span>
              </div>
            </div>
          </div>

          <div>
            <h4 className="font-medium text-gray-700 mb-3">Component Analysis</h4>
            <div className="space-y-2">
              {Object.entries(componentTypeData).slice(0, 4).map(([type, count]) => (
                <div key={type} className="flex justify-between py-2 border-b border-gray-100">
                  <span className="text-sm text-gray-600 capitalize">{type}</span>
                  <span className="text-sm font-medium">{count}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProjectAnalytics;
