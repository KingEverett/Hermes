import React, { useState } from 'react';
import { useServiceDetails } from '../../hooks/useServiceDetails';
import { useServiceVulnerabilities } from '../../hooks/useServiceVulnerabilities';

interface ServiceDetailPanelProps {
  serviceId: string;
}

export const ServiceDetailPanel: React.FC<ServiceDetailPanelProps> = ({ serviceId }) => {
  const { data: service, isLoading, error } = useServiceDetails(serviceId);
  const { data: vulnerabilities } = useServiceVulnerabilities(serviceId);
  const [bannerExpanded, setBannerExpanded] = useState(false);

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-4">
        <div className="h-6 bg-gray-700 rounded w-3/4"></div>
        <div className="h-4 bg-gray-700 rounded w-1/2"></div>
        <div className="h-4 bg-gray-700 rounded w-2/3"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-red-400 p-4 bg-red-900/20 rounded border border-red-800">
        <p className="font-semibold mb-2">Unable to load service details</p>
        <p className="text-sm">{error instanceof Error ? error.message : 'An error occurred'}</p>
      </div>
    );
  }

  if (!service) {
    return (
      <div className="text-gray-400 p-4">
        <p>Service not found</p>
      </div>
    );
  }

  const getConfidenceBadge = (confidence: string) => {
    const confidenceColors = {
      high: 'bg-green-600 text-white',
      medium: 'bg-yellow-600 text-white',
      low: 'bg-orange-600 text-white',
    };
    return confidenceColors[confidence as keyof typeof confidenceColors] || 'bg-gray-600 text-white';
  };

  const getSeverityBadge = (severity: string) => {
    const severityColors = {
      critical: 'bg-red-600 text-white border-red-500',
      high: 'bg-orange-600 text-white border-orange-500',
      medium: 'bg-yellow-600 text-white border-yellow-500',
      low: 'bg-blue-600 text-white border-blue-500',
      info: 'bg-gray-600 text-white border-gray-500',
    };
    return severityColors[severity as keyof typeof severityColors] || 'bg-gray-600 text-white border-gray-500';
  };

  return (
    <div className="space-y-6">
      {/* Port and Protocol Section */}
      <div>
        <label className="text-sm text-gray-400 block mb-1">Port / Protocol</label>
        <div className="flex items-center gap-3">
          <span className="font-mono text-2xl font-bold text-gray-100">{service.port}</span>
          <span className="text-gray-400">/</span>
          <span className="text-lg text-gray-300 uppercase">{service.protocol}</span>
        </div>
      </div>

      {/* Service Name Section */}
      <div>
        <label className="text-sm text-gray-400 block mb-1">Service Name</label>
        <span className="text-gray-100 text-lg">
          {service.service_name || <span className="text-gray-500">Unknown</span>}
        </span>
      </div>

      {/* Product and Version Section */}
      {(service.product || service.version) && (
        <div>
          <label className="text-sm text-gray-400 block mb-1">Product / Version</label>
          <div className="text-gray-100">
            {service.product && <span className="font-semibold">{service.product}</span>}
            {service.product && service.version && <span className="text-gray-400 mx-2">•</span>}
            {service.version && <span className="text-gray-300">{service.version}</span>}
          </div>
        </div>
      )}

      {/* Confidence Level Section */}
      <div>
        <label className="text-sm text-gray-400 block mb-1">Detection Confidence</label>
        <span className={`inline-block px-3 py-1 rounded text-sm font-semibold ${getConfidenceBadge(service.confidence)}`}>
          {service.confidence.toUpperCase()}
        </span>
      </div>

      {/* CPE String Section */}
      {service.cpe && (
        <div>
          <label className="text-sm text-gray-400 block mb-1">CPE String</label>
          <code className="block bg-gray-700 px-3 py-2 rounded font-mono text-xs text-gray-200 break-all">
            {service.cpe}
          </code>
        </div>
      )}

      {/* Banner Information Section */}
      {service.banner && (
        <div>
          <label className="text-sm text-gray-400 block mb-1">Banner Information</label>
          <div className="bg-gray-700 rounded overflow-hidden">
            <button
              onClick={() => setBannerExpanded(!bannerExpanded)}
              className="w-full text-left px-3 py-2 text-blue-400 hover:text-blue-300 flex items-center justify-between"
            >
              <span className="text-sm">
                {bannerExpanded ? 'Hide Banner' : 'Show Banner'}
              </span>
              <span className="text-xs">{bannerExpanded ? '▼' : '▶'}</span>
            </button>
            {bannerExpanded && (
              <pre className="px-3 py-2 text-xs text-gray-200 font-mono whitespace-pre-wrap break-all border-t border-gray-600">
                {service.banner}
              </pre>
            )}
          </div>
        </div>
      )}

      {/* Related Vulnerabilities Section */}
      <div>
        <label className="text-sm text-gray-400 block mb-2">Related Vulnerabilities</label>
        {vulnerabilities && vulnerabilities.length > 0 ? (
          <div className="space-y-2">
            {vulnerabilities.slice(0, 5).map((vuln) => (
              <div
                key={vuln.id}
                className="bg-gray-700 border-l-4 rounded px-3 py-2"
                style={{ borderLeftColor: getSeverityBadge(vuln.severity).split(' ')[1] }}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1">
                    {vuln.cve_id && (
                      <div className="font-mono text-sm text-gray-100 font-semibold">{vuln.cve_id}</div>
                    )}
                    <div className="text-xs text-gray-300 mt-1 line-clamp-2">{vuln.description}</div>
                  </div>
                  <div className="flex flex-col items-end gap-1">
                    <span className={`text-xs px-2 py-0.5 rounded font-semibold ${getSeverityBadge(vuln.severity)}`}>
                      {vuln.severity.toUpperCase()}
                    </span>
                    {vuln.cvss_score !== undefined && (
                      <span className="text-xs text-gray-400">CVSS: {vuln.cvss_score.toFixed(1)}</span>
                    )}
                  </div>
                </div>
              </div>
            ))}
            {vulnerabilities.length > 5 && (
              <div className="text-sm text-gray-400 text-center pt-2">
                + {vulnerabilities.length - 5} more vulnerabilities
              </div>
            )}
          </div>
        ) : (
          <span className="text-gray-500">No vulnerabilities identified</span>
        )}
      </div>

      {/* Timestamps Section */}
      <div className="border-t border-gray-700 pt-4">
        <div>
          <label className="text-xs text-gray-500 block">Detected At</label>
          <span className="text-sm text-gray-300">
            {new Date(service.created_at).toLocaleString('en-US', {
              year: 'numeric',
              month: 'short',
              day: 'numeric',
              hour: '2-digit',
              minute: '2-digit',
            })}
          </span>
        </div>
      </div>
    </div>
  );
};
