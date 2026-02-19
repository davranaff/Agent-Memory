import React from 'react';
import { Project } from '../types';

interface TechnologyStackProps {
  project: Project;
}

const TechnologyStack: React.FC<TechnologyStackProps> = ({ project }) => {
  const architecture = project.architecture_type || 'unknown';

  const getLanguageColor = (lang: string) => {
    const colors: Record<string, string> = {
      python: 'bg-blue-100 text-blue-800',
      javascript: 'bg-yellow-100 text-yellow-800',
      typescript: 'bg-blue-100 text-blue-800',
      java: 'bg-red-100 text-red-800',
      go: 'bg-cyan-100 text-cyan-800',
      rust: 'bg-orange-100 text-orange-800',
      csharp: 'bg-purple-100 text-purple-800',
      cpp: 'bg-blue-100 text-blue-800',
      php: 'bg-indigo-100 text-indigo-800',
      ruby: 'bg-red-100 text-red-800',
      swift: 'bg-orange-100 text-orange-800',
      kotlin: 'bg-purple-100 text-purple-800',
      dart: 'bg-blue-100 text-blue-800',
      scala: 'bg-red-100 text-red-800',
      lua: 'bg-blue-100 text-blue-800',
    };
    return colors[lang.toLowerCase()] || 'bg-gray-100 text-gray-800';
  };

  const getFrameworkColor = (framework: string) => {
    const colors: Record<string, string> = {
      fastapi: 'bg-green-100 text-green-800',
      django: 'bg-green-100 text-green-800',
      flask: 'bg-blue-100 text-blue-800',
      react: 'bg-cyan-100 text-cyan-800',
      vue: 'bg-green-100 text-green-800',
      angular: 'bg-red-100 text-red-800',
      express: 'bg-yellow-100 text-yellow-800',
      spring: 'bg-green-100 text-green-800',
      rails: 'bg-red-100 text-red-800',
      laravel: 'bg-red-100 text-red-800',
    };
    return colors[framework.toLowerCase()] || 'bg-gray-100 text-gray-800';
  };

  const getDatabaseColor = (db: string) => {
    const colors: Record<string, string> = {
      postgresql: 'bg-blue-100 text-blue-800',
      mysql: 'bg-blue-100 text-blue-800',
      sqlite: 'bg-gray-100 text-gray-800',
      mongodb: 'bg-green-100 text-green-800',
      redis: 'bg-red-100 text-red-800',
      elasticsearch: 'bg-yellow-100 text-yellow-800',
      cassandra: 'bg-blue-100 text-blue-800',
      dynamodb: 'bg-orange-100 text-orange-800',
    };
    return colors[db.toLowerCase()] || 'bg-gray-100 text-gray-800';
  };

  const getBuildToolColor = (tool: string) => {
    const colors: Record<string, string> = {
      npm: 'bg-red-100 text-red-800',
      yarn: 'bg-blue-100 text-blue-800',
      pip: 'bg-blue-100 text-blue-800',
      docker: 'bg-blue-100 text-blue-800',
      makefile: 'bg-yellow-100 text-yellow-800',
      gradle: 'bg-green-100 text-green-800',
      maven: 'bg-red-100 text-red-800',
      cargo: 'bg-orange-100 text-orange-800',
    };
    return colors[tool.toLowerCase()] || 'bg-gray-100 text-gray-800';
  };

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Programming Languages</h3>
          <div className="space-y-3">
            {project.languages.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {project.languages.map((lang) => (
                  <span
                    key={lang}
                    className={`px-3 py-1 rounded-full text-sm font-medium ${getLanguageColor(lang)}`}
                  >
                    {lang}
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-gray-500 text-center py-4">No languages detected</p>
            )}
            
            <div className="mt-4 p-4 bg-gray-50 rounded">
              <h4 className="font-medium text-gray-700 mb-2">Language Analysis</h4>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">Primary Language:</span>
                  <span className="font-medium">{project.languages[0] || 'N/A'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Language Count:</span>
                  <span className="font-medium">{project.languages.length}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Polyglot:</span>
                  <span className={`font-medium ${project.languages.length > 1 ? 'text-green-600' : 'text-gray-600'}`}>
                    {project.languages.length > 1 ? 'Yes' : 'No'}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Frameworks & Libraries</h3>
          <div className="space-y-3">
            {project.frameworks.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {project.frameworks.map((framework) => (
                  <span
                    key={framework}
                    className={`px-3 py-1 rounded-full text-sm font-medium ${getFrameworkColor(framework)}`}
                  >
                    {framework}
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-gray-500 text-center py-4">No frameworks detected</p>
            )}
            
            <div className="mt-4 p-4 bg-gray-50 rounded">
              <h4 className="font-medium text-gray-700 mb-2">Framework Analysis</h4>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">Framework Count:</span>
                  <span className="font-medium">{project.frameworks.length}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Web Framework:</span>
                  <span className="font-medium">
                    {project.frameworks.some(f => ['fastapi', 'django', 'flask', 'express', 'spring'].includes(f.toLowerCase())) 
                      ? 'Yes' 
                      : 'No'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Frontend:</span>
                  <span className="font-medium">
                    {project.frameworks.some(f => ['react', 'vue', 'angular'].includes(f.toLowerCase())) 
                      ? 'Yes' 
                      : 'No'}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Data Storage</h3>
          <div className="space-y-3">
            {project.databases.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {project.databases.map((db) => (
                  <span
                    key={db}
                    className={`px-3 py-1 rounded-full text-sm font-medium ${getDatabaseColor(db)}`}
                  >
                    {db}
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-gray-500 text-center py-4">No databases detected</p>
            )}
            
            <div className="mt-4 p-4 bg-gray-50 rounded">
              <h4 className="font-medium text-gray-700 mb-2">Database Analysis</h4>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">Database Count:</span>
                  <span className="font-medium">{project.databases.length}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">SQL Database:</span>
                  <span className="font-medium">
                    {project.databases.some(db => ['postgresql', 'mysql', 'sqlite'].includes(db.toLowerCase())) 
                      ? 'Yes' 
                      : 'No'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">NoSQL Database:</span>
                  <span className="font-medium">
                    {project.databases.some(db => ['mongodb', 'redis', 'elasticsearch'].includes(db.toLowerCase())) 
                      ? 'Yes' 
                      : 'No'}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Build & Deployment</h3>
          <div className="space-y-3">
            {project.build_tools.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {project.build_tools.map((tool) => (
                  <span
                    key={tool}
                    className={`px-3 py-1 rounded-full text-sm font-medium ${getBuildToolColor(tool)}`}
                  >
                    {tool}
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-gray-500 text-center py-4">No build tools detected</p>
            )}
            
            <div className="mt-4 p-4 bg-gray-50 rounded">
              <h4 className="font-medium text-gray-700 mb-2">Build Analysis</h4>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">Build Tools:</span>
                  <span className="font-medium">{project.build_tools.length}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Containerized:</span>
                  <span className="font-medium">
                    {project.build_tools.includes('docker') ? 'Yes' : 'No'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Package Manager:</span>
                  <span className="font-medium">
                    {project.build_tools.some(tool => ['npm', 'yarn', 'pip'].includes(tool.toLowerCase())) 
                      ? 'Yes' 
                      : 'No'}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Technology Summary</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="text-center p-4 bg-gray-50 rounded">
            <div className="text-2xl font-bold text-blue-600">{project.languages.length}</div>
            <div className="text-sm text-gray-600">Languages</div>
          </div>
          <div className="text-center p-4 bg-gray-50 rounded">
            <div className="text-2xl font-bold text-green-600">{project.frameworks.length}</div>
            <div className="text-sm text-gray-600">Frameworks</div>
          </div>
          <div className="text-center p-4 bg-gray-50 rounded">
            <div className="text-2xl font-bold text-purple-600">{project.databases.length}</div>
            <div className="text-sm text-gray-600">Databases</div>
          </div>
          <div className="text-center p-4 bg-gray-50 rounded">
            <div className="text-2xl font-bold text-amber-600">{project.build_tools.length}</div>
            <div className="text-sm text-gray-600">Build Tools</div>
          </div>
        </div>
        
        <div className="mt-6 p-4 bg-blue-50 rounded">
          <h4 className="font-medium text-blue-900 mb-2">Architecture Type</h4>
          <div className="flex items-center gap-3">
            <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-medium capitalize">
              {architecture}
            </span>
            <span className="text-sm text-blue-700">
              {architecture === 'mvc' && 'Model-View-Controller pattern'}
              {architecture === 'microservices' && 'Microservices architecture'}
              {architecture === 'layered' && 'Layered architecture'}
              {architecture === 'monolith' && 'Monolithic architecture'}
              {!['mvc', 'microservices', 'layered', 'monolith'].includes(architecture) && 'Custom architecture'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TechnologyStack;
