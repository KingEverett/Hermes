import { useQuery } from '@tanstack/react-query';

interface Service {
  id: string;
  host_id: string;
  port: number;
  protocol: 'tcp' | 'udp';
  service_name?: string;
  product?: string;
  version?: string;
}

interface SharedVulnerabilityItem {
  service: Service;
  shared_cves: string[];
}

const fetchSharedVulnerabilities = async (serviceId: string): Promise<SharedVulnerabilityItem[]> => {
  const response = await fetch(`/api/v1/services/${serviceId}/shared-vulnerabilities`);

  if (!response.ok) {
    if (response.status === 404) {
      return []; // Return empty array if no shared vulnerabilities found
    }
    throw new Error('Failed to fetch shared vulnerabilities');
  }

  return response.json();
};

export const useSharedVulnerabilities = (serviceId: string | undefined) => {
  return useQuery({
    queryKey: ['service', serviceId, 'shared-vulnerabilities'],
    queryFn: () => fetchSharedVulnerabilities(serviceId!),
    enabled: !!serviceId,
    staleTime: 60000, // 60 seconds (less frequently changing data)
    refetchOnWindowFocus: false,
  });
};
