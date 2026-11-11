import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { ChevronRight, Home } from 'lucide-react';

const routeNames: Record<string, string> = {
  dashboard: 'Dashboard',
  projects: 'Projects',
  handover: 'Handover Sessions',
  documents: 'Knowledge Base',
  review: 'Review Queue',
  settings: 'Settings',
  design: 'Design System',
};

export const Breadcrumbs: React.FC = () => {
  const location = useLocation();
  const pathnames = location.pathname.split('/').filter(Boolean);

  if (pathnames.length === 0) {
    return (
      <div className="flex items-center text-xs text-slate-400 font-medium">
        <span className="flex items-center gap-1.5 text-slate-200">
          <Home className="h-3.5 w-3.5 text-brand-400" />
          <span>Knowledge Handover</span>
        </span>
      </div>
    );
  }

  return (
    <nav className="flex items-center text-xs text-slate-400 font-medium">
      <Link
        to="/dashboard"
        className="flex items-center gap-1.5 text-slate-400 hover:text-slate-200 transition-colors"
      >
        <Home className="h-3.5 w-3.5" />
      </Link>

      {pathnames.map((segment, index) => {
        const isLast = index === pathnames.length - 1;
        const href = `/${pathnames.slice(0, index + 1).join('/')}`;
        const displayName = routeNames[segment] || segment.replace(/-/g, ' ');

        return (
          <React.Fragment key={href}>
            <ChevronRight className="h-3.5 w-3.5 mx-2 text-slate-600 shrink-0" />
            {isLast ? (
              <span className="text-slate-200 font-semibold capitalize">{displayName}</span>
            ) : (
              <Link to={href} className="text-slate-400 hover:text-slate-200 capitalize transition-colors">
                {displayName}
              </Link>
            )}
          </React.Fragment>
        );
      })}
    </nav>
  );
};
