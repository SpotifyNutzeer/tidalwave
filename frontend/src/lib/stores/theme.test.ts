import { describe, it, expect, beforeEach } from 'vitest';
import { get } from 'svelte/store';
import { theme, toggleTheme } from './theme';

describe('theme store', () => {
  beforeEach(() => { localStorage.clear(); theme.set('mocha'); });

  it('toggles between mocha and latte', () => {
    toggleTheme();
    expect(get(theme)).toBe('latte');
    toggleTheme();
    expect(get(theme)).toBe('mocha');
  });

  it('persists the choice to localStorage', () => {
    toggleTheme();
    expect(localStorage.getItem('tw-theme')).toBe('latte');
  });

  it('reflects the choice on the document element', () => {
    toggleTheme();
    expect(document.documentElement.dataset.theme).toBe('latte');
  });
});
