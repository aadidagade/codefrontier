import { AppSettingsPayload, RegisteredPasskey } from '../types/settings';

const STORAGE_KEY = 'kh_platform_settings_v1';

export const defaultSettings: AppSettingsPayload = {
  profile: {
    name: 'Elena Rostova',
    email: 'elena.rostova@techfrontier.io',
    roleTitle: 'Staff Platform Architect & Lead',
    department: 'Distributed Systems',
    avatarUrl: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80',
    bio: 'Oversees distributed service resilience, multi-PSP payment gateways, and knowledge handover workflows.',
    timezone: 'UTC+00:00 (London, Dublin, Lisbon)',
    githubHandle: 'elena-rostova-dev',
  },
  account: {
    language: 'English (United States)',
    dateFormat: 'YYYY-MM-DD',
    timeFormat: '24h',
    defaultProjectView: 'grid',
    autoSaveDrafts: true,
  },
  theme: {
    mode: 'dark',
    accentColor: 'violet',
    density: 'comfortable',
  },
  notifications: {
    emailDigestFrequency: 'daily',
    inAppNewHandoverReceived: true,
    inAppReviewRequested: true,
    inAppHandoverApproved: true,
    inAppChangesRequested: true,
    inAppDocUploaded: true,
    inAppConflictDetected: true,
    inAppIncomingAcknowledged: true,
    browserPushNotifications: true,
  },
  workspace: {
    workspaceName: 'TechFrontier · Core Platform Engineering',
    workspaceSlug: 'techfrontier-core',
    apiBaseUrl: 'http://localhost:8000/api/v1',
    mockMode: true,
    aiModel: 'gemini-2.5-flash',
    documentRetentionDays: 90,
  },
  security: {
    twoFactorAuth: true,
    passkeysEnabled: true,
    registeredPasskeys: [
      {
        id: 'pk-macbook',
        name: 'MacBook Pro Touch ID (FIDO2 L3)',
        createdDate: '2026-09-14',
        lastUsed: 'Today at 08:34 UTC',
      },
      {
        id: 'pk-yubikey',
        name: 'YubiKey 5Ci NFC Hardware Token',
        createdDate: '2026-10-02',
        lastUsed: 'Yesterday at 17:10 UTC',
      },
    ],
    activeSessions: [
      {
        id: 'sess-curr',
        device: 'macOS Sequoia 15.1 · Chrome 130',
        browser: 'Google Chrome',
        ip: '198.51.100.42',
        location: 'London, United Kingdom',
        lastActive: 'Active now',
        isCurrent: true,
      },
      {
        id: 'sess-mobile',
        device: 'iPhone 16 Pro · Mobile Safari',
        browser: 'Safari',
        ip: '198.51.100.45',
        location: 'London, United Kingdom',
        lastActive: '2 hours ago',
        isCurrent: false,
      },
      {
        id: 'sess-linux',
        device: 'Ubuntu 24.04 LTS · Firefox Dev Edition',
        browser: 'Firefox',
        ip: '192.0.2.78',
        location: 'Frankfurt, Germany (VPN)',
        lastActive: '3 days ago',
        isCurrent: false,
      },
    ],
    auditLogging: true,
  },
};

class SettingsService {
  private load(): AppSettingsPayload {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(defaultSettings));
        return { ...defaultSettings };
      }
      return JSON.parse(raw);
    } catch {
      return { ...defaultSettings };
    }
  }

  getSettings(): AppSettingsPayload {
    return this.load();
  }

  saveSettings(settings: AppSettingsPayload): void {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
    } catch (err) {
      console.warn('Failed to save settings:', err);
    }
  }

  resetToDefaults(): AppSettingsPayload {
    this.saveSettings(defaultSettings);
    return { ...defaultSettings };
  }

  revokeSession(sessionId: string): AppSettingsPayload {
    const current = this.load();
    current.security.activeSessions = current.security.activeSessions.filter((s) => s.id !== sessionId || s.isCurrent);
    this.saveSettings(current);
    return current;
  }

  revokeAllOtherSessions(): AppSettingsPayload {
    const current = this.load();
    current.security.activeSessions = current.security.activeSessions.filter((s) => s.isCurrent);
    this.saveSettings(current);
    return current;
  }

  registerPasskey(name: string): RegisteredPasskey {
    const current = this.load();
    const newPasskey: RegisteredPasskey = {
      id: `pk-${Date.now()}`,
      name: name.trim() || 'FIDO2 Security Key',
      createdDate: new Date().toISOString().split('T')[0],
      lastUsed: 'Just registered',
    };
    current.security.registeredPasskeys.push(newPasskey);
    this.saveSettings(current);
    return newPasskey;
  }

  removePasskey(passkeyId: string): AppSettingsPayload {
    const current = this.load();
    current.security.registeredPasskeys = current.security.registeredPasskeys.filter((p) => p.id !== passkeyId);
    this.saveSettings(current);
    return current;
  }
}

export const settingsService = new SettingsService();
