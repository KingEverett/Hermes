import React, { useState } from 'react';
import { useValidationQueue } from '../../hooks/useQualityMetrics';
import { useQualityStore } from '../../stores/qualityStore';

const ValidationQueue: React.FC = () => {
  const { filters, setFilters, setSelectedFinding, setShowValidationModal } = useQualityStore();
  const validationFilters = {
    priority: filters.priority || undefined,
    status: filters.status || undefined,
    finding_type: filters.finding_type || undefined,
  };
  const { data, isLoading } = useValidationQueue(validationFilters);
  const [selectedPriority, setSelectedPriority] = useState<string>('');
  const [selectedStatus, setSelectedStatus] = useState<string>('');

  const priorityColors: Record<string, string> = {
    critical: 'bg-red-100 text-red-800',
    high: 'bg-orange-100 text-orange-800',
    medium: 'bg-yellow-100 text-yellow-800',
    low: 'bg-blue-100 text-blue-800',
  };

  const handleFilterChange = () => {
    setFilters({
      priority: selectedPriority || undefined,
      status: selectedStatus || undefined,
      finding_type: undefined,
    });
  };

  const handleReview = (findingId: string) => {
    setSelectedFinding(findingId);
    setShowValidationModal(true);
  };

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4">Validation Queue</h2>
        <p className="text-gray-500">Loading queue items...</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="p-6 border-b border-gray-200">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold">Validation Queue</h2>
          <span className="text-sm text-gray-600">
            {data?.total || 0} items
          </span>
        </div>

        {/* Filters */}
        <div className="flex gap-4">
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Priority
            </label>
            <select
              value={selectedPriority}
              onChange={(e) => {
                setSelectedPriority(e.target.value);
                setTimeout(() => handleFilterChange(), 0);
              }}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
            >
              <option value="">All</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </div>
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Status
            </label>
            <select
              value={selectedStatus}
              onChange={(e) => {
                setSelectedStatus(e.target.value);
                setTimeout(() => handleFilterChange(), 0);
              }}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
            >
              <option value="">All</option>
              <option value="pending">Pending</option>
              <option value="in_review">In Review</option>
              <option value="completed">Completed</option>
            </select>
          </div>
        </div>
      </div>

      {/* Queue Items */}
      <div className="divide-y divide-gray-200">
        {data?.items && data.items.length > 0 ? (
          data.items.map((item) => (
            <div key={item.id} className="p-4 hover:bg-gray-50">
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <span
                      className={`px-2 py-1 rounded text-xs font-medium ${
                        priorityColors[item.priority] || 'bg-gray-100 text-gray-800'
                      }`}
                    >
                      {item.priority.toUpperCase()}
                    </span>
                    <span className="text-sm text-gray-600">{item.finding_type}</span>
                  </div>
                  <div className="text-sm text-gray-900 mb-1">
                    Finding ID: {item.finding_id.slice(0, 8)}...
                  </div>
                  <div className="text-xs text-gray-500">
                    Created: {new Date(item.created_at).toLocaleDateString()}
                  </div>
                </div>
                <button
                  onClick={() => handleReview(item.finding_id)}
                  className="px-4 py-2 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700"
                >
                  Review
                </button>
              </div>
            </div>
          ))
        ) : (
          <div className="p-8 text-center text-gray-500">
            No items in validation queue
          </div>
        )}
      </div>
    </div>
  );
};

export default ValidationQueue;
