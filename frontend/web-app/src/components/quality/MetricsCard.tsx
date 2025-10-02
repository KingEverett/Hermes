import React from 'react';

interface MetricsCardProps {
  title: string;
  value: string | number;
  subtitle: string;
  trend: 'up' | 'down' | 'neutral';
}

const MetricsCard: React.FC<MetricsCardProps> = ({ title, value, subtitle, trend }) => {
  const getTrendColor = () => {
    switch (trend) {
      case 'up':
        return 'text-green-600';
      case 'down':
        return 'text-red-600';
      default:
        return 'text-gray-600';
    }
  };

  const getTrendIcon = () => {
    switch (trend) {
      case 'up':
        return '↑';
      case 'down':
        return '↓';
      default:
        return '−';
    }
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex justify-between items-start">
        <div className="flex-1">
          <h3 className="text-sm font-medium text-gray-600 mb-2">{title}</h3>
          <div className="text-3xl font-bold text-gray-900 mb-1">{value}</div>
          <p className="text-sm text-gray-500">{subtitle}</p>
        </div>
        <div className={`text-2xl ${getTrendColor()}`}>{getTrendIcon()}</div>
      </div>
    </div>
  );
};

export default MetricsCard;
