import React, { useState } from 'react';
import { useTemplates } from '../../hooks/useTemplates';
import { Template } from '../../services/documentationApi';

interface TemplateSelectorProps {
  onTemplateSelect: (content: string) => void;
}

/**
 * Dropdown component for selecting and inserting documentation templates
 */
export const TemplateSelector: React.FC<TemplateSelectorProps> = ({
  onTemplateSelect,
}) => {
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [isOpen, setIsOpen] = useState(false);
  const [hoveredTemplate, setHoveredTemplate] = useState<Template | null>(null);
  const [showPreview, setShowPreview] = useState(false);

  const { data: templates, isLoading } = useTemplates(selectedCategory || undefined);

  const categories = [
    'vulnerability-assessment',
    'host-reconnaissance',
    'exploitation',
    'post-exploitation',
  ];

  const handleTemplateSelect = (template: Template) => {
    onTemplateSelect(template.content);
    setIsOpen(false);
    setHoveredTemplate(null);
  };

  const handlePreview = (template: Template) => {
    setHoveredTemplate(template);
    setShowPreview(true);
  };

  if (isLoading) {
    return (
      <button
        disabled
        className="px-3 py-1 text-sm bg-gray-200 text-gray-600 rounded border border-gray-300 cursor-not-allowed"
      >
        Loading templates...
      </button>
    );
  }

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="px-3 py-1 text-sm bg-white text-gray-700 rounded border border-gray-300 hover:bg-gray-50 flex items-center gap-2"
      >
        📋 Insert Template
        <span className="text-xs">{isOpen ? '▲' : '▼'}</span>
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 bg-white rounded-lg shadow-xl border border-gray-200 z-50">
          {/* Category Filter */}
          <div className="p-3 border-b border-gray-200">
            <label className="text-xs font-semibold text-gray-700 mb-2 block">
              Filter by Category
            </label>
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="w-full px-2 py-1 text-sm border border-gray-300 rounded"
            >
              <option value="">All Categories</option>
              {categories.map((cat) => (
                <option key={cat} value={cat}>
                  {cat
                    .split('-')
                    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
                    .join(' ')}
                </option>
              ))}
            </select>
          </div>

          {/* Templates List */}
          <div className="max-h-96 overflow-y-auto">
            {templates && templates.length > 0 ? (
              templates.map((template) => (
                <div
                  key={template.id}
                  className="p-3 border-b border-gray-100 hover:bg-gray-50 cursor-pointer"
                  onMouseEnter={() => setHoveredTemplate(template)}
                  onMouseLeave={() => setHoveredTemplate(null)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1" onClick={() => handleTemplateSelect(template)}>
                      <div className="font-semibold text-sm text-gray-800 mb-1">
                        {template.name}
                        {template.is_system && (
                          <span className="ml-2 px-2 py-0.5 text-xs bg-blue-100 text-blue-800 rounded">
                            System
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-gray-600">{template.description}</div>
                      <div className="text-xs text-gray-400 mt-1">
                        Category: {template.category}
                      </div>
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handlePreview(template);
                      }}
                      className="ml-2 px-2 py-1 text-xs text-blue-600 hover:bg-blue-100 rounded"
                      title="Preview template"
                    >
                      👁️
                    </button>
                  </div>
                </div>
              ))
            ) : (
              <div className="p-6 text-center text-gray-500 text-sm">
                No templates found
                {selectedCategory && ' in this category'}
              </div>
            )}
          </div>

          {/* Close Button */}
          <div className="p-3 border-t border-gray-200 bg-gray-50">
            <button
              onClick={() => setIsOpen(false)}
              className="w-full px-3 py-2 text-sm bg-gray-200 text-gray-800 rounded hover:bg-gray-300"
            >
              Close
            </button>
          </div>
        </div>
      )}

      {/* Preview Modal */}
      {showPreview && hoveredTemplate && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-3xl w-full max-h-[80vh] flex flex-col">
            <div className="p-4 border-b border-gray-200 flex items-center justify-between">
              <div>
                <h3 className="font-semibold text-lg">{hoveredTemplate.name}</h3>
                <p className="text-sm text-gray-600 mt-1">{hoveredTemplate.description}</p>
              </div>
              <button
                onClick={() => setShowPreview(false)}
                className="text-gray-500 hover:text-gray-700 text-2xl leading-none"
              >
                ×
              </button>
            </div>

            <div className="p-4 overflow-auto flex-1">
              <pre className="text-sm bg-gray-50 p-4 rounded border border-gray-200 whitespace-pre-wrap font-mono">
                {hoveredTemplate.content}
              </pre>
            </div>

            <div className="p-4 border-t border-gray-200 flex justify-end gap-2">
              <button
                onClick={() => setShowPreview(false)}
                className="px-4 py-2 text-sm bg-gray-200 text-gray-800 rounded hover:bg-gray-300"
              >
                Close
              </button>
              <button
                onClick={() => {
                  handleTemplateSelect(hoveredTemplate);
                  setShowPreview(false);
                }}
                className="px-4 py-2 text-sm bg-blue-500 text-white rounded hover:bg-blue-600"
              >
                Use This Template
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TemplateSelector;
