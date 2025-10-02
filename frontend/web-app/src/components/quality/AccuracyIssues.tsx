import React from 'react';

interface AccuracyIssue {
  type: string;
  severity: string;
  description: string;
  recommendation: string;
}

interface AccuracyIssuesProps {
  issues: AccuracyIssue[];
  loading?: boolean;
}

const AccuracyIssues: React.FC<AccuracyIssuesProps> = ({ issues, loading }) => {
  const severityColors: Record<string, string> = {
    high: 'bg-red-100 border-red-500 text-red-800',
    medium: 'bg-yellow-100 border-yellow-500 text-yellow-800',
    low: 'bg-blue-100 border-blue-500 text-blue-800',
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4">Accuracy Issues</h2>
        <p className="text-gray-500">Loading issues...</p>
      </div>
    );
  }

  if (!issues || issues.length === 0) {
    return null;
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-lg font-semibold mb-4">
        Accuracy Issues
        <span className="ml-2 text-sm font-normal text-gray-600">
          ({issues.length} {issues.length === 1 ? 'issue' : 'issues'} detected)
        </span>
      </h2>

      <div className="space-y-4">
        {issues.map((issue, index) => (
          <div
            key={index}
            className={`border-l-4 p-4 rounded ${
              severityColors[issue.severity] || 'bg-gray-100 border-gray-500 text-gray-800'
            }`}
          >
            <div className="flex items-start justify-between mb-2">
              <div className="font-medium">{issue.type.replace(/_/g, ' ').toUpperCase()}</div>
              <span className="text-xs uppercase px-2 py-1 rounded bg-white bg-opacity-50">
                {issue.severity}
              </span>
            </div>
            <p className="text-sm mb-2">{issue.description}</p>
            <div className="text-sm">
              <span className="font-medium">Recommendation:</span> {issue.recommendation}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default AccuracyIssues;
