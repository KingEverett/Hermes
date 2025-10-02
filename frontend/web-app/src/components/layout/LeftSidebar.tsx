import React from 'react';

export const LeftSidebar: React.FC = () => {
  return (
    <div className="h-full bg-gray-800 border-r border-gray-700 p-4 overflow-y-auto">
      {/* Project Browser Section */}
      <div className="mb-6">
        <h2 className="text-lg font-semibold mb-3 text-gray-100">Projects</h2>
        <select className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500">
          <option>Select Project</option>
        </select>
      </div>

      {/* Scan History Section */}
      <div className="mb-6">
        <h2 className="text-lg font-semibold mb-3 text-gray-100">Scan History</h2>
        <div className="text-gray-400 text-sm">
          No scans imported yet
        </div>
      </div>

      {/* Filter Panel Section */}
      <div>
        <h2 className="text-lg font-semibold mb-3 text-gray-100">Filters</h2>
        <div className="text-gray-400 text-sm">
          Coming soon...
        </div>
      </div>
    </div>
  );
};
