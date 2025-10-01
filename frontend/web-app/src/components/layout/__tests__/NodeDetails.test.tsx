import { render, screen } from '@testing-library/react';
import { NodeDetails } from '../NodeDetails';

describe('NodeDetails', () => {
  test('renders basic node information', () => {
    const mockNode = {
      id: 'host_1',
      type: 'host' as const,
      label: '192.168.1.1',
    };

    render(<NodeDetails node={mockNode} />);

    expect(screen.getByText('Node Details')).toBeInTheDocument();
    expect(screen.getByText('host_1')).toBeInTheDocument();
    expect(screen.getByText('192.168.1.1')).toBeInTheDocument();
  });

  test('renders host information section for host nodes', () => {
    const mockNode = {
      id: 'host_1',
      type: 'host' as const,
      label: '192.168.1.1',
    };

    render(<NodeDetails node={mockNode} />);

    expect(screen.getByText('Host Information')).toBeInTheDocument();
    expect(screen.queryByText('Service Information')).not.toBeInTheDocument();
  });

  test('renders service information section for service nodes', () => {
    const mockNode = {
      id: 'service_1',
      type: 'service' as const,
      label: 'HTTP (80/tcp)',
    };

    render(<NodeDetails node={mockNode} />);

    expect(screen.getByText('Service Information')).toBeInTheDocument();
    expect(screen.queryByText('Host Information')).not.toBeInTheDocument();
  });

  test('renders vulnerabilities section with placeholder', () => {
    const mockNode = {
      id: 'host_1',
      type: 'host' as const,
      label: '192.168.1.1',
    };

    render(<NodeDetails node={mockNode} />);

    expect(screen.getByText('Vulnerabilities')).toBeInTheDocument();
    expect(screen.getByText('Full details coming in Story 3.4')).toBeInTheDocument();
  });

  test('displays placeholder data for host details', () => {
    const mockNode = {
      id: 'host_1',
      type: 'host' as const,
      label: '192.168.1.1',
    };

    render(<NodeDetails node={mockNode} />);

    const loadingTexts = screen.getAllByText('Loading...');
    expect(loadingTexts.length).toBeGreaterThan(0);
  });

  test('capitalizes node type display', () => {
    const mockNode = {
      id: 'host_1',
      type: 'host' as const,
      label: '192.168.1.1',
    };

    const { container } = render(<NodeDetails node={mockNode} />);

    // The type should be in a paragraph with capitalize class
    const typeElement = container.querySelector('.capitalize');
    expect(typeElement).toBeInTheDocument();
  });
});
