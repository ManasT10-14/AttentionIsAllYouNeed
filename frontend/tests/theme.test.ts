import test from 'node:test';
import assert from 'node:assert/strict';
import { runInNewContext } from 'node:vm';
import { readFileSync, readdirSync } from 'node:fs';
import postcss from 'postcss';
import { resolveTheme, themeBootstrap, THEME_STORAGE_KEY } from '../src/lib/theme';

test('theme boot applies a saved preference before paint, with a system fallback and blocked storage support', () => {
  for (const sample of [
    { saved: 'dark', systemDark: false, expected: 'dark' },
    { saved: 'light', systemDark: true, expected: 'light' },
    { saved: null, systemDark: true, expected: 'dark' },
    { saved: 'invalid', systemDark: false, expected: 'light' },
    { saved: null, systemDark: true, blocked: true, expected: 'dark' },
  ]) {
    const element = { dataset: {} as Record<string, string>, style: {} as Record<string, string> };
    runInNewContext(themeBootstrap, {
      localStorage: { getItem(key: string) { assert.equal(key, THEME_STORAGE_KEY); if (sample.blocked) throw new Error('Storage blocked'); return sample.saved; } },
      window: { matchMedia(query: string) { assert.equal(query, '(prefers-color-scheme: dark)'); return { matches: sample.systemDark }; } },
      document: { documentElement: element },
    });
    assert.equal(element.dataset.theme, sample.expected);
    assert.equal(element.style.colorScheme, sample.expected);
    assert.equal(resolveTheme(sample.saved, sample.systemDark), sample.expected);
  }
});

const appDirectory = new URL('../src/app/', import.meta.url);
const themeCSS = postcss.parse(readFileSync(new URL('theme.css', appDirectory), 'utf8'));
const tokens = new Map<string, string>();
themeCSS.walkRules(rule => {
  if (rule.selector === "html[data-theme='dark']") rule.walkDecls(d => { tokens.set(d.prop, d.value); });
});
function value(name: string): string {
  const result = tokens.get(name);
  assert.ok(result, 'Missing theme token: ' + name);
  return result.startsWith('var(') ? value(result.slice(4, -1)) : result;
}

test('every migrated site color has a dark token and an explicit light fallback', () => {
  for (const file of readdirSync(appDirectory).filter(name => name.endsWith('.css') && name !== 'theme.css')) {
    const css = readFileSync(new URL(file, appDirectory), 'utf8');
    for (const match of css.matchAll(/var\((--theme-[a-z-]+)([^)]*)\)/g)) {
      assert.ok(tokens.has(match[1]), file + ' references undefined ' + match[1]);
      assert.match(match[2], /^,\s*\S/, file + ' is missing its light-mode fallback');
    }
  }
});

function luminance(hex: string) {
  const rgb = hex.slice(1).match(/../g)!.slice(0, 3).map(channel => {
    const v = parseInt(channel, 16) / 255;
    return v <= .04045 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4;
  });
  return .2126 * rgb[0] + .7152 * rgb[1] + .0722 * rgb[2];
}
function contrast(foreground: string, background: string) {
  const values = [luminance(foreground), luminance(background)].sort((a, b) => b - a);
  return (values[0] + .05) / (values[1] + .05);
}

test('dark text and exposure cells maintain readable contrast at small text sizes', () => {
  for (const foreground of ['--theme-ink', '--theme-text', '--theme-muted', '--theme-accent']) {
    for (const background of ['--theme-surface', '--theme-surface-subtle', '--theme-surface-raised', '--theme-surface-blue']) {
      assert.ok(contrast(value(foreground), value(background)) >= 4.5, foreground + ' on ' + background);
    }
  }
  for (let level = 0; level <= 4; level++) {
    let foreground = ''; let background = '';
    themeCSS.walkRules(rule => {
      if (rule.selector !== "html[data-theme='dark'] .risk-level-" + level) return;
      rule.walkDecls(d => { if (d.prop === 'color') foreground = d.value === '#fff' ? '#ffffff' : d.value; if (d.prop === 'background') background = d.value; });
    });
    assert.ok(contrast(foreground, background) >= 4.5, 'Exposure level ' + level);
  }
});
