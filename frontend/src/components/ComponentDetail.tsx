import React, { useState } from 'react';
import { Component } from '../types';
import { 
  Code, 
  FileText, 
  GitBranch, 
  Package, 
  ExternalLink,
  Copy,
  ChevronDown,
  ChevronRight
} from 'lucide-react';

interface ComponentDetailProps {
  component: Component;
  onBack?: () => void;
}

const ComponentDetail: React.FC<ComponentDetailProps> = ({ component, onBack }) => {
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['overview']));

  const toggleSection = (section: string) => {
    const newExpanded = new Set(expandedSections);
    if (newExpanded.has(section)) {
      newExpanded.delete(section);
    } else {
      newExpanded.add(section);
    }
    setExpandedSections(newExpanded);
  };

  const getComplexityColor = (score: number) => {
    if (score <= 5) return 'bg-green-100 text-green-800';
    if (score <= 10) return 'bg-yellow-100 text-yellow-800';
    return 'bg-red-100 text-red-800';
  };

  const getComplexityLabel = (score: number) => {
    if (score <= 5) return 'Simple';
    if (score <= 10) return 'Moderate';
    return 'Complex';
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const SectionHeader: React.FC<{ 
    title: string; 
    section: string; 
    icon: React.ReactNode;
    count?: number;
  }> = ({ title, section, icon, count }) => (
    <button
      onClick={() => toggleSection(section)}
      className="flex items-center gap-3 w-full text-left hover:bg-gray-50 p-2 rounded"
    >
      {expandedSections.has(section) ? (
        <ChevronDown className="w-4 h-4 text-gray-500" />
      ) : (
        <ChevronRight className="w-4 h-4 text-gray-500" />
      )}
      {icon}
      <span className="font-medium text-gray-900">{title}</span>
      {count !== undefined && (
        <span className="text-sm text-gray-500">({count})</span>
      )}
    </button>
  );

  return (
    <div className="space-y-6">
      {onBack && (
        <button
          onClick={onBack}
          className="flex items-center gap-2 text-blue-600 hover:text-blue-800"
        >
          ← Back to Components
        </button>
      )}

      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="flex items-start justify-between mb-6">
          <div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">{component.name}</h2>
            <p className="text-gray-600 font-mono text-sm bg-gray-50 p-2 rounded">
              {component.path}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className={`px-3 py-1 rounded-full text-sm font-medium ${getComplexityColor(component.complexity_score)}`}>
              {getComplexityLabel(component.complexity_score)} ({component.complexity_score})
            </span>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-100 rounded-lg">
              <Code className="w-4 h-4 text-blue-600" />
            </div>
            <div>
              <p className="text-sm text-gray-600">Type</p>
              <p className="font-medium">{component.type}</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="p-2 bg-green-100 rounded-lg">
              <FileText className="w-4 h-4 text-green-600" />
            </div>
            <div>
              <p className="text-sm text-gray-600">Lines</p>
              <p className="font-medium">{component.line_count}</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="p-2 bg-purple-100 rounded-lg">
              <Package className="w-4 h-4 text-purple-600" />
            </div>
            <div>
              <p className="text-sm text-gray-600">Language</p>
              <p className="font-medium">{component.language}</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="p-2 bg-amber-100 rounded-lg">
              <GitBranch className="w-4 h-4 text-amber-600" />
            </div>
            <div>
              <p className="text-sm text-gray-600">Dependencies</p>
              <p className="font-medium">{component.dependencies.length}</p>
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <div className="border border-gray-200 rounded-lg">
            <SectionHeader
              title="Overview"
              section="overview"
              icon={<Code className="w-4 h-4" />}
            />
            {expandedSections.has('overview') && (
              <div className="p-4 border-t border-gray-200">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <h4 className="font-medium text-gray-700 mb-2">Component Details</h4>
                    <dl className="space-y-2">
                      <div className="flex justify-between">
                        <dt className="text-sm text-gray-600">ID:</dt>
                        <dd className="text-sm font-mono">{component.id}</dd>
                      </div>
                      <div className="flex justify-between">
                        <dt className="text-sm text-gray-600">Name:</dt>
                        <dd className="text-sm font-medium">{component.name}</dd>
                      </div>
                      <div className="flex justify-between">
                        <dt className="text-sm text-gray-600">Type:</dt>
                        <dd className="text-sm">{component.type}</dd>
                      </div>
                    </dl>
                  </div>
                  <div>
                    <h4 className="font-medium text-gray-700 mb-2">Metrics</h4>
                    <dl className="space-y-2">
                      <div className="flex justify-between">
                        <dt className="text-sm text-gray-600">Lines of Code:</dt>
                        <dd className="text-sm font-medium">{component.line_count}</dd>
                      </div>
                      <div className="flex justify-between">
                        <dt className="text-sm text-gray-600">Complexity:</dt>
                        <dd className="text-sm">
                          <span className={`px-2 py-1 rounded text-xs ${getComplexityColor(component.complexity_score)}`}>
                            {component.complexity_score}
                          </span>
                        </dd>
                      </div>
                      <div className="flex justify-between">
                        <dt className="text-sm text-gray-600">Language:</dt>
                        <dd className="text-sm">{component.language}</dd>
                      </div>
                    </dl>
                  </div>
                </div>
              </div>
            )}
          </div>

          <div className="border border-gray-200 rounded-lg">
            <SectionHeader
              title="Dependencies"
              section="dependencies"
              icon={<GitBranch className="w-4 h-4" />}
              count={component.dependencies.length}
            />
            {expandedSections.has('dependencies') && (
              <div className="p-4 border-t border-gray-200">
                {component.dependencies.length > 0 ? (
                  <div className="space-y-2">
                    {component.dependencies.map((dep, index) => (
                      <div
                        key={index}
                        className="flex items-center justify-between p-2 bg-gray-50 rounded hover:bg-gray-100"
                      >
                        <span className="font-mono text-sm">{dep}</span>
                        <button
                          onClick={() => copyToClipboard(dep)}
                          className="p-1 hover:bg-gray-200 rounded"
                          title="Copy to clipboard"
                        >
                          <Copy className="w-3 h-3 text-gray-500" />
                        </button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-gray-500 text-center py-4">No dependencies found</p>
                )}
              </div>
            )}
          </div>

          <div className="border border-gray-200 rounded-lg">
            <SectionHeader
              title="Exports"
              section="exports"
              icon={<ExternalLink className="w-4 h-4" />}
              count={component.exports.length}
            />
            {expandedSections.has('exports') && (
              <div className="p-4 border-t border-gray-200">
                {component.exports.length > 0 ? (
                  <div className="space-y-2">
                    {component.exports.map((exp, index) => (
                      <div
                        key={index}
                        className="flex items-center justify-between p-2 bg-gray-50 rounded hover:bg-gray-100"
                      >
                        <span className="font-mono text-sm">{exp}</span>
                        <button
                          onClick={() => copyToClipboard(exp)}
                          className="p-1 hover:bg-gray-200 rounded"
                          title="Copy to clipboard"
                        >
                          <Copy className="w-3 h-3 text-gray-500" />
                        </button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-gray-500 text-center py-4">No exports found</p>
                )}
              </div>
            )}
          </div>

          <div className="border border-gray-200 rounded-lg">
            <SectionHeader
              title="File Information"
              section="fileinfo"
              icon={<FileText className="w-4 h-4" />}
            />
            {expandedSections.has('fileinfo') && (
              <div className="p-4 border-t border-gray-200">
                <div className="space-y-3">
                  <div>
                    <h4 className="font-medium text-gray-700 mb-2">File Path</h4>
                    <div className="flex items-center gap-2">
                      <p className="font-mono text-sm bg-gray-50 p-2 rounded flex-1">
                        {component.path}
                      </p>
                      <button
                        onClick={() => copyToClipboard(component.path)}
                        className="p-2 hover:bg-gray-200 rounded"
                        title="Copy path"
                      >
                        <Copy className="w-4 h-4 text-gray-500" />
                      </button>
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <h4 className="font-medium text-gray-700 mb-2">File Statistics</h4>
                      <dl className="space-y-1">
                        <div className="flex justify-between">
                          <dt className="text-sm text-gray-600">Line Count:</dt>
                          <dd className="text-sm font-medium">{component.line_count}</dd>
                        </div>
                        <div className="flex justify-between">
                          <dt className="text-sm text-gray-600">Language:</dt>
                          <dd className="text-sm">{component.language}</dd>
                        </div>
                      </dl>
                    </div>
                    
                    <div>
                      <h4 className="font-medium text-gray-700 mb-2">Component Analysis</h4>
                      <dl className="space-y-1">
                        <div className="flex justify-between">
                          <dt className="text-sm text-gray-600">Type:</dt>
                          <dd className="text-sm">{component.type}</dd>
                        </div>
                        <div className="flex justify-between">
                          <dt className="text-sm text-gray-600">Complexity:</dt>
                          <dd className="text-sm">
                            <span className={`px-2 py-1 rounded text-xs ${getComplexityColor(component.complexity_score)}`}>
                              {component.complexity_score}
                            </span>
                          </dd>
                        </div>
                      </dl>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ComponentDetail;
