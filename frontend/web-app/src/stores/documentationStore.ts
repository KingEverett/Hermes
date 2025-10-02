import { create } from 'zustand';
import {
  DocumentationSection,
  DocumentationVersion,
} from '../services/documentationApi';

interface SelectedEntity {
  type: string;
  id: string;
}

interface DocumentationStore {
  // State
  currentDoc: DocumentationSection | null;
  versions: DocumentationVersion[];
  isEditing: boolean;
  selectedEntity: SelectedEntity | null;
  unsavedChanges: boolean;

  // Actions
  setCurrentDoc: (doc: DocumentationSection | null) => void;
  setVersions: (versions: DocumentationVersion[]) => void;
  setEditing: (isEditing: boolean) => void;
  toggleEditMode: () => void;
  setSelectedEntity: (entity: SelectedEntity | null) => void;
  setUnsavedChanges: (hasChanges: boolean) => void;
  reset: () => void;
}

const initialState = {
  currentDoc: null,
  versions: [],
  isEditing: false,
  selectedEntity: null,
  unsavedChanges: false,
};

export const useDocumentationStore = create<DocumentationStore>((set) => ({
  ...initialState,

  setCurrentDoc: (doc: DocumentationSection | null) => set({ currentDoc: doc }),

  setVersions: (versions: DocumentationVersion[]) => set({ versions }),

  setEditing: (isEditing: boolean) => set({ isEditing }),

  toggleEditMode: () => set((state) => ({ isEditing: !state.isEditing })),

  setSelectedEntity: (entity: SelectedEntity | null) =>
    set({
      selectedEntity: entity,
      isEditing: false,
      unsavedChanges: false,
    }),

  setUnsavedChanges: (hasChanges: boolean) => set({ unsavedChanges: hasChanges }),

  reset: () => set(initialState),
}));

export default useDocumentationStore;
