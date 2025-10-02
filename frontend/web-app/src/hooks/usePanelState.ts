import { useState, useEffect, useCallback, useRef } from 'react';

interface PanelSizes {
  left: number;
  center: number;
  right: number;
}

const DEFAULT_SIZES: PanelSizes = {
  left: 15,
  center: 60,
  right: 25,
};

const STORAGE_KEY = 'hermes-panel-layout';
const DEBOUNCE_DELAY = 500; // 500ms as specified in AC #7

export const usePanelState = () => {
  const [sizes, setSizes] = useState<PanelSizes>(DEFAULT_SIZES);
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Load saved panel sizes on mount
  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const parsedSizes = JSON.parse(saved);
        setSizes(parsedSizes);
      }
    } catch (error) {
      console.warn('Failed to load panel state:', error);
    }
  }, []);

  // Cleanup debounce timer on unmount
  useEffect(() => {
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, []);

  // Save panel sizes with 500ms debouncing to avoid excessive localStorage writes
  const saveSizes = useCallback((newSizes: PanelSizes) => {
    setSizes(newSizes);

    // Clear existing timer
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    // Set new timer to save after delay
    debounceTimerRef.current = setTimeout(() => {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(newSizes));
      } catch (error) {
        console.warn('Failed to save panel state:', error);
      }
    }, DEBOUNCE_DELAY);
  }, []);

  return { sizes, saveSizes };
};
