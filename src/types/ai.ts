export interface KnowledgeConflict {
  id: string;
  topic: string;
  severity: 'high' | 'medium' | 'low';
  description: string;
  sourceA: { title: string; excerpt: string; date: string; author: string };
  sourceB: { title: string; excerpt: string; date: string; author: string };
  suggestedResolution: string;
  resolved: boolean;
}

export interface KnowledgeGap {
  id: string;
  area: string;
  importance: 'critical' | 'high' | 'medium';
  missingInformation: string;
  recommendedSubjectExpert: string;
  status: 'open' | 'investigating' | 'resolved';
}

export interface AiInsightSummary {
  projectId: string;
  healthScore: number;
  criticalGapsCount: number;
  conflictsCount: number;
  evidenceBackedRatio: number;
  executiveSummary: string;
}
