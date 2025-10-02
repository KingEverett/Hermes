import { useQuery } from '@tanstack/react-query';

interface Service {
  id: string;
  host_id: string;
  port: number;
  protocol: 'tcp' | 'udp';
  service_name?: string;
  product?: string;
  version?: string;
  banner?: string;
  cpe?: string;
  confidence: 'high' | 'medium' | 'low';
  created_at: Date | string;
}

const fetchHostServices = async (hostId: string): Promise<Service[]> => {
  const response = await fetch(`/api/v1/hosts/${hostId}/services`);

  if (!response.ok) {
    if (response.status === 404) {
      return []; // Return empty array if no services found
    }
    throw new Error('Failed to fetch host services');
  }

  return response.json();
};

export const useHostServices = (hostId: string | undefined) => {
  return useQuery({
    queryKey: ['host', hostId, 'services'],
    queryFn: () => fetchHostServices(hostId!),
    enabled: !!hostId,
    staleTime: 30000, // 30 seconds
    refetchOnWindowFocus: true,
  });
};
