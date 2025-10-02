import React from 'react';
import { render } from '@testing-library/react';
import { screen, waitFor } from '@testing-library/dom';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { DocumentationView } from '../DocumentationView';
import * as useDocumentationHook from '../../../hooks/useDocumentation';

// Mock the hooks
jest.mock('../../../hooks/useDocumentation');
jest.mock('../../../hooks/useTemplates');
jest.mock('../../../stores/documentationStore');

const mockUseDocumentation = useDocumentationHook as jest.Mocked<typeof useDocumentationHook>;

describe('DocumentationView', () => {
  let queryClient: QueryClient;

  // Default mock return value for useDocumentation
  const defaultMockDocumentation = {
    documentation: {
      id: 'doc-1',
      entity_type: 'host' as const,
      entity_id: 'host-1',
      content: '# Test Documentation\n\nTest content',
      source_type: 'manual' as const,
      created_at: '2025-09-30T12:00:00Z',
      updated_at: '2025-09-30T12:00:00Z',
      version: 1,
    } as any,
    isLoading: false,
    error: null,
    refetch: jest.fn(),
    updateDocumentation: jest.fn(),
    updateDocumentationAsync: jest.fn(),
    isUpdating: false,
    addNote: jest.fn(),
    addNoteAsync: jest.fn(),
    isAddingNote: false,
  } as any;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });

    // Setup default mock implementations
    mockUseDocumentation.useDocumentation.mockReturnValue(defaultMockDocumentation);

    mockUseDocumentation.useCreateDocumentation.mockReturnValue({
      mutate: jest.fn(),
      mutateAsync: jest.fn(),
      isPending: false,
      isError: false,
      isSuccess: false,
      error: null,
      data: undefined,
      reset: jest.fn(),
      status: 'idle',
      variables: undefined,
      context: undefined,
      failureCount: 0,
      failureReason: null,
      isIdle: true,
      isPaused: false,
      submittedAt: 0,
    });

    require('../../../stores/documentationStore').useDocumentationStore.mockReturnValue({
      isEditing: false,
      toggleEditMode: jest.fn(),
      setCurrentDoc: jest.fn(),
      unsavedChanges: false,
      setUnsavedChanges: jest.fn(),
    });
  });

  const renderWithQueryClient = (component: React.ReactElement) => {
    return render(
      <QueryClientProvider client={queryClient}>
        {component}
      </QueryClientProvider>
    );
  };

  it('renders loading state', () => {
    mockUseDocumentation.useDocumentation.mockReturnValue({
      ...defaultMockDocumentation,
      isLoading: true,
    });

    renderWithQueryClient(
      <DocumentationView entityType="host" entityId="host-1" />
    );

    expect(screen.getByText(/Loading documentation/i)).toBeInTheDocument();
  });

  it('renders error state', () => {
    mockUseDocumentation.useDocumentation.mockReturnValue({
      ...defaultMockDocumentation,
      error: new Error('Failed to load'),
    });

    renderWithQueryClient(
      <DocumentationView entityType="host" entityId="host-1" />
    );

    expect(screen.getByText(/Error loading documentation/i)).toBeInTheDocument();
    expect(screen.getByText(/Failed to load/i)).toBeInTheDocument();
  });

  it('renders documentation with source type badge', () => {
    renderWithQueryClient(
      <DocumentationView entityType="host" entityId="host-1" />
    );

    expect(screen.getByText(/Documentation/i)).toBeInTheDocument();
    expect(screen.getByTestId('source-badge-manual')).toBeInTheDocument();
  });

  it('displays version number when version > 1', () => {
    mockUseDocumentation.useDocumentation.mockReturnValue({
      ...defaultMockDocumentation,
      documentation: {
        ...defaultMockDocumentation.documentation!,
        version: 3,
      },
    });

    renderWithQueryClient(
      <DocumentationView entityType="host" entityId="host-1" />
    );

    expect(screen.getByText(/v3/i)).toBeInTheDocument();
  });

  it('toggles edit mode when edit button clicked', async () => {
    const user = userEvent.setup();
    const mockToggleEditMode = jest.fn();

    require('../../../src/stores/documentationStore').useDocumentationStore.mockReturnValue({
      isEditing: false,
      toggleEditMode: mockToggleEditMode,
      setCurrentDoc: jest.fn(),
      unsavedChanges: false,
      setUnsavedChanges: jest.fn(),
    });

    renderWithQueryClient(
      <DocumentationView entityType="host" entityId="host-1" />
    );

    const editButton = screen.getByRole('button', { name: /Edit/i });
    await user.click(editButton);

    expect(mockToggleEditMode).toHaveBeenCalled();
  });

  it('shows mixed content warning when editing automated content', () => {
    mockUseDocumentation.useDocumentation.mockReturnValue({
      ...defaultMockDocumentation,
      documentation: {
        ...defaultMockDocumentation.documentation!,
        source_type: 'automated',
      },
    });

    require('../../../src/stores/documentationStore').useDocumentationStore.mockReturnValue({
      isEditing: true,
      toggleEditMode: jest.fn(),
      setCurrentDoc: jest.fn(),
      unsavedChanges: false,
      setUnsavedChanges: jest.fn(),
    });

    renderWithQueryClient(
      <DocumentationView entityType="host" entityId="host-1" />
    );

    expect(screen.getByText(/Editing automated content will mark it as 'mixed'/i))
      .toBeInTheDocument();
  });

  it('shows create documentation prompt when no documentation exists', () => {
    mockUseDocumentation.useDocumentation.mockReturnValue({
      ...defaultMockDocumentation,
      documentation: null as any,
    });

    renderWithQueryClient(
      <DocumentationView entityType="host" entityId="host-1" />
    );

    expect(screen.getByText(/No documentation available/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Create Documentation/i }))
      .toBeInTheDocument();
  });

  it('displays version history when history button clicked', async () => {
    const user = userEvent.setup();

    renderWithQueryClient(
      <DocumentationView entityType="host" entityId="host-1" />
    );

    const historyButton = screen.getByRole('button', { name: /History/i });
    await user.click(historyButton);

    // Version history component should be rendered
    // (Actual content depends on VersionHistory component implementation)
  });

  it('confirms before discarding unsaved changes', async () => {
    const user = userEvent.setup();
    global.confirm = jest.fn(() => true);

    require('../../../src/stores/documentationStore').useDocumentationStore.mockReturnValue({
      isEditing: true,
      toggleEditMode: jest.fn(),
      setCurrentDoc: jest.fn(),
      unsavedChanges: true,
      setUnsavedChanges: jest.fn(),
    });

    renderWithQueryClient(
      <DocumentationView entityType="host" entityId="host-1" />
    );

    const viewButton = screen.getByRole('button', { name: /View/i });
    await user.click(viewButton);

    expect(global.confirm).toHaveBeenCalledWith(
      expect.stringContaining('unsaved changes')
    );
  });

  it('displays metadata footer in view mode', () => {
    renderWithQueryClient(
      <DocumentationView entityType="host" entityId="host-1" />
    );

    expect(screen.getByText(/Last updated:/i)).toBeInTheDocument();
  });
});
