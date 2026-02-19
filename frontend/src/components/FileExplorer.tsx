import React, { useState } from 'react';
import { Component } from '../types';
import { 
  File, 
  FileText, 
  Code, 
  Search,
  ChevronDown,
  ChevronRight,
  Copy,
  Eye,
  GitBranch
} from 'lucide-react';

interface FileExplorerProps {
  components: Component[];
}

interface FileNode {
  name: string;
  path: string;
  type: 'file' | 'folder';
  children?: FileNode[];
  component?: Component;
  expanded?: boolean;
}

const FileExplorer: React.FC<FileExplorerProps> = ({ components }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedFile, setSelectedFile] = useState<Component | null>(null);
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set());
  const [selectedType, setSelectedType] = useState<string>('all');

  // Build file tree structure
  const buildFileTree = (components: Component[]): FileNode[] => {
    const tree: FileNode[] = [];
    const nodeMap = new Map<string, FileNode>();

    components.forEach(component => {
      const parts = component.path.split('/');
      let currentPath = '';
      let currentLevel = tree;

      parts.forEach((part, index) => {
        currentPath = currentPath ? `${currentPath}/${part}` : part;
        const isLastPart = index === parts.length - 1;
        const nodeType = isLastPart ? 'file' : 'folder';

        if (!nodeMap.has(currentPath)) {
          const node: FileNode = {
            name: part,
            path: currentPath,
            type: nodeType,
            children: nodeType === 'folder' ? [] : undefined,
            component: isLastPart ? component : undefined,
            expanded: false
          };

          if (nodeType === 'folder') {
            currentLevel.push(node);
            currentLevel = node.children!;
          } else {
            currentLevel.push(node);
          }

          nodeMap.set(currentPath, node);
        } else {
          const node = nodeMap.get(currentPath)!;
          if (node.type === 'folder') {
            currentLevel = node.children!;
          }
        }
      });
    });

    return tree;
  };

  const fileTree = buildFileTree(components);

  // Filter tree based on search
  const filterTree = (nodes: FileNode[], term: string): FileNode[] => {
    if (!term) return nodes;

    return nodes.reduce((acc: FileNode[], node) => {
      const matchesSearch = node.name.toLowerCase().includes(term.toLowerCase());
      const hasMatchingChildren = node.children ? filterTree(node.children, term).length > 0 : false;

      if (matchesSearch || hasMatchingChildren) {
        const filteredNode = { ...node };
        if (node.children) {
          filteredNode.children = filterTree(node.children, term);
          filteredNode.expanded = true; // Auto-expand if has matching children
        }
        acc.push(filteredNode);
      }

      return acc;
    }, []);
  };

  const filteredTree = filterTree(fileTree, searchTerm);

  // Toggle node expansion
  const toggleNode = (path: string) => {
    const newExpanded = new Set(expandedNodes);
    if (newExpanded.has(path)) {
      newExpanded.delete(path);
    } else {
      newExpanded.add(path);
    }
    setExpandedNodes(newExpanded);
  };

  // Get file icon based on type and extension
  const getFileIcon = (node: FileNode) => {
    if (node.type === 'folder') {
      return expandedNodes.has(node.path) ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />;
    }

    const extension = node.name.split('.').pop()?.toLowerCase();
    switch (extension) {
      case 'py':
        return <Code className="w-4 h-4 text-blue-600" />;
      case 'js':
      case 'jsx':
        return <Code className="w-4 h-4 text-yellow-600" />;
      case 'ts':
      case 'tsx':
        return <Code className="w-4 h-4 text-blue-700" />;
      case 'java':
        return <Code className="w-4 h-4 text-red-600" />;
      case 'go':
        return <Code className="w-4 h-4 text-cyan-600" />;
      case 'rs':
        return <Code className="w-4 h-4 text-orange-600" />;
      case 'cpp':
      case 'c':
      case 'h':
        return <Code className="w-4 h-4 text-gray-600" />;
      case 'md':
        return <FileText className="w-4 h-4 text-gray-600" />;
      case 'json':
      case 'yaml':
      case 'yml':
        return <File className="w-4 h-4 text-green-600" />;
      default:
        return <File className="w-4 h-4 text-gray-500" />;
    }
  };

  // Copy path to clipboard
  const copyPath = (path: string) => {
    navigator.clipboard.writeText(path);
  };

  // Render file tree node
  const renderNode = (node: FileNode, level: number = 0) => {
    const isExpanded = expandedNodes.has(node.path);
    const isSelected = selectedFile?.id === node.component?.id;

    return (
      <div key={node.path}>
        <div
          className={`flex items-center gap-2 py-1 px-2 hover:bg-gray-100 cursor-pointer rounded ${
            isSelected ? 'bg-blue-100' : ''
          }`}
          style={{ paddingLeft: `${level * 20 + 8}px` }}
          onClick={() => {
            if (node.type === 'folder') {
              toggleNode(node.path);
            } else if (node.component) {
              setSelectedFile(node.component);
            }
          }}
        >
          {getFileIcon(node)}
          <span className={`text-sm ${isSelected ? 'text-blue-700 font-medium' : 'text-gray-700'}`}>
            {node.name}
          </span>
          {node.component && (
            <div className="ml-auto flex items-center gap-1">
              <span className={`px-2 py-0.5 text-xs rounded ${
                node.component.type === 'class' ? 'bg-blue-100 text-blue-700' :
                node.component.type === 'function' ? 'bg-green-100 text-green-700' :
                'bg-gray-100 text-gray-700'
              }`}>
                {node.component.type}
              </span>
              <span className="text-xs text-gray-500">
                {node.component.line_count} lines
              </span>
            </div>
          )}
        </div>
        
        {node.type === 'folder' && isExpanded && node.children && (
          <div>
            {node.children.map(child => renderNode(child, level + 1))}
          </div>
        )}
      </div>
    );
  };

  // Get unique file types
  const fileTypes = Array.from(new Set(components.map(c => c.type)));

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* File Tree */}
      <div className="lg:col-span-1">
        <div className="bg-white rounded-lg border border-gray-200">
          <div className="p-4 border-b border-gray-200">
            <h3 className="font-semibold text-gray-900 mb-4">File Explorer</h3>
            
            {/* Search */}
            <div className="relative mb-4">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
              <input
                type="text"
                placeholder="Search files..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
              />
            </div>

            {/* Type Filter */}
            <select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
            >
              <option value="all">All Types</option>
              {fileTypes.map(type => (
                <option key={type} value={type}>{type}</option>
              ))}
            </select>
          </div>

          {/* Tree */}
          <div className="p-4 max-h-96 overflow-y-auto">
            {filteredTree.length > 0 ? (
              filteredTree.map(node => renderNode(node))
            ) : (
              <div className="text-center text-gray-500 py-8">
                <File className="w-8 h-8 mx-auto mb-2 text-gray-300" />
                <p className="text-sm">No files found</p>
              </div>
            )}
          </div>
        </div>

        {/* Statistics */}
        <div className="bg-white rounded-lg border border-gray-200 mt-4 p-4">
          <h4 className="font-medium text-gray-900 mb-3">File Statistics</h4>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600">Total Files:</span>
              <span className="font-medium">{components.length}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Total Lines:</span>
              <span className="font-medium">{components.reduce((sum, c) => sum + c.line_count, 0).toLocaleString()}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Avg Lines/File:</span>
              <span className="font-medium">
                {components.length > 0 ? Math.round(components.reduce((sum, c) => sum + c.line_count, 0) / components.length) : 0}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* File Details */}
      <div className="lg:col-span-2">
        {selectedFile ? (
          <div className="bg-white rounded-lg border border-gray-200">
            <div className="p-6 border-b border-gray-200">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">{selectedFile.name}</h3>
                  <p className="text-sm text-gray-600 font-mono bg-gray-50 p-2 rounded">{selectedFile.path}</p>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => copyPath(selectedFile.path)}
                    className="p-2 hover:bg-gray-100 rounded"
                    title="Copy path"
                  >
                    <Copy className="w-4 h-4 text-gray-500" />
                  </button>
                </div>
              </div>
            </div>

            <div className="p-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                <div>
                  <h4 className="font-medium text-gray-700 mb-3">File Information</h4>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-600">Type:</span>
                      <span className="text-sm font-medium capitalize">{selectedFile.type}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-600">Language:</span>
                      <span className="text-sm font-medium">{selectedFile.language}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-600">Lines:</span>
                      <span className="text-sm font-medium">{selectedFile.line_count}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-600">Complexity:</span>
                      <span className={`text-sm font-medium px-2 py-1 rounded ${
                        selectedFile.complexity_score > 10 ? 'bg-red-100 text-red-800' :
                        selectedFile.complexity_score > 5 ? 'bg-yellow-100 text-yellow-800' :
                        'bg-green-100 text-green-800'
                      }`}>
                        {selectedFile.complexity_score}
                      </span>
                    </div>
                  </div>
                </div>

                <div>
                  <h4 className="font-medium text-gray-700 mb-3">Dependencies</h4>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-600">Count:</span>
                      <span className="text-sm font-medium">{selectedFile.dependencies.length}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-600">Exports:</span>
                      <span className="text-sm font-medium">{selectedFile.exports.length}</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Dependencies List */}
              {selectedFile.dependencies.length > 0 && (
                <div className="mb-6">
                  <h4 className="font-medium text-gray-700 mb-3">Dependencies</h4>
                  <div className="bg-gray-50 rounded p-3 max-h-32 overflow-y-auto">
                    <div className="space-y-1">
                      {selectedFile.dependencies.map((dep, index) => (
                        <div key={index} className="text-sm font-mono text-gray-700 bg-white px-2 py-1 rounded border border-gray-200">
                          {dep}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* Exports List */}
              {selectedFile.exports.length > 0 && (
                <div className="mb-6">
                  <h4 className="font-medium text-gray-700 mb-3">Exports</h4>
                  <div className="bg-gray-50 rounded p-3 max-h-32 overflow-y-auto">
                    <div className="space-y-1">
                      {selectedFile.exports.map((exp, index) => (
                        <div key={index} className="text-sm font-mono text-gray-700 bg-white px-2 py-1 rounded border border-gray-200">
                          {exp}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* Actions */}
              <div className="flex gap-3">
                <button className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
                  <Eye className="w-4 h-4" />
                  View Code
                </button>
                <button className="flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50">
                  <GitBranch className="w-4 h-4" />
                  Show Dependencies
                </button>
              </div>
            </div>
          </div>
        ) : (
          <div className="bg-white rounded-lg border border-gray-200 p-12">
            <div className="text-center text-gray-500">
              <File className="w-12 h-12 mx-auto mb-4 text-gray-300" />
              <p className="text-lg font-medium mb-2">No file selected</p>
              <p className="text-sm">Select a file from the explorer to view details</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default FileExplorer;
