import React from 'react';

export type SourceType = 'automated' | 'manual' | 'mixed';

interface SourceTypeBadgeProps {
  sourceType: SourceType;
  className?: string;
}

const sourceTypeConfig = {
  automated: {
    label: '🤖 Automated',
    badgeClass: 'bg-blue-100 text-blue-800 border-blue-300',
    containerClass: 'bg-blue-50 border-blue-200 border-l-4',
  },
  manual: {
    label: '✏️ Manual',
    badgeClass: 'bg-green-100 text-green-800 border-green-300',
    containerClass: 'bg-green-50 border-green-200 border-l-4',
  },
  mixed: {
    label: '🔀 Mixed',
    badgeClass: 'bg-purple-100 text-purple-800 border-purple-300',
    containerClass: 'bg-purple-50 border-purple-200 border-l-4',
  },
};

/**
 * Badge component to visually distinguish automated, manual, and mixed content
 */
export const SourceTypeBadge: React.FC<SourceTypeBadgeProps> = ({
  sourceType,
  className = '',
}) => {
  const config = sourceTypeConfig[sourceType];

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${config.badgeClass} ${className}`}
      data-testid={`source-badge-${sourceType}`}
    >
      {config.label}
    </span>
  );
};

export { sourceTypeConfig };
export default SourceTypeBadge;
