import React from 'react';
import { useQualityStore } from '../../stores/qualityStore';
import { useQualityMetrics, useAccuracyIssues } from '../../hooks/useQualityMetrics';
import MetricsCard from './MetricsCard';
import ValidationQueue from './ValidationQueue';
import AccuracyIssues from './AccuracyIssues';

const QualityDashboard: React.FC = () => {
  const { currentProjectId } = useQualityStore();
  const { data: metrics, isLoading: metricsLoading } = useQualityMetrics(currentProjectId);
  const { data: issues, isLoading: issuesLoading } = useAccuracyIssues(currentProjectId);

  if (!currentProjectId) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-gray-500">Please select a project to view quality metrics</p>
      </div>
    );
  }

  if (metricsLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-gray-500">Loading quality metrics...</p>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">Quality Control Dashboard</h1>
        <div className="text-sm text-gray-500">
          {metrics?.calculated_at && (
            <span>Last updated: {new Date(metrics.calculated_at).toLocaleString()}</span>
          )}
        </div>
      </div>

      {/* Metrics Cards Grid */}
      {metrics && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricsCard
            title="Total Findings"
            value={metrics.total_findings}
            subtitle={`${metrics.validated_findings} validated`}
            trend="neutral"
          />
          <MetricsCard
            title="Accuracy Rate"
            value={`${metrics.accuracy_rate}%`}
            subtitle="Validated correct"
            trend={metrics.accuracy_rate >= 80 ? 'up' : metrics.accuracy_rate >= 60 ? 'neutral' : 'down'}
          />
          <MetricsCard
            title="False Positive Rate"
            value={`${metrics.false_positive_rate}%`}
            subtitle={`${metrics.false_positives} false positives`}
            trend={metrics.false_positive_rate <= 10 ? 'up' : metrics.false_positive_rate <= 20 ? 'neutral' : 'down'}
          />
          <MetricsCard
            title="Validation Queue"
            value={metrics.validation_queue_size}
            subtitle="Pending review"
            trend="neutral"
          />
        </div>
      )}

      {/* Confidence Distribution */}
      {metrics && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4">Confidence Distribution</h2>
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center">
              <div className="text-3xl font-bold text-green-600">
                {metrics.confidence_distribution.high}
              </div>
              <div className="text-sm text-gray-600">High Confidence</div>
              <div className="text-xs text-gray-500">(≥ 0.8)</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-yellow-600">
                {metrics.confidence_distribution.medium}
              </div>
              <div className="text-sm text-gray-600">Medium Confidence</div>
              <div className="text-xs text-gray-500">(0.5 - 0.79)</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-red-600">
                {metrics.confidence_distribution.low}
              </div>
              <div className="text-sm text-gray-600">Low Confidence</div>
              <div className="text-xs text-gray-500">(&lt; 0.5)</div>
            </div>
          </div>
        </div>
      )}

      {/* Accuracy Issues */}
      {issues && issues.length > 0 && (
        <AccuracyIssues issues={issues} loading={issuesLoading} />
      )}

      {/* Validation Queue */}
      <ValidationQueue />
    </div>
  );
};

export default QualityDashboard;
