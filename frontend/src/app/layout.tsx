import type { Metadata } from 'next';
import { MotionConfig } from 'motion/react';
import { WorkspaceProvider } from '@/components/providers';
import { ThemeProvider } from '@/components/theme-provider';
import { themeBootstrap } from '@/lib/theme';
import '@fontsource-variable/inter';
import '@fontsource-variable/manrope';
import './globals.css';
import './design-system.css';
import './expressive.css';
import './integration.css';
import './landing-security.css';
import './dashboard-refinement.css';
import './theme.css';
import './workplan.css';

export const metadata: Metadata = { title: { default: 'Odin — Contract intelligence', template: '%s · Odin' }, description: 'Understand obligations, anticipate contract risk, and act with evidence.' };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en" suppressHydrationWarning><head><script dangerouslySetInnerHTML={{ __html: themeBootstrap }} /></head><body><ThemeProvider><MotionConfig reducedMotion="user"><WorkspaceProvider>{children}</WorkspaceProvider></MotionConfig></ThemeProvider></body></html>;
}
