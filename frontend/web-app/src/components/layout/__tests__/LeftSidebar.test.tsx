import { render } from '@testing-library/react';
import { screen } from '@testing-library/dom';
import { LeftSidebar } from '../LeftSidebar';

describe('LeftSidebar', () => {
  test('renders all sections', () => {
    render(<LeftSidebar />);

    expect(screen.getByText('Projects')).toBeInTheDocument();
    expect(screen.getByText('Scan History')).toBeInTheDocument();
    expect(screen.getByText('Filters')).toBeInTheDocument();
  });

  test('renders project selection dropdown', () => {
    render(<LeftSidebar />);

    const select = screen.getByRole('combobox');
    expect(select).toBeInTheDocument();
    expect(screen.getByText('Select Project')).toBeInTheDocument();
  });

  test('renders scan history placeholder', () => {
    render(<LeftSidebar />);

    expect(screen.getByText('No scans imported yet')).toBeInTheDocument();
  });

  test('renders filter placeholder', () => {
    render(<LeftSidebar />);

    expect(screen.getByText('Coming soon...')).toBeInTheDocument();
  });

  test('applies dark theme styling', () => {
    const { container } = render(<LeftSidebar />);

    const sidebar = container.firstChild;
    expect(sidebar).toHaveClass('bg-gray-800', 'border-r', 'border-gray-700');
  });

  test('has proper height and overflow classes', () => {
    const { container } = render(<LeftSidebar />);

    const sidebar = container.firstChild;
    expect(sidebar).toHaveClass('h-full', 'overflow-y-auto');
  });
});
