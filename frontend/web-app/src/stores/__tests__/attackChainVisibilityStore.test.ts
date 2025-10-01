/**
 * Unit tests for attackChainVisibilityStore
 *
 * DEV TEAM: These test the Zustand store logic directly.
 * Goal: Verify state mutations work correctly.
 */

import { useAttackChainVisibilityStore } from '../attackChainVisibilityStore';

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};

  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value;
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
  };
})();

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
});

describe('attackChainVisibilityStore', () => {
  beforeEach(() => {
    // Reset store to initial state before each test
    useAttackChainVisibilityStore.setState({
      visibleChainIds: new Set(),
      activeChainId: null,
    });
    localStorageMock.clear();
  });

  test('initializes with empty visible chains', () => {
    const state = useAttackChainVisibilityStore.getState();
    expect(state.visibleChainIds.size).toBe(0);
    expect(state.activeChainId).toBe(null);
  });

  test('toggleChainVisibility adds chain to visible set', () => {
    const { toggleChainVisibility } = useAttackChainVisibilityStore.getState();

    toggleChainVisibility('chain-1');

    const state = useAttackChainVisibilityStore.getState();
    expect(state.visibleChainIds.has('chain-1')).toBe(true);
  });

  test('toggleChainVisibility removes chain from visible set', () => {
    const { toggleChainVisibility } = useAttackChainVisibilityStore.getState();

    // Add then remove
    toggleChainVisibility('chain-1');
    toggleChainVisibility('chain-1');

    const state = useAttackChainVisibilityStore.getState();
    expect(state.visibleChainIds.has('chain-1')).toBe(false);
  });

  test('toggleChainVisibility clears active chain when hiding it', () => {
    const { toggleChainVisibility, setActiveChain } = useAttackChainVisibilityStore.getState();

    // Make chain visible and active
    toggleChainVisibility('chain-1');
    setActiveChain('chain-1');

    // Hide the active chain
    toggleChainVisibility('chain-1');

    const state = useAttackChainVisibilityStore.getState();
    expect(state.activeChainId).toBe(null);
  });

  test('setActiveChain sets the active chain ID', () => {
    const { setActiveChain } = useAttackChainVisibilityStore.getState();

    setActiveChain('chain-1');

    const state = useAttackChainVisibilityStore.getState();
    expect(state.activeChainId).toBe('chain-1');
  });

  test('setActiveChain can clear active chain with null', () => {
    const { setActiveChain } = useAttackChainVisibilityStore.getState();

    setActiveChain('chain-1');
    setActiveChain(null);

    const state = useAttackChainVisibilityStore.getState();
    expect(state.activeChainId).toBe(null);
  });

  test('hideAllChains clears visible set and active chain', () => {
    const { toggleChainVisibility, setActiveChain, hideAllChains } =
      useAttackChainVisibilityStore.getState();

    // Set up some state
    toggleChainVisibility('chain-1');
    toggleChainVisibility('chain-2');
    setActiveChain('chain-1');

    // Hide all
    hideAllChains();

    const state = useAttackChainVisibilityStore.getState();
    expect(state.visibleChainIds.size).toBe(0);
    expect(state.activeChainId).toBe(null);
  });

  test('showAllChains sets multiple chains visible', () => {
    const { showAllChains } = useAttackChainVisibilityStore.getState();

    showAllChains(['chain-1', 'chain-2', 'chain-3']);

    const state = useAttackChainVisibilityStore.getState();
    expect(state.visibleChainIds.size).toBe(3);
    expect(state.visibleChainIds.has('chain-1')).toBe(true);
    expect(state.visibleChainIds.has('chain-2')).toBe(true);
    expect(state.visibleChainIds.has('chain-3')).toBe(true);
  });

  test('isChainVisible returns correct visibility status', () => {
    const { toggleChainVisibility, isChainVisible } =
      useAttackChainVisibilityStore.getState();

    toggleChainVisibility('chain-1');

    expect(isChainVisible('chain-1')).toBe(true);
    expect(isChainVisible('chain-2')).toBe(false);
  });

  test('handles multiple chains independently', () => {
    const { toggleChainVisibility } = useAttackChainVisibilityStore.getState();

    toggleChainVisibility('chain-1');
    toggleChainVisibility('chain-2');
    toggleChainVisibility('chain-3');

    const state = useAttackChainVisibilityStore.getState();
    expect(state.visibleChainIds.size).toBe(3);

    // Toggle one off
    toggleChainVisibility('chain-2');

    const state2 = useAttackChainVisibilityStore.getState();
    expect(state2.visibleChainIds.size).toBe(2);
    expect(state2.visibleChainIds.has('chain-1')).toBe(true);
    expect(state2.visibleChainIds.has('chain-2')).toBe(false);
    expect(state2.visibleChainIds.has('chain-3')).toBe(true);
  });

  test('persists state to localStorage', () => {
    const { toggleChainVisibility } = useAttackChainVisibilityStore.getState();

    toggleChainVisibility('chain-1');

    // Check that localStorage was called
    const stored = localStorageMock.getItem('hermes-attack-chain-visibility');
    expect(stored).toBeTruthy();

    // Parse and verify
    if (stored) {
      const parsed = JSON.parse(stored);
      expect(parsed.state.visibleChainIds).toContain('chain-1');
    }
  });
});
