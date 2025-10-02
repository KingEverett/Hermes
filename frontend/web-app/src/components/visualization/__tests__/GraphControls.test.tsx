/**
 * GraphControls Component Tests
 *
 * Test suite for the graph navigation controls toolbar.
 */

import React from 'react';
import { render } from '@testing-library/react';
import { screen, fireEvent } from '@testing-library/dom';
import { GraphControls } from '../GraphControls';

describe('GraphControls', () => {
  const mockHandlers = {
    onZoomIn: jest.fn(),
    onZoomOut: jest.fn(),
    onFitToScreen: jest.fn(),
    onReset: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Rendering', () => {
    test('renders all control buttons', () => {
      render(<GraphControls {...mockHandlers} zoomLevel={1} />);

      expect(screen.getByLabelText('Zoom in')).toBeInTheDocument();
      expect(screen.getByLabelText('Zoom out')).toBeInTheDocument();
      expect(screen.getByLabelText('Fit to screen')).toBeInTheDocument();
      expect(screen.getByLabelText('Reset view')).toBeInTheDocument();
    });

    test('displays zoom level percentage', () => {
      render(<GraphControls {...mockHandlers} zoomLevel={1.5} />);

      expect(screen.getByText('150%')).toBeInTheDocument();
    });

    test('displays 100% for zoom level 1', () => {
      render(<GraphControls {...mockHandlers} zoomLevel={1} />);

      expect(screen.getByText('100%')).toBeInTheDocument();
    });

    test('rounds zoom level to nearest integer', () => {
      render(<GraphControls {...mockHandlers} zoomLevel={1.456} />);

      expect(screen.getByText('146%')).toBeInTheDocument();
    });
  });

  describe('Button Interactions', () => {
    test('zoom in button calls handler', () => {
      render(<GraphControls {...mockHandlers} zoomLevel={1} />);

      fireEvent.click(screen.getByLabelText('Zoom in'));
      expect(mockHandlers.onZoomIn).toHaveBeenCalledTimes(1);
    });

    test('zoom out button calls handler', () => {
      render(<GraphControls {...mockHandlers} zoomLevel={1} />);

      fireEvent.click(screen.getByLabelText('Zoom out'));
      expect(mockHandlers.onZoomOut).toHaveBeenCalledTimes(1);
    });

    test('fit to screen button calls handler', () => {
      render(<GraphControls {...mockHandlers} zoomLevel={1} />);

      fireEvent.click(screen.getByLabelText('Fit to screen'));
      expect(mockHandlers.onFitToScreen).toHaveBeenCalledTimes(1);
    });

    test('reset button calls handler', () => {
      render(<GraphControls {...mockHandlers} zoomLevel={1} />);

      fireEvent.click(screen.getByLabelText('Reset view'));
      expect(mockHandlers.onReset).toHaveBeenCalledTimes(1);
    });

    test('multiple clicks trigger handler multiple times', () => {
      render(<GraphControls {...mockHandlers} zoomLevel={1} />);

      const zoomInButton = screen.getByLabelText('Zoom in');
      fireEvent.click(zoomInButton);
      fireEvent.click(zoomInButton);
      fireEvent.click(zoomInButton);

      expect(mockHandlers.onZoomIn).toHaveBeenCalledTimes(3);
    });
  });

  describe('Accessibility', () => {
    test('all buttons have aria-label attributes', () => {
      render(<GraphControls {...mockHandlers} zoomLevel={1} />);

      expect(screen.getByLabelText('Zoom in')).toHaveAttribute('aria-label', 'Zoom in');
      expect(screen.getByLabelText('Zoom out')).toHaveAttribute('aria-label', 'Zoom out');
      expect(screen.getByLabelText('Fit to screen')).toHaveAttribute('aria-label', 'Fit to screen');
      expect(screen.getByLabelText('Reset view')).toHaveAttribute('aria-label', 'Reset view');
    });

    test('all buttons have title tooltips', () => {
      render(<GraphControls {...mockHandlers} zoomLevel={1} />);

      expect(screen.getByLabelText('Zoom in')).toHaveAttribute('title', 'Zoom in (+)');
      expect(screen.getByLabelText('Zoom out')).toHaveAttribute('title', 'Zoom out (-)');
      expect(screen.getByLabelText('Fit to screen')).toHaveAttribute('title', 'Fit to screen (F)');
      expect(screen.getByLabelText('Reset view')).toHaveAttribute('title', 'Reset view (0)');
    });

    test('buttons are keyboard accessible', () => {
      render(<GraphControls {...mockHandlers} zoomLevel={1} />);

      const zoomInButton = screen.getByLabelText('Zoom in');
      zoomInButton.focus();

      expect(document.activeElement).toBe(zoomInButton);
    });
  });

  describe('Styling', () => {
    test('toolbar has correct positioning classes', () => {
      const { container } = render(<GraphControls {...mockHandlers} zoomLevel={1} />);

      const toolbar = container.firstChild as HTMLElement;
      expect(toolbar).toHaveClass('absolute', 'top-4', 'right-4');
    });

    test('toolbar has dark theme styling', () => {
      const { container } = render(<GraphControls {...mockHandlers} zoomLevel={1} />);

      const toolbar = container.firstChild as HTMLElement;
      expect(toolbar).toHaveClass('bg-gray-800', 'border-gray-700');
    });
  });

  describe('Zoom Level Display', () => {
    test('handles very small zoom levels', () => {
      render(<GraphControls {...mockHandlers} zoomLevel={0.1} />);

      expect(screen.getByText('10%')).toBeInTheDocument();
    });

    test('handles very large zoom levels', () => {
      render(<GraphControls {...mockHandlers} zoomLevel={10} />);

      expect(screen.getByText('1000%')).toBeInTheDocument();
    });

    test('handles zero zoom level', () => {
      render(<GraphControls {...mockHandlers} zoomLevel={0} />);

      expect(screen.getByText('0%')).toBeInTheDocument();
    });
  });
});
