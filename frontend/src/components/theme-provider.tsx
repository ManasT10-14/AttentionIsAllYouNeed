'use client';

import { createContext, useContext, useSyncExternalStore, type ReactNode } from 'react';
import { flushSync } from 'react-dom';
import { Moon, Sun } from 'lucide-react';
import { parseTheme, resolveTheme, THEME_STORAGE_KEY, type Theme } from '@/lib/theme';

const CHANGE_EVENT = 'odin-theme-change';
let memoryPreference: Theme | null = null;

function preference() {
  try { return memoryPreference ?? parseTheme(localStorage.getItem(THEME_STORAGE_KEY)); }
  catch { return memoryPreference; }
}

function applyTheme(theme: Theme) {
  document.documentElement.dataset.theme = theme;
  document.documentElement.style.colorScheme = theme;
}

function subscribe(callback: () => void) {
  const system = window.matchMedia('(prefers-color-scheme: dark)');
  const sync = () => {
    applyTheme(resolveTheme(preference(), system.matches));
    callback();
  };
  const storage = (event: StorageEvent) => {
    if (event.key !== THEME_STORAGE_KEY && event.key !== null) return;
    memoryPreference = parseTheme(event.newValue);
    sync();
  };
  window.addEventListener(CHANGE_EVENT, sync);
  window.addEventListener('storage', storage);
  system.addEventListener('change', sync);
  sync();
  return () => {
    window.removeEventListener(CHANGE_EVENT, sync);
    window.removeEventListener('storage', storage);
    system.removeEventListener('change', sync);
  };
}

const snapshot = (): Theme => parseTheme(document.documentElement.dataset.theme) ?? 'light';
const serverSnapshot = (): Theme => 'light';
type Origin = { x: number; y: number };
const ThemeContext = createContext<{ theme: Theme; setTheme: (theme: Theme, origin?: Origin) => void } | null>(null);
let switching = false;

async function setTheme(theme: Theme, origin?: Origin) {
  if (switching || snapshot() === theme) return;
  const commit = () => {
    memoryPreference = theme;
    try { localStorage.setItem(THEME_STORAGE_KEY, theme); } catch { /* Keep the choice for this session when storage is unavailable. */ }
    // Include React-rendered graph labels and edges in the new theme snapshot.
    flushSync(() => {
      applyTheme(theme);
      window.dispatchEvent(new Event(CHANGE_EVENT));
    });
  };
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) { commit(); return; }

  const root = document.documentElement;
  switching = true;
  if (!document.startViewTransition) {
    root.dataset.themeTransition = 'fade';
    commit();
    window.setTimeout(() => { delete root.dataset.themeTransition; switching = false; }, 500);
    return;
  }

  root.dataset.themeTransition = 'reveal';
  let transition: ViewTransition | undefined;
  try {
    transition = document.startViewTransition(commit);
    await transition.ready;
    const x = Math.max(0, Math.min(window.innerWidth, origin?.x ?? window.innerWidth / 2));
    const y = Math.max(0, Math.min(window.innerHeight, origin?.y ?? window.innerHeight / 2));
    const radius = Math.hypot(Math.max(x, window.innerWidth - x), Math.max(y, window.innerHeight - y));
    await root.animate(
      { clipPath: [`circle(0px at ${x}px ${y}px)`, `circle(${Math.ceil(radius)}px at ${x}px ${y}px)`] },
      { duration: 650, easing: 'cubic-bezier(.22,.68,0,1)', pseudoElement: '::view-transition-new(root)' },
    ).finished;
    await transition.finished;
  } catch {
    transition?.skipTransition();
    await transition?.finished.catch(() => {});
    if (snapshot() !== theme) commit();
  } finally {
    delete root.dataset.themeTransition;
    switching = false;
  }
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const theme = useSyncExternalStore(subscribe, snapshot, serverSnapshot);
  return <ThemeContext.Provider value={{ theme, setTheme }}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) throw new Error('useTheme requires ThemeProvider');
  return context;
}

export function ThemeToggle({ className = '' }: { className?: string }) {
  const { theme, setTheme } = useTheme();
  return <button type="button" className={'theme-toggle ' + className} aria-label="Dark mode" aria-pressed={theme === 'dark'} title={'Switch to ' + (theme === 'dark' ? 'light' : 'dark') + ' mode'} onClick={event => {
    const bounds = event.currentTarget.getBoundingClientRect();
    void setTheme(theme === 'dark' ? 'light' : 'dark', { x: bounds.left + bounds.width / 2, y: bounds.top + bounds.height / 2 });
  }}>
    <span className="theme-toggle-thumb" aria-hidden="true" /><Sun className="theme-sun" aria-hidden="true" size={15} strokeWidth={1.8} /><Moon className="theme-moon" aria-hidden="true" size={15} strokeWidth={1.8} />
  </button>;
}
