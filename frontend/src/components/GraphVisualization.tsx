import React, { useState, useEffect, useRef } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { Component, GraphData } from '../types';
import { projectService } from '../services/api';
import { Network, RotateCcw, ZoomIn, ZoomOut } from 'lucide-react';

interface GraphVisualizationProps {
  projectId: string;
  components: Component[];
  height?: number;
}

const GraphVisualization: React.FC<GraphVisualizationProps> = ({ 
  projectId, 
  components,
  height = 600 
}) => {
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], links: [] });
  const [graphStats, setGraphStats] = useState<{ nodes: number; edges: number; cycles: number } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const graphRef = useRef<any>();

  useEffect(() => {
    loadGraphData();
  }, [projectId, components]);

  const buildGraphFromComponents = (source: Component[]): GraphData => {
    const nodes = source.map((component) => ({
      id: component.id,
      name: component.name,
      type: component.type,
      group: component.type,
      color: getNodeColor(component.type),
      size: getNodeSize(component.type),
    }));

    const byId = new Map(source.map((component) => [component.id, component]));
    const byName = new Map(source.map((component) => [component.name, component]));
    const links: Array<{ source: string; target: string; value: number; type: string; color: string }> = [];
    const seen = new Set<string>();

    source.forEach((component) => {
      component.dependencies.forEach((depRaw) => {
        const dep = String(depRaw || '').trim();
        if (!dep) return;
        const target =
          byId.get(dep) ||
          byName.get(dep) ||
          source.find((candidate) => candidate.path.endsWith(dep));
        if (!target) return;
        const key = `${component.id}:${target.id}`;
        if (seen.has(key)) return;
        seen.add(key);
        links.push({
          source: component.id,
          target: target.id,
          value: 1,
          type: 'dependency',
          color: getLinkColor('dependency'),
        });
      });
    });

    return { nodes, links };
  };

  const loadGraphData = async () => {
    try {
      setLoading(true);
      setError(null);
      const localGraph = buildGraphFromComponents(components || []);
      setGraphData(localGraph);

      try {
        const depAnalysis = await projectService.getDependencyAnalysis(projectId);
        setGraphStats({
          nodes: depAnalysis.nodes || localGraph.nodes.length,
          edges: depAnalysis.edges || localGraph.links.length,
          cycles: depAnalysis.cycles_detected || 0,
        });
      } catch {
        setGraphStats({
          nodes: localGraph.nodes.length,
          edges: localGraph.links.length,
          cycles: 0,
        });
      }
    } catch (err) {
      console.error('Failed to load graph data:', err);
      setError('Failed to load dependency graph');
    } finally {
      setLoading(false);
    }
  };

  const getNodeColor = (type: string): string => {
    const colors: Record<string, string> = {
      file: '#94a3b8',
      class: '#3b82f6',
      function: '#10b981',
      async_function: '#f59e0b',
      interface: '#8b5cf6',
      module: '#ef4444',
    };
    return colors[type] || '#64748b';
  };

  const getNodeSize = (type: string): number => {
    const sizes: Record<string, number> = {
      file: 4,
      class: 8,
      function: 6,
      async_function: 6,
      interface: 7,
      module: 5,
    };
    return sizes[type] || 4;
  };

  const getLinkColor = (type?: string): string => {
    const colors: Record<string, string> = {
      import: '#3b82f6',
      dependency: '#10b981',
      inheritance: '#f59e0b',
      reference: '#8b5cf6',
    };
    return colors[type || 'dependency'] || '#94a3b8';
  };

  const handleZoomIn = () => {
    if (graphRef.current) {
      graphRef.current.zoom(1.2);
    }
  };

  const handleZoomOut = () => {
    if (graphRef.current) {
      graphRef.current.zoom(0.8);
    }
  };

  const handleReset = () => {
    if (graphRef.current) {
      graphRef.current.zoomToFit(400);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-red-600">
        <Network className="w-12 h-12 mb-4" />
        <p>{error}</p>
        <button
          onClick={loadGraphData}
          className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="relative bg-white rounded-lg shadow-md border border-gray-200">
      {graphStats && (
        <div className="absolute left-4 top-4 z-10 rounded bg-white/95 px-3 py-2 text-xs text-gray-700 shadow">
          <div>nodes: {graphStats.nodes}</div>
          <div>edges: {graphStats.edges}</div>
          <div>cycles: {graphStats.cycles}</div>
        </div>
      )}
      <div className="absolute top-4 right-4 z-10 flex gap-2">
        <button
          onClick={handleZoomIn}
          className="p-2 bg-white rounded shadow hover:bg-gray-100"
          title="Zoom In"
        >
          <ZoomIn className="w-4 h-4" />
        </button>
        <button
          onClick={handleZoomOut}
          className="p-2 bg-white rounded shadow hover:bg-gray-100"
          title="Zoom Out"
        >
          <ZoomOut className="w-4 h-4" />
        </button>
        <button
          onClick={handleReset}
          className="p-2 bg-white rounded shadow hover:bg-gray-100"
          title="Reset View"
        >
          <RotateCcw className="w-4 h-4" />
        </button>
      </div>

      <ForceGraph2D
        ref={graphRef}
        graphData={graphData}
        width={undefined}
        height={height}
        nodeLabel={(node: any) => `${node.name} (${node.type})`}
        nodeColor={(node: any) => node.color}
        nodeVal={(node: any) => node.size}
        linkColor={(link: any) => link.color}
        linkWidth={2}
        linkDirectionalArrowLength={6}
        linkDirectionalArrowRelPos={1}
        enableNodeDrag={true}
        enableZoomInteraction={true}
        enablePanInteraction={true}
        cooldownTicks={100}
        d3AlphaDecay={0.02}
        d3VelocityDecay={0.3}
      />

      <div className="absolute bottom-4 left-4 bg-white p-3 rounded shadow text-xs">
        <div className="font-semibold mb-2">Node Types:</div>
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-blue-500"></div>
            <span>Class</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-green-500"></div>
            <span>Function</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-amber-500"></div>
            <span>Async Function</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-purple-500"></div>
            <span>Interface</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-slate-400"></div>
            <span>File</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default GraphVisualization;
