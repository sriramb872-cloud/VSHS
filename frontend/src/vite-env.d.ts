/// <reference types="vite/client" />
/// <reference types="vite-plugin-pwa/client" />

// Ambient types for the variables Vite injects at build time. The project reads
// `import.meta.env.VITE_API_BASE_URL` in src/services/api.ts; without this
// reference `ImportMeta.env` is untyped and that call fails to type-check.
interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
