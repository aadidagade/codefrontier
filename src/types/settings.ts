export interface ProfileSettings {
  name: string;
  email: string;
  roleTitle: string;
  department: string;
  avatarUrl: string;
  bio: string;
  timezone: string;
  githubHandle: string;
}

export interface AccountPreferences {
  language: string;
  dateFormat: string;
  timeFormat: '12h' | '24h';
  defaultProjectView: 'grid' | 'table';
  autoSaveDrafts: boolean;
}

export interface ThemeSettings {
  mode: 'dark' | 'light' | 'system';
  accentColor: 'violet' | 'indigo' | 'cyan' | 'emerald';
  density: 'compact' | 'comfortable';
}

export interface NotificationPreferences {
  emailDigestFrequency: 'instant' | 'daily' | 'weekly' | 'off';
  inAppNewHandoverReceived: boolean;
  inAppReviewRequested: boolean;
  inAppHandoverApproved: boolean;
  inAppChangesRequested: boolean;
  inAppDocUploaded: boolean;
  inAppConflictDetected: boolean;
  inAppIncomingAcknowledged: boolean;
  browserPushNotifications: boolean;
}

export interface WorkspaceSettings {
  workspaceName: string;
  workspaceSlug: string;
  apiBaseUrl: string;
  mockMode: boolean;
  aiModel: 'gemini-2.5-flash' | 'claude-3-5-sonnet' | 'gpt-4o';
  documentRetentionDays: number;
}

export interface RegisteredPasskey {
  id: string;
  name: string;
  createdDate: string;
  lastUsed: string;
}

export interface ActiveSession {
  id: string;
  device: string;
  browser: string;
  ip: string;
  location: string;
  lastActive: string;
  isCurrent: boolean;
}

export interface SecuritySettings {
  twoFactorAuth: boolean;
  passkeysEnabled: boolean;
  registeredPasskeys: RegisteredPasskey[];
  activeSessions: ActiveSession[];
  auditLogging: boolean;
}

export interface AppSettingsPayload {
  profile: ProfileSettings;
  account: AccountPreferences;
  theme: ThemeSettings;
  notifications: NotificationPreferences;
  workspace: WorkspaceSettings;
  security: SecuritySettings;
}
