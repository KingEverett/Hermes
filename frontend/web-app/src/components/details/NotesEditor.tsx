import React, { useState, useEffect, useCallback, useRef } from 'react';
import MDEditor from '@uiw/react-md-editor';
import { useNotes, useCreateNote, useUpdateNote } from '../../hooks/useNotes';

interface NotesEditorProps {
  entityType: 'host' | 'service' | 'vulnerability';
  entityId: string;
  projectId: string;
}

interface Note {
  id: string;
  project_id: string;
  entity_type: 'host' | 'service' | 'vulnerability';
  entity_id: string;
  content: string;
  author?: string;
  tags: string[];
  created_at: Date | string;
  updated_at: Date | string;
}

export const NotesEditor: React.FC<NotesEditorProps> = ({ entityType, entityId, projectId }) => {
  const { data: notes, isLoading } = useNotes(entityType, entityId);
  const createNoteMutation = useCreateNote();
  const updateNoteMutation = useUpdateNote();

  const [currentNote, setCurrentNote] = useState<Note | null>(null);
  const [content, setContent] = useState('');
  const [tags, setTags] = useState<string[]>([]);
  const [tagInput, setTagInput] = useState('');
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved'>('idle');

  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Load the first note or create a new one
  useEffect(() => {
    if (notes && notes.length > 0) {
      const latestNote = notes[0];
      setCurrentNote(latestNote);
      setContent(latestNote.content);
      setTags(latestNote.tags || []);
    } else {
      setCurrentNote(null);
      setContent('');
      setTags([]);
    }
  }, [notes]);

  // Auto-save with debouncing
  const saveNote = useCallback(async () => {
    if (!content.trim() && tags.length === 0) {
      return; // Don't save empty notes
    }

    setSaveStatus('saving');

    try {
      if (currentNote) {
        // Update existing note
        await updateNoteMutation.mutateAsync({
          id: currentNote.id,
          content,
          tags,
        });
      } else {
        // Create new note
        const newNote = await createNoteMutation.mutateAsync({
          project_id: projectId,
          entity_type: entityType,
          entity_id: entityId,
          content,
          tags,
        });
        setCurrentNote(newNote);
      }
      setSaveStatus('saved');
      setTimeout(() => setSaveStatus('idle'), 2000);
    } catch (error) {
      console.error('Failed to save note:', error);
      setSaveStatus('idle');
    }
  }, [content, tags, currentNote, entityType, entityId, projectId, createNoteMutation, updateNoteMutation]);

  // Debounced save handler
  useEffect(() => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    debounceTimerRef.current = setTimeout(() => {
      if (content.trim() || tags.length > 0) {
        saveNote();
      }
    }, 2000);

    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, [content, tags, saveNote]);

  const handleAddTag = () => {
    const trimmedTag = tagInput.trim();
    if (trimmedTag && !tags.includes(trimmedTag)) {
      setTags([...tags, trimmedTag]);
      setTagInput('');
    }
  };

  const handleRemoveTag = (tagToRemove: string) => {
    setTags(tags.filter(tag => tag !== tagToRemove));
  };

  const handleTagInputKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleAddTag();
    }
  };

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-4">
        <div className="h-40 bg-gray-700 rounded"></div>
        <div className="h-6 bg-gray-700 rounded w-1/2"></div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Save Status Indicator */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-100">Notes</h3>
        {saveStatus !== 'idle' && (
          <div className="flex items-center gap-2 text-sm">
            {saveStatus === 'saving' && (
              <>
                <svg className="animate-spin h-4 w-4 text-blue-400" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <span className="text-blue-400">Saving...</span>
              </>
            )}
            {saveStatus === 'saved' && (
              <>
                <svg className="h-4 w-4 text-green-400" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                <span className="text-green-400">Saved</span>
              </>
            )}
          </div>
        )}
      </div>

      {/* Markdown Editor */}
      <div data-color-mode="dark">
        <MDEditor
          value={content}
          onChange={(val) => setContent(val || '')}
          height={400}
          preview="edit"
          className="bg-gray-800"
          textareaProps={{
            placeholder: 'Add your notes here... (Markdown supported)',
          }}
        />
      </div>

      {/* Tags Section */}
      <div>
        <label className="text-sm text-gray-400 block mb-2">Tags</label>
        <div className="flex items-center gap-2 mb-2">
          <input
            type="text"
            value={tagInput}
            onChange={(e) => setTagInput(e.target.value)}
            onKeyDown={handleTagInputKeyDown}
            placeholder="Add a tag..."
            className="flex-1 bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-blue-600"
          />
          <button
            onClick={handleAddTag}
            disabled={!tagInput.trim()}
            className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:text-gray-500 text-white px-4 py-2 rounded text-sm font-semibold transition-colors"
          >
            Add
          </button>
        </div>

        {/* Tag List */}
        {tags.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {tags.map((tag) => (
              <span
                key={tag}
                className="inline-flex items-center gap-1 bg-blue-900/50 border border-blue-700 text-blue-300 px-3 py-1 rounded-full text-sm"
              >
                {tag}
                <button
                  onClick={() => handleRemoveTag(tag)}
                  className="hover:text-blue-100 transition-colors"
                  aria-label={`Remove ${tag} tag`}
                >
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                  </svg>
                </button>
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Note Metadata */}
      {currentNote && (
        <div className="border-t border-gray-700 pt-4 space-y-1 text-xs text-gray-500">
          {currentNote.author && (
            <div>Author: <span className="text-gray-400">{currentNote.author}</span></div>
          )}
          <div>
            Created: <span className="text-gray-400">
              {new Date(currentNote.created_at).toLocaleString('en-US', {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
              })}
            </span>
          </div>
          <div>
            Last Updated: <span className="text-gray-400">
              {new Date(currentNote.updated_at).toLocaleString('en-US', {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
              })}
            </span>
          </div>
        </div>
      )}

      {/* All Notes List */}
      {notes && notes.length > 1 && (
        <div className="border-t border-gray-700 pt-4">
          <h4 className="text-sm font-semibold text-gray-300 mb-2">Previous Notes</h4>
          <div className="space-y-2">
            {notes.slice(1).map((note) => (
              <button
                key={note.id}
                onClick={() => {
                  setCurrentNote(note);
                  setContent(note.content);
                  setTags(note.tags || []);
                }}
                className="w-full text-left bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded p-3 text-sm transition-colors"
              >
                <div className="text-gray-300 line-clamp-2 mb-1">{note.content || 'Empty note'}</div>
                <div className="text-xs text-gray-500">
                  {new Date(note.updated_at).toLocaleString('en-US', {
                    month: 'short',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
