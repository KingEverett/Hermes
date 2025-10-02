import { useQuery } from '@tanstack/react-query';

interface Reference {
  url: string;
  source: string;
}

interface Vulnerability {
  id: string;
  cve_id?: string;
  cvss_score?: number;
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info';
  description: string;
  remediation?: string;
  exploit_available: boolean;
  references: Reference[];
  cisa_kev: boolean;
  published_date?: Date | string;
  created_at: Date | string;
  updated_at: Date | string;
}

const fetchServiceVulnerabilities = async (serviceId: string): Promise<Vulnerability[]> => {
  const response = await fetch(`/api/v1/services/${serviceId}/vulnerabilities`);

  if (!response.ok) {
    if (response.status === 404) {
      return []; // Return empty array if no vulnerabilities found
    }
    throw new Error('Failed to fetch service vulnerabilities');
  }

  return response.json();
};

export const useServiceVulnerabilities = (serviceId: string | undefined) => {
  return useQuery({
    queryKey: ['service', serviceId, 'vulnerabilities'],
    queryFn: () => fetchServiceVulnerabilities(serviceId!),
    enabled: !!serviceId,
    staleTime: 30000, // 30 seconds
    refetchOnWindowFocus: true,
  });
};
