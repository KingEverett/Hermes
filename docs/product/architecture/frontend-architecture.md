# Frontend Architecture

## React Application Structure

```
frontend/web-app/
├── public/
│   └── index.html
├── src/
│   ├── components/
│   │   ├── layout/
│   │   │   ├── ThreePanelLayout.tsx
│   │   │   ├── LeftSidebar.tsx
│   │   │   └── RightPanel.tsx
│   │   ├── visualization/
│   │   │   ├── NetworkGraph.tsx
│   │   │   └── GraphControls.tsx
│   │   ├── scan/
│   │   │   ├── ScanImport.tsx
│   │   │   └── ScanProgress.tsx
│   │   └── common/
│   │       └── DataTable.tsx
│   ├── pages/
│   │   ├── Dashboard.tsx
│   │   ├── ProjectView.tsx
│   │   └── Settings.tsx
│   ├── hooks/
│   │   ├── useWebSocket.ts
│   │   └── useNetworkData.ts
│   ├── services/
│   │   └── api.ts
│   ├── stores/
│   │   └── projectStore.ts
│   └── App.tsx
└── package.json
```

## Three-Panel Layout Implementation

```typescript
import React, { useState } from 'react';
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';

export const ThreePanelLayout: React.FC = () => {
  const [selectedNode, setSelectedNode] = useState(null);
  
  return (
    <div className="h-screen bg-gray-900 text-gray-100">
      <PanelGroup direction="horizontal">
        {/* Left Sidebar - Navigation */}
        <Panel defaultSize={15} minSize={10} maxSize={25}>
          <div className="h-full bg-gray-800 border-r border-gray-700 p-4">
            <ProjectBrowser />
            <ScanHistory />
            <FilterPanel />
          </div>
        </Panel>
        
        <PanelResizeHandle className="w-1 bg-gray-700 hover:bg-blue-600" />
        
        {/* Center - Network Visualization */}
        <Panel defaultSize={60}>
          <div className="h-full relative">
            <NetworkGraph onNodeSelect={setSelectedNode} />
            <GraphControls />
          </div>
        </Panel>
        
        <PanelResizeHandle className="w-1 bg-gray-700 hover:bg-blue-600" />
        
        {/* Right Panel - Context Information */}
        <Panel defaultSize={25} minSize={15} maxSize={40}>
          <div className="h-full bg-gray-800 border-l border-gray-700 p-4">
            {selectedNode ? (
              <NodeDetails node={selectedNode} />
            ) : (
              <ProjectSummary />
            )}
          </div>
        </Panel>
      </PanelGroup>
    </div>
  );
};
```

## Network Visualization Component

```typescript
import React, { useRef, useEffect } from 'react';
import * as d3 from 'd3';
import { useNetworkData } from '../hooks/useNetworkData';

export const NetworkGraph: React.FC<{ onNodeSelect: (node: any) => void }> = ({ 
  onNodeSelect 
}) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const { nodes, edges } = useNetworkData();
  
  useEffect(() => {
    if (!svgRef.current || !nodes.length) return;
    
    const svg = d3.select(svgRef.current);
    const width = svgRef.current.clientWidth;
    const height = svgRef.current.clientHeight;
    
    // Clear previous render
    svg.selectAll('*').remove();
    
    // Create zoom container
    const g = svg.append('g');
    
    // Setup zoom
    const zoom = d3.zoom()
      .scaleExtent([0.1, 10])
      .on('zoom', (event) => {
        g.attr('transform', event.transform);
      });
    
    svg.call(zoom);
    
    // Create force simulation
    const simulation = d3.forceSimulation(nodes)
      .force('link', d3.forceLink(edges).id((d: any) => d.id).distance(100))
      .force('charge', d3.forceManyBody().strength(-300))
      .force('center', d3.forceCenter(width / 2, height / 2));
    
    // Draw edges
    const link = g.append('g')
      .selectAll('line')
      .data(edges)
      .enter().append('line')
      .attr('stroke', '#4B5563')
      .attr('stroke-width', 2);
    
    // Draw nodes
    const node = g.append('g')
      .selectAll('g')
      .data(nodes)
      .enter().append('g')
      .on('click', (event, d) => onNodeSelect(d))
      .call(d3.drag()
        .on('start', dragStarted)
        .on('drag', dragged)
        .on('end', dragEnded));
    
    // Node circles with severity-based colors
    node.append('circle')
      .attr('r', d => d.type === 'host' ? 20 : 15)
      .attr('fill', d => {
        if (d.type === 'host') return '#3B82F6';
        if (d.vulnerabilities?.some(v => v.severity === 'critical')) return '#DC2626';
        if (d.vulnerabilities?.some(v => v.severity === 'high')) return '#F59E0B';
        return '#10B981';
      });
    
    // Node labels
    node.append('text')
      .attr('dy', 30)
      .attr('text-anchor', 'middle')
      .attr('fill', '#D1D5DB')
      .style('font-size', '12px')
      .text(d => d.label);
    
    // Simulation tick
    simulation.on('tick', () => {
      link
        .attr('x1', d => d.source.x)
        .attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x)
        .attr('y2', d => d.target.y);
      
      node.attr('transform', d => `translate(${d.x},${d.y})`);
    });
    
    function dragStarted(event, d) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      d.fx = d.x;
      d.fy = d.y;
    }
    
    function dragged(event, d) {
      d.fx = event.x;
      d.fy = event.y;
    }
    
    function dragEnded(event, d) {
      if (!event.active) simulation.alphaTarget(0);
    }
    
  }, [nodes, edges]);
  
  return <svg ref={svgRef} className="w-full h-full" />;
};
```
