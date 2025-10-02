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

const fetchService = async (serviceId: string): Promise<Service> => {
  const response = await fetch(`/api/v1/services/${serviceId}`);

  if (!response.ok) {
    if (response.status === 404) {
      throw new Error('Service not found');
    }
    throw new Error('Failed to fetch service details');
  }

  return response.json();
};

export const useServiceDetails = (serviceId: string | undefined) => {
  return useQuery({
    queryKey: ['service', serviceId],
    queryFn: () => fetchService(serviceId!),
    enabled: !!serviceId,
    staleTime: 30000, // 30 seconds
    refetchOnWindowFocus: true,
  });
};
