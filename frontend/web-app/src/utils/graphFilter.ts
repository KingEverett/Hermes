/**
 * Graph Filtering Utility
 * Filters graph nodes and edges based on various criteria for selective exports
 */

import { Severity } from '../services/graphExport';

export interface NetworkNode {
  id: string;
  type: 'host' | 'service';
  label: string;
  data?: {
    vulnerabilities?: Array<{
      severity: Severity;
      cve_id?: string;
      [key: string]: any;
    }>;
    [key: string]: any;
  };
  [key: string]: any;
}

export interface NetworkEdge {
  source: string;
  target: string;
  [key: string]: any;
}

export interface FilteredGraph {
  nodes: NetworkNode[];
  edges: NetworkEdge[];
}

/**
 * Filter graph by vulnerability severity
 * Keeps all hosts, filters services by vulnerability severity
 * @param nodes - Array of network nodes
 * @param edges - Array of network edges
 * @param severities - Array of severities to include
 * @returns Filtered graph with nodes and edges
 */
export const filterGraphBySeverity = (
  nodes: NetworkNode[],
  edges: NetworkEdge[],
  severities: Severity[]
): FilteredGraph => {
  // Always keep all host nodes
  const hostNodes = nodes.filter(n => n.type === 'host');

  // Filter service nodes by vulnerability severity
  const serviceNodes = nodes.filter(n => {
    if (n.type !== 'service') return false;

    // Check if service has vulnerabilities matching filter
    const vulns = n.data?.vulnerabilities || [];
    return vulns.some(v => severities.includes(v.severity));
  });

  const filteredNodes = [...hostNodes, ...serviceNodes];
  const filteredNodeIds = new Set(filteredNodes.map(n => n.id));

  // Filter edges to only include those connected to remaining nodes
  const filteredEdges = edges.filter(e =>
    filteredNodeIds.has(e.source) && filteredNodeIds.has(e.target)
  );

  return {
    nodes: filteredNodes,
    edges: filteredEdges
  };
};

/**
 * Filter graph to show only vulnerable services
 * @param nodes - Array of network nodes
 * @param edges - Array of network edges
 * @returns Filtered graph showing only hosts and services with vulnerabilities
 */
export const filterGraphByVulnerable = (
  nodes: NetworkNode[],
  edges: NetworkEdge[]
): FilteredGraph => {
  // Keep all hosts
  const hostNodes = nodes.filter(n => n.type === 'host');

  // Keep only services with at least one vulnerability
  const vulnerableServices = nodes.filter(n => {
    if (n.type !== 'service') return false;
    const vulns = n.data?.vulnerabilities || [];
    return vulns.length > 0;
  });

  const filteredNodes = [...hostNodes, ...vulnerableServices];
  const filteredNodeIds = new Set(filteredNodes.map(n => n.id));

  const filteredEdges = edges.filter(e =>
    filteredNodeIds.has(e.source) && filteredNodeIds.has(e.target)
  );

  return {
    nodes: filteredNodes,
    edges: filteredEdges
  };
};

/**
 * Filter graph by specific host IDs
 * @param nodes - Array of network nodes
 * @param edges - Array of network edges
 * @param hostIds - Array of host IDs to include
 * @returns Filtered graph showing only specified hosts and their services
 */
export const filterGraphByHosts = (
  nodes: NetworkNode[],
  edges: NetworkEdge[],
  hostIds: string[]
): FilteredGraph => {
  const hostIdSet = new Set(hostIds);

  // Keep only specified hosts
  const filteredHosts = nodes.filter(n => n.type === 'host' && hostIdSet.has(n.id));

  // Find all edges connected to these hosts
  const connectedServiceIds = new Set<string>();
  edges.forEach(e => {
    if (hostIdSet.has(e.source)) {
      connectedServiceIds.add(e.target);
    }
  });

  // Keep services connected to filtered hosts
  const connectedServices = nodes.filter(n =>
    n.type === 'service' && connectedServiceIds.has(n.id)
  );

  const filteredNodes = [...filteredHosts, ...connectedServices];
  const filteredNodeIds = new Set(filteredNodes.map(n => n.id));

  const filteredEdges = edges.filter(e =>
    filteredNodeIds.has(e.source) && filteredNodeIds.has(e.target)
  );

  return {
    nodes: filteredNodes,
    edges: filteredEdges
  };
};

/**
 * Filter graph by service types
 * @param nodes - Array of network nodes
 * @param edges - Array of network edges
 * @param serviceTypes - Array of service types to include (e.g., ['http', 'ssh'])
 * @returns Filtered graph showing only specified service types
 */
export const filterGraphByServiceTypes = (
  nodes: NetworkNode[],
  edges: NetworkEdge[],
  serviceTypes: string[]
): FilteredGraph => {
  const serviceTypeSet = new Set(serviceTypes.map(t => t.toLowerCase()));

  // Keep all hosts
  const hostNodes = nodes.filter(n => n.type === 'host');

  // Filter services by type
  const filteredServices = nodes.filter(n => {
    if (n.type !== 'service') return false;

    // Extract service type from label or data
    const serviceType = (n.data?.service_name || n.label).toLowerCase();
    return Array.from(serviceTypeSet).some(type => serviceType.includes(type));
  });

  const filteredNodes = [...hostNodes, ...filteredServices];
  const filteredNodeIds = new Set(filteredNodes.map(n => n.id));

  const filteredEdges = edges.filter(e =>
    filteredNodeIds.has(e.source) && filteredNodeIds.has(e.target)
  );

  return {
    nodes: filteredNodes,
    edges: filteredEdges
  };
};

/**
 * Get severity level counts from graph
 * @param nodes - Array of network nodes
 * @returns Object with count of each severity level
 */
export const getSeverityCounts = (nodes: NetworkNode[]): Record<Severity, number> => {
  const counts: Record<Severity, number> = {
    critical: 0,
    high: 0,
    medium: 0,
    low: 0,
    info: 0
  };

  nodes.forEach(node => {
    if (node.type === 'service') {
      const vulns = node.data?.vulnerabilities || [];
      vulns.forEach(v => {
        if (v.severity in counts) {
          counts[v.severity]++;
        }
      });
    }
  });

  return counts;
};
