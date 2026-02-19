import React from 'react';
import { ProjectAnalytics } from '../types';
import { 
  Heart, 
  CheckCircle, 
  TrendingUp,
  Shield,
  Zap,
  Target,
  Activity
} from 'lucide-react';

interface ProjectHealthProps {
  analytics: ProjectAnalytics | null;
  totalFiles: number;
}

const ProjectHealth: React.FC<ProjectHealthProps> = ({ 
  analytics, 
  totalFiles 
}) => {
  if (!analytics) {
    return (
      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <div className="text-center text-gray-500 py-8">
          <Activity className="w-12 h-12 mx-auto mb-4 text-gray-300" />
          <p>No analytics data available</p>
        </div>
      </div>
    );
  }

  const getHealthScore = () => {
    let score = 100;
    
    // Test coverage impact
    if (analytics.test_ratio < 0.8) score -= (0.8 - analytics.test_ratio) * 50;
    
    // Complexity impact
    if (analytics.complexity_score > 7) score -= (analytics.complexity_score - 7) * 10;
    if (analytics.complexity_score > 10) score -= (analytics.complexity_score - 10) * 20;
    
    // Language diversity (moderate is good)
    if (analytics.languages_count === 1) score -= 5;
    if (analytics.languages_count > 5) score -= 10;
    
    return Math.max(0, Math.min(100, Math.round(score)));
  };

  const getHealthColor = (score: number) => {
    if (score >= 80) return 'text-green-600 bg-green-100';
    if (score >= 60) return 'text-yellow-600 bg-yellow-100';
    return 'text-red-600 bg-red-100';
  };

  const getHealthLabel = (score: number) => {
    if (score >= 80) return 'Excellent';
    if (score >= 60) return 'Good';
    if (score >= 40) return 'Fair';
    return 'Needs Attention';
  };

  const getTestCoverageGrade = (ratio: number) => {
    if (ratio >= 0.8) return { grade: 'A', color: 'text-green-600' };
    if (ratio >= 0.6) return { grade: 'B', color: 'text-yellow-600' };
    if (ratio >= 0.4) return { grade: 'C', color: 'text-orange-600' };
    return { grade: 'D', color: 'text-red-600' };
  };

  const getComplexityGrade = (score: number) => {
    if (score <= 3) return { grade: 'A', color: 'text-green-600' };
    if (score <= 5) return { grade: 'B', color: 'text-yellow-600' };
    if (score <= 8) return { grade: 'C', color: 'text-orange-600' };
    return { grade: 'D', color: 'text-red-600' };
  };

  const healthScore = getHealthScore();
  const testGrade = getTestCoverageGrade(analytics.test_ratio);
  const complexityGrade = getComplexityGrade(analytics.complexity_score);

  const recommendations = [];
  
  if (analytics.test_ratio < 0.8) {
    recommendations.push({
      type: 'testing',
      title: 'Improve Test Coverage',
      description: `Increase test coverage from ${(analytics.test_ratio * 100).toFixed(1)}% to 80%+`,
      priority: analytics.test_ratio < 0.4 ? 'high' : 'medium'
    });
  }
  
  if (analytics.complexity_score > 7) {
    recommendations.push({
      type: 'complexity',
      title: 'Reduce Code Complexity',
      description: `Current complexity score (${analytics.complexity_score}) is higher than ideal`,
      priority: analytics.complexity_score > 10 ? 'high' : 'medium'
    });
  }
  
  if (analytics.languages_count === 1 && totalFiles > 50) {
    recommendations.push({
      type: 'diversity',
      title: 'Consider Language Diversity',
      description: 'Large project with single language may benefit from specialized tools',
      priority: 'low'
    });
  }

  return (
    <div className="space-y-6">
      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <div className="flex items-center gap-3 mb-6">
          <Heart className="w-6 h-6 text-red-500" />
          <h3 className="text-lg font-semibold text-gray-900">Project Health Score</h3>
        </div>
        
        <div className="text-center mb-6">
          <div className={`inline-flex items-center justify-center w-24 h-24 rounded-full text-3xl font-bold ${getHealthColor(healthScore)}`}>
            {healthScore}
          </div>
          <p className={`mt-2 text-lg font-medium ${getHealthColor(healthScore).split(' ')[0]}`}>
            {getHealthLabel(healthScore)}
          </p>
          <p className="text-sm text-gray-600 mt-1">Overall project health</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="text-center p-4 bg-gray-50 rounded-lg">
            <div className={`text-2xl font-bold ${testGrade.color}`}>
              {testGrade.grade}
            </div>
            <p className="text-sm text-gray-600 mt-1">Test Coverage</p>
            <p className="text-xs text-gray-500">{(analytics.test_ratio * 100).toFixed(1)}%</p>
          </div>
          
          <div className="text-center p-4 bg-gray-50 rounded-lg">
            <div className={`text-2xl font-bold ${complexityGrade.color}`}>
              {complexityGrade.grade}
            </div>
            <p className="text-sm text-gray-600 mt-1">Complexity</p>
            <p className="text-xs text-gray-500">Score: {analytics.complexity_score}</p>
          </div>
          
          <div className="text-center p-4 bg-gray-50 rounded-lg">
            <div className="text-2xl font-bold text-blue-600">
              {analytics.languages_count}
            </div>
            <p className="text-sm text-gray-600 mt-1">Languages</p>
            <p className="text-xs text-gray-500">Diversity</p>
          </div>
        </div>
      </div>

      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <div className="flex items-center gap-3 mb-4">
          <Shield className="w-5 h-5 text-gray-600" />
          <h3 className="text-lg font-semibold text-gray-900">Quality Metrics</h3>
        </div>
        
        <div className="space-y-4">
          <div className="flex items-center justify-between p-3 bg-gray-50 rounded">
            <div className="flex items-center gap-3">
              <CheckCircle className="w-5 h-5 text-green-600" />
              <span className="text-sm font-medium">Test Coverage</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-24 bg-gray-200 rounded-full h-2">
                <div 
                  className="bg-green-600 h-2 rounded-full" 
                  style={{ width: `${Math.min(analytics.test_ratio * 100, 100)}%` }}
                ></div>
              </div>
              <span className="text-sm font-medium">{(analytics.test_ratio * 100).toFixed(1)}%</span>
            </div>
          </div>

          <div className="flex items-center justify-between p-3 bg-gray-50 rounded">
            <div className="flex items-center gap-3">
              <Zap className="w-5 h-5 text-yellow-600" />
              <span className="text-sm font-medium">Code Complexity</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-24 bg-gray-200 rounded-full h-2">
                <div 
                  className={`h-2 rounded-full ${
                    analytics.complexity_score <= 3 ? 'bg-green-600' :
                    analytics.complexity_score <= 7 ? 'bg-yellow-600' : 'bg-red-600'
                  }`}
                  style={{ width: `${Math.min(analytics.complexity_score * 10, 100)}%` }}
                ></div>
              </div>
              <span className="text-sm font-medium">{analytics.complexity_score}</span>
            </div>
          </div>

          <div className="flex items-center justify-between p-3 bg-gray-50 rounded">
            <div className="flex items-center gap-3">
              <Target className="w-5 h-5 text-blue-600" />
              <span className="text-sm font-medium">Language Diversity</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-24 bg-gray-200 rounded-full h-2">
                <div 
                  className="bg-blue-600 h-2 rounded-full" 
                  style={{ width: `${Math.min(analytics.languages_count * 20, 100)}%` }}
                ></div>
              </div>
              <span className="text-sm font-medium">{analytics.languages_count}</span>
            </div>
          </div>
        </div>
      </div>

      {recommendations.length > 0 && (
        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <div className="flex items-center gap-3 mb-4">
            <TrendingUp className="w-5 h-5 text-gray-600" />
            <h3 className="text-lg font-semibold text-gray-900">Recommendations</h3>
          </div>
          
          <div className="space-y-3">
            {recommendations.map((rec, index) => (
              <div key={index} className="flex items-start gap-3 p-3 border border-gray-200 rounded-lg">
                <div className={`flex-shrink-0 w-2 h-2 rounded-full mt-2 ${
                  rec.priority === 'high' ? 'bg-red-500' :
                  rec.priority === 'medium' ? 'bg-yellow-500' : 'bg-blue-500'
                }`}></div>
                <div className="flex-1">
                  <h4 className="font-medium text-gray-900">{rec.title}</h4>
                  <p className="text-sm text-gray-600 mt-1">{rec.description}</p>
                  <span className={`inline-block mt-2 px-2 py-1 text-xs rounded-full ${
                    rec.priority === 'high' ? 'bg-red-100 text-red-800' :
                    rec.priority === 'medium' ? 'bg-yellow-100 text-yellow-800' : 
                    'bg-blue-100 text-blue-800'
                  }`}>
                    {rec.priority} priority
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default ProjectHealth;
