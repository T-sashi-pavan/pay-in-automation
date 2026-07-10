const STORAGE_KEY = 'pay_in_edited_by';

/**
 * Lightweight attribution for the audit log — this app has no auth system,
 * so we ask once for a display name and remember it locally. Not a login.
 */
export const getEditedBy = (): string => {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved && saved.trim()) return saved.trim();
  } catch {}
  return 'User';
};

export const setEditedBy = (name: string): void => {
  try { localStorage.setItem(STORAGE_KEY, name.trim() || 'User'); } catch {}
};
