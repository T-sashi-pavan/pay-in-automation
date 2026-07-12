import React, { useState } from 'react';
import {
  LayoutDashboard,
  UploadCloud,
  Sliders,
  ChevronLeft,
  ChevronRight,
  Layers,
} from 'lucide-react';
import { useSidebar } from '../contexts/SidebarContext';

interface DashboardLayoutProps {
  activeTab: 'dashboard' | 'upload' | 'customise';
  onTabChange: (tab: 'dashboard' | 'upload' | 'customise') => void;
  children: React.ReactNode;
}

const EXPANDED_WIDTH = 192;
const COLLAPSED_WIDTH = 56;

const getSavedCollapsed = (): boolean => {
  try { return localStorage.getItem('sidebar_collapsed') === 'true'; } catch { return false; }
};

export const DashboardLayout: React.FC<DashboardLayoutProps> = ({ activeTab, onTabChange, children }) => {
  const [collapsed, setCollapsed] = useState<boolean>(getSavedCollapsed);
  const { mobileOpen, closeMobileSidebar } = useSidebar();

  const toggleCollapsed = () => {
    setCollapsed(prev => {
      const next = !prev;
      try { localStorage.setItem('sidebar_collapsed', String(next)); } catch {}
      return next;
    });
  };

  const navItems = [
    { id: 'dashboard' as const, label: 'Dashboard', icon: LayoutDashboard },
    { id: 'upload' as const, label: 'Upload Files', icon: UploadCloud },
    { id: 'customise' as const, label: 'Organise the Data', icon: Sliders },
  ];

  const sidebarWidth = collapsed ? COLLAPSED_WIDTH : EXPANDED_WIDTH;

  const SidebarContent = () => (
    <div className="flex flex-col h-full">
      {/* Logo */}
      <div
        className="flex items-center h-14 border-b border-[#E5E7EB] dark:border-[#1F2937] flex-shrink-0 px-3 overflow-hidden"
        style={{ justifyContent: collapsed && !mobileOpen ? 'center' : 'flex-start' }}
      >
        <div className="w-7 h-7 rounded-lg bg-[#4F46E5] flex items-center justify-center flex-shrink-0">
          <Layers className="w-3.5 h-3.5 text-white" />
        </div>
        {(!collapsed || mobileOpen) && (
          <div className="ml-2.5 min-w-0">
            <p className="text-sm font-bold text-slate-900 dark:text-slate-100 whitespace-nowrap leading-tight">PAY-IN</p>
            <p className="text-[10px] text-[#4F46E5] dark:text-indigo-400 font-semibold tracking-widest whitespace-nowrap uppercase leading-tight">Automation V1</p>
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-2 flex flex-col gap-0.5 mt-1 overflow-hidden">
        {navItems.map(({ id, label, icon: Icon }) => {
          const isActive = activeTab === id;
          return (
            <button
              key={id}
              type="button"
              onClick={() => { onTabChange(id); closeMobileSidebar(); }}
              title={collapsed && !mobileOpen ? label : undefined}
              className={`flex items-center h-8 rounded-lg transition-colors duration-150 cursor-pointer w-full text-left overflow-hidden
                ${isActive
                  ? 'bg-[#4F46E5] text-white'
                  : 'text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800'
                }
                ${collapsed && !mobileOpen ? 'justify-center px-0' : 'px-2 gap-2'}
              `}
            >
              <Icon className="w-4 h-4 flex-shrink-0" />
              {(!collapsed || mobileOpen) && (
                <span className="text-[13px] font-medium whitespace-nowrap">{label}</span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Collapse Toggle (desktop only) — compact icon button */}
      <div className="hidden md:flex p-2 border-t border-[#E5E7EB] dark:border-[#1F2937] flex-shrink-0 justify-center">
        <button
          type="button"
          onClick={toggleCollapsed}
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          className="flex items-center justify-center w-8 h-8 rounded-lg text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors duration-150 cursor-pointer"
        >
          {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      </div>
    </div>
  );

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-white dark:bg-[#0B1220] text-slate-900 dark:text-slate-100 font-sans">

      {/* ── DESKTOP SIDEBAR ── */}
      <aside
        style={{ width: sidebarWidth }}
        className="hidden md:flex flex-col flex-shrink-0 bg-[#F8FAFC] dark:bg-[#111827] border-r border-[#E5E7EB] dark:border-[#1F2937] transition-[width] duration-300 ease-in-out overflow-hidden"
      >
        <SidebarContent />
      </aside>

      {/* ── MOBILE OVERLAY SIDEBAR ── */}
      <>
        <div
          onClick={() => closeMobileSidebar()}
          className={`md:hidden fixed inset-0 z-40 bg-black/60 backdrop-blur-sm transition-opacity duration-300 ${
            mobileOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
          }`}
        />
        <div
          className={`md:hidden fixed left-0 top-0 bottom-0 z-50 w-56 bg-[#F8FAFC] dark:bg-[#111827] border-r border-[#E5E7EB] dark:border-[#1F2937] transition-transform duration-300 ease-in-out ${
            mobileOpen ? 'translate-x-0' : '-translate-x-full'
          }`}
        >
          <SidebarContent />
        </div>
      </>

      {/* ── MAIN AREA ── */}
      {/* Top header bar was removed — the mobile menu trigger and theme
          toggle now live inside each page's own toolbar instead (see
          Dashboard.tsx/CustomiseData.tsx), wired via SidebarContext/ThemeContext. */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">

        {/* PAGE CONTENT */}
        <main className="flex-1 overflow-hidden min-h-0 bg-white dark:bg-[#0B1220]">
          {children}
        </main>
      </div>
    </div>
  );
};
