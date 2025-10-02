import React, { useState, useEffect } from 'react';
import { MarkdownEditor } from './MarkdownEditor';
import { SourceTypeBadge, SourceType } from './SourceTypeBadge';
import { VersionHistory } from './VersionHistory';
import { TemplateSelector } from './TemplateSelector';
import { useDocumentation, useCreateDocumentation } from '../../hooks/useDocumentation';
import { useDocumentationStore } from '../../stores/documentationStore';
import MDEditor from '@uiw/react-md-editor';

interface DocumentationViewProps {
  entityType: string;
  entityId: string;
}

/**
 * Main documentation display and editing component
 */
export const DocumentationView: React.FC<DocumentationViewProps> = ({
  entityType,
  entityId,
}) => {
  const {
    documentation,
    isLoading,
    error,
    updateDocumentation,
    isUpdating,
    addNote,
  } = useDocumentation(entityType, entityId);

  const createMutation = useCreateDocumentation();

  const {
    isEditing,
    toggleEditMode,
    setCurrentDoc,
    unsavedChanges,
    setUnsavedChanges,
  } = useDocumentationStore();

  const [localContent, setLocalContent] = useState('');
  const [showVersionHistory, setShowVersionHistory] = useState(false);
  const [showMixedWarning, setShowMixedWarning] = useState(false);

  // Update local content when documentation loads
  useEffect(() => {
    if (documentation) {
      setLocalContent(documentation.content);
      setCurrentDoc(documentation);
      setUnsavedChanges(false);
    } else {
      setLocalContent('');
    }
  }, [documentation, setCurrentDoc, setUnsavedChanges]);

  // Show warning when editing automated content
  useEffect(() => {
    if (
      isEditing &&
      documentation?.source_type === 'automated' &&
      !sessionStorage.getItem('mixedWarningDismissed')
    ) {
      setShowMixedWarning(true);
    }
  }, [isEditing, documentation?.source_type]);

  const handleContentChange = (newContent: string) => {
    setLocalContent(newContent);
    setUnsavedChanges(newContent !== documentation?.content);
  };

  const handleSave = (content: string) => {
    if (!documentation) {
      // Create new documentation
      createMutation.mutate({
        entity_type: entityType,
        entity_id: entityId,
        content,
        source_type: 'manual',
      });
    } else {
      // Determine new source type
      let newSourceType: SourceType = documentation.source_type;
      if (documentation.source_type === 'automated' && content !== documentation.content) {
        newSourceType = 'mixed';
      }

      updateDocumentation({
        content,
        source_type: newSourceType,
      });
    }
    setUnsavedChanges(false);
  };

  const handleAddNote = () => {
    const note = prompt('Enter your note:');
    if (note) {
      addNote({ content: note });
    }
  };

  const handleTemplateInsert = (templateContent: string) => {
    setLocalContent(templateContent);
    setUnsavedChanges(true);
  };

  const handleToggleEdit = () => {
    if (isEditing && unsavedChanges) {
      if (window.confirm('You have unsaved changes. Do you want to discard them?')) {
        setLocalContent(documentation?.content || '');
        setUnsavedChanges(false);
        toggleEditMode();
      }
    } else {
      toggleEditMode();
    }
  };

  const dismissMixedWarning = () => {
    setShowMixedWarning(false);
    sessionStorage.setItem('mixedWarningDismissed', 'true');
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-600">Loading documentation...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-red-50 border border-red-200 rounded">
        <div className="text-red-800 font-semibold">Error loading documentation</div>
        <div className="text-red-600 text-sm mt-1">{(error as Error).message}</div>
      </div>
    );
  }

  const hasDocumentation = !!documentation;

  return (
    <div className="documentation-view h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-4 pb-3 border-b border-gray-200">
        <div className="flex items-center gap-3">
          <h3 className="text-lg font-semibold text-gray-900">Documentation</h3>
          {hasDocumentation && (
            <>
              <SourceTypeBadge sourceType={documentation.source_type} />
              {documentation.version > 1 && (
                <span className="text-xs text-gray-500">v{documentation.version}</span>
              )}
            </>
          )}
        </div>

        <div className="flex items-center gap-2">
          {hasDocumentation && (
            <button
              onClick={() => setShowVersionHistory(!showVersionHistory)}
              className="px-3 py-1 text-sm text-gray-700 hover:bg-gray-100 rounded border border-gray-300"
              title="View version history"
            >
              📜 History
            </button>
          )}
          <button
            onClick={handleToggleEdit}
            className={`px-3 py-1 text-sm rounded border ${
              isEditing
                ? 'bg-gray-200 text-gray-800 border-gray-400'
                : 'bg-blue-500 text-white border-blue-600 hover:bg-blue-600'
            }`}
          >
            {isEditing ? '👁️ View' : '✏️ Edit'}
          </button>
          {!hasDocumentation && (
            <button
              onClick={handleAddNote}
              className="px-3 py-1 text-sm bg-green-500 text-white rounded border border-green-600 hover:bg-green-600"
            >
              ➕ Add Note
            </button>
          )}
        </div>
      </div>

      {/* Mixed content warning */}
      {showMixedWarning && (
        <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded flex items-start justify-between">
          <div className="flex items-start gap-2">
            <span className="text-yellow-600">⚠️</span>
            <div className="text-sm text-yellow-800">
              Editing automated content will mark it as 'mixed'
            </div>
          </div>
          <button
            onClick={dismissMixedWarning}
            className="text-yellow-600 hover:text-yellow-800 text-lg leading-none"
          >
            ×
          </button>
        </div>
      )}

      {/* Version History Panel */}
      {showVersionHistory && hasDocumentation && (
        <div className="mb-4">
          <VersionHistory documentationId={documentation.id} />
        </div>
      )}

      {/* Content Area */}
      <div className="flex-1 overflow-auto">
        {isEditing ? (
          <div className="space-y-3">
            {hasDocumentation && (
              <div className="flex justify-end">
                <TemplateSelector onTemplateSelect={handleTemplateInsert} />
              </div>
            )}
            <MarkdownEditor
              value={localContent}
              onChange={handleContentChange}
              onSave={handleSave}
              autoSaveDelay={2000}
            />
            {isUpdating && (
              <div className="text-sm text-blue-600">Saving changes...</div>
            )}
          </div>
        ) : (
          <div className="prose prose-sm max-w-none">
            {hasDocumentation ? (
              <div data-color-mode="light">
                <MDEditor.Markdown source={documentation.content} />
              </div>
            ) : (
              <div className="text-center py-12 text-gray-500">
                <p className="mb-4">No documentation available for this entity.</p>
                <button
                  onClick={handleToggleEdit}
                  className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
                >
                  Create Documentation
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Footer with metadata */}
      {hasDocumentation && !isEditing && (
        <div className="mt-4 pt-3 border-t border-gray-200 text-xs text-gray-500">
          <div className="flex justify-between">
            <span>
              Last updated: {new Date(documentation.updated_at).toLocaleString()}
            </span>
            {documentation.author && <span>Author: {documentation.author}</span>}
          </div>
        </div>
      )}
    </div>
  );
};

export default DocumentationView;
