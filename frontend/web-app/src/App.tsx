import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ProjectView } from './pages/ProjectView';
import { useDefaultProject } from './hooks/useDefaultProject';
import { ErrorBoundary } from './components/common/ErrorBoundary';

// Configure QueryClient with default options
// 5 minutes stale time matches backend cache TTL
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      gcTime: 10 * 60 * 1000, // 10 minutes (formerly cacheTime)
      retry: process.env.NODE_ENV === 'test' ? false : 2, // Disable retries in tests
      refetchOnWindowFocus: false,
    },
  },
});

export function AppContent() {
  const { project, hasProjects, isLoading, error, refetch } = useDefaultProject();

  // Loading state
  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4"></div>
          <p className="text-gray-100">Loading Hermes...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center max-w-md">
          <div className="text-red-500 text-5xl mb-4">⚠️</div>
          <h2 className="text-xl font-semibold text-gray-100 mb-2">Cannot connect to backend</h2>
          <p className="text-gray-400 mb-4">{error.message}</p>
          <button
            onClick={() => refetch()}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
          >
            Retry
          </button>
          <p className="text-gray-500 text-sm mt-4">
            Check if backend is running at <code className="text-blue-400">http://localhost:8000</code>
          </p>
        </div>
      </div>
    );
  }

  // Empty state - no projects
  if (!hasProjects || !project) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center max-w-md">
          <div className="text-gray-400 text-5xl mb-4">📋</div>
          <h2 className="text-xl font-semibold text-gray-100 mb-2">No projects found</h2>
          <p className="text-gray-400">Import your first scan to get started.</p>
        </div>
      </div>
    );
  }

  // Render ProjectView with default project
  return (
    <div className="h-screen">
      <ProjectView projectId={project.id} />
    </div>
  );
}

function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <AppContent />
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

export default App;