import React, { useState } from 'react';
import { Component } from '../types';
import { 
  GitBranch, 
  AlertTriangle, 
  CheckCircle, 
  Info,
  Search,
  ArrowRight
} from 'lucide-react';

interface DependencyAnalysisProps {
  components: Component[];
}

const DependencyAnalysis: React.FC<DependencyAnalysisProps> = ({ components }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedType, setSelectedType] = useState<'all' | 'high' | 'medium' | 'low'>('all');
  const [showCircular, setShowCircular] = useState(false);

  // Analyze dependencies
  const dependencyMap = new Map<string, Set<string>>();
  const reverseDependencyMap = new Map<string, Set<string>>();
  
  components.forEach(component => {
    component.dependencies.forEach(dep => {
      if (!dependencyMap.has(component.id)) {
        dependencyMap.set(component.id, new Set());
      }
      dependencyMap.get(component.id)!.add(dep);
      
      if (!reverseDependencyMap.has(dep)) {
        reverseDependencyMap.set(dep, new Set());
      }
      reverseDependencyMap.get(dep)!.add(component.id);
    });
  });

  // Find circular dependencies
  const findCircularDependencies = (): string[][] => {
    const circular: string[][] = [];
    const visited = new Set<string>();
    const recursionStack = new Set<string>();

    const dfs = (componentId: string, path: string[]): void => {
      if (recursionStack.has(componentId)) {
        const startIndex = path.indexOf(componentId);
        circular.push(path.slice(startIndex));
        return;
      }
      
      if (visited.has(componentId)) return;
      
      visited.add(componentId);
      recursionStack.add(componentId);
      
      const deps = dependencyMap.get(componentId) || new Set();
      deps.forEach(dep => dfs(dep, [...path, componentId]));
      
      recursionStack.delete(componentId);
    };

    components.forEach(component => {
      if (!visited.has(component.id)) {
        dfs(component.id, []);
      }
    });

    return circular;
  };

  const circularDependencies = findCircularDependencies();

  // Calculate dependency statistics
  const getDependencyStats = () => {
    const stats = {
      totalDependencies: 0,
      avgDependencies: 0,
      maxDependencies: 0,
      componentsWithNoDeps: 0,
      mostDependent: [] as Array<{component: Component, count: number}>,
      mostUsed: [] as Array<{component: Component, count: number}>
    };

    components.forEach(component => {
      const depCount = component.dependencies.length;
      stats.totalDependencies += depCount;
      stats.maxDependencies = Math.max(stats.maxDependencies, depCount);
      if (depCount === 0) stats.componentsWithNoDeps++;
    });

    stats.avgDependencies = components.length > 0 ? stats.totalDependencies / components.length : 0;

    // Most dependent components
    stats.mostDependent = components
      .map(component => ({ component, count: component.dependencies.length }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 5);

    // Most used components
    stats.mostUsed = components
      .map(component => ({ 
        component, 
        count: reverseDependencyMap.get(component.id)?.size || 0 
      }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 5);

    return stats;
  };

  const stats = getDependencyStats();

  // Get dependency level
  const getDependencyLevel = (count: number) => {
    if (count >= 20) return { level: 'High', color: 'text-red-600 bg-red-100' };
    if (count >= 10) return { level: 'Medium', color: 'text-yellow-600 bg-yellow-100' };
    if (count >= 5) return { level: 'Medium', color: 'text-yellow-600 bg-yellow-100' };
    return { level: 'Low', color: 'text-green-600 bg-green-100' };
  };

  // Filter components
  const filteredComponents = components.filter(component => {
    const matchesSearch = component.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         component.path.toLowerCase().includes(searchTerm.toLowerCase());
    
    if (selectedType === 'all') return matchesSearch;
    
    const level = getDependencyLevel(component.dependencies.length);
    return matchesSearch && level.level.toLowerCase() === selectedType;
  });

  return (
    <div className="space-y-6">
      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <div className="flex items-center gap-3 mb-2">
            <GitBranch className="w-5 h-5 text-blue-600" />
            <h3 className="font-medium text-gray-700">Total Dependencies</h3>
          </div>
          <p className="text-2xl font-bold text-gray-900">{stats.totalDependencies}</p>
          <p className="text-sm text-gray-600">Across {components.length} components</p>
        </div>

        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <div className="flex items-center gap-3 mb-2">
            <Info className="w-5 h-5 text-green-600" />
            <h3 className="font-medium text-gray-700">Avg Dependencies</h3>
          </div>
          <p className="text-2xl font-bold text-gray-900">{stats.avgDependencies.toFixed(1)}</p>
          <p className="text-sm text-gray-600">Per component</p>
        </div>

        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <div className="flex items-center gap-3 mb-2">
            <CheckCircle className="w-5 h-5 text-green-600" />
            <h3 className="font-medium text-gray-700">No Dependencies</h3>
          </div>
          <p className="text-2xl font-bold text-gray-900">{stats.componentsWithNoDeps}</p>
          <p className="text-sm text-gray-600">Standalone components</p>
        </div>

        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <div className="flex items-center gap-3 mb-2">
            <AlertTriangle className="w-5 h-5 text-red-600" />
            <h3 className="font-medium text-gray-700">Circular Deps</h3>
          </div>
          <p className="text-2xl font-bold text-gray-900">{circularDependencies.length}</p>
          <p className="text-sm text-gray-600">Potential issues</p>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <div className="flex flex-col md:flex-row gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
            <input
              type="text"
              placeholder="Search components..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          
          <select
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value as any)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="all">All Levels</option>
            <option value="high">High Dependencies</option>
            <option value="medium">Medium Dependencies</option>
            <option value="low">Low Dependencies</option>
          </select>

          <button
            onClick={() => setShowCircular(!showCircular)}
            className={`px-4 py-2 rounded-lg border transition-colors ${
              showCircular 
                ? 'bg-red-100 border-red-300 text-red-700' 
                : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50'
            }`}
          >
            {showCircular ? 'Show All' : 'Show Circular'}
          </button>
        </div>
      </div>

      {/* Circular Dependencies */}
      {showCircular && circularDependencies.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <div className="flex items-center gap-2 mb-4">
            <AlertTriangle className="w-5 h-5 text-red-600" />
            <h3 className="text-lg font-semibold text-red-900">Circular Dependencies Detected</h3>
          </div>
          <div className="space-y-3">
            {circularDependencies.map((cycle, index) => (
              <div key={index} className="flex items-center gap-2 p-3 bg-white rounded border border-red-200">
                {cycle.map((componentId: string, idx: number) => {
                  const component = components.find(c => c.id === componentId);
                  return (
                    <React.Fragment key={componentId}>
                      <span className="text-sm font-medium">{component?.name || componentId}</span>
                      {idx < cycle.length - 1 && <ArrowRight className="w-4 h-4 text-red-500" />}
                    </React.Fragment>
                  );
                })}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Components List */}
      <div className="bg-white rounded-lg border border-gray-200">
        <div className="p-6 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">Component Dependencies</h3>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left py-3 px-6 font-medium text-gray-700">Component</th>
                <th className="text-left py-3 px-6 font-medium text-gray-700">Type</th>
                <th className="text-left py-3 px-6 font-medium text-gray-700">Dependencies</th>
                <th className="text-left py-3 px-6 font-medium text-gray-700">Used By</th>
                <th className="text-left py-3 px-6 font-medium text-gray-700">Level</th>
              </tr>
            </thead>
            <tbody>
              {filteredComponents.map((component) => {
                const depLevel = getDependencyLevel(component.dependencies.length);
                const usedByCount = reverseDependencyMap.get(component.id)?.size || 0;
                
                return (
                  <tr key={component.id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="py-3 px-6">
                      <div>
                        <p className="font-medium text-gray-900">{component.name}</p>
                        <p className="text-sm text-gray-500">{component.path}</p>
                      </div>
                    </td>
                    <td className="py-3 px-6">
                      <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs">
                        {component.type}
                      </span>
                    </td>
                    <td className="py-3 px-6">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{component.dependencies.length}</span>
                        {component.dependencies.length > 0 && (
                          <div className="flex -space-x-1">
                            {component.dependencies.slice(0, 3).map((dep, idx) => (
                              <div
                                key={idx}
                                className="w-2 h-2 bg-blue-500 rounded-full border border-white"
                                title={dep}
                              ></div>
                            ))}
                            {component.dependencies.length > 3 && (
                              <div className="w-2 h-2 bg-gray-400 rounded-full border border-white">
                                +{component.dependencies.length - 3}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    </td>
                    <td className="py-3 px-6">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{usedByCount}</span>
                        {usedByCount > 0 && (
                          <div className="flex -space-x-1">
                            {Array.from({ length: Math.min(usedByCount, 3) }).map((_, idx) => (
                              <div
                                key={idx}
                                className="w-2 h-2 bg-green-500 rounded-full border border-white"
                              ></div>
                            ))}
                            {usedByCount > 3 && (
                              <div className="w-2 h-2 bg-gray-400 rounded-full border border-white">
                                +{usedByCount - 3}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    </td>
                    <td className="py-3 px-6">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${depLevel.color}`}>
                        {depLevel.level}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Top Components */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Most Dependent Components</h3>
          <div className="space-y-3">
            {stats.mostDependent.map(({ component, count }, index) => (
              <div key={component.id} className="flex items-center justify-between p-3 bg-gray-50 rounded">
                <div className="flex items-center gap-3">
                  <span className="text-sm font-medium text-gray-500 w-6">#{index + 1}</span>
                  <div>
                    <p className="font-medium text-gray-900">{component.name}</p>
                    <p className="text-sm text-gray-500">{component.type}</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="font-medium text-gray-900">{count}</p>
                  <p className="text-sm text-gray-500">dependencies</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Most Used Components</h3>
          <div className="space-y-3">
            {stats.mostUsed.map(({ component, count }, index) => (
              <div key={component.id} className="flex items-center justify-between p-3 bg-gray-50 rounded">
                <div className="flex items-center gap-3">
                  <span className="text-sm font-medium text-gray-500 w-6">#{index + 1}</span>
                  <div>
                    <p className="font-medium text-gray-900">{component.name}</p>
                    <p className="text-sm text-gray-500">{component.type}</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="font-medium text-gray-900">{count}</p>
                  <p className="text-sm text-gray-500">used by</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default DependencyAnalysis;
