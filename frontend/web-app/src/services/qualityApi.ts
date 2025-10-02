export interface QualityMetrics {
  total_findings: number;
  validated_findings: number;
  false_positives: number;
  accuracy_rate: number;
  false_positive_rate: number;
  confidence_distribution: {
    high: number;
    medium: number;
    low: number;
  };
  validation_queue_size: number;
  calculated_at: string;
}

export interface ValidationQueueItem {
  id: string;
  finding_type: string;
  finding_id: string;
  priority: string;
  status: string;
  assigned_to: string | null;
  created_at: string;
  reviewed_at: string | null;
  review_notes: string | null;
}

export interface ValidationQueueResponse {
  items: ValidationQueueItem[];
  total: number;
}

export interface ValidationDecisionRequest {
  decision: 'approve' | 'reject' | 'override';
  justification: string;
  notes?: string;
  validated_by: string;
}

export interface ValidationDecisionResponse {
  success: boolean;
  finding_id: string;
  decision: string;
  validation_status: string;
  confidence_score: number | null;
  validated_at: string | null;
  validated_by: string;
  audit_created: boolean;
}

export interface ValidationFeedbackRequest {
  finding_id: string;
  feedback_type: 'false_positive' | 'false_negative' | 'correct';
  comment: string;
  user_id?: string;
}

export interface TrendDataPoint {
  metric_type: string;
  value: number;
  calculated_at: string;
  metadata: Record<string, any>;
}

export interface TrendDataResponse {
  data_points: TrendDataPoint[];
  start_date: string;
  end_date: string;
}

export interface AccuracyIssue {
  type: string;
  severity: string;
  description: string;
  recommendation: string;
}

export interface CoverageMetrics {
  total_services: number;
  services_researched: number;
  coverage_rate: number;
  services_pending: number;
}

class QualityApi {
  private baseUrl = '/api/v1';

  async getQualityMetrics(projectId: string): Promise<QualityMetrics> {
    const response = await fetch(`${this.baseUrl}/quality/metrics/${projectId}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch quality metrics: ${response.statusText}`);
    }
    return response.json();
  }

  async getQualityTrends(
    projectId: string,
    params?: {
      start_date?: string;
      end_date?: string;
      metric_type?: string;
      days?: number;
    }
  ): Promise<TrendDataResponse> {
    const queryParams = new URLSearchParams();
    if (params?.start_date) queryParams.append('start_date', params.start_date);
    if (params?.end_date) queryParams.append('end_date', params.end_date);
    if (params?.metric_type) queryParams.append('metric_type', params.metric_type);
    if (params?.days) queryParams.append('days', params.days.toString());

    const url = `${this.baseUrl}/quality/trends/${projectId}${
      queryParams.toString() ? '?' + queryParams.toString() : ''
    }`;

    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Failed to fetch quality trends: ${response.statusText}`);
    }
    return response.json();
  }

  async getValidationQueue(params?: {
    priority?: string;
    status?: string;
    finding_type?: string;
    limit?: number;
    offset?: number;
  }): Promise<ValidationQueueResponse> {
    const queryParams = new URLSearchParams();
    if (params?.priority) queryParams.append('priority', params.priority);
    if (params?.status) queryParams.append('status', params.status);
    if (params?.finding_type) queryParams.append('finding_type', params.finding_type);
    if (params?.limit) queryParams.append('limit', params.limit.toString());
    if (params?.offset) queryParams.append('offset', params.offset.toString());

    const url = `${this.baseUrl}/validation/queue${
      queryParams.toString() ? '?' + queryParams.toString() : ''
    }`;

    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Failed to fetch validation queue: ${response.statusText}`);
    }
    return response.json();
  }

  async submitValidationReview(
    findingId: string,
    request: ValidationDecisionRequest
  ): Promise<ValidationDecisionResponse> {
    const response = await fetch(`${this.baseUrl}/validation/${findingId}/review`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to submit validation review');
    }
    return response.json();
  }

  async getValidationHistory(findingId: string): Promise<any> {
    const response = await fetch(`${this.baseUrl}/validation/history/${findingId}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch validation history: ${response.statusText}`);
    }
    return response.json();
  }

  async submitFeedback(request: ValidationFeedbackRequest): Promise<any> {
    const response = await fetch(`${this.baseUrl}/quality/feedback`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to submit feedback');
    }
    return response.json();
  }

  async getAccuracyIssues(projectId: string): Promise<AccuracyIssue[]> {
    const response = await fetch(`${this.baseUrl}/quality/issues/${projectId}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch accuracy issues: ${response.statusText}`);
    }
    const data = await response.json();
    return data.issues;
  }

  async getCoverageMetrics(projectId: string): Promise<CoverageMetrics> {
    const response = await fetch(`${this.baseUrl}/quality/coverage/${projectId}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch coverage metrics: ${response.statusText}`);
    }
    return response.json();
  }

  async refreshVulnerability(vulnId: string): Promise<any> {
    const response = await fetch(`${this.baseUrl}/vulnerabilities/${vulnId}/refresh`, {
      method: 'POST',
    });

    if (!response.ok) {
      throw new Error(`Failed to refresh vulnerability: ${response.statusText}`);
    }
    return response.json();
  }
}

export const qualityApi = new QualityApi();
