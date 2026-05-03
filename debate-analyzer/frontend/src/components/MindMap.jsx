import ForceGraph2D from 'react-force-graph-2d';
import { useRef, useCallback, useEffect, useState } from 'react';

const NODE_COLORS = {
  speaker:   '#534AB7',
  topic:     '#1D9E75',
  claim:     '#D85A30',
  consensus: '#639922',
  shift:     '#BA7517',
};

export function MindMap({ graphData, onNodeClick }) {
  const fgRef = useRef();
  const containerRef = useRef();
  const [dimensions, setDimensions] = useState({ width: 800, height: 500 });

  useEffect(() => {
    if (!containerRef.current) return;
    const ro = new ResizeObserver(entries => {
      const { width } = entries[0].contentRect;
      setDimensions({ width, height: Math.min(600, Math.max(400, width * 0.6)) });
    });
    ro.observe(containerRef.current);
    return () => ro.disconnect();
  }, []);

  if (!graphData || !graphData.nodes || !graphData.edges) {
    return <div className="text-slate-400">Loading graph data...</div>;
  }

  // Transform edges: react-force-graph uses "links" not "edges"
  const fgData = {
    nodes: graphData.nodes,
    links: graphData.edges.map(e => ({
      source: e.source, target: e.target,
      label: e.label, strength: e.strength, relation: e.relation
    }))
  };

  const handleNodeClick = useCallback((node) => {
    // Zoom to node on click
    if(fgRef.current) {
        fgRef.current.centerAt(node.x, node.y, 600);
        fgRef.current.zoom(2.5, 600);
    }
    onNodeClick?.(node);
  }, [onNodeClick]);

  return (
    <div ref={containerRef} className="rounded-xl overflow-hidden shadow-2xl border border-slate-700 bg-slate-900/50 w-full">
      <ForceGraph2D
        ref={fgRef}
        graphData={fgData}
        nodeLabel="label"
        nodeVal={node => (node.weight || 5) * 2}
        nodeColor={node => NODE_COLORS[node.type] || '#888780'}
        linkWidth={link => Math.max(0.5, (link.strength || 1) * 0.8)}
        linkLabel="label"
        linkDirectionalArrowLength={5}
        linkDirectionalArrowRelPos={1}
        linkColor={() => '#73726c'}
        cooldownTicks={120}
        onNodeClick={handleNodeClick}
        nodeCanvasObjectMode={() => 'after'}
        nodeCanvasObject={(node, ctx, globalScale) => {
          const label = node.label;
          const fontSize = Math.max(8, 12 / globalScale);
          ctx.font = `${fontSize}px sans-serif`;
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillStyle = '#ffffff';
          ctx.fillText(label, node.x, node.y);
        }}
        width={dimensions.width}
        height={dimensions.height}
      />
    </div>
  );
}
