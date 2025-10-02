import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

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

interface CreateNoteInput {
  project_id: string;
  entity_type: 'host' | 'service' | 'vulnerability';
  entity_id: string;
  content: string;
  tags: string[];
}

interface UpdateNoteInput {
  id: string;
  content: string;
  tags: string[];
}

const fetchNotes = async (entityType: string, entityId: string): Promise<Note[]> => {
  const response = await fetch(`/api/v1/notes?entity_type=${entityType}&entity_id=${entityId}`);

  if (!response.ok) {
    if (response.status === 404) {
      return []; // Return empty array if no notes found
    }
    throw new Error('Failed to fetch notes');
  }

  return response.json();
};

const createNote = async (input: CreateNoteInput): Promise<Note> => {
  const response = await fetch('/api/v1/notes', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(input),
  });

  if (!response.ok) {
    throw new Error('Failed to create note');
  }

  return response.json();
};

const updateNote = async (input: UpdateNoteInput): Promise<Note> => {
  const response = await fetch(`/api/v1/notes/${input.id}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      content: input.content,
      tags: input.tags,
    }),
  });

  if (!response.ok) {
    throw new Error('Failed to update note');
  }

  return response.json();
};

export const useNotes = (entityType: string, entityId: string) => {
  return useQuery({
    queryKey: ['notes', entityType, entityId],
    queryFn: () => fetchNotes(entityType, entityId),
    enabled: !!entityType && !!entityId,
    staleTime: 30000, // 30 seconds
  });
};

export const useCreateNote = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createNote,
    onSuccess: (newNote: Note) => {
      // Invalidate and refetch notes query
      queryClient.invalidateQueries({
        queryKey: ['notes', newNote.entity_type, newNote.entity_id],
      });
    },
  });
};

export const useUpdateNote = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: updateNote,
    onSuccess: (updatedNote: Note) => {
      // Invalidate and refetch notes query
      queryClient.invalidateQueries({
        queryKey: ['notes', updatedNote.entity_type, updatedNote.entity_id],
      });
    },
  });
};
