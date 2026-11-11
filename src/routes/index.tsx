import React from 'react';
import { createBrowserRouter, Navigate } from 'react-router-dom';
import { AppLayout } from '../layouts/AppLayout';
import { PublicLayout } from '../layouts/PublicLayout';

// Public pages
import { LandingPage } from '../pages/public/LandingPage';
import { LoginPage } from '../pages/public/LoginPage';
import { RegisterPage } from '../pages/public/RegisterPage';
import { ForgotPasswordPage } from '../pages/public/ForgotPasswordPage';

// Authenticated application pages
import { DashboardPage } from '../pages/dashboard/DashboardPage';
import { ProjectsPage } from '../pages/projects/ProjectsPage';
import { ProjectWorkspacePage } from '../pages/projects/ProjectWorkspacePage';
import { HandoverSessionsPage } from '../pages/handover/HandoverSessionsPage';
import { GenerateHandoverPage } from '../pages/handover/GenerateHandoverPage';
import { DocumentsPage } from '../pages/documents/DocumentsPage';
import { ReviewQueuePage } from '../pages/review/ReviewQueuePage';
import { HandoverReviewWorkspacePage } from '../pages/review/HandoverReviewWorkspacePage';
import { ConflictsPage } from '../pages/review/ConflictsPage';
import { MyHandoversPage } from '../pages/incoming/MyHandoversPage';
import { IncomingHandoverOverviewPage } from '../pages/incoming/IncomingHandoverOverviewPage';
import { MyTasksPage } from '../pages/tasks/MyTasksPage';
import { TeamMembersPage } from '../pages/team/TeamMembersPage';
import { SettingsPage } from '../pages/settings/SettingsPage';
import { ComponentShowcasePage } from '../pages/common/ComponentShowcasePage';

export const router = createBrowserRouter([
  // Public Marketing & Auth routes
  {
    path: '/',
    element: <PublicLayout />,
    children: [
      {
        index: true,
        element: <LandingPage />,
      },
      {
        path: 'login',
        element: <LoginPage />,
      },
      {
        path: 'register',
        element: <RegisterPage />,
      },
      {
        path: 'forgot-password',
        element: <ForgotPasswordPage />,
      },
    ],
  },

  // Authenticated App Shell routes
  {
    path: '/',
    element: <AppLayout />,
    children: [
      {
        path: 'dashboard',
        element: <DashboardPage />,
      },
      {
        path: 'projects',
        element: <ProjectsPage />,
      },
      {
        path: 'projects/:id',
        element: <ProjectWorkspacePage />,
      },
      {
        path: 'knowledge-sources',
        element: <DocumentsPage />,
      },
      {
        path: 'documents',
        element: <DocumentsPage />,
      },
      {
        path: 'handover',
        element: <HandoverSessionsPage />,
      },
      {
        path: 'handovers',
        element: <HandoverSessionsPage />,
      },
      {
        path: 'handover/generate',
        element: <GenerateHandoverPage />,
      },
      {
        path: 'handovers/generate',
        element: <GenerateHandoverPage />,
      },
      {
        path: 'review',
        element: <ReviewQueuePage />,
      },
      {
        path: 'review/:id',
        element: <HandoverReviewWorkspacePage />,
      },
      {
        path: 'reviews',
        element: <ReviewQueuePage />,
      },
      {
        path: 'handover/review/:id',
        element: <HandoverReviewWorkspacePage />,
      },
      {
        path: 'my-handovers',
        element: <MyHandoversPage />,
      },
      {
        path: 'my-handovers/:id',
        element: <IncomingHandoverOverviewPage />,
      },
      {
        path: 'handovers/:id/view',
        element: <IncomingHandoverOverviewPage />,
      },
      {
        path: 'conflicts',
        element: <ConflictsPage />,
      },
      {
        path: 'tasks',
        element: <MyTasksPage />,
      },
      {
        path: 'team',
        element: <TeamMembersPage />,
      },
      {
        path: 'settings',
        element: <SettingsPage />,
      },
      {
        path: 'design-system',
        element: <ComponentShowcasePage />,
      },
    ],
  },

  // Fallback
  {
    path: '*',
    element: <Navigate to="/" replace />,
  },
]);
