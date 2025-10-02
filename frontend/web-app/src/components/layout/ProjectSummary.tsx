import React from 'react';

export const ProjectSummary: React.FC = () => {
  return (
    <div className="text-gray-100">
      <h2 className="text-xl font-semibold mb-4">Project Overview</h2>

      {/* Project Info */}
      <div className="mb-6">
        <h3 className="text-lg font-semibold mb-2">Current Project</h3>
        <p className="text-gray-400 text-sm">Select a project from the left sidebar to begin</p>
      </div>

      {/* Summary Statistics */}
      <div className="mb-6">
        <h3 className="text-lg font-semibold mb-3">Statistics</h3>
        <div className="space-y-3">
          <div className="bg-gray-700 rounded p-3">
            <p className="text-2xl font-bold text-blue-400">0</p>
            <p className="text-sm text-gray-400">Hosts</p>
          </div>
          <div className="bg-gray-700 rounded p-3">
            <p className="text-2xl font-bold text-green-400">0</p>
            <p className="text-sm text-gray-400">Services</p>
          </div>
          <div className="bg-gray-700 rounded p-3">
            <p className="text-2xl font-bold text-red-400">0</p>
            <p className="text-sm text-gray-400">Vulnerabilities</p>
          </div>
        </div>
      </div>

      {/* Recent Activity */}
      <div>
        <h3 className="text-lg font-semibold mb-2">Recent Activity</h3>
        <div className="bg-gray-700 rounded p-3 text-sm text-gray-400">
          No recent activity
        </div>
      </div>
    </div>
  );
};
