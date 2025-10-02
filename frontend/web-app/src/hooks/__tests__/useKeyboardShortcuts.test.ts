/**
 * useKeyboardShortcuts Hook Tests
 *
 * Test suite for keyboard navigation shortcuts.
 */

import { renderHook } from '@testing-library/react';
import { useKeyboardShortcuts } from '../useKeyboardShortcuts';

describe('useKeyboardShortcuts', () => {
  const handlers = {
    onZoomIn: jest.fn(),
    onZoomOut: jest.fn(),
    onReset: jest.fn(),
    onFit: jest.fn(),
    onSelectAll: jest.fn(),
    onClearSelection: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Zoom Shortcuts', () => {
    test('calls onZoomIn when + key pressed', () => {
      renderHook(() => useKeyboardShortcuts(handlers));

      const event = new KeyboardEvent('keydown', { key: '+' });
      window.dispatchEvent(event);

      expect(handlers.onZoomIn).toHaveBeenCalledTimes(1);
    });

    test('calls onZoomIn when = key pressed', () => {
      renderHook(() => useKeyboardShortcuts(handlers));

      const event = new KeyboardEvent('keydown', { key: '=' });
      window.dispatchEvent(event);

      expect(handlers.onZoomIn).toHaveBeenCalledTimes(1);
    });

    test('calls onZoomOut when - key pressed', () => {
      renderHook(() => useKeyboardShortcuts(handlers));

      const event = new KeyboardEvent('keydown', { key: '-' });
      window.dispatchEvent(event);

      expect(handlers.onZoomOut).toHaveBeenCalledTimes(1);
    });
  });

  describe('Navigation Shortcuts', () => {
    test('calls onReset when 0 key pressed', () => {
      renderHook(() => useKeyboardShortcuts(handlers));

      const event = new KeyboardEvent('keydown', { key: '0' });
      window.dispatchEvent(event);

      expect(handlers.onReset).toHaveBeenCalledTimes(1);
    });

    test('calls onFit when f key pressed', () => {
      renderHook(() => useKeyboardShortcuts(handlers));

      const event = new KeyboardEvent('keydown', { key: 'f' });
      window.dispatchEvent(event);

      expect(handlers.onFit).toHaveBeenCalledTimes(1);
    });

    test('calls onFit when F key pressed', () => {
      renderHook(() => useKeyboardShortcuts(handlers));

      const event = new KeyboardEvent('keydown', { key: 'F' });
      window.dispatchEvent(event);

      expect(handlers.onFit).toHaveBeenCalledTimes(1);
    });
  });

  describe('Selection Shortcuts', () => {
    test('calls onSelectAll when Ctrl+A pressed', () => {
      renderHook(() => useKeyboardShortcuts(handlers));

      const event = new KeyboardEvent('keydown', { key: 'a', ctrlKey: true });
      window.dispatchEvent(event);

      expect(handlers.onSelectAll).toHaveBeenCalledTimes(1);
    });

    test('calls onSelectAll when Cmd+A pressed (macOS)', () => {
      renderHook(() => useKeyboardShortcuts(handlers));

      const event = new KeyboardEvent('keydown', { key: 'a', metaKey: true });
      window.dispatchEvent(event);

      expect(handlers.onSelectAll).toHaveBeenCalledTimes(1);
    });

    test('calls onClearSelection when Escape pressed', () => {
      renderHook(() => useKeyboardShortcuts(handlers));

      const event = new KeyboardEvent('keydown', { key: 'Escape' });
      window.dispatchEvent(event);

      expect(handlers.onClearSelection).toHaveBeenCalledTimes(1);
    });
  });

  describe('Input Field Handling', () => {
    test('does not trigger when typing in input field', () => {
      renderHook(() => useKeyboardShortcuts(handlers));

      const input = document.createElement('input');
      document.body.appendChild(input);

      const event = new KeyboardEvent('keydown', { key: '+', bubbles: true });
      Object.defineProperty(event, 'target', { value: input, enumerable: true });
      input.dispatchEvent(event);

      expect(handlers.onZoomIn).not.toHaveBeenCalled();

      document.body.removeChild(input);
    });

    test('does not trigger when typing in textarea', () => {
      renderHook(() => useKeyboardShortcuts(handlers));

      const textarea = document.createElement('textarea');
      document.body.appendChild(textarea);

      const event = new KeyboardEvent('keydown', { key: '-', bubbles: true });
      Object.defineProperty(event, 'target', { value: textarea, enumerable: true });
      textarea.dispatchEvent(event);

      expect(handlers.onZoomOut).not.toHaveBeenCalled();

      document.body.removeChild(textarea);
    });

    test('triggers shortcuts when not focused on input', () => {
      renderHook(() => useKeyboardShortcuts(handlers));

      const event = new KeyboardEvent('keydown', { key: '+' });
      window.dispatchEvent(event);

      expect(handlers.onZoomIn).toHaveBeenCalledTimes(1);
    });
  });

  describe('Event Cleanup', () => {
    test('removes event listener on unmount', () => {
      const addSpy = jest.spyOn(window, 'addEventListener');
      const removeSpy = jest.spyOn(window, 'removeEventListener');

      const { unmount } = renderHook(() => useKeyboardShortcuts(handlers));

      expect(addSpy).toHaveBeenCalledWith('keydown', expect.any(Function));

      unmount();

      expect(removeSpy).toHaveBeenCalledWith('keydown', expect.any(Function));

      addSpy.mockRestore();
      removeSpy.mockRestore();
    });

    test('does not trigger after unmount', () => {
      const { unmount } = renderHook(() => useKeyboardShortcuts(handlers));

      unmount();

      const event = new KeyboardEvent('keydown', { key: '+' });
      window.dispatchEvent(event);

      expect(handlers.onZoomIn).not.toHaveBeenCalled();
    });
  });

  describe('Multiple Key Presses', () => {
    test('handles rapid key presses', () => {
      renderHook(() => useKeyboardShortcuts(handlers));

      for (let i = 0; i < 5; i++) {
        const event = new KeyboardEvent('keydown', { key: '+' });
        window.dispatchEvent(event);
      }

      expect(handlers.onZoomIn).toHaveBeenCalledTimes(5);
    });

    test('handles different shortcuts in sequence', () => {
      renderHook(() => useKeyboardShortcuts(handlers));

      window.dispatchEvent(new KeyboardEvent('keydown', { key: '+' }));
      window.dispatchEvent(new KeyboardEvent('keydown', { key: '-' }));
      window.dispatchEvent(new KeyboardEvent('keydown', { key: '0' }));
      window.dispatchEvent(new KeyboardEvent('keydown', { key: 'f' }));

      expect(handlers.onZoomIn).toHaveBeenCalledTimes(1);
      expect(handlers.onZoomOut).toHaveBeenCalledTimes(1);
      expect(handlers.onReset).toHaveBeenCalledTimes(1);
      expect(handlers.onFit).toHaveBeenCalledTimes(1);
    });
  });

  describe('Unhandled Keys', () => {
    test('ignores keys without assigned handlers', () => {
      renderHook(() => useKeyboardShortcuts(handlers));

      const event = new KeyboardEvent('keydown', { key: 'x' });
      window.dispatchEvent(event);

      expect(handlers.onZoomIn).not.toHaveBeenCalled();
      expect(handlers.onZoomOut).not.toHaveBeenCalled();
      expect(handlers.onReset).not.toHaveBeenCalled();
      expect(handlers.onFit).not.toHaveBeenCalled();
      expect(handlers.onSelectAll).not.toHaveBeenCalled();
      expect(handlers.onClearSelection).not.toHaveBeenCalled();
    });
  });
});
