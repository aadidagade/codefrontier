import React, { useState, useEffect } from 'react';
import {
  User,
  Sliders,
  Moon,
  Sun,
  Bell,
  Building,
  Shield,
  Key,
  Laptop,
  Smartphone,
  Globe,
  Database,
  CheckCircle2,
  AlertTriangle,
  RotateCcw,
  Save,
  Trash2,
  Plus,
  Sparkles,
  ExternalLink,
  ShieldCheck,
  Check,
} from 'lucide-react';
import { Card, CardTitle, CardDescription, CardContent } from '../../components/common/Card';
import { Button } from '../../components/common/Button';
import { Badge } from '../../components/common/Badge';
import { Modal } from '../../components/common/Modal';
import { ConfirmDialog } from '../../components/common/ConfirmDialog';
import { useTheme } from '../../hooks/useTheme';
import { useToast } from '../../hooks/useToast';
import { useRole } from '../../context/RoleContext';
import { settingsService } from '../../services/settingsService';
import { AppSettingsPayload, RegisteredPasskey } from '../../types/settings';

type SettingsTab = 'profile' | 'account' | 'theme' | 'notifications' | 'workspace' | 'security';

export const SettingsPage: React.FC = () => {
  const { theme, toggleTheme, setTheme } = useTheme();
  const { currentRole, roleLabel } = useRole();
  const { success, info, error } = useToast();

  const [activeTab, setActiveTab] = useState<SettingsTab>('profile');
  const [settings, setSettings] = useState<AppSettingsPayload>(() => settingsService.getSettings());
  const [isRegisterPasskeyOpen, setIsRegisterPasskeyOpen] = useState(false);
  const [isConfirmResetOpen, setIsConfirmResetOpen] = useState(false);
  const [newPasskeyName, setNewPasskeyName] = useState('');
  const [isVerifyingApi, setIsVerifyingApi] = useState(false);

  useEffect(() => {
    setSettings(settingsService.getSettings());
  }, []);

  const handleSaveAll = () => {
    settingsService.saveSettings(settings);
    // Also sync theme
    if (settings.theme.mode === 'dark' || settings.theme.mode === 'light') {
      setTheme(settings.theme.mode);
    }
    success('Settings Persisted', 'All workspace preferences and security configurations have been updated.');
  };

  const handleConfirmReset = () => {
    const reset = settingsService.resetToDefaults();
    setSettings(reset);
    setTheme('dark');
    setIsConfirmResetOpen(false);
    info('Reset Complete', 'Default platform settings restored.');
  };

  const handleRegisterPasskey = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newPasskeyName.trim()) return;

    const created = settingsService.registerPasskey(newPasskeyName);
    setSettings(settingsService.getSettings());
    setIsRegisterPasskeyOpen(false);
    setNewPasskeyName('');
    success(
      'Passkey Enrolled',
      `Hardware credential "${created.name}" is now active for biometric zero-trust logins.`
    );
  };

  const handleRemovePasskey = (passkeyId: string) => {
    const updated = settingsService.removePasskey(passkeyId);
    setSettings(updated);
    info('Passkey Revoked', 'Hardware credential removed from this account.');
  };

  const handleRevokeSession = (sessionId: string) => {
    const updated = settingsService.revokeSession(sessionId);
    setSettings(updated);
    info('Session Terminated', 'Remote device signed out successfully.');
  };

  const handleRevokeAllOtherSessions = () => {
    const updated = settingsService.revokeAllOtherSessions();
    setSettings(updated);
    success('All Other Sessions Revoked', 'Only your current browser session remains active.');
  };

  const handleVerifyApiHealth = () => {
    setIsVerifyingApi(true);
    setTimeout(() => {
      setIsVerifyingApi(false);
      success(
        'Backend Health 200 OK',
        `Endpoint reachable: ${settings.workspace.apiBaseUrl}/health. Simulated latency: 24ms.`
      );
    }, 800);
  };

  const tabs = [
    { id: 'profile', label: 'Personal Profile', icon: <User className="h-4 w-4" /> },
    { id: 'account', label: 'Account Preferences', icon: <Sliders className="h-4 w-4" /> },
    { id: 'theme', label: 'Theme & Appearance', icon: <Moon className="h-4 w-4" /> },
    { id: 'notifications', label: 'Notifications', icon: <Bell className="h-4 w-4" /> },
    { id: 'workspace', label: 'Team & Workspace', icon: <Building className="h-4 w-4" /> },
    { id: 'security', label: 'Security & Passkeys', icon: <Shield className="h-4 w-4" /> },
  ];

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-16">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Platform Settings</h1>
          <p className="text-xs text-slate-400 mt-1">
            Manage your personal profile, role preferences, theme, notification channels, and workspace connectors
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <Button
            variant="ghost"
            size="sm"
            leftIcon={<RotateCcw className="h-3.5 w-3.5" />}
            onClick={() => setIsConfirmResetOpen(true)}
          >
            Reset
          </Button>
          <Button
            variant="primary"
            size="sm"
            leftIcon={<Save className="h-3.5 w-3.5" />}
            onClick={handleSaveAll}
          >
            Save Changes
          </Button>
        </div>
      </div>

      {/* Tabs Layout */}
      <div className="flex flex-col md:flex-row gap-6">
        {/* Left Vertical Nav */}
        <div className="w-full md:w-64 shrink-0 space-y-1">
          {tabs.map((tab) => {
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as SettingsTab)}
                className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-xs font-medium text-left transition-all ${
                  isActive
                    ? 'bg-brand-500/10 text-brand-400 border border-brand-500/30'
                    : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
                }`}
              >
                {tab.icon}
                <span>{tab.label}</span>
              </button>
            );
          })}

          <div className="mt-6 p-3 rounded-lg bg-slate-900/40 border border-slate-800/80 text-[11px] text-slate-400 space-y-1.5">
            <div className="flex items-center justify-between">
              <span>Active Role:</span>
              <span className="font-semibold text-white">{roleLabel}</span>
            </div>
            <div className="flex items-center justify-between">
              <span>Platform Mode:</span>
              <span className="text-emerald-400 font-mono">Mock Connected</span>
            </div>
          </div>
        </div>

        {/* Right Tab Content */}
        <div className="flex-1 min-w-0 space-y-6">
          {/* TAB 1: PERSONAL PROFILE */}
          {activeTab === 'profile' && (
            <Card className="bg-[#0F172A] border-slate-800 p-6 space-y-6">
              <div>
                <CardTitle className="text-base text-white">Personal Profile</CardTitle>
                <CardDescription>
                  Your engineering identity, title, and public handover attribution
                </CardDescription>
              </div>

              {/* Avatar & Photo */}
              <div className="flex items-center gap-4 pb-6 border-b border-slate-800">
                <img
                  src={settings.profile.avatarUrl}
                  alt={settings.profile.name}
                  className="h-16 w-16 rounded-full border-2 border-slate-700 object-cover"
                />
                <div>
                  <div className="text-xs font-semibold text-white">{settings.profile.name}</div>
                  <div className="text-xs text-slate-400 font-mono mt-0.5">{settings.profile.email}</div>
                  <div className="mt-2 flex items-center gap-2">
                    <Badge variant="accent" size="sm">
                      {roleLabel}
                    </Badge>
                    <span className="text-[11px] text-slate-500">{settings.profile.department}</span>
                  </div>
                </div>
              </div>

              {/* Form Fields */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Full Name</label>
                  <input
                    type="text"
                    value={settings.profile.name}
                    onChange={(e) =>
                      setSettings({
                        ...settings,
                        profile: { ...settings.profile, name: e.target.value },
                      })
                    }
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-xs text-white focus:outline-none focus:border-brand-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Work Email</label>
                  <input
                    type="email"
                    value={settings.profile.email}
                    onChange={(e) =>
                      setSettings({
                        ...settings,
                        profile: { ...settings.profile, email: e.target.value },
                      })
                    }
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-xs text-white focus:outline-none focus:border-brand-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Job Title</label>
                  <input
                    type="text"
                    value={settings.profile.roleTitle}
                    onChange={(e) =>
                      setSettings({
                        ...settings,
                        profile: { ...settings.profile, roleTitle: e.target.value },
                      })
                    }
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-xs text-white focus:outline-none focus:border-brand-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Department</label>
                  <input
                    type="text"
                    value={settings.profile.department}
                    onChange={(e) =>
                      setSettings({
                        ...settings,
                        profile: { ...settings.profile, department: e.target.value },
                      })
                    }
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-xs text-white focus:outline-none focus:border-brand-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Primary Timezone</label>
                  <select
                    value={settings.profile.timezone}
                    onChange={(e) =>
                      setSettings({
                        ...settings,
                        profile: { ...settings.profile, timezone: e.target.value },
                      })
                    }
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-xs text-white focus:outline-none focus:border-brand-500"
                  >
                    <option value="UTC+00:00 (London, Dublin, Lisbon)">UTC+00:00 (London, Dublin, Lisbon)</option>
                    <option value="UTC-05:00 (Eastern Time - US & Canada)">UTC-05:00 (Eastern Time - US & Canada)</option>
                    <option value="UTC-08:00 (Pacific Time - US & Canada)">UTC-08:00 (Pacific Time - US & Canada)</option>
                    <option value="UTC+01:00 (Berlin, Paris, Amsterdam)">UTC+01:00 (Berlin, Paris, Amsterdam)</option>
                    <option value="UTC+05:30 (India Standard Time)">UTC+05:30 (India Standard Time)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">GitHub Username</label>
                  <input
                    type="text"
                    value={settings.profile.githubHandle}
                    onChange={(e) =>
                      setSettings({
                        ...settings,
                        profile: { ...settings.profile, githubHandle: e.target.value },
                      })
                    }
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-xs text-white focus:outline-none focus:border-brand-500 font-mono"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Bio & Knowledge Scope</label>
                <textarea
                  rows={3}
                  value={settings.profile.bio}
                  onChange={(e) =>
                    setSettings({
                      ...settings,
                      profile: { ...settings.profile, bio: e.target.value },
                    })
                  }
                  className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-xs text-white focus:outline-none focus:border-brand-500 resize-none"
                />
              </div>
            </Card>
          )}

          {/* TAB 2: ACCOUNT PREFERENCES */}
          {activeTab === 'account' && (
            <Card className="bg-[#0F172A] border-slate-800 p-6 space-y-6">
              <div>
                <CardTitle className="text-base text-white">Account Preferences</CardTitle>
                <CardDescription>
                  Regional formatting, layout density, and draft auto-persistence
                </CardDescription>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Interface Language</label>
                  <select
                    value={settings.account.language}
                    onChange={(e) =>
                      setSettings({
                        ...settings,
                        account: { ...settings.account, language: e.target.value },
                      })
                    }
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-xs text-white"
                  >
                    <option value="English (United States)">English (United States)</option>
                    <option value="English (United Kingdom)">English (United Kingdom)</option>
                    <option value="German (Deutsch)">German (Deutsch)</option>
                    <option value="Japanese (日本語)">Japanese (日本語)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Date Format</label>
                  <select
                    value={settings.account.dateFormat}
                    onChange={(e) =>
                      setSettings({
                        ...settings,
                        account: { ...settings.account, dateFormat: e.target.value },
                      })
                    }
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-xs text-white font-mono"
                  >
                    <option value="YYYY-MM-DD">YYYY-MM-DD (ISO standard)</option>
                    <option value="DD/MM/YYYY">DD/MM/YYYY</option>
                    <option value="MM/DD/YYYY">MM/DD/YYYY</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Time Display</label>
                  <div className="flex items-center gap-4 mt-2 text-xs text-slate-300">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        name="timeFormat"
                        value="24h"
                        checked={settings.account.timeFormat === '24h'}
                        onChange={() =>
                          setSettings({
                            ...settings,
                            account: { ...settings.account, timeFormat: '24h' },
                          })
                        }
                        className="text-brand-500"
                      />
                      <span>24-Hour (14:30)</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        name="timeFormat"
                        value="12h"
                        checked={settings.account.timeFormat === '12h'}
                        onChange={() =>
                          setSettings({
                            ...settings,
                            account: { ...settings.account, timeFormat: '12h' },
                          })
                        }
                        className="text-brand-500"
                      />
                      <span>12-Hour (2:30 PM)</span>
                    </label>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Default Projects View</label>
                  <div className="flex items-center gap-4 mt-2 text-xs text-slate-300">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        name="defaultProjectView"
                        value="grid"
                        checked={settings.account.defaultProjectView === 'grid'}
                        onChange={() =>
                          setSettings({
                            ...settings,
                            account: { ...settings.account, defaultProjectView: 'grid' },
                          })
                        }
                        className="text-brand-500"
                      />
                      <span>Grid View (Cards)</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        name="defaultProjectView"
                        value="table"
                        checked={settings.account.defaultProjectView === 'table'}
                        onChange={() =>
                          setSettings({
                            ...settings,
                            account: { ...settings.account, defaultProjectView: 'table' },
                          })
                        }
                        className="text-brand-500"
                      />
                      <span>List / Table View</span>
                    </label>
                  </div>
                </div>
              </div>

              {/* Auto save checkbox */}
              <div className="pt-4 border-t border-slate-800 flex items-center justify-between">
                <div>
                  <div className="text-xs font-semibold text-white">Auto-Save Handover Drafts</div>
                  <div className="text-[11px] text-slate-400">
                    Automatically persist in-flight section reviews and claim verifications every 15 seconds
                  </div>
                </div>
                <input
                  type="checkbox"
                  checked={settings.account.autoSaveDrafts}
                  onChange={(e) =>
                    setSettings({
                      ...settings,
                      account: { ...settings.account, autoSaveDrafts: e.target.checked },
                    })
                  }
                  className="rounded border-slate-700 text-brand-500 focus:ring-0 bg-slate-900 h-4 w-4"
                />
              </div>
            </Card>
          )}

          {/* TAB 3: THEME & APPEARANCE */}
          {activeTab === 'theme' && (
            <Card className="bg-[#0F172A] border-slate-800 p-6 space-y-6">
              <div>
                <CardTitle className="text-base text-white">Theme & Appearance</CardTitle>
                <CardDescription>
                  Premium dark-first styling inspired by Linear and Notion with customizable accent colors
                </CardDescription>
              </div>

              {/* Theme Mode Selection */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-2">Base Theme</label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div
                    onClick={() => {
                      setTheme('dark');
                      setSettings({
                        ...settings,
                        theme: { ...settings.theme, mode: 'dark' },
                      });
                    }}
                    className={`p-4 rounded-xl border cursor-pointer transition-all ${
                      theme === 'dark'
                        ? 'bg-[#080C14] border-violet-500/80 ring-2 ring-violet-500/30'
                        : 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Moon className="h-4 w-4 text-violet-400" />
                        <span className="text-xs font-bold text-white">Dark Theme (Default)</span>
                      </div>
                      {theme === 'dark' && <CheckCircle2 className="h-4 w-4 text-violet-400" />}
                    </div>
                    <p className="text-[11px] text-slate-400 mt-2">
                      Deep slate (#080C14) canvas, high-contrast typography, and glowing violet indicators.
                    </p>
                  </div>

                  <div
                    onClick={() => {
                      setTheme('light');
                      setSettings({
                        ...settings,
                        theme: { ...settings.theme, mode: 'light' },
                      });
                    }}
                    className={`p-4 rounded-xl border cursor-pointer transition-all ${
                      theme === 'light'
                        ? 'bg-slate-100 border-violet-500 ring-2 ring-violet-500/30 text-slate-900'
                        : 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Sun className="h-4 w-4 text-amber-400" />
                        <span className="text-xs font-bold text-slate-200">Light Theme</span>
                      </div>
                      {theme === 'light' && <CheckCircle2 className="h-4 w-4 text-violet-400" />}
                    </div>
                    <p className="text-[11px] text-slate-400 mt-2">
                      Clean off-white canvas with sharp slate borders and neutral contrasts.
                    </p>
                  </div>
                </div>
              </div>

              {/* Accent Palette */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-2">Accent Hue</label>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                  {[
                    { id: 'violet', label: 'Electric Violet', color: 'bg-violet-500' },
                    { id: 'indigo', label: 'Deep Indigo', color: 'bg-indigo-500' },
                    { id: 'cyan', label: 'Hyper Cyan', color: 'bg-cyan-500' },
                    { id: 'emerald', label: 'Cyber Emerald', color: 'bg-emerald-500' },
                  ].map((acc) => (
                    <button
                      key={acc.id}
                      onClick={() =>
                        setSettings({
                          ...settings,
                          theme: { ...settings.theme, accentColor: acc.id as any },
                        })
                      }
                      className={`p-3 rounded-lg border text-left flex items-center justify-between transition-all ${
                        settings.theme.accentColor === acc.id
                          ? 'border-brand-500 bg-brand-500/10'
                          : 'border-slate-800 bg-slate-900 hover:border-slate-700'
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <span className={`h-3 w-3 rounded-full ${acc.color}`} />
                        <span className="text-xs text-white font-medium">{acc.label}</span>
                      </div>
                      {settings.theme.accentColor === acc.id && (
                        <Check className="h-3.5 w-3.5 text-brand-400" />
                      )}
                    </button>
                  ))}
                </div>
              </div>

              {/* Density */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Layout Density</label>
                <div className="flex items-center gap-4 text-xs text-slate-300 mt-2">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="radio"
                      name="density"
                      value="comfortable"
                      checked={settings.theme.density === 'comfortable'}
                      onChange={() =>
                        setSettings({
                          ...settings,
                          theme: { ...settings.theme, density: 'comfortable' },
                        })
                      }
                      className="text-brand-500"
                    />
                    <span>Comfortable (Standard spacing)</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="radio"
                      name="density"
                      value="compact"
                      checked={settings.theme.density === 'compact'}
                      onChange={() =>
                        setSettings({
                          ...settings,
                          theme: { ...settings.theme, density: 'compact' },
                        })
                      }
                      className="text-brand-500"
                    />
                    <span>Compact (High data density)</span>
                  </label>
                </div>
              </div>
            </Card>
          )}

          {/* TAB 4: NOTIFICATION PREFERENCES */}
          {activeTab === 'notifications' && (
            <Card className="bg-[#0F172A] border-slate-800 p-6 space-y-6">
              <div>
                <CardTitle className="text-base text-white">Notification Preferences</CardTitle>
                <CardDescription>
                  Configure granular in-app alerts and email summaries for each handover lifecycle event
                </CardDescription>
              </div>

              {/* Email Digest Frequency */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Email Digest Frequency</label>
                <select
                  value={settings.notifications.emailDigestFrequency}
                  onChange={(e) =>
                    setSettings({
                      ...settings,
                      notifications: {
                        ...settings.notifications,
                        emailDigestFrequency: e.target.value as any,
                      },
                    })
                  }
                  className="w-full sm:w-72 px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-xs text-white"
                >
                  <option value="instant">Instant Realtime Email</option>
                  <option value="daily">Daily Morning Digest (Recommended)</option>
                  <option value="weekly">Weekly Recap</option>
                  <option value="off">Disabled</option>
                </select>
              </div>

              {/* In-app Event Toggles for all 7 Prompt Items */}
              <div className="space-y-3 pt-3 border-t border-slate-800">
                <div className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                  In-App Notification Events
                </div>

                {[
                  {
                    key: 'inAppNewHandoverReceived',
                    title: 'New Handover Received',
                    desc: 'Notify when a new handover package is assigned to you as incoming successor.',
                  },
                  {
                    key: 'inAppReviewRequested',
                    title: 'Review Requested',
                    desc: 'Alert when an outgoing author submits a project brief for Project Lead audit.',
                  },
                  {
                    key: 'inAppHandoverApproved',
                    title: 'Handover Approved',
                    desc: 'Notify when a handover brief receives formal certification and executive lock.',
                  },
                  {
                    key: 'inAppChangesRequested',
                    title: 'Changes Requested',
                    desc: 'Notify when a reviewer flags sections or claims needing additional evidence.',
                  },
                  {
                    key: 'inAppDocUploaded',
                    title: 'New Project Document Uploaded',
                    desc: 'Alert when teammates upload runbooks, ADRs, or schemas for AI indexing.',
                  },
                  {
                    key: 'inAppConflictDetected',
                    title: 'Conflict Detected',
                    desc: 'Urgent alert when contradictory deadlines or configurations are flagged by AI.',
                  },
                  {
                    key: 'inAppIncomingAcknowledged',
                    title: 'Incoming Member Acknowledged',
                    desc: 'Confirm when the successor accepts ownership and begins continuation tasks.',
                  },
                ].map((item) => {
                  const isChecked = (settings.notifications as any)[item.key];
                  return (
                    <div
                      key={item.key}
                      className="p-3 rounded-lg bg-slate-900/60 border border-slate-800/80 flex items-center justify-between gap-4"
                    >
                      <div>
                        <div className="text-xs font-semibold text-white">{item.title}</div>
                        <div className="text-[11px] text-slate-400 mt-0.5">{item.desc}</div>
                      </div>
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={(e) =>
                          setSettings({
                            ...settings,
                            notifications: {
                              ...settings.notifications,
                              [item.key]: e.target.checked,
                            },
                          })
                        }
                        className="rounded border-slate-700 text-brand-500 focus:ring-0 bg-slate-800 h-4 w-4"
                      />
                    </div>
                  );
                })}
              </div>

              {/* Browser Push */}
              <div className="pt-4 border-t border-slate-800 flex items-center justify-between">
                <div>
                  <div className="text-xs font-semibold text-white">Browser Push Notifications</div>
                  <div className="text-[11px] text-slate-400">
                    Receive OS desktop notifications when browser tab is running in background
                  </div>
                </div>
                <input
                  type="checkbox"
                  checked={settings.notifications.browserPushNotifications}
                  onChange={(e) =>
                    setSettings({
                      ...settings,
                      notifications: {
                        ...settings.notifications,
                        browserPushNotifications: e.target.checked,
                      },
                    })
                  }
                  className="rounded border-slate-700 text-brand-500 focus:ring-0 bg-slate-800 h-4 w-4"
                />
              </div>
            </Card>
          )}

          {/* TAB 5: TEAM & WORKSPACE */}
          {activeTab === 'workspace' && (
            <Card className="bg-[#0F172A] border-slate-800 p-6 space-y-6">
              <div>
                <CardTitle className="text-base text-white">Team & Workspace Settings</CardTitle>
                <CardDescription>
                  Configure organization boundaries, backend API connectors, and AI generation parameters
                </CardDescription>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Workspace Name</label>
                  <input
                    type="text"
                    value={settings.workspace.workspaceName}
                    onChange={(e) =>
                      setSettings({
                        ...settings,
                        workspace: { ...settings.workspace, workspaceName: e.target.value },
                      })
                    }
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-xs text-white"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Workspace Slug</label>
                  <input
                    type="text"
                    value={settings.workspace.workspaceSlug}
                    onChange={(e) =>
                      setSettings({
                        ...settings,
                        workspace: { ...settings.workspace, workspaceSlug: e.target.value },
                      })
                    }
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-xs text-white font-mono"
                  />
                </div>
              </div>

              {/* Backend API Connector */}
              <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Database className="h-4 w-4 text-brand-400" />
                    <span className="text-xs font-bold text-white">FastAPI Backend Connector</span>
                  </div>
                  <Badge variant="success" size="sm">
                    Ready to Connect
                  </Badge>
                </div>

                <div>
                  <label className="block text-[11px] font-semibold text-slate-400 mb-1">
                    API Base URL (REST & WebSocket)
                  </label>
                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      value={settings.workspace.apiBaseUrl}
                      onChange={(e) =>
                        setSettings({
                          ...settings,
                          workspace: { ...settings.workspace, apiBaseUrl: e.target.value },
                        })
                      }
                      className="flex-1 px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-brand-300 font-mono"
                    />
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleVerifyApiHealth}
                      disabled={isVerifyingApi}
                    >
                      {isVerifyingApi ? 'Testing...' : 'Verify Endpoint'}
                    </Button>
                  </div>
                </div>

                <div className="flex items-center justify-between pt-2">
                  <div>
                    <div className="text-xs font-semibold text-white">Mock Fallback Mode</div>
                    <div className="text-[11px] text-slate-400">
                      When enabled, the frontend returns immediate synthetic responses for all endpoints
                    </div>
                  </div>
                  <input
                    type="checkbox"
                    checked={settings.workspace.mockMode}
                    onChange={(e) =>
                      setSettings({
                        ...settings,
                        workspace: { ...settings.workspace, mockMode: e.target.checked },
                      })
                    }
                    className="rounded border-slate-700 text-brand-500 focus:ring-0 bg-slate-900 h-4 w-4"
                  />
                </div>
              </div>

              {/* AI Engine & Retention */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Default AI Synthesis Model
                  </label>
                  <select
                    value={settings.workspace.aiModel}
                    onChange={(e) =>
                      setSettings({
                        ...settings,
                        workspace: { ...settings.workspace, aiModel: e.target.value as any },
                      })
                    }
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-xs text-white"
                  >
                    <option value="gemini-2.5-flash">Gemini 2.5 Flash (1M tokens context, fast)</option>
                    <option value="claude-3-5-sonnet">Claude 3.5 Sonnet (Deep reasoning)</option>
                    <option value="gpt-4o">OpenAI GPT-4o (Multimodal)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Document Retention Policy
                  </label>
                  <select
                    value={settings.workspace.documentRetentionDays}
                    onChange={(e) =>
                      setSettings({
                        ...settings,
                        workspace: {
                          ...settings.workspace,
                          documentRetentionDays: parseInt(e.target.value, 10),
                        },
                      })
                    }
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-xs text-white"
                  >
                    <option value={30}>30 Days (Ephemeral)</option>
                    <option value={90}>90 Days (Recommended)</option>
                    <option value={180}>180 Days (Compliance)</option>
                    <option value={365}>365 Days (Annual Audit)</option>
                  </select>
                </div>
              </div>
            </Card>
          )}

          {/* TAB 6: SECURITY & PASSKEYS */}
          {activeTab === 'security' && (
            <Card className="bg-[#0F172A] border-slate-800 p-6 space-y-6">
              <div>
                <CardTitle className="text-base text-white">Security & Passkeys</CardTitle>
                <CardDescription>
                  Hardware passkeys, WebAuthn MFA, active session management, and access audit logging
                </CardDescription>
              </div>

              {/* Passkeys Enrolled Section */}
              <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Key className="h-4 w-4 text-violet-400" />
                    <span className="text-xs font-bold text-white">FIDO2 / WebAuthn Hardware Passkeys</span>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    leftIcon={<Plus className="h-3 w-3" />}
                    onClick={() => {
                      setNewPasskeyName('');
                      setIsRegisterPasskeyOpen(true);
                    }}
                  >
                    Add Passkey
                  </Button>
                </div>

                <p className="text-[11px] text-slate-400">
                  Passwordless authentication with Touch ID, Face ID, or external security keys protects against credential harvesting.
                </p>

                <div className="space-y-2">
                  {settings.security.registeredPasskeys.map((pk) => (
                    <div
                      key={pk.id}
                      className="p-3 rounded-lg bg-slate-950/60 border border-slate-800 flex items-center justify-between"
                    >
                      <div className="flex items-center gap-3">
                        <ShieldCheck className="h-4 w-4 text-emerald-400 shrink-0" />
                        <div>
                          <div className="text-xs font-semibold text-white">{pk.name}</div>
                          <div className="text-[10px] text-slate-500">
                            Created: {pk.createdDate} · Last used: {pk.lastUsed}
                          </div>
                        </div>
                      </div>
                      <button
                        onClick={() => handleRemovePasskey(pk.id)}
                        className="p-1.5 text-slate-500 hover:text-red-400 rounded hover:bg-slate-800"
                        title="Remove Passkey"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>

              {/* Active Sessions */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-xs font-bold text-white">Active Signed-in Sessions</div>
                    <div className="text-[11px] text-slate-400">
                      Devices and locations currently authorized to access your account
                    </div>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleRevokeAllOtherSessions}
                    className="text-red-400 border-red-500/30 hover:bg-red-500/10"
                  >
                    Revoke Other Sessions
                  </Button>
                </div>

                <div className="space-y-2">
                  {settings.security.activeSessions.map((session) => (
                    <div
                      key={session.id}
                      className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 flex items-center justify-between text-xs"
                    >
                      <div className="flex items-center gap-3">
                        {session.device.includes('iPhone') ? (
                          <Smartphone className="h-4 w-4 text-slate-400 shrink-0" />
                        ) : (
                          <Laptop className="h-4 w-4 text-slate-400 shrink-0" />
                        )}
                        <div>
                          <div className="font-semibold text-white flex items-center gap-2">
                            <span>{session.device}</span>
                            {session.isCurrent && (
                              <Badge variant="success" size="sm">
                                This Browser
                              </Badge>
                            )}
                          </div>
                          <div className="text-[11px] text-slate-400 font-mono mt-0.5">
                            {session.ip} · {session.location}
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-3">
                        <span className="text-[11px] text-slate-500">{session.lastActive}</span>
                        {!session.isCurrent && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleRevokeSession(session.id)}
                            className="text-red-400 hover:bg-red-500/10"
                          >
                            Revoke
                          </Button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Audit Logging Toggle */}
              <div className="pt-4 border-t border-slate-800 flex items-center justify-between">
                <div>
                  <div className="text-xs font-semibold text-white">Security & Audit Logging</div>
                  <div className="text-[11px] text-slate-400">
                    Record immutable tamper-evident logs for every document upload, review sign-off, and role mutation
                  </div>
                </div>
                <input
                  type="checkbox"
                  checked={settings.security.auditLogging}
                  onChange={(e) =>
                    setSettings({
                      ...settings,
                      security: { ...settings.security, auditLogging: e.target.checked },
                    })
                  }
                  className="rounded border-slate-700 text-brand-500 focus:ring-0 bg-slate-800 h-4 w-4"
                />
              </div>
            </Card>
          )}
        </div>
      </div>

      {/* REGISTER PASSKEY MODAL */}
      <Modal
        isOpen={isRegisterPasskeyOpen}
        onClose={() => setIsRegisterPasskeyOpen(false)}
        maxWidth="md"
        title="Enroll Security Passkey"
      >
        <form onSubmit={handleRegisterPasskey} className="space-y-4">
          <p className="text-xs text-slate-400">
            Insert your USB/NFC hardware security key (YubiKey) or use your device's built-in biometric sensor (Touch ID / Windows Hello).
          </p>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Passkey Label / Device Name
            </label>
            <input
              type="text"
              required
              placeholder="e.g. Work MacBook Touch ID or YubiKey 5C"
              value={newPasskeyName}
              onChange={(e) => setNewPasskeyName(e.target.value)}
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:border-brand-500"
              autoFocus
            />
          </div>

          <div className="p-3 rounded-lg bg-violet-500/10 border border-violet-500/20 text-xs text-violet-300 flex items-center gap-2.5">
            <ShieldCheck className="h-4 w-4 text-violet-400 shrink-0" />
            <span>FIDO2 / WebAuthn Level 3 compliant cryptography backed by hardware secure enclave.</span>
          </div>

          <div className="pt-3 border-t border-slate-800 flex items-center justify-end gap-2">
            <Button variant="ghost" size="sm" type="button" onClick={() => setIsRegisterPasskeyOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" size="sm" type="submit" leftIcon={<Key className="h-3.5 w-3.5" />}>
              Activate Passkey
            </Button>
          </div>
        </form>
      </Modal>

      {/* CONFIRM RESET DIALOG */}
      <ConfirmDialog
        isOpen={isConfirmResetOpen}
        onClose={() => setIsConfirmResetOpen(false)}
        onConfirm={handleConfirmReset}
        title="Reset Platform Preferences"
        message="Are you sure you want to reset all workspace settings, theme parameters, and notification options back to platform factory defaults?"
        confirmLabel="Reset Defaults"
        variant="warning"
      />
    </div>
  );
};
