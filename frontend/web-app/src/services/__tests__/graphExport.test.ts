/**
 * Tests for GraphExport Service
 */

import { exportSVG, exportPNG, generateExportFilename } from '../graphExport';

// Mock browser APIs
const mockCreateObjectURL = jest.fn(() => 'blob:mock-url');
const mockRevokeObjectURL = jest.fn();

global.URL.createObjectURL = mockCreateObjectURL;
global.URL.revokeObjectURL = mockRevokeObjectURL;

describe('GraphExport Service', () => {
  let mockSvgElement: SVGElement;

  beforeEach(() => {
    // Create mock SVG element
    mockSvgElement = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    mockSvgElement.setAttribute('width', '1000');
    mockSvgElement.setAttribute('height', '800');

    // Reset mocks
    mockCreateObjectURL.mockClear();
    mockRevokeObjectURL.mockClear();

    // Clear any created links
    document.body.innerHTML = '';
  });

  describe('exportSVG', () => {
    it('should create SVG blob and trigger download', () => {
      exportSVG(mockSvgElement, 'test-graph.svg');

      expect(mockCreateObjectURL).toHaveBeenCalledWith(
        expect.any(Blob)
      );

      // Check that the blob has correct type
      expect(mockCreateObjectURL.mock.calls.length).toBeGreaterThan(0);
      const calls = mockCreateObjectURL.mock.calls as unknown as Array<[Blob]>;
      const blobArg = calls[0][0];
      expect(blobArg.type).toBe('image/svg+xml;charset=utf-8');

      // Check if link was created and clicked
      const link = document.querySelector('a[download="test-graph.svg"]');
      expect(link).toBeTruthy();

      // Check that URL was revoked
      expect(mockRevokeObjectURL).toHaveBeenCalledWith('blob:mock-url');
    });

    it('should include XML declaration in SVG export', async () => {
      exportSVG(mockSvgElement, 'test-graph.svg');

      expect(mockCreateObjectURL.mock.calls.length).toBeGreaterThan(0);
      const calls = mockCreateObjectURL.mock.calls as unknown as Array<[Blob]>;
      const blobArg = calls[0][0];
      const text = await blobArg.text();
      expect(text).toContain('<?xml version="1.0" encoding="UTF-8"?>');
    });

    it('should clone SVG without modifying original', () => {
      const originalChildCount = mockSvgElement.childNodes.length;

      exportSVG(mockSvgElement, 'test-graph.svg');

      expect(mockSvgElement.childNodes.length).toBe(originalChildCount);
    });
  });

  describe('exportPNG', () => {
    it('should create canvas with correct resolution', async () => {
      const resolution = 2;

      // Mock Image onload
      let imageOnLoad: () => void;
      const mockImage = {
        onload: null as any,
        onerror: null as any,
        src: ''
      };

      jest.spyOn(window, 'Image').mockImplementation(() => {
        const img = mockImage as any;
        setTimeout(() => {
          if (img.onload) img.onload();
        }, 0);
        return img;
      });

      // Mock canvas
      const mockCanvas = document.createElement('canvas');
      const mockContext = {
        drawImage: jest.fn()
      };
      jest.spyOn(document, 'createElement').mockImplementation((tag) => {
        if (tag === 'canvas') {
          const canvas = mockCanvas;
          canvas.getContext = jest.fn(() => mockContext as any);
          canvas.toBlob = jest.fn((callback) => {
            callback(new Blob(['mock'], { type: 'image/png' }));
          });
          return canvas as any;
        }
        return document.createElement(tag);
      });

      await exportPNG(mockSvgElement, resolution, 'test-graph.png');

      expect(mockCanvas.width).toBe(1000 * resolution);
      expect(mockCanvas.height).toBe(800 * resolution);
    });

    it('should handle export errors gracefully', async () => {
      // Mock Image to trigger error
      jest.spyOn(window, 'Image').mockImplementation(() => {
        const img = {
          onload: null as any,
          onerror: null as any,
          src: ''
        };
        setTimeout(() => {
          if (img.onerror) img.onerror();
        }, 0);
        return img as any;
      });

      await expect(exportPNG(mockSvgElement, 1, 'test.png')).rejects.toThrow('Failed to load SVG image');
    });
  });

  describe('generateExportFilename', () => {
    it('should generate correct filename format', () => {
      const filename = generateExportFilename('Test Project', 'svg');

      expect(filename).toMatch(/^test-project-network-graph-\d{4}-\d{2}-\d{2}T\d{2}-\d{2}\.svg$/);
    });

    it('should include filter label when provided', () => {
      const filename = generateExportFilename('Test Project', 'png', 'Critical Only');

      expect(filename).toContain('-critical-only-');
      expect(filename.endsWith('.png')).toBe(true);
    });

    it('should sanitize project name', () => {
      const filename = generateExportFilename('Test @#$ Project!!!', 'svg');

      expect(filename).toMatch(/^test-----project----network-graph/);
    });
  });
});
