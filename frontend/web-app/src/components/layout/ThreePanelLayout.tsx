import React, { useState } from 'react';
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';
import { usePanelState } from '../../hooks/usePanelState';

interface ThreePanelLayoutProps {
  left: React.ReactNode;
  center: React.ReactNode;
  right: React.ReactNode;
}

export const ThreePanelLayout: React.FC<ThreePanelLayoutProps> = ({
  left,
  center,
  right,
}) => {
  const [showLeftPanel, setShowLeftPanel] = useState(false);
  const [showRightPanel, setShowRightPanel] = useState(false);
  const { sizes, saveSizes } = usePanelState();

  const handleResize = (sizes: number[]) => {
    if (sizes.length === 3) {
      saveSizes({
        left: sizes[0],
        center: sizes[1],
        right: sizes[2],
      });
    }
  };

  return (
    <div className="h-screen bg-gray-900 text-gray-100">
      {/* Mobile toggle buttons */}
      <div className="lg:hidden fixed top-4 left-4 z-50 flex gap-2">
        <button
          onClick={() => {
            setShowLeftPanel(!showLeftPanel);
            if (!showLeftPanel) setShowRightPanel(false); // Close right panel when opening left
          }}
          className="bg-gray-800 border border-gray-700 px-3 py-2 rounded hover:bg-gray-700 transition-colors"
          aria-label="Toggle navigation"
        >
          ☰
        </button>
        <button
          onClick={() => {
            setShowRightPanel(!showRightPanel);
            if (!showRightPanel) setShowLeftPanel(false); // Close left panel when opening right
          }}
          className="bg-gray-800 border border-gray-700 px-3 py-2 rounded hover:bg-gray-700 transition-colors"
          aria-label="Toggle details"
        >
          ⓘ
        </button>
      </div>

      {/* Mobile left sidebar overlay */}
      {showLeftPanel && (
        <div className="lg:hidden fixed inset-0 z-40">
          <div
            className="absolute inset-0 bg-black bg-opacity-50"
            onClick={() => setShowLeftPanel(false)}
          />
          <div className="absolute left-0 top-0 bottom-0 w-64 bg-gray-800 shadow-xl">
            {left}
          </div>
        </div>
      )}

      {/* Mobile right panel overlay */}
      {showRightPanel && (
        <div className="lg:hidden fixed inset-0 z-40">
          <div
            className="absolute inset-0 bg-black bg-opacity-50"
            onClick={() => setShowRightPanel(false)}
          />
          <div className="absolute right-0 top-0 bottom-0 w-80 bg-gray-800 shadow-xl">
            {right}
          </div>
        </div>
      )}

      {/* Desktop three-panel layout */}
      <PanelGroup direction="horizontal" className="hidden lg:flex" onLayout={handleResize}>
        {/* Left Sidebar - Navigation */}
        <Panel defaultSize={sizes.left} minSize={10} maxSize={25}>
          {left}
        </Panel>

        <PanelResizeHandle className="w-1 bg-gray-700 hover:bg-blue-600 transition-colors" />

        {/* Center - Network Visualization */}
        <Panel defaultSize={sizes.center}>
          {center}
        </Panel>

        <PanelResizeHandle className="w-1 bg-gray-700 hover:bg-blue-600 transition-colors" />

        {/* Right Panel - Context Information */}
        <Panel defaultSize={sizes.right} minSize={15} maxSize={40}>
          {right}
        </Panel>
      </PanelGroup>

      {/* Mobile center-only view */}
      <div className="lg:hidden h-full">
        {center}
      </div>
    </div>
  );
};
