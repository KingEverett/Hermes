import { renderHook, act } from '@testing-library/react';
import { usePanelState } from '../usePanelState';

describe('usePanelState', () => {
  beforeEach(() => {
    localStorage.clear();
    jest.clearAllMocks();
  });

  test('returns default sizes when no saved state exists', () => {
    const { result } = renderHook(() => usePanelState());

    expect(result.current.sizes).toEqual({
      left: 15,
      center: 60,
      right: 25,
    });
  });

  test('loads saved sizes from localStorage', () => {
    const savedSizes = { left: 20, center: 50, right: 30 };
    localStorage.setItem('hermes-panel-layout', JSON.stringify(savedSizes));

    const { result } = renderHook(() => usePanelState());

    expect(result.current.sizes).toEqual(savedSizes);
  });

  test('saves new sizes to localStorage', () => {
    jest.useFakeTimers();
    const { result } = renderHook(() => usePanelState());
    const newSizes = { left: 20, center: 55, right: 25 };

    act(() => {
      result.current.saveSizes(newSizes);
    });

    expect(result.current.sizes).toEqual(newSizes);

    // Fast-forward timers to trigger debounced save
    act(() => {
      jest.advanceTimersByTime(500);
    });

    expect(localStorage.getItem('hermes-panel-layout')).toBe(
      JSON.stringify(newSizes)
    );

    jest.useRealTimers();
  });

  test('handles localStorage load errors gracefully', () => {
    const consoleSpy = jest.spyOn(console, 'warn').mockImplementation();
    localStorage.setItem('hermes-panel-layout', 'invalid-json');

    const { result } = renderHook(() => usePanelState());

    // Should fall back to default sizes
    expect(result.current.sizes).toEqual({
      left: 15,
      center: 60,
      right: 25,
    });

    expect(consoleSpy).toHaveBeenCalledWith(
      'Failed to load panel state:',
      expect.any(Error)
    );

    consoleSpy.mockRestore();
  });

  test('handles localStorage save errors gracefully', () => {
    jest.useFakeTimers();
    const consoleSpy = jest.spyOn(console, 'warn').mockImplementation();
    jest.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('Quota exceeded');
    });

    const { result } = renderHook(() => usePanelState());
    const newSizes = { left: 20, center: 55, right: 25 };

    act(() => {
      result.current.saveSizes(newSizes);
    });

    // State should still update even if save fails
    expect(result.current.sizes).toEqual(newSizes);

    // Fast-forward timers to trigger debounced save (which will fail)
    act(() => {
      jest.advanceTimersByTime(500);
    });

    expect(consoleSpy).toHaveBeenCalledWith(
      'Failed to save panel state:',
      expect.any(Error)
    );

    consoleSpy.mockRestore();
    jest.useRealTimers();
  });

  test('updates sizes multiple times', () => {
    const { result } = renderHook(() => usePanelState());

    act(() => {
      result.current.saveSizes({ left: 10, center: 70, right: 20 });
    });

    expect(result.current.sizes).toEqual({ left: 10, center: 70, right: 20 });

    act(() => {
      result.current.saveSizes({ left: 25, center: 50, right: 25 });
    });

    expect(result.current.sizes).toEqual({ left: 25, center: 50, right: 25 });
  });

  // Debounce tests
  describe('Debouncing', () => {
    beforeEach(() => {
      localStorage.clear();
      jest.clearAllMocks();
    });

    test('debounces localStorage writes with 500ms delay', () => {
      jest.useFakeTimers();
      const setItemSpy = jest.spyOn(Storage.prototype, 'setItem');

      const { result } = renderHook(() => usePanelState());
      const newSizes = { left: 20, center: 55, right: 25 };

      act(() => {
        result.current.saveSizes(newSizes);
      });

      // State should update immediately
      expect(result.current.sizes).toEqual(newSizes);

      // localStorage setItem should NOT have been called yet
      expect(setItemSpy).not.toHaveBeenCalled();

      // Fast-forward time by 500ms
      act(() => {
        jest.advanceTimersByTime(500);
      });

      // Now localStorage setItem should have been called
      expect(setItemSpy).toHaveBeenCalledWith(
        'hermes-panel-layout',
        JSON.stringify(newSizes)
      );

      setItemSpy.mockRestore();
      jest.useRealTimers();
    });

    test('rapid calls only save once after delay', () => {
      jest.useFakeTimers();
      const { result } = renderHook(() => usePanelState());
      const setItemSpy = jest.spyOn(Storage.prototype, 'setItem');

      // Simulate rapid resize events
      act(() => {
        result.current.saveSizes({ left: 10, center: 70, right: 20 });
      });

      act(() => {
        jest.advanceTimersByTime(100);
      });

      act(() => {
        result.current.saveSizes({ left: 15, center: 65, right: 20 });
      });

      act(() => {
        jest.advanceTimersByTime(100);
      });

      act(() => {
        result.current.saveSizes({ left: 20, center: 60, right: 20 });
      });

      // No saves yet
      expect(setItemSpy).not.toHaveBeenCalled();

      // Fast-forward by 500ms
      act(() => {
        jest.advanceTimersByTime(500);
      });

      // Only one save should have occurred (the last one)
      expect(setItemSpy).toHaveBeenCalledTimes(1);
      expect(setItemSpy).toHaveBeenCalledWith(
        'hermes-panel-layout',
        JSON.stringify({ left: 20, center: 60, right: 20 })
      );

      setItemSpy.mockRestore();
      jest.useRealTimers();
    });

    test('cleans up timer on unmount', () => {
      jest.useFakeTimers();
      const { result, unmount } = renderHook(() => usePanelState());
      const clearTimeoutSpy = jest.spyOn(global, 'clearTimeout');

      act(() => {
        result.current.saveSizes({ left: 20, center: 55, right: 25 });
      });

      // Unmount before timer fires
      unmount();

      // clearTimeout should have been called
      expect(clearTimeoutSpy).toHaveBeenCalled();

      clearTimeoutSpy.mockRestore();
      jest.useRealTimers();
    });

    test('state updates immediately but localStorage write is delayed', () => {
      jest.useFakeTimers();
      const { result } = renderHook(() => usePanelState());
      const newSizes = { left: 30, center: 50, right: 20 };

      act(() => {
        result.current.saveSizes(newSizes);
      });

      // Immediate state update
      expect(result.current.sizes).toEqual(newSizes);

      // Delayed localStorage write
      expect(localStorage.getItem('hermes-panel-layout')).toBeNull();

      act(() => {
        jest.advanceTimersByTime(500);
      });

      expect(localStorage.getItem('hermes-panel-layout')).toBe(
        JSON.stringify(newSizes)
      );

      jest.useRealTimers();
    });
  });
});
