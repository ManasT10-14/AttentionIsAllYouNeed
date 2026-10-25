export type Theme = 'light' | 'dark';
export const THEME_STORAGE_KEY = 'odin-theme';

export function parseTheme(value: unknown): Theme | null {
  return value === 'light' || value === 'dark' ? value : null;
}

export function resolveTheme(preference: unknown, systemDark: boolean): Theme {
  return parseTheme(preference) ?? (systemDark ? 'dark' : 'light');
}

// Runs before the page is painted, including on exported/static routes.
export const themeBootstrap = `(()=>{let preference;try{preference=localStorage.getItem('${THEME_STORAGE_KEY}')}catch{}const theme=preference==='light'||preference==='dark'?preference:window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';document.documentElement.dataset.theme=theme;document.documentElement.style.colorScheme=theme})()`;
