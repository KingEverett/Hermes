/**
 * Attack Chain API Service
 *
 * Handles all HTTP requests for attack chain CRUD operations.
 */

import type {
  AttackChain,
  AttackChainListItem,
  AttackChainCreate,
  AttackChainUpdate,
} from '../types/attackChain';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

/**
 * Fetch all attack chains for a project
 */
export const getProjectAttackChains = async (
  projectId: string
): Promise<AttackChainListItem[]> => {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/projects/${projectId}/attack-chains`
  );

  if (!response.ok) {
    throw new Error(`Failed to fetch attack chains: ${response.statusText}`);
  }

  return response.json();
};

/**
 * Fetch a single attack chain by ID with all nodes
 */
export const getAttackChain = async (chainId: string): Promise<AttackChain> => {
  const response = await fetch(`${API_BASE_URL}/api/v1/attack-chains/${chainId}`);

  if (!response.ok) {
    throw new Error(`Failed to fetch attack chain: ${response.statusText}`);
  }

  return response.json();
};

/**
 * Create a new attack chain
 */
export const createAttackChain = async (
  projectId: string,
  data: AttackChainCreate
): Promise<AttackChain> => {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/projects/${projectId}/attack-chains`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    }
  );

  if (!response.ok) {
    throw new Error(`Failed to create attack chain: ${response.statusText}`);
  }

  return response.json();
};

/**
 * Update an existing attack chain
 */
export const updateAttackChain = async (
  chainId: string,
  data: AttackChainUpdate
): Promise<AttackChain> => {
  const response = await fetch(`${API_BASE_URL}/api/v1/attack-chains/${chainId}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    throw new Error(`Failed to update attack chain: ${response.statusText}`);
  }

  return response.json();
};

/**
 * Delete an attack chain
 */
export const deleteAttackChain = async (chainId: string): Promise<void> => {
  const response = await fetch(`${API_BASE_URL}/api/v1/attack-chains/${chainId}`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    throw new Error(`Failed to delete attack chain: ${response.statusText}`);
  }
};
