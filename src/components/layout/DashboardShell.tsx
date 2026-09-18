'use client';

import React, { useState } from 'react';
import { Sidebar, DashboardTab } from './Sidebar';
import { Topbar } from './Topbar';

interface DashboardShellProps {
  activeTab: DashboardTab;
  onSelectTab: (tab: DashboardTab) => void;
  children: React.ReactNode;
  location?: string;
  tempC?: number;
  isDemoMode?: boolean;
  onExitDemo?: () => void;
}

export const DashboardShell: React.FC<DashboardShellProps> = ({
  activeTab,
  onSelectTab,
  children,
  location,
  tempC,
  isDemoMode = false,
  onExitDemo,
}) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <div className="min-h-screen bg-slate-50/70 flex font-sans">
      <Sidebar
        activeTab={activeTab}
        onSelectTab={onSelectTab}
        isOpenMobile={mobileMenuOpen}
        onCloseMobile={() => setMobileMenuOpen(false)}
      />

      <div className="flex-1 flex flex-col min-w-0">
        <Topbar
          onOpenMobileMenu={() => setMobileMenuOpen(true)}
          location={location}
          tempC={tempC}
          isDemoMode={isDemoMode}
          onExitDemo={onExitDemo}
        />

        <main className="flex-1 p-4 md:p-8 max-w-7xl w-full mx-auto">
          {children}
        </main>
      </div>
    </div>
  );
};
