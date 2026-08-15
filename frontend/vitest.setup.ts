// Stub API browser yang tidak diimplementasi jsdom tapi dipakai komponen shadcn/Radix.
// Tanpa ini `useIsMobile` (src/hooks/use-mobile.tsx) melempar saat komponen sidebar dirender.

if (!window.matchMedia) {
  window.matchMedia = (query: string) =>
    ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }) as unknown as MediaQueryList;
}

// Radix Select/DropdownMenu memanggil API pointer capture dan scrollIntoView yang
// tidak ada di jsdom. Tanpa stub ini, membuka menu di test melempar TypeError.
if (!Element.prototype.hasPointerCapture) {
  Element.prototype.hasPointerCapture = () => false;
  Element.prototype.setPointerCapture = () => {};
  Element.prototype.releasePointerCapture = () => {};
}

if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = () => {};
}

if (!window.ResizeObserver) {
  window.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver;
}
