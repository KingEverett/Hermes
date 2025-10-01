// jest-dom adds custom jest matchers for asserting on DOM nodes.
import '@testing-library/jest-dom';

// Mock D3.js globally for all tests
jest.mock('d3', () => {
  const mockSelection = {
    select: jest.fn().mockReturnThis(),
    selectAll: jest.fn().mockReturnThis(),
    append: jest.fn().mockReturnThis(),
    attr: jest.fn().mockReturnThis(),
    style: jest.fn().mockReturnThis(),
    text: jest.fn().mockReturnThis(),
    remove: jest.fn().mockReturnThis(),
    node: jest.fn(() => ({
      getTotalLength: () => 100,
    })),
    transition: jest.fn().mockReturnThis(),
    duration: jest.fn().mockReturnThis(),
    ease: jest.fn().mockReturnThis(),
    on: jest.fn().mockReturnThis(),
    data: jest.fn().mockReturnThis(),
    join: jest.fn().mockReturnThis(),
    each: jest.fn().mockReturnThis(),
    empty: jest.fn(() => false),
  };

  return {
    select: jest.fn(() => mockSelection),
    line: jest.fn(() => {
      const lineGenerator: any = jest.fn((data: any[]) => {
        if (!data || data.length === 0) return '';
        return `M ${data[0].x} ${data[0].y} L ${data[data.length - 1].x} ${data[data.length - 1].y}`;
      });
      lineGenerator.x = jest.fn().mockReturnThis();
      lineGenerator.y = jest.fn().mockReturnThis();
      lineGenerator.curve = jest.fn().mockReturnThis();
      return lineGenerator;
    }),
    curveCatmullRom: jest.fn(),
    easeLinear: jest.fn(),
  };
});

// Mock SVG path methods (only if SVGPathElement exists)
if (typeof SVGPathElement !== 'undefined') {
  Object.defineProperty(SVGPathElement.prototype, 'getTotalLength', {
    value: () => 100,
    writable: true,
  });
}

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(),
    removeListener: jest.fn(),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});
