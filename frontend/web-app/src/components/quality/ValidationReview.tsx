import React, { useState } from 'react';
import DOMPurify from 'dompurify';
import {
  useValidationHistory,
  useSubmitValidationReview,
} from '../../hooks/useQualityMetrics';
import { useQualityStore } from '../../stores/qualityStore';

interface ValidationReviewProps {
  findingId: string;
  onClose: () => void;
}

const ValidationReview: React.FC<ValidationReviewProps> = ({ findingId, onClose }) => {
  const [decision, setDecision] = useState<'approve' | 'reject' | 'override'>('approve');
  const [justification, setJustification] = useState('');
  const [notes, setNotes] = useState('');
  const [error, setError] = useState<string | null>(null);

  const { data: history, isLoading: historyLoading } = useValidationHistory(findingId);
  const submitReview = useSubmitValidationReview();

  const validateForm = (): boolean => {
    setError(null);

    if (justification.length < 10) {
      setError('Justification must be at least 10 characters long');
      return false;
    }

    if (decision === 'override' && justification.length < 50) {
      setError('Override decisions require detailed justification (minimum 50 characters)');
      return false;
    }

    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    // Sanitize user input
    const sanitizedJustification = DOMPurify.sanitize(justification);
    const sanitizedNotes = DOMPurify.sanitize(notes);

    try {
      await submitReview.mutateAsync({
        findingId,
        request: {
          decision,
          justification: sanitizedJustification,
          notes: sanitizedNotes || undefined,
          validated_by: 'current_user', // TODO: Get from auth context
        },
      });

      // Success - close modal
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit review');
    }
  };

  const getConfidenceColor = (score: number | null) => {
    if (!score) return 'text-gray-600';
    if (score >= 0.8) return 'text-green-600';
    if (score >= 0.5) return 'text-yellow-600';
    return 'text-red-600';
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="p-6 border-b border-gray-200">
          <div className="flex justify-between items-center">
            <h2 className="text-xl font-bold">Validation Review</h2>
            <button
              onClick={onClose}
              className="text-gray-500 hover:text-gray-700"
              aria-label="Close"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6">
          {/* Finding Details */}
          {historyLoading ? (
            <p className="text-gray-500">Loading finding details...</p>
          ) : history ? (
            <div className="mb-6 p-4 bg-gray-50 rounded">
              <h3 className="font-semibold mb-2">Finding Details</h3>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-gray-600">Status:</span>{' '}
                  <span className="font-medium">{history.validation_status || 'pending'}</span>
                </div>
                <div>
                  <span className="text-gray-600">Confidence Score:</span>{' '}
                  <span className={`font-medium ${getConfidenceColor(history.confidence_score)}`}>
                    {history.confidence_score?.toFixed(2) || 'N/A'}
                  </span>
                </div>
                {history.validated_by && (
                  <div>
                    <span className="text-gray-600">Validated By:</span>{' '}
                    <span className="font-medium">{history.validated_by}</span>
                  </div>
                )}
                {history.validated_at && (
                  <div>
                    <span className="text-gray-600">Validated At:</span>{' '}
                    <span className="font-medium">
                      {new Date(history.validated_at).toLocaleString()}
                    </span>
                  </div>
                )}
              </div>
            </div>
          ) : null}

          {/* Validation Checklist */}
          <div className="mb-6 p-4 border border-gray-200 rounded">
            <h3 className="font-semibold mb-3">Validation Checklist</h3>
            <div className="space-y-2 text-sm">
              <label className="flex items-center">
                <input type="checkbox" className="mr-2" />
                <span>CVE ID matches service version</span>
              </label>
              <label className="flex items-center">
                <input type="checkbox" className="mr-2" />
                <span>CVSS score is appropriate</span>
              </label>
              <label className="flex items-center">
                <input type="checkbox" className="mr-2" />
                <span>Exploit availability confirmed</span>
              </label>
              <label className="flex items-center">
                <input type="checkbox" className="mr-2" />
                <span>No known false positive patterns</span>
              </label>
            </div>
          </div>

          {/* Validation Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Decision */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Decision *
              </label>
              <div className="flex gap-4">
                <label className="flex items-center">
                  <input
                    type="radio"
                    name="decision"
                    value="approve"
                    checked={decision === 'approve'}
                    onChange={(e) => setDecision(e.target.value as any)}
                    className="mr-2"
                  />
                  <span>Approve</span>
                </label>
                <label className="flex items-center">
                  <input
                    type="radio"
                    name="decision"
                    value="reject"
                    checked={decision === 'reject'}
                    onChange={(e) => setDecision(e.target.value as any)}
                    className="mr-2"
                  />
                  <span>Reject</span>
                </label>
                <label className="flex items-center">
                  <input
                    type="radio"
                    name="decision"
                    value="override"
                    checked={decision === 'override'}
                    onChange={(e) => setDecision(e.target.value as any)}
                    className="mr-2"
                  />
                  <span>Override</span>
                </label>
              </div>
            </div>

            {/* Justification */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Justification * {decision === 'override' && '(minimum 50 characters)'}
              </label>
              <textarea
                value={justification}
                onChange={(e) => setJustification(e.target.value)}
                rows={4}
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                placeholder="Provide detailed justification for your decision..."
                required
              />
              <p className="text-xs text-gray-500 mt-1">
                {justification.length} characters
              </p>
            </div>

            {/* Notes */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Additional Notes (Optional)
              </label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={2}
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                placeholder="Any additional observations or comments..."
              />
            </div>

            {/* Error Message */}
            {error && (
              <div className="p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
                {error}
              </div>
            )}

            {/* Actions */}
            <div className="flex justify-end gap-3 pt-4">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 border border-gray-300 rounded-md text-sm hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={submitReview.isPending}
                className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700 disabled:bg-gray-400"
              >
                {submitReview.isPending ? 'Submitting...' : 'Submit Review'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default ValidationReview;
