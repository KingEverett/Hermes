import React from 'react';
import { render } from '@testing-library/react';
import { screen } from '@testing-library/dom';
import MetricsCard from '../MetricsCard';

describe('MetricsCard', () => {
  it('renders title and value correctly', () => {
    render(
      <MetricsCard
        title="Total Findings"
        value={42}
        subtitle="validated"
        trend="neutral"
      />
    );

    expect(screen.getByText('Total Findings')).toBeInTheDocument();
    expect(screen.getByText('42')).toBeInTheDocument();
    expect(screen.getByText('validated')).toBeInTheDocument();
  });

  it('renders string value correctly', () => {
    render(
      <MetricsCard
        title="Accuracy Rate"
        value="85.5%"
        subtitle="validated correct"
        trend="up"
      />
    );

    expect(screen.getByText('85.5%')).toBeInTheDocument();
  });

  it('displays up trend indicator', () => {
    const { container } = render(
      <MetricsCard
        title="Test"
        value="100"
        subtitle="test"
        trend="up"
      />
    );

    const trendIcon = container.querySelector('.text-green-600');
    expect(trendIcon).toBeInTheDocument();
    expect(trendIcon?.textContent).toBe('↑');
  });

  it('displays down trend indicator', () => {
    const { container } = render(
      <MetricsCard
        title="Test"
        value="100"
        subtitle="test"
        trend="down"
      />
    );

    const trendIcon = container.querySelector('.text-red-600');
    expect(trendIcon).toBeInTheDocument();
    expect(trendIcon?.textContent).toBe('↓');
  });

  it('displays neutral trend indicator', () => {
    render(
      <MetricsCard
        title="Test"
        value="100"
        subtitle="test"
        trend="neutral"
      />
    );

    expect(screen.getByText('−')).toBeInTheDocument();
  });
});
