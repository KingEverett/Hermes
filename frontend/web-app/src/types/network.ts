/**
 * Shared type definitions for network visualization components
 */

export interface NetworkNode {
  id: string;
  type: 'host' | 'service';
  label: string;
  data?: any;
}
