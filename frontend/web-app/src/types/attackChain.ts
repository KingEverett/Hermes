/**
 * Attack Chain types for documenting exploitation paths
 */

export interface AttackChainNode {
  id: string;
  attack_chain_id: string;
  entity_type: 'host' | 'service';
  entity_id: string;
  sequence_order: number;
  method_notes?: string;
  is_branch_point: boolean;
  branch_description?: string;
  created_at: Date;
}

export interface AttackChain {
  id: string;
  project_id: string;
  name: string;
  description?: string;
  color: string;
  created_at: Date;
  updated_at: Date;
  nodes: AttackChainNode[];
}

export interface AttackChainListItem {
  id: string;
  project_id: string;
  name: string;
  description?: string;
  color: string;
  node_count: number;
  created_at: Date;
  updated_at: Date;
}

export interface AttackChainNodeCreate {
  entity_type: 'host' | 'service';
  entity_id: string;
  sequence_order: number;
  method_notes?: string;
  is_branch_point?: boolean;
  branch_description?: string;
}

export interface AttackChainCreate {
  name: string;
  description?: string;
  color?: string;
  nodes: AttackChainNodeCreate[];
}

export interface AttackChainUpdate {
  name?: string;
  description?: string;
  color?: string;
  nodes?: AttackChainNodeCreate[];
}
