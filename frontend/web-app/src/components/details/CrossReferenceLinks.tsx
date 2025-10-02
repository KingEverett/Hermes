import React from 'react';
import { useHostServices } from '../../hooks/useHostServices';
import { useServiceHost } from '../../hooks/useServiceHost';
import { useSharedVulnerabilities } from '../../hooks/useSharedVulnerabilities';

interface Service {
  id: string;
  port: number;
  protocol: string;
  service_name?: string;
  product?: string;
  version?: string;
}

interface SharedVulnItem {
  service: Service;
  shared_cves: string[];
}

interface CrossReferenceLinksProps {
  nodeType: 'host' | 'service';
  nodeId: string;
  hostId?: string; // Required when nodeType is 'service'
  onNodeSelect: (nodeId: string, nodeType: 'host' | 'service') => void;
}

export const CrossReferenceLinks: React.FC<CrossReferenceLinksProps> = ({
  nodeType,
  nodeId,
  hostId,
  onNodeSelect,
}) => {
  const { data: services, isLoading: servicesLoading } = useHostServices(
    nodeType === 'host' ? nodeId : undefined
  );

  const { data: host, isLoading: hostLoading } = useServiceHost(
    nodeType === 'service' ? (hostId || '') : undefined
  );

  const { data: sharedVulns, isLoading: sharedVulnsLoading } = useSharedVulnerabilities(
    nodeType === 'service' ? nodeId : undefined
  );

  const linkClasses = "text-blue-400 hover:text-blue-300 underline cursor-pointer transition-colors flex items-center gap-1";

  return (
    <div className="space-y-6">
      {/* Host Services Links (when viewing a host) */}
      {nodeType === 'host' && (
        <div>
          <h4 className="text-sm font-semibold text-gray-300 mb-3">Services on this Host</h4>
          {servicesLoading ? (
            <div className="animate-pulse space-y-2">
              <div className="h-8 bg-gray-700 rounded"></div>
              <div className="h-8 bg-gray-700 rounded"></div>
            </div>
          ) : services && services.length > 0 ? (
            <div className="space-y-2">
              {services.map((service: Service) => (
                <button
                  key={service.id}
                  onClick={() => onNodeSelect(service.id, 'service')}
                  className="w-full text-left bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded p-3 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-gray-100 font-semibold">
                        Port {service.port}/{service.protocol.toUpperCase()}
                      </div>
                      <div className="text-sm text-gray-400">
                        {service.service_name || 'Unknown Service'}
                        {service.product && ` - ${service.product}`}
                        {service.version && ` ${service.version}`}
                      </div>
                    </div>
                    <svg className="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                  </div>
                </button>
              ))}
            </div>
          ) : (
            <div className="text-gray-500 text-sm">No services detected on this host</div>
          )}
        </div>
      )}

      {/* Parent Host Link (when viewing a service) */}
      {nodeType === 'service' && (
        <div>
          <h4 className="text-sm font-semibold text-gray-300 mb-3">Parent Host</h4>
          {hostLoading ? (
            <div className="animate-pulse">
              <div className="h-16 bg-gray-700 rounded"></div>
            </div>
          ) : host ? (
            <button
              onClick={() => onNodeSelect(host.id, 'host')}
              className="w-full text-left bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded p-3 transition-colors"
            >
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-gray-100 font-semibold font-mono">{host.ip_address}</div>
                  <div className="text-sm text-gray-400">
                    {host.hostname || 'No hostname'}
                    {host.os_family && ` • ${host.os_family}`}
                  </div>
                </div>
                <svg className="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </div>
            </button>
          ) : (
            <div className="text-gray-500 text-sm">Host information not available</div>
          )}
        </div>
      )}

      {/* Shared Vulnerabilities (when viewing a service) */}
      {nodeType === 'service' && (
        <div>
          <h4 className="text-sm font-semibold text-gray-300 mb-3">Shared Vulnerabilities</h4>
          {sharedVulnsLoading ? (
            <div className="animate-pulse space-y-2">
              <div className="h-12 bg-gray-700 rounded"></div>
              <div className="h-12 bg-gray-700 rounded"></div>
            </div>
          ) : sharedVulns && sharedVulns.length > 0 ? (
            <div className="space-y-3">
              <p className="text-xs text-gray-400">
                Other services with common vulnerabilities:
              </p>
              {sharedVulns.map((item: SharedVulnItem) => (
                <div
                  key={item.service.id}
                  className="bg-gray-800 border border-gray-700 rounded p-3"
                >
                  <button
                    onClick={() => onNodeSelect(item.service.id, 'service')}
                    className="w-full text-left mb-2"
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="text-gray-100 font-semibold text-sm">
                          Port {item.service.port}/{item.service.protocol.toUpperCase()}
                        </div>
                        <div className="text-xs text-gray-400">
                          {item.service.service_name || 'Unknown'}
                          {item.service.product && ` - ${item.service.product}`}
                        </div>
                      </div>
                      <svg className="w-4 h-4 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                    </div>
                  </button>

                  {/* Shared CVEs */}
                  <div className="mt-2 space-y-1">
                    <div className="text-xs text-gray-500">Shared CVEs:</div>
                    <div className="flex flex-wrap gap-1">
                      {item.shared_cves.slice(0, 3).map((cve: string) => (
                        <span
                          key={cve}
                          className="text-xs bg-red-900/30 text-red-400 px-2 py-0.5 rounded font-mono"
                        >
                          {cve}
                        </span>
                      ))}
                      {item.shared_cves.length > 3 && (
                        <span className="text-xs text-gray-500">
                          +{item.shared_cves.length - 3} more
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-gray-500 text-sm">No other services with shared vulnerabilities</div>
          )}
        </div>
      )}
    </div>
  );
};
