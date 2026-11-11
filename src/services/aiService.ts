import { apiClient, ApiResponse } from './apiClient';
import { KnowledgeConflict, KnowledgeGap, AiInsightSummary } from '../types/ai';
import { mockConflicts, mockGaps } from '../data/mockData';

class AiService {
  async getConflicts(): Promise<ApiResponse<KnowledgeConflict[]>> {
    return apiClient.executeMock(() => [...mockConflicts]);
  }

  async getGaps(): Promise<ApiResponse<KnowledgeGap[]>> {
    return apiClient.executeMock(() => [...mockGaps]);
  }

  async getProjectSummary(projectId: string): Promise<ApiResponse<AiInsightSummary>> {
    return apiClient.executeMock(() => ({
      projectId,
      healthScore: 89,
      criticalGapsCount: 2,
      conflictsCount: 1,
      evidenceBackedRatio: 0.94,
      executiveSummary: 'Knowledge continuity is high across payment routing and cryptographic secrets. 1 high-severity failover discrepancy requires architect resolution before sign-off.',
    }));
  }
}

export const aiService = new AiService();
