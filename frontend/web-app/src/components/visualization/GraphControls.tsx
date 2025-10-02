/**
 * GraphControls Component
 *
 * Floating toolbar providing zoom, pan, and navigation controls for the network graph.
 * Positioned in top-right corner with dark theme styling.
 */

import React from 'react';

interface GraphControlsProps {
  onZoomIn: () => void;
  onZoomOut: () => void;
  onFitToScreen: () => void;
  onReset: () => void;
  zoomLevel: number;
}

export const GraphControls: React.FC<GraphControlsProps> = ({
  onZoomIn,
  onZoomOut,
  onFitToScreen,
  onReset,
  zoomLevel
}) => {
  return (
    <div className="absolute top-4 right-4 flex flex-col gap-2 bg-gray-800 border border-gray-700 rounded-lg p-2 shadow-lg z-20">
      <button
        onClick={onZoomIn}
        className="p-2 hover:bg-gray-700 rounded transition-colors text-white"
        aria-label="Zoom in"
        title="Zoom in (+)"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className="h-5 w-5"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v6m3-3H7"
          />
        </svg>
      </button>

      <button
        onClick={onZoomOut}
        className="p-2 hover:bg-gray-700 rounded transition-colors text-white"
        aria-label="Zoom out"
        title="Zoom out (-)"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className="h-5 w-5"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM13 10H7"
          />
        </svg>
      </button>

      <div className="border-t border-gray-700 my-1" />

      <button
        onClick={onFitToScreen}
        className="p-2 hover:bg-gray-700 rounded transition-colors text-white"
        aria-label="Fit to screen"
        title="Fit to screen (F)"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className="h-5 w-5"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4"
          />
        </svg>
      </button>

      <button
        onClick={onReset}
        className="p-2 hover:bg-gray-700 rounded transition-colors text-white"
        aria-label="Reset view"
        title="Reset view (0)"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className="h-5 w-5"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
          />
        </svg>
      </button>

      <div className="text-xs text-gray-400 text-center mt-1 px-1">
        {Math.round(zoomLevel * 100)}%
      </div>
    </div>
  );
};

export default GraphControls;
