export type ThemeMode = 'dark' | 'light';

export interface BreadcrumbItem {
  label: string;
  href?: string;
  current?: boolean;
}

export type StatusVariant = 'draft' | 'in_progress' | 'under_review' | 'approved' | 'rejected' | 'at_risk' | 'archived';

export interface User {
  id: string;
  name: string;
  email: string;
  role: 'admin' | 'lead_engineer' | 'engineer' | 'reviewer' | 'product_manager';
  avatarUrl?: string;
  department?: string;
  lastActive?: string;
}

export interface PaginationParams {
  page: number;
  limit: number;
  total?: number;
}
