import { render } from '@testing-library/react';
import { screen } from '@testing-library/dom';
import { ProjectSummary } from '../ProjectSummary';

describe('ProjectSummary', () => {
  test('renders project overview heading', () => {
    render(<ProjectSummary />);

    expect(screen.getByText('Project Overview')).toBeInTheDocument();
  });

  test('renders current project section', () => {
    render(<ProjectSummary />);

    expect(screen.getByText('Current Project')).toBeInTheDocument();
    expect(screen.getByText('Select a project from the left sidebar to begin')).toBeInTheDocument();
  });

  test('renders statistics section with zero values', () => {
    render(<ProjectSummary />);

    expect(screen.getByText('Statistics')).toBeInTheDocument();
    expect(screen.getByText('Hosts')).toBeInTheDocument();
    expect(screen.getByText('Services')).toBeInTheDocument();
    expect(screen.getByText('Vulnerabilities')).toBeInTheDocument();

    const zeroValues = screen.getAllByText('0');
    expect(zeroValues).toHaveLength(3);
  });

  test('renders recent activity section with placeholder', () => {
    render(<ProjectSummary />);

    expect(screen.getByText('Recent Activity')).toBeInTheDocument();
    expect(screen.getByText('No recent activity')).toBeInTheDocument();
  });

  test('applies color coding to statistics', () => {
    const { container } = render(<ProjectSummary />);

    // Check for colored statistics
    const blueText = container.querySelector('.text-blue-400');
    const greenText = container.querySelector('.text-green-400');
    const redText = container.querySelector('.text-red-400');

    expect(blueText).toBeInTheDocument();
    expect(greenText).toBeInTheDocument();
    expect(redText).toBeInTheDocument();
  });

  test('uses dark theme styling', () => {
    const { container } = render(<ProjectSummary />);

    const grayBackgrounds = container.querySelectorAll('.bg-gray-700');
    expect(grayBackgrounds.length).toBeGreaterThan(0);
  });
});
