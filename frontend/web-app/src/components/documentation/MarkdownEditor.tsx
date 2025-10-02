import React, { useCallback, useEffect, useRef, useState } from 'react';
import MDEditor from '@uiw/react-md-editor';
import DOMPurify from 'dompurify';
import '@uiw/react-md-editor/markdown-editor.css';

interface MarkdownEditorProps {
  value: string;
  onChange: (value: string) => void;
  onSave?: (value: string) => void;
  autoSaveDelay?: number;
  maxLength?: number;
  readOnly?: boolean;
  placeholder?: string;
  height?: number;
}

/**
 * Rich markdown editor component with live preview, auto-save, and XSS protection
 */
export const MarkdownEditor: React.FC<MarkdownEditorProps> = ({
  value,
  onChange,
  onSave,
  autoSaveDelay = 2000,
  maxLength = 1048576, // 1MB default
  readOnly = false,
  placeholder = 'Start writing your documentation...',
  height = 500,
}) => {
  const [localValue, setLocalValue] = useState(value);
  const [isSaving, setIsSaving] = useState(false);
  const [lastSaved, setLastSaved] = useState<Date | null>(null);
  const autoSaveTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Update local value when prop changes
  useEffect(() => {
    setLocalValue(value);
  }, [value]);

  // Auto-save functionality with debouncing
  const triggerAutoSave = useCallback(() => {
    if (onSave && localValue !== value) {
      setIsSaving(true);
      onSave(localValue);
      setLastSaved(new Date());
      setTimeout(() => setIsSaving(false), 500);
    }
  }, [localValue, value, onSave]);

  // Debounced auto-save
  useEffect(() => {
    if (autoSaveTimerRef.current) {
      clearTimeout(autoSaveTimerRef.current);
    }

    if (localValue !== value && !readOnly) {
      autoSaveTimerRef.current = setTimeout(() => {
        triggerAutoSave();
      }, autoSaveDelay);
    }

    return () => {
      if (autoSaveTimerRef.current) {
        clearTimeout(autoSaveTimerRef.current);
      }
    };
  }, [localValue, value, autoSaveDelay, triggerAutoSave, readOnly]);

  // Sanitize markdown content
  const sanitizeContent = (content: string): string => {
    return DOMPurify.sanitize(content, {
      ALLOWED_TAGS: [
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'p', 'br', 'hr',
        'code', 'pre',
        'ul', 'ol', 'li',
        'a', 'strong', 'em', 'del', 'ins',
        'blockquote',
        'table', 'thead', 'tbody', 'tr', 'th', 'td',
        'img',
      ],
      ALLOWED_ATTR: ['href', 'class', 'src', 'alt', 'title', 'target'],
    });
  };

  const handleChange = (newValue?: string) => {
    const sanitized = sanitizeContent(newValue || '');

    // Check length limit
    if (sanitized.length <= maxLength) {
      setLocalValue(sanitized);
      onChange(sanitized);
    }
  };

  const characterCount = localValue.length;
  const percentUsed = (characterCount / maxLength) * 100;
  const showWarning = percentUsed >= 80;

  return (
    <div className="markdown-editor-container">
      <div className="flex justify-between items-center mb-2 text-sm text-gray-600">
        <div className="flex items-center gap-4">
          <span className={`${showWarning ? 'text-orange-600 font-semibold' : ''}`}>
            {characterCount.toLocaleString()} / {maxLength.toLocaleString()} characters
          </span>
          {showWarning && (
            <span className="text-orange-600">
              ⚠️ Approaching character limit
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {isSaving && (
            <span className="text-blue-600">💾 Saving...</span>
          )}
          {lastSaved && !isSaving && (
            <span className="text-gray-500">
              Last saved: {lastSaved.toLocaleTimeString()}
            </span>
          )}
        </div>
      </div>

      <div data-color-mode="light">
        <MDEditor
          value={localValue}
          onChange={handleChange}
          height={height}
          preview="live"
          hideToolbar={readOnly}
          enableScroll={true}
          textareaProps={{
            readOnly,
            placeholder,
          }}
          previewOptions={{
            rehypePlugins: [],
          }}
        />
      </div>

      {showWarning && (
        <div className="mt-2 p-2 bg-orange-50 border border-orange-200 rounded text-sm text-orange-800">
          You are approaching the character limit. Consider breaking content into multiple sections.
        </div>
      )}
    </div>
  );
};

export default MarkdownEditor;
