# Coding Standards

**Last Updated:** 2025-10-02

## Introduction

This document defines coding standards and conventions for the Hermes project based on actual patterns used in Stories 3.1-3.10. These are living standards that should evolve as project patterns mature. All examples reference actual project code for consistency.

## TypeScript Conventions

### Naming Conventions

**Interfaces:**
- Use PascalCase for interface names
- Suffix component props interfaces with `Props`
- Use descriptive names that reflect purpose

```typescript
// Component props interface (ErrorBoundary.tsx:9-11)
interface Props {
  children: ReactNode;
}

// State interface (ErrorBoundary.tsx:13-17)
interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

// Component-specific props (MarkdownEditor.tsx:6-15)
interface MarkdownEditorProps {
  value: string;
  onChange: (value: string) => void;
  onSave?: (value: string) => void;
  autoSaveDelay?: number;
  maxLength?: number;
  readOnly?: boolean;
  placeholder?: string;
  height?: number;
}
```

**Variables and Functions:**
- Use camelCase for variables, functions, and methods
- Use descriptive names that indicate purpose
- Boolean variables should use `is`, `has`, `should` prefixes

```typescript
// Boolean variables (App.tsx:21, 58)
const isLoading = true;
const hasProjects = (data?.length ?? 0) > 0;

// Handler functions (ErrorBoundary.tsx:43)
const handleReset = (): void => { ... };

// Async fetch functions (useDefaultProject.ts:16-24)
const fetchProjects = async (): Promise<Project[]> => {
  const response = await fetch('/api/v1/projects/');
  if (!response.ok) {
    throw new Error(`Failed to fetch projects: ${response.statusText}`);
  }
  return response.json();
};
```

**Constants:**
- Use UPPER_SNAKE_CASE for true constants (rare in our codebase)
- Use camelCase for configuration objects

```typescript
// Configuration object (App.tsx:9-18)
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      gcTime: 10 * 60 * 1000,   // 10 minutes
      retry: process.env.NODE_ENV === 'test' ? false : 2,
      refetchOnWindowFocus: false,
    },
  },
});
```

### Type Annotations

**Explicit Return Types:**
- Use explicit return types for functions and methods
- Helps catch errors early and improves readability

```typescript
// Explicit return type (useDefaultProject.ts:16)
const fetchProjects = async (): Promise<Project[]> => { ... };

// Explicit void return (ErrorBoundary.tsx:43)
const handleReset = (): void => { ... };
```

**Type Inference:**
- Let TypeScript infer types for simple variable assignments
- Use explicit types when inference is ambiguous

```typescript
// Type inference (App.tsx:21)
const { project, hasProjects, isLoading, error, refetch } = useDefaultProject();

// Explicit type when needed (MarkdownEditor.tsx:32)
const [lastSaved, setLastSaved] = useState<Date | null>(null);
```

## React Patterns

### Component Declaration

**Functional Components:**
- Use function declarations with explicit `React.FC` or function type
- Export named functions (not default exports, except for App)

```typescript
// React.FC with props interface (MarkdownEditor.tsx:20-29)
export const MarkdownEditor: React.FC<MarkdownEditorProps> = ({
  value,
  onChange,
  onSave,
  autoSaveDelay = 2000,
  maxLength = 1048576,
  readOnly = false,
  placeholder = 'Start writing your documentation...',
  height = 500,
}) => {
  // Component implementation
};

// Function declaration (App.tsx:20, 78)
export function AppContent() { ... }
function App() { ... }

// Default export only for main App (App.tsx:88)
export default App;
```

**Class Components (Error Boundaries Only):**
- Use class components only for error boundaries
- Implement required lifecycle methods

```typescript
// Error Boundary class component (ErrorBoundary.tsx:19-27)
export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    this.setState({ error, errorInfo });
  }
}
```

### Hooks Usage

**Hook Order and Rules:**
- Call hooks at top level of component
- Follow hooks in this order: state, effects, callbacks, custom hooks
- Never call hooks conditionally

```typescript
// State hooks first (MarkdownEditor.tsx:30-33)
const [localValue, setLocalValue] = useState(value);
const [isSaving, setIsSaving] = useState(false);
const [lastSaved, setLastSaved] = useState<Date | null>(null);
const autoSaveTimerRef = useRef<NodeJS.Timeout | null>(null);

// Effects next (MarkdownEditor.tsx:36-38, 51-67)
useEffect(() => {
  setLocalValue(value);
}, [value]);

useEffect(() => {
  // Debounced auto-save logic
}, [localValue, value, autoSaveDelay, triggerAutoSave, readOnly]);

// Callbacks last (MarkdownEditor.tsx:41-48)
const triggerAutoSave = useCallback(() => {
  if (onSave && localValue !== value) {
    setIsSaving(true);
    onSave(localValue);
    setLastSaved(new Date());
    setTimeout(() => setIsSaving(false), 500);
  }
}, [localValue, value, onSave]);
```

**Custom Hooks:**
- Prefix custom hook names with `use`
- Return object with named properties (not arrays)

```typescript
// Custom hook (useDefaultProject.ts:26-43)
export const useDefaultProject = () => {
  const { data, isLoading, error, refetch } = useQuery<Project[], Error>({
    queryKey: ['projects'],
    queryFn: fetchProjects,
  });

  const defaultProject = data?.[0] || null;
  const hasProjects = (data?.length ?? 0) > 0;

  return {
    project: defaultProject,
    hasProjects,
    isLoading,
    error,
    refetch,
  };
};
```

## File Organization

### Directory Structure

```
src/
├── components/
│   ├── common/              # Shared components (ErrorBoundary)
│   ├── details/             # Detail panel components
│   ├── documentation/       # Documentation feature components
│   ├── export/              # Export functionality components
│   ├── layout/              # Layout components
│   ├── quality/             # Quality dashboard components
│   └── visualization/       # Graph and visualization components
├── hooks/                   # Custom React hooks
├── pages/                   # Top-level page components
├── services/                # API services
├── stores/                  # Zustand state management
├── types/                   # TypeScript type definitions
├── utils/                   # Utility functions
└── __tests__/               # Integration tests
    └── App.test.tsx
```

**Component Co-location:**
- Place component tests in `__tests__/` subdirectory
- Keep related components grouped by feature

```
components/documentation/
├── DocumentationView.tsx
├── MarkdownEditor.tsx
├── TemplateSelector.tsx
├── VersionHistory.tsx
├── SourceTypeBadge.tsx
├── index.ts                 # Barrel exports
└── __tests__/
    ├── DocumentationView.test.tsx
    ├── MarkdownEditor.test.tsx
    ├── TemplateSelector.test.tsx
    └── VersionHistory.test.tsx
```

### File Naming

- Use PascalCase for component files: `NetworkGraph.tsx`
- Use camelCase for utilities and hooks: `useDefaultProject.ts`
- Use kebab-case for test files: `NetworkGraph.test.tsx`
- Use `index.ts` for barrel exports

## Import/Export Conventions

### Import Order

Group imports in this order with blank lines between groups:

```typescript
// 1. React and third-party libraries (App.tsx:1-2)
import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// 2. Pages (App.tsx:3)
import { ProjectView } from './pages/ProjectView';

// 3. Hooks (App.tsx:4)
import { useDefaultProject } from './hooks/useDefaultProject';

// 4. Components (App.tsx:5)
import { ErrorBoundary } from './components/common/ErrorBoundary';

// 5. Styles (if any)
import '@uiw/react-md-editor/markdown-editor.css';
```

### Export Patterns

**Named Exports (Preferred):**
```typescript
// Named exports (ErrorBoundary.tsx:19, MarkdownEditor.tsx:20)
export class ErrorBoundary extends Component<Props, State> { ... }
export const MarkdownEditor: React.FC<MarkdownEditorProps> = ({ ... }) => { ... };
```

**Default Exports (App.tsx only):**
```typescript
// Default export only for main App component (App.tsx:88)
export default App;
```

**Barrel Exports:**
```typescript
// components/documentation/index.ts pattern
export { DocumentationView } from './DocumentationView';
export { MarkdownEditor } from './MarkdownEditor';
export { TemplateSelector } from './TemplateSelector';
```

## State Management

### React Query for Server State

**Configuration:**
```typescript
// QueryClient configuration (App.tsx:9-18)
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,     // 5 minutes - matches backend cache TTL
      gcTime: 10 * 60 * 1000,       // 10 minutes - garbage collection time
      retry: process.env.NODE_ENV === 'test' ? false : 2,
      refetchOnWindowFocus: false,
    },
  },
});
```

**Query Hooks:**
```typescript
// useQuery pattern (useDefaultProject.ts:27-30)
const { data, isLoading, error, refetch } = useQuery<Project[], Error>({
  queryKey: ['projects'],
  queryFn: fetchProjects,
});
```

### Zustand for UI State

**Store Creation:**
```typescript
// Zustand store pattern (graphSelectionStore.ts:22-41)
export const useGraphSelectionStore = create<GraphSelectionState>((set) => ({
  // State
  selectedNodeIds: [],
  hoveredNodeId: null,

  // Actions
  selectNode: (nodeId: string) => set({ selectedNodeIds: [nodeId] }),

  toggleNode: (nodeId: string) => set((state) => ({
    selectedNodeIds: state.selectedNodeIds.includes(nodeId)
      ? state.selectedNodeIds.filter((id: string) => id !== nodeId)
      : [...state.selectedNodeIds, nodeId]
  })),

  clearSelection: () => set({ selectedNodeIds: [] }),

  setHoveredNode: (nodeId: string | null) => set({ hoveredNodeId: nodeId }),
}));
```

**Store Usage:**
```typescript
// Use Zustand store in components
const { selectedNodeIds, selectNode, clearSelection } = useGraphSelectionStore();
```

### Local Component State

Use `useState` for component-specific state:

```typescript
// Local state (MarkdownEditor.tsx:30-33)
const [localValue, setLocalValue] = useState(value);
const [isSaving, setIsSaving] = useState(false);
const [lastSaved, setLastSaved] = useState<Date | null>(null);
```

## Error Handling

### React Error Boundaries

**Wrap App in ErrorBoundary:**
```typescript
// App.tsx:78-85
function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <AppContent />
      </QueryClientProvider>
    </ErrorBoundary>
  );
}
```

### API Error Handling

**Throw errors in fetch functions:**
```typescript
// useDefaultProject.ts:16-24
const fetchProjects = async (): Promise<Project[]> => {
  const response = await fetch('/api/v1/projects/');

  if (!response.ok) {
    throw new Error(`Failed to fetch projects: ${response.statusText}`);
  }

  return response.json();
};
```

**Handle errors in component UI:**
```typescript
// App.tsx:36-55
if (error) {
  return (
    <div className="min-h-screen bg-gray-900 flex items-center justify-center">
      <div className="text-center max-w-md">
        <div className="text-red-500 text-5xl mb-4">⚠️</div>
        <h2 className="text-xl font-semibold text-gray-100 mb-2">
          Cannot connect to backend
        </h2>
        <p className="text-gray-400 mb-4">{error.message}</p>
        <button
          onClick={() => refetch()}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Retry
        </button>
      </div>
    </div>
  );
}
```

### Try/Catch in Async Operations

Use try/catch for async operations that need custom error handling:

```typescript
// Example pattern
const handleSave = async () => {
  try {
    await saveData(data);
  } catch (error) {
    console.error('Failed to save:', error);
    setError(error.message);
  }
};
```

## Styling with Tailwind CSS

### Dark Theme First

All components use dark theme by default:

```typescript
// Dark theme classes (App.tsx:26, 38, 60)
<div className="min-h-screen bg-gray-900 flex items-center justify-center">
  <div className="text-center">
    <p className="text-gray-100">Loading Hermes...</p>
  </div>
</div>
```

### Color Palette

**Text Colors:**
- `text-gray-100`: Primary text (white)
- `text-gray-400`: Secondary text
- `text-gray-500`: Tertiary text
- `text-blue-400`, `text-blue-600`: Links and primary actions
- `text-red-400`, `text-red-500`: Errors
- `text-orange-600`: Warnings

**Background Colors:**
- `bg-gray-900`: Primary background
- `bg-gray-800`: Secondary background/cards
- `bg-gray-700`: Tertiary elements
- `bg-blue-600`: Primary buttons
- `bg-red-600`: Destructive actions

### Component Classes

**Button Pattern:**
```typescript
// Primary button (App.tsx:45)
className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"

// Secondary button (ErrorBoundary.tsx:90)
className="px-6 py-2 bg-gray-700 text-white rounded hover:bg-gray-600 transition-colors"
```

**Layout Classes:**
```typescript
// Full-screen container
className="min-h-screen bg-gray-900"

// Centered content
className="flex items-center justify-center"

// Card/panel
className="bg-gray-800 rounded-lg p-4"
```

## Code Comments and Documentation

### JSDoc Comments for Files

Add file-level JSDoc comments describing purpose:

```typescript
/**
 * React Query test wrapper for isolated QueryClient per test
 *
 * This wrapper ensures each test gets a fresh QueryClient instance,
 * preventing cache pollution between tests.
 *
 * Usage:
 *   import { renderWithQueryClient } from '../test-utils/query-test-wrapper';
 *   renderWithQueryClient(<App />);
 *
 * @see https://tanstack.com/query/latest/docs/react/guides/testing
 */
```

### Inline Comments

Use inline comments for complex logic:

```typescript
// App.tsx:7-8
// Configure QueryClient with default options
// 5 minutes stale time matches backend cache TTL
const queryClient = new QueryClient({ ... });

// App.tsx:14
retry: process.env.NODE_ENV === 'test' ? false : 2, // Disable retries in tests
```

### Component Comments

Add JSDoc comments for exported components:

```typescript
/**
 * Rich markdown editor component with live preview, auto-save, and XSS protection
 */
export const MarkdownEditor: React.FC<MarkdownEditorProps> = ({ ... }) => { ... };
```

## Code Review Checklist

**TypeScript:**
- [ ] All functions have explicit return types
- [ ] Interfaces use PascalCase, variables use camelCase
- [ ] Props interfaces end with `Props` suffix
- [ ] No `any` types (use `unknown` if needed)

**React:**
- [ ] Components use function declarations (not arrow functions at top level)
- [ ] Hooks are called at top level, not conditionally
- [ ] Custom hooks start with `use` prefix
- [ ] Named exports (except App.tsx default export)

**State Management:**
- [ ] Server state uses React Query
- [ ] UI state uses Zustand stores
- [ ] Component-specific state uses useState
- [ ] QueryClient uses project-standard config (5min stale, 10min gc)

**Error Handling:**
- [ ] App wrapped in ErrorBoundary
- [ ] API errors thrown in fetch functions
- [ ] Error states displayed with retry buttons
- [ ] Errors logged to console in development

**Styling:**
- [ ] Dark theme classes (`bg-gray-900`, `text-gray-100`)
- [ ] Consistent spacing and sizing
- [ ] Hover states for interactive elements
- [ ] Responsive design considered

**File Organization:**
- [ ] Tests in `__tests__/` subdirectory
- [ ] Related components grouped by feature
- [ ] Imports grouped and ordered correctly
- [ ] File names match component names

**Code Quality:**
- [ ] File-level JSDoc comments present
- [ ] Complex logic has inline comments
- [ ] No console.logs in production code
- [ ] Code follows DRY principle

## References

- [App.tsx](frontend/web-app/src/App.tsx) - Main app setup, React Query config
- [ErrorBoundary.tsx](frontend/web-app/src/components/common/ErrorBoundary.tsx) - Error boundary pattern
- [MarkdownEditor.tsx](frontend/web-app/src/components/documentation/MarkdownEditor.tsx) - Component patterns
- [useDefaultProject.ts](frontend/web-app/src/hooks/useDefaultProject.ts) - Custom hook pattern
- [graphSelectionStore.ts](frontend/web-app/src/stores/graphSelectionStore.ts) - Zustand pattern
- [React Query Docs](https://tanstack.com/query/latest/docs/react/overview)
- [Zustand Docs](https://github.com/pmndrs/zustand)
- [Tailwind CSS Docs](https://tailwindcss.com/docs)
