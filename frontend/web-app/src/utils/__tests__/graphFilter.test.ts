/**
 * Tests for Graph Filtering Utility
 */

import {
  filterGraphBySeverity,
  filterGraphByVulnerable,
  filterGraphByHosts,
  getSeverityCounts,
  NetworkNode,
  NetworkEdge
} from '../graphFilter';

describe('Graph Filtering', () => {
  const mockNodes: NetworkNode[] = [
    { id: 'host_1', type: 'host', label: '192.168.1.1' },
    { id: 'host_2', type: 'host', label: '192.168.1.2' },
    {
      id: 'service_1',
      type: 'service',
      label: '22/tcp',
      data: {
        vulnerabilities: [
          { severity: 'critical', cve_id: 'CVE-2023-1234' }
        ]
      }
    },
    {
      id: 'service_2',
      type: 'service',
      label: '80/tcp',
      data: {
        vulnerabilities: [
          { severity: 'low', cve_id: 'CVE-2023-5678' }
        ]
      }
    },
    {
      id: 'service_3',
      type: 'service',
      label: '443/tcp',
      data: {
        vulnerabilities: []
      }
    }
  ];

  const mockEdges: NetworkEdge[] = [
    { source: 'host_1', target: 'service_1' },
    { source: 'host_1', target: 'service_2' },
    { source: 'host_2', target: 'service_3' }
  ];

  describe('filterGraphBySeverity', () => {
    it('should filter services by critical severity only', () => {
      const result = filterGraphBySeverity(mockNodes, mockEdges, ['critical']);

      expect(result.nodes).toHaveLength(3); // 2 hosts + 1 critical service
      expect(result.nodes.find(n => n.id === 'service_2')).toBeUndefined();
      expect(result.nodes.find(n => n.id === 'service_1')).toBeDefined();
      expect(result.edges).toHaveLength(1); // Only edge to critical service
    });

    it('should keep all hosts regardless of filter', () => {
      const result = filterGraphBySeverity(mockNodes, mockEdges, ['critical']);

      const hostCount = result.nodes.filter(n => n.type === 'host').length;
      expect(hostCount).toBe(2);
    });

    it('should handle multiple severity levels', () => {
      const result = filterGraphBySeverity(mockNodes, mockEdges, ['critical', 'low']);

      expect(result.nodes).toHaveLength(4); // 2 hosts + 2 services
      expect(result.edges).toHaveLength(2);
    });

    it('should return empty services for non-matching severities', () => {
      const result = filterGraphBySeverity(mockNodes, mockEdges, ['high']);

      expect(result.nodes).toHaveLength(2); // Only hosts
      expect(result.edges).toHaveLength(0);
    });
  });

  describe('filterGraphByVulnerable', () => {
    it('should keep only services with vulnerabilities', () => {
      const result = filterGraphByVulnerable(mockNodes, mockEdges);

      const serviceNodes = result.nodes.filter(n => n.type === 'service');
      expect(serviceNodes).toHaveLength(2); // service_1 and service_2 have vulns
      expect(result.nodes.find(n => n.id === 'service_3')).toBeUndefined();
    });

    it('should keep all hosts', () => {
      const result = filterGraphByVulnerable(mockNodes, mockEdges);

      const hostNodes = result.nodes.filter(n => n.type === 'host');
      expect(hostNodes).toHaveLength(2);
    });

    it('should update edges accordingly', () => {
      const result = filterGraphByVulnerable(mockNodes, mockEdges);

      expect(result.edges).toHaveLength(2); // Edges to service_1 and service_2
      expect(result.edges.find(e => e.target === 'service_3')).toBeUndefined();
    });
  });

  describe('filterGraphByHosts', () => {
    it('should keep only specified hosts and their services', () => {
      const result = filterGraphByHosts(mockNodes, mockEdges, ['host_1']);

      expect(result.nodes.filter(n => n.type === 'host')).toHaveLength(1);
      expect(result.nodes.find(n => n.id === 'host_2')).toBeUndefined();
    });

    it('should include services connected to filtered hosts', () => {
      const result = filterGraphByHosts(mockNodes, mockEdges, ['host_1']);

      const serviceNodes = result.nodes.filter(n => n.type === 'service');
      expect(serviceNodes).toHaveLength(2); // service_1 and service_2
      expect(result.nodes.find(n => n.id === 'service_3')).toBeUndefined();
    });
  });

  describe('getSeverityCounts', () => {
    it('should count vulnerabilities by severity', () => {
      const counts = getSeverityCounts(mockNodes);

      expect(counts.critical).toBe(1);
      expect(counts.low).toBe(1);
      expect(counts.high).toBe(0);
      expect(counts.medium).toBe(0);
      expect(counts.info).toBe(0);
    });

    it('should handle nodes with no vulnerabilities', () => {
      const nodesWithoutVulns: NetworkNode[] = [
        { id: 'host_1', type: 'host', label: 'Host 1' },
        { id: 'service_1', type: 'service', label: 'Service 1', data: {} }
      ];

      const counts = getSeverityCounts(nodesWithoutVulns);

      expect(counts.critical).toBe(0);
      expect(counts.high).toBe(0);
    });
  });
});
