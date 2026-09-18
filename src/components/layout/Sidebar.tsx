'use client';

import React from 'react';
import { Logo } from '@/components/brand/Logo';
import {
  LayoutDashboard,
  FilePlus,
  BarChart3,
  TrendingUp,
  PiggyBank,
  MessageSquare,
  FolderText,
  Settings,
  HelpCircle,
  X,
} from 'lucide-react';

export type DashboardTab =
  | 'dashboard'
  | 'analyze'
  | 'consumption'
  | 'forecast'
  | 'savings'
  | 'assistant'
  | 'documents';

interface SidebarProps {
  activeTab: DashboardTab;
  onSelectTab: (tab: DashboardTab) => void;
  isOpenMobile?: boolean;
  onCloseMobile?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  onSelectTab,
  isOpenMobile = false,
  onCloseMobile,
}) => {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'analyze', label: 'Analyze Bill', icon: FilePlus },
    { id: 'consumption', label: 'Consumption', icon: BarChart3 },
    { id: 'forecast', label: 'Forecast', icon: TrendingUp },
    { id: 'savings', label: 'Savings', icon: PiggyBank },
    { id: 'assistant', label: 'Ask Assistant', icon: MessageSquare },
    { id: 'documents', label: 'Documents', icon: FolderText },
  ] as const;

  const bottomItems = [
    { id: 'settings', label: 'Settings', icon: Settings },
    { id: 'help', label: 'Help', icon: HelpCircle },
  ] as const;

  const sidebarContent = (
    <div className="h-full flex flex-col justify-between p-5 bg-white border-r border-slate-200/80 w-64 select-none">
      <div>
        {/* Top Logo */}
        <div className="flex items-center justify-between pb-6 border-b border-slate-100">
          <Logo size="md" />
          {onCloseMobile && (
            <button
              onClick={onCloseMobile}
              className="lg:hidden p-1 text-slate-400 hover:text-slate-600 rounded-lg"
            >
              <X className="w-5 h-5" />
            </button>
          )}
        </div>

        {/* Primary Navigation */}
        <nav className="mt-6 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;

            return (
              <button
                key={item.id}
                onClick={() => {
                  onSelectTab(item.id as DashboardTab);
                  if (onCloseMobile) onCloseMobile();
                }}
                className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-semibold transition-all duration-150 cursor-pointer ${
                  isActive
                    ? 'bg-emerald-50 text-emerald-700 font-bold border border-emerald-200/60 shadow-xs'
                    : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900 font-medium'
                }`}
              >
                <Icon
                  className={`w-4 h-4 shrink-0 transition-colors ${
                    isActive ? 'text-emerald-600 stroke-[2.3]' : 'text-slate-400 stroke-[1.8]'
                  }`}
                />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
      </div>

      {/* Bottom Utility Navigation */}
      <div className="pt-4 border-t border-slate-100 space-y-1">
        {bottomItems.map((item) => {
          const Icon = item.icon;
          return (
            <button
              key={item.id}
              onClick={() => alert(`${item.label} section clicked`)}
              className="w-full flex items-center gap-3 px-3.5 py-2 text-xs font-semibold text-slate-500 hover:bg-slate-50 hover:text-slate-900 rounded-xl transition-colors cursor-pointer"
            >
              <Icon className="w-4 h-4 text-slate-400 stroke-[1.8]" />
              <span>{item.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop Persistent Sidebar */}
      <aside className="hidden lg:block h-screen sticky top-0 shrink-0 z-20">
        {sidebarContent}
      </aside>

      {/* Mobile Drawer Overlay */}
      {isOpenMobile && (
        <div className="lg:hidden fixed inset-0 z-50 flex">
          <div
            className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs"
            onClick={onCloseMobile}
          />
          <div className="relative z-10 w-64 max-w-xs h-full bg-white shadow-2xl">
            {sidebarContent}
          </div>
        </div>
      )}
    </>
  );
};
