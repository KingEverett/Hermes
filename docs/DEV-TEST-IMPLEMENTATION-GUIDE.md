# Frontend Test Implementation Guide - Story 3.6

**Status**: Test scaffolds created by Scrum Master (Bob)
**Dev Team Action Required**: Implement and verify tests pass
**Estimated Time**: 3-5 hours
**Priority**: Required before Story 3.6 can move to Done

---

## What Was Scaffolded

I've created **4 test files** with basic test cases:

### 1. AttackChainOverlay Tests
**Location**: `frontend/web-app/src/components/visualization/__tests__/AttackChainOverlay.test.tsx`

**Test Cases**:
- ✓ Renders without crashing when visible
- ✓ Does not render when not visible
- ✓ Applies active styling when isActive=true
- ✓ Handles empty nodes array gracefully
- ✓ Renders sequence badges for each node
- ✓ Renders branch indicators for branch points

**Action Needed**:
- Verify mock data matches your AttackChain interface
- Ensure D3.js rendering is testable (may need to mock d3 methods)
- Run tests and fix any failures

### 2. AttackChainTree Tests
**Location**: `frontend/web-app/src/components/layout/__tests__/AttackChainTree.test.tsx`

**Test Cases**:
- ✓ Renders without crashing
- ✓ Displays all chains from list
- ✓ Shows create button
- ✓ Calls onCreateChain when button clicked
- ✓ Displays node count for each chain
- ✓ Shows visibility toggle icons
- ✓ Renders empty state when no chains
- ✓ Shows loading state
- ✓ Expands chain details on click
- ✓ Displays color indicator

**Action Needed**:
- Verify React Query mocks work with your setup
- Ensure Zustand store mocks return correct shape
- Test expand/collapse functionality works

### 3. AttackChainCreator Tests
**Location**: `frontend/web-app/src/components/visualization/__tests__/AttackChainCreator.test.tsx`

**Test Cases**:
- ✓ Renders without crashing when open
- ✓ Does not render when closed
- ✓ Displays name input field
- ✓ Displays description textarea
- ✓ Displays color picker
- ✓ Accepts text input for chain name
- ✓ Accepts text input for description
- ✓ Shows cancel button
- ✓ Calls onClose when cancel clicked
- ✓ Shows create/save button
- ✓ Displays step indicator or progress
- ✓ Prevents submission with empty name
- ✓ Handles form submission with valid data

**Action Needed**:
- Verify modal rendering (may need to adjust queries)
- Test multi-step workflow if implemented
- Ensure validation logic works

### 4. attackChainVisibilityStore Tests
**Location**: `frontend/web-app/src/stores/__tests__/attackChainVisibilityStore.test.ts`

**Test Cases**:
- ✓ Initializes with empty visible chains
- ✓ toggleChainVisibility adds chain to visible set
- ✓ toggleChainVisibility removes chain from visible set
- ✓ toggleChainVisibility clears active chain when hiding it
- ✓ setActiveChain sets the active chain ID
- ✓ setActiveChain can clear active chain with null
- ✓ hideAllChains clears visible set and active chain
- ✓ showAllChains sets multiple chains visible
- ✓ isChainVisible returns correct visibility status
- ✓ Handles multiple chains independently
- ✓ Persists state to localStorage

**Action Needed**:
- Run tests (these should work out of the box)
- Verify localStorage mocking works in your test environment

---

## Mock Data Utilities

**Location**: `frontend/web-app/src/test-utils/attackChainMocks.ts`

**What's Included**:
- `mockAttackChainNode` - Single node
- `mockBranchPointNode` - Node with branch point
- `mockAttackChain` - Full chain with nodes
- `mockAttackChainListItem` - List item without nodes
- `mockChains` - Array of chains
- `mockGraphNodes` - Graph node positions
- `mockGraphEdges` - Graph edges for validation
- `createMockSvgRef()` - Helper for D3.js tests
- `cleanupMockSvgRef()` - Cleanup helper

**Usage**:
```typescript
import { mockAttackChain, mockGraphNodes } from '../../../test-utils/attackChainMocks';
```

---

## Running the Tests

### Run all attack chain tests:
```bash
npm test -- --testPathPattern=AttackChain
```

### Run specific test file:
```bash
npm test -- AttackChainOverlay.test.tsx
```

### Run in watch mode:
```bash
npm test -- --watch --testPathPattern=AttackChain
```

---

## Expected Issues & Fixes

### Issue 1: D3.js is not defined
**Symptom**: `ReferenceError: d3 is not defined`

**Fix**: Mock D3.js in test setup:
```typescript
jest.mock('d3', () => ({
  select: jest.fn(() => ({
    append: jest.fn().mockReturnThis(),
    attr: jest.fn().mockReturnThis(),
    selectAll: jest.fn().mockReturnThis(),
    // ... other D3 methods
  })),
}));
```

### Issue 2: SVG methods not available in jsdom
**Symptom**: `getTotalLength is not a function`

**Fix**: Mock SVG path methods:
```typescript
beforeAll(() => {
  Object.defineProperty(SVGPathElement.prototype, 'getTotalLength', {
    value: () => 100,
    writable: true,
  });
});
```

### Issue 3: React Query needs QueryClientProvider
**Symptom**: `No QueryClient set, use QueryClientProvider`

**Fix**: Already wrapped in tests, but ensure your component uses the right context.

### Issue 4: Zustand store persists between tests
**Symptom**: Tests fail when run together but pass individually

**Fix**: Reset store in `beforeEach`:
```typescript
beforeEach(() => {
  useAttackChainVisibilityStore.setState({
    visibleChainIds: new Set(),
    activeChainId: null,
  });
});
```

---

## Success Criteria

**Before marking Story 3.6 as Done**:

1. ✅ All 4 test files run without errors
2. ✅ At least 80% of test cases pass (some may need adjustments)
3. ✅ Run `npm test` and verify no new failures introduced
4. ✅ Tests are committed to the repository

---

## What Happens After Tests Pass?

1. **Dev Team** commits test files
2. **Scrum Master (me)** notifies Quinn (QA) for re-review
3. **Quinn** runs tests, verifies gate changes from CONCERNS → PASS
4. **Story moves to Done** ✅

---

## Questions?

If you hit issues:
1. Check the "Expected Issues & Fixes" section above
2. Google the error message (usually Jest/React Testing Library related)
3. Ask me (Bob) or Quinn for guidance
4. Check Jest docs: https://jestjs.io/docs/getting-started
5. Check React Testing Library docs: https://testing-library.com/docs/react-testing-library/intro/

---

## Time Estimate Breakdown

- **Setup/Install** (if needed): 30 min
- **Fix mock data issues**: 1 hour
- **Fix D3.js mocking**: 1 hour
- **Fix component-specific issues**: 1-2 hours
- **Verify all tests pass**: 30 min

**Total**: 3-5 hours

---

Good luck! These tests will protect us from regressions and make future development much safer.

— Bob (Scrum Master)
