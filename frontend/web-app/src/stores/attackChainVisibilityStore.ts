/**
 * Attack Chain Visibility State Management
 *
 * Zustand store for managing which attack chains are visible on the network graph
 * and which chain is currently active (highlighted).
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface AttackChainVisibilityState {
  visibleChainIds: Set<string>;
  activeChainId: string | null;

  toggleChainVisibility: (chainId: string) => void;
  setActiveChain: (chainId: string | null) => void;
  hideAllChains: () => void;
  showAllChains: (chainIds: string[]) => void;
  isChainVisible: (chainId: string) => boolean;
}

export const useAttackChainVisibilityStore = create<AttackChainVisibilityState>()(
  persist(
    (set, get) => ({
      visibleChainIds: new Set<string>(),
      activeChainId: null,

      toggleChainVisibility: (chainId: string) => set((state) => {
        const newSet = new Set(state.visibleChainIds);
        if (newSet.has(chainId)) {
          newSet.delete(chainId);
          // If hiding the active chain, clear active state
          if (state.activeChainId === chainId) {
            return { visibleChainIds: newSet, activeChainId: null };
          }
        } else {
          newSet.add(chainId);
        }
        return { visibleChainIds: newSet };
      }),

      setActiveChain: (chainId: string | null) => set({ activeChainId: chainId }),

      hideAllChains: () => set({ visibleChainIds: new Set(), activeChainId: null }),

      showAllChains: (chainIds: string[]) => set({ visibleChainIds: new Set(chainIds) }),

      isChainVisible: (chainId: string) => get().visibleChainIds.has(chainId),
    }),
    {
      name: 'hermes-attack-chain-visibility',
      // Custom storage to handle Set serialization
      storage: {
        getItem: (name: string) => {
          const str = localStorage.getItem(name);
          if (!str) return null;
          const { state } = JSON.parse(str);
          return {
            state: {
              ...state,
              visibleChainIds: new Set(state.visibleChainIds || []),
            },
          };
        },
        setItem: (name: string, value: any) => {
          const { state } = value;
          localStorage.setItem(
            name,
            JSON.stringify({
              state: {
                ...state,
                visibleChainIds: Array.from(state.visibleChainIds),
              },
            })
          );
        },
        removeItem: (name: string) => localStorage.removeItem(name),
      },
    }
  )
);
