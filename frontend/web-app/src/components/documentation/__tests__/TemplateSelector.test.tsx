import React from 'react';
import { render } from '@testing-library/react';
import { screen, waitFor } from '@testing-library/dom';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TemplateSelector } from '../TemplateSelector';
import * as useTemplatesHook from '../../../hooks/useTemplates';

jest.mock('../../../hooks/useTemplates');

const mockUseTemplates = useTemplatesHook as jest.Mocked<typeof useTemplatesHook>;

describe('TemplateSelector', () => {
  let queryClient: QueryClient;
  const mockOnTemplateSelect = jest.fn();

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });

    mockUseTemplates.useTemplates.mockReturnValue({
      data: [
        {
          id: 'tmpl-1',
          name: 'Service Vulnerability Assessment',
          description: 'Template for service vulnerability analysis',
          category: 'vulnerability-assessment',
          content: '# Service Assessment\n\n## Findings\n...',
          is_system: true,
          created_at: '2025-09-30T10:00:00Z',
          updated_at: '2025-09-30T10:00:00Z',
        },
        {
          id: 'tmpl-2',
          name: 'Host Reconnaissance',
          description: 'Template for host recon notes',
          category: 'host-reconnaissance',
          content: '# Host Recon\n\n## Discovery\n...',
          is_system: true,
          created_at: '2025-09-30T10:00:00Z',
          updated_at: '2025-09-30T10:00:00Z',
        },
      ],
      isLoading: false,
      error: null,
    } as any);

    mockOnTemplateSelect.mockClear();
  });

  const renderWithQueryClient = (component: React.ReactElement) => {
    return render(
      <QueryClientProvider client={queryClient}>
        {component}
      </QueryClientProvider>
    );
  };

  it('renders insert template button', () => {
    renderWithQueryClient(
      <TemplateSelector onTemplateSelect={mockOnTemplateSelect} />
    );

    expect(screen.getByRole('button', { name: /Insert Template/i }))
      .toBeInTheDocument();
  });

  it('shows loading state', () => {
    mockUseTemplates.useTemplates.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    } as any);

    renderWithQueryClient(
      <TemplateSelector onTemplateSelect={mockOnTemplateSelect} />
    );

    expect(screen.getByText(/Loading templates/i)).toBeInTheDocument();
  });

  it('opens dropdown when button clicked', async () => {
    const user = userEvent.setup();

    renderWithQueryClient(
      <TemplateSelector onTemplateSelect={mockOnTemplateSelect} />
    );

    const button = screen.getByRole('button', { name: /Insert Template/i });
    await user.click(button);

    expect(screen.getByText(/Filter by Category/i)).toBeInTheDocument();
    expect(screen.getByText(/Service Vulnerability Assessment/i)).toBeInTheDocument();
  });

  it('displays all templates in dropdown', async () => {
    const user = userEvent.setup();

    renderWithQueryClient(
      <TemplateSelector onTemplateSelect={mockOnTemplateSelect} />
    );

    const button = screen.getByRole('button', { name: /Insert Template/i });
    await user.click(button);

    expect(screen.getByText(/Service Vulnerability Assessment/i)).toBeInTheDocument();
    expect(screen.getByText(/Host Reconnaissance/i)).toBeInTheDocument();
  });

  it('filters templates by category', async () => {
    const user = userEvent.setup();

    renderWithQueryClient(
      <TemplateSelector onTemplateSelect={mockOnTemplateSelect} />
    );

    const button = screen.getByRole('button', { name: /Insert Template/i });
    await user.click(button);

    const categorySelect = screen.getByRole('combobox');
    await user.selectOptions(categorySelect, 'vulnerability-assessment');

    // Mock should be called with the category filter
    expect(mockUseTemplates.useTemplates).toHaveBeenCalledWith('vulnerability-assessment');
  });

  it('calls onTemplateSelect when template is clicked', async () => {
    const user = userEvent.setup();

    renderWithQueryClient(
      <TemplateSelector onTemplateSelect={mockOnTemplateSelect} />
    );

    const button = screen.getByRole('button', { name: /Insert Template/i });
    await user.click(button);

    const template = screen.getByText(/Service Vulnerability Assessment/i);
    await user.click(template);

    expect(mockOnTemplateSelect).toHaveBeenCalledWith(
      '# Service Assessment\n\n## Findings\n...'
    );
  });

  it('shows system badge for system templates', async () => {
    const user = userEvent.setup();

    renderWithQueryClient(
      <TemplateSelector onTemplateSelect={mockOnTemplateSelect} />
    );

    const button = screen.getByRole('button', { name: /Insert Template/i });
    await user.click(button);

    const systemBadges = screen.getAllByText(/System/i);
    expect(systemBadges.length).toBeGreaterThan(0);
  });

  it('opens preview modal when preview button clicked', async () => {
    const user = userEvent.setup();

    renderWithQueryClient(
      <TemplateSelector onTemplateSelect={mockOnTemplateSelect} />
    );

    const button = screen.getByRole('button', { name: /Insert Template/i });
    await user.click(button);

    const previewButtons = screen.getAllByRole('button', { name: /👁️/i });
    await user.click(previewButtons[0]);

    await waitFor(() => {
      expect(screen.getByText(/Service Vulnerability Assessment/i)).toBeInTheDocument();
      expect(screen.getByText(/# Service Assessment/i)).toBeInTheDocument();
    });
  });

  it('closes preview modal', async () => {
    const user = userEvent.setup();

    renderWithQueryClient(
      <TemplateSelector onTemplateSelect={mockOnTemplateSelect} />
    );

    // Open dropdown and preview
    const button = screen.getByRole('button', { name: /Insert Template/i });
    await user.click(button);

    const previewButtons = screen.getAllByRole('button', { name: /👁️/i });
    await user.click(previewButtons[0]);

    // Close preview
    const closeButtons = screen.getAllByRole('button', { name: /Close/i });
    await user.click(closeButtons[0]);

    await waitFor(() => {
      expect(screen.queryByText(/# Service Assessment/i)).not.toBeInTheDocument();
    });
  });

  it('inserts template from preview modal', async () => {
    const user = userEvent.setup();

    renderWithQueryClient(
      <TemplateSelector onTemplateSelect={mockOnTemplateSelect} />
    );

    // Open dropdown and preview
    const button = screen.getByRole('button', { name: /Insert Template/i });
    await user.click(button);

    const previewButtons = screen.getAllByRole('button', { name: /👁️/i });
    await user.click(previewButtons[0]);

    // Click use template button
    const useButton = screen.getByRole('button', { name: /Use This Template/i });
    await user.click(useButton);

    expect(mockOnTemplateSelect).toHaveBeenCalledWith(
      '# Service Assessment\n\n## Findings\n...'
    );
  });

  it('closes dropdown when close button clicked', async () => {
    const user = userEvent.setup();

    renderWithQueryClient(
      <TemplateSelector onTemplateSelect={mockOnTemplateSelect} />
    );

    const button = screen.getByRole('button', { name: /Insert Template/i });
    await user.click(button);

    const closeButton = screen.getByRole('button', { name: /^Close$/i });
    await user.click(closeButton);

    await waitFor(() => {
      expect(screen.queryByText(/Filter by Category/i)).not.toBeInTheDocument();
    });
  });

  it('shows no templates message when list is empty', async () => {
    const user = userEvent.setup();

    mockUseTemplates.useTemplates.mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    } as any);

    renderWithQueryClient(
      <TemplateSelector onTemplateSelect={mockOnTemplateSelect} />
    );

    const button = screen.getByRole('button', { name: /Insert Template/i });
    await user.click(button);

    expect(screen.getByText(/No templates found/i)).toBeInTheDocument();
  });
});
