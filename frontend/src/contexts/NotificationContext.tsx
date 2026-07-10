import React, { createContext, useContext, useEffect, useState } from 'react';
import { CheckCircle2, AlertCircle, X } from 'lucide-react';

type NotificationType = 'success' | 'error';

interface NotificationAction {
  label: string;
  onClick: () => void;
}

interface Notification {
  message: string;
  type: NotificationType;
  action?: NotificationAction;
}

interface NotificationContextValue {
  notify: (message: string, type: NotificationType, action?: NotificationAction) => void;
}

const NotificationContext = createContext<NotificationContextValue | undefined>(undefined);

export const NotificationProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [notification, setNotification] = useState<Notification | null>(null);

  useEffect(() => {
    if (notification) {
      const timer = setTimeout(() => setNotification(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [notification]);

  const notify = (message: string, type: NotificationType, action?: NotificationAction) => {
    setNotification({ message, type, action });
  };

  return (
    <NotificationContext.Provider value={{ notify }}>
      {children}
      {notification && (
        <div className="fixed bottom-6 right-6 z-[100] animate-in fade-in slide-in-from-bottom-2 duration-300">
          <div className={`flex items-center gap-3 px-4 py-3.5 rounded-xl border shadow-lg backdrop-blur-md max-w-sm ${
            notification.type === 'success'
              ? 'bg-white/95 dark:bg-slate-900/95 border-emerald-200 dark:border-emerald-500/30'
              : 'bg-white/95 dark:bg-slate-900/95 border-rose-200 dark:border-rose-500/30'
          }`}>
            {notification.type === 'success' ? (
              <CheckCircle2 className="w-5 h-5 text-emerald-500 dark:text-emerald-400 flex-shrink-0" />
            ) : (
              <AlertCircle className="w-5 h-5 text-rose-500 dark:text-rose-400 flex-shrink-0" />
            )}
            <p className="text-xs font-semibold text-slate-800 dark:text-slate-100 leading-relaxed flex-1 pr-2">
              {notification.message}
            </p>
            {notification.action && (
              <button
                type="button"
                onClick={() => { notification.action!.onClick(); setNotification(null); }}
                className="px-2.5 py-1 rounded-lg text-xs font-bold text-[#4F46E5] dark:text-indigo-400 hover:bg-[#4F46E5]/10 transition-colors cursor-pointer flex-shrink-0"
              >
                {notification.action.label}
              </button>
            )}
            <button
              type="button"
              onClick={() => setNotification(null)}
              className="p-1 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 transition-colors cursor-pointer flex-shrink-0"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </NotificationContext.Provider>
  );
};

export const useNotification = (): NotificationContextValue => {
  const ctx = useContext(NotificationContext);
  if (!ctx) throw new Error('useNotification must be used within a NotificationProvider');
  return ctx;
};
