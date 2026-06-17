import '@testing-library/jest-dom/vitest';

// LayerChart (via @layerstack/svelte-stores) calls window.matchMedia at module
// load time.  jsdom doesn't implement it, so we stub it so imports don't crash.
if (typeof window !== 'undefined' && !window.matchMedia) {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: (query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false
    })
  });
}

// LayerCake (used by LayerChart) uses ResizeObserver to measure chart containers.
// jsdom doesn't implement it, so we stub it.
if (typeof globalThis.ResizeObserver === 'undefined') {
  globalThis.ResizeObserver = class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver;
}
