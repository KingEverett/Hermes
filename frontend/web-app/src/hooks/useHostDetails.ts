import { useQuery } from '@tanstack/react-query';

interface HostMetadata {
  open_ports_count?: number;
  vulnerability_summary?: {
    critical: number;
    high: number;
    medium: number;
    low: number;
  };
}

interface Host {
  id: string;
  project_id: string;
  ip_address: string;
  hostname?: string;
  os_family?: string;
  os_details?: string;
  mac_address?: string;
  status: 'up' | 'down' | 'filtered';
  confidence_score?: number;
  first_seen: Date | string;
  last_seen: Date | string;
  metadata: HostMetadata;
}

const fetchHost = async (hostId: string): Promise<Host> => {
  const response = await fetch(`/api/v1/hosts/${hostId}`);

  if (!response.ok) {
    if (response.status === 404) {
      throw new Error('Host not found');
    }
    throw new Error('Failed to fetch host details');
  }

  return response.json();
};

export const useHostDetails = (hostId: string | undefined) => {
  return useQuery({
    queryKey: ['host', hostId],
    queryFn: () => fetchHost(hostId!),
    enabled: !!hostId,
    staleTime: 30000, // 30 seconds
    refetchOnWindowFocus: true,
  });
};
