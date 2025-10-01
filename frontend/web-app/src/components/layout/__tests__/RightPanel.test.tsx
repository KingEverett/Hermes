import { render, screen } from '@testing-library/react';
import { RightPanel } from '../RightPanel';

describe('RightPanel', () => {
  test('renders NodeDetails when node is selected', () => {
    const mockNode = {
      id: 'host_1',
      type: 'host' as const,
      label: '192.168.1.1',
    };

    render(<RightPanel selectedNode={mockNode} />);

    expect(screen.getByText('Node Details')).toBeInTheDocument();
    expect(screen.getByText('host_1')).toBeInTheDocument();
    expect(screen.getByText('192.168.1.1')).toBeInTheDocument();
  });

  test('renders ProjectSummary when no node is selected', () => {
    render(<RightPanel selectedNode={null} />);

    expect(screen.getByText('Project Overview')).toBeInTheDocument();
    expect(screen.getByText('Current Project')).toBeInTheDocument();
  });

  test('applies dark theme styling', () => {
    const { container } = render(<RightPanel selectedNode={null} />);

    const panel = container.firstChild;
    expect(panel).toHaveClass('bg-gray-800', 'border-l', 'border-gray-700');
  });

  test('has proper height and overflow classes', () => {
    const { container } = render(<RightPanel selectedNode={null} />);

    const panel = container.firstChild;
    expect(panel).toHaveClass('h-full', 'overflow-y-auto');
  });

  test('switches from ProjectSummary to NodeDetails when node selected', () => {
    const { rerender } = render(<RightPanel selectedNode={null} />);
    expect(screen.getByText('Project Overview')).toBeInTheDocument();

    const mockNode = {
      id: 'service_1',
      type: 'service' as const,
      label: 'HTTP (80/tcp)',
    };

    rerender(<RightPanel selectedNode={mockNode} />);
    expect(screen.getByText('Node Details')).toBeInTheDocument();
    expect(screen.queryByText('Project Overview')).not.toBeInTheDocument();
  });
});
