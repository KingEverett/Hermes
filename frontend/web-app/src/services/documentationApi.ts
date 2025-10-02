import { SourceType } from '../components/documentation/SourceTypeBadge';

export interface DocumentationSection {
  id: string;
  entity_type: 'host' | 'service' | 'vulnerability' | 'project';
  entity_id: string;
  content: string;
  source_type: SourceType;
  created_at: string;
  updated_at: string;
  version: number;
  author?: string;
}

export interface DocumentationVersion {
  id: string;
  documentation_id: string;
  content: string;
  version: number;
  created_at: string;
  author?: string;
}

export interface Template {
  id: string;
  name: string;
  description: string;
  category: string;
  content: string;
  is_system: boolean;
  created_at: string;
  updated_at: string;
}

export interface CreateDocumentationRequest {
  entity_type: string;
  entity_id: string;
  content: string;
  source_type: SourceType;
}

export interface UpdateDocumentationRequest {
  content: string;
  source_type?: SourceType;
}

export interface AddNoteRequest {
  content: string;
}

export interface CreateTemplateRequest {
  name: string;
  description: string;
  category: string;
  content: string;
}

class DocumentationApi {
  private baseUrl = '/api/v1';

  private async fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  // Documentation CRUD operations
  async getDocumentation(
    entityType: string,
    entityId: string
  ): Promise<DocumentationSection> {
    return this.fetchJson<DocumentationSection>(
      `${this.baseUrl}/documentation/${entityType}/${entityId}`
    );
  }

  async createDocumentation(
    data: CreateDocumentationRequest
  ): Promise<DocumentationSection> {
    return this.fetchJson<DocumentationSection>(`${this.baseUrl}/documentation`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateDocumentation(
    entityType: string,
    entityId: string,
    data: UpdateDocumentationRequest
  ): Promise<DocumentationSection> {
    return this.fetchJson<DocumentationSection>(
      `${this.baseUrl}/documentation/${entityType}/${entityId}`,
      {
        method: 'PUT',
        body: JSON.stringify(data),
      }
    );
  }

  async addNote(
    entityType: string,
    entityId: string,
    data: AddNoteRequest
  ): Promise<DocumentationSection> {
    return this.fetchJson<DocumentationSection>(
      `${this.baseUrl}/documentation/${entityType}/${entityId}/notes`,
      {
        method: 'POST',
        body: JSON.stringify(data),
      }
    );
  }

  // Version control operations
  async getVersionHistory(docId: string): Promise<DocumentationVersion[]> {
    return this.fetchJson<DocumentationVersion[]>(
      `${this.baseUrl}/documentation/sections/${docId}/versions`
    );
  }

  async rollbackToVersion(
    docId: string,
    versionId: string
  ): Promise<DocumentationSection> {
    return this.fetchJson<DocumentationSection>(
      `${this.baseUrl}/documentation/sections/${docId}/rollback/${versionId}`,
      {
        method: 'POST',
      }
    );
  }

  // Template operations
  async getTemplates(category?: string): Promise<Template[]> {
    const url = category
      ? `${this.baseUrl}/templates?category=${encodeURIComponent(category)}`
      : `${this.baseUrl}/templates`;
    return this.fetchJson<Template[]>(url);
  }

  async getTemplate(id: string): Promise<Template> {
    return this.fetchJson<Template>(`${this.baseUrl}/templates/${id}`);
  }

  async createTemplate(data: CreateTemplateRequest): Promise<Template> {
    return this.fetchJson<Template>(`${this.baseUrl}/templates`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateTemplate(id: string, data: Partial<CreateTemplateRequest>): Promise<Template> {
    return this.fetchJson<Template>(`${this.baseUrl}/templates/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteTemplate(id: string): Promise<void> {
    await this.fetchJson<void>(`${this.baseUrl}/templates/${id}`, {
      method: 'DELETE',
    });
  }
}

export const documentationApi = new DocumentationApi();
export default documentationApi;
