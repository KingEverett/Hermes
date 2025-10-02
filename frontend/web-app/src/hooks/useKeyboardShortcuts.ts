/**
 * Keyboard Shortcuts Hook
 *
 * Custom hook for managing global keyboard shortcuts for graph navigation.
 * Prevents shortcuts from triggering when user is typing in input fields.
 */

import { useEffect } from 'react';

interface ShortcutHandlers {
  onZoomIn: () => void;
  onZoomOut: () => void;
  onReset: () => void;
  onFit: () => void;
  onSelectAll: () => void;
  onClearSelection: () => void;
}

export const useKeyboardShortcuts = (handlers: ShortcutHandlers) => {
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Ignore if typing in input fields
      if (
        event.target instanceof HTMLInputElement ||
        event.target instanceof HTMLTextAreaElement
      ) {
        return;
      }

      const { key, ctrlKey, metaKey } = event;

      if (key === '+' || key === '=') {
        event.preventDefault();
        handlers.onZoomIn();
      } else if (key === '-') {
        event.preventDefault();
        handlers.onZoomOut();
      } else if (key === '0') {
        event.preventDefault();
        handlers.onReset();
      } else if (key === 'f' || key === 'F') {
        event.preventDefault();
        handlers.onFit();
      } else if ((ctrlKey || metaKey) && key === 'a') {
        event.preventDefault();
        handlers.onSelectAll();
      } else if (key === 'Escape') {
        event.preventDefault();
        handlers.onClearSelection();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handlers]);
};
