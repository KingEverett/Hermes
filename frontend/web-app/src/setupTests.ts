// jest-dom adds custom jest matchers for asserting on DOM nodes.
import '@testing-library/jest-dom';
import { server } from './test-utils/msw-server';

// Establish API mocking before all tests
beforeAll(() => {
  server.listen({
    onUnhandledRequest: 'warn', // Warn about unhandled requests
  });
});

// Reset any request handlers that are added during tests
afterEach(() => {
  server.resetHandlers();
  // Clear React Query cache between tests
  jest.clearAllMocks();
});

// Clean up after all tests are done
afterAll(() => {
  server.close();
});

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

// Mock URL.createObjectURL and URL.revokeObjectURL for blob downloads
global.URL.createObjectURL = jest.fn(() => 'blob:mock-url');
global.URL.revokeObjectURL = jest.fn();

// Mock HTMLCanvasElement methods
Object.defineProperty(HTMLCanvasElement.prototype, 'getContext', {
  value: jest.fn(() => ({
    drawImage: jest.fn(),
    getImageData: jest.fn(() => ({ data: new Uint8ClampedArray(4) })),
    putImageData: jest.fn(),
    measureText: jest.fn(() => ({ width: 100 })),
    fillText: jest.fn(),
    strokeText: jest.fn(),
    clearRect: jest.fn(),
    fillRect: jest.fn(),
    strokeRect: jest.fn(),
    beginPath: jest.fn(),
    moveTo: jest.fn(),
    lineTo: jest.fn(),
    arc: jest.fn(),
    stroke: jest.fn(),
    fill: jest.fn(),
    save: jest.fn(),
    restore: jest.fn(),
    translate: jest.fn(),
    rotate: jest.fn(),
    scale: jest.fn(),
  })),
});

// Mock HTMLCanvasElement toBlob method
Object.defineProperty(HTMLCanvasElement.prototype, 'toBlob', {
  value: jest.fn((callback) => {
    const mockBlob = new Blob(['fake-image-data'], { type: 'image/png' });
    callback(mockBlob);
  }),
});

// Mock Image constructor for canvas operations
global.Image = class {
  onload: (() => void) | null = null;
  onerror: (() => void) | null = null;
  src: string = '';

  constructor() {
    // Simulate immediate load
    setTimeout(() => {
      if (this.onload) this.onload();
    }, 0);
  }
} as any;

// Note: Individual tests will mock document.createElement as needed

// Mock Blob.text() method for modern blob API
if (typeof Blob !== 'undefined') {
  Object.defineProperty(Blob.prototype, 'text', {
    value: jest.fn().mockResolvedValue('mock-blob-text'),
  });
}
