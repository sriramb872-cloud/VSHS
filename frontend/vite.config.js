import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { VitePWA } from 'vite-plugin-pwa'

// SCHOLARIS PWA configuration.
//
// Design notes
// ------------
// * The web app manifest is hand-authored at `public/manifest.webmanifest` and
//   linked from `index.html`, so it is served identically in `npm run dev` and
//   in the production build. `manifest: false` below stops the plugin from
//   generating a second, competing manifest.
//
// * The service worker precaches ONLY files emitted by the Vite build
//   (JS/CSS/HTML/icons). The backend API is a different origin, is never
//   precached, and has no runtime cache route - see the `runtimeCaching`
//   comment. Authenticated ERP responses are therefore never written to a
//   shared Cache Storage bucket.
//
// * `registerType: 'prompt'` + `injectRegister: null`: registration is done in
//   `src/pwa/registerServiceWorker.ts` so the update UX can be surfaced to the
//   user instead of silently swapping the app under them mid-edit.
//
// * `skipWaiting: false` is deliberate - see that key below.
//
// * The Content-Security-Policy is generated at BUILD time from
//   VITE_API_BASE_URL (see cspFromEnv below), so the API origin the policy
//   allows is always the one set in the Vercel environment variable.

// Builds the CSP <meta> tag from VITE_API_BASE_URL. Whatever URL the env
// variable holds is the URL `connect-src` allows. Build-only: the dev server
// is left without a CSP because Vite's HMR needs inline scripts.
function cspFromEnv(mode) {
  const env = loadEnv(mode, process.cwd(), '')
  const raw = env.VITE_API_BASE_URL
  if (!raw) {
    throw new Error(
      'VITE_API_BASE_URL is not set - refusing to build (it would fall back to localhost).',
    )
  }
  const api = new URL(raw).origin

  const csp = [
    "default-src 'self'",
    "script-src 'self' https://checkout.razorpay.com",
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
    "font-src 'self' data: https://fonts.gstatic.com",
    "img-src 'self' data: blob: https:",
    `connect-src 'self' ${api} https://fonts.googleapis.com https://fonts.gstatic.com https://api.razorpay.com https://lumberjack.razorpay.com`,
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-src 'self' https://checkout.razorpay.com https://api.razorpay.com",
    "worker-src 'self'",
    "manifest-src 'self'",
  ].join('; ')

  return {
    name: 'csp-from-env',
    apply: 'build',
    transformIndexHtml: {
      order: 'post',
      handler: () => [
        {
          tag: 'meta',
          attrs: { 'http-equiv': 'Content-Security-Policy', content: csp },
          injectTo: 'head-prepend',
        },
      ],
    },
  }
}

export default defineConfig(({ mode }) => ({
  plugins: [
    react(),
    tailwindcss(),
    cspFromEnv(mode),
    VitePWA({
      // The manifest lives in public/ and is linked from index.html.
      manifest: false,

      // We register the worker ourselves via `virtual:pwa-register` so the
      // "update available" prompt can be wired to real UI.
      injectRegister: null,

      // Ask before taking over, so a deploy never interrupts a user mid-edit.
      registerType: 'prompt',

      // Only meaningful with a custom service worker; kept for clarity that we
      // deliberately do NOT let the worker call skipWaiting() on its own.
      workbox: {
        // Do not activate a new worker until the user accepts the update.
        // Without this a deploy would swap the shell out from under someone
        // who is halfway through a form.
        skipWaiting: false,

        // Let the worker take control of the page that installed it, instead
        // of waiting for the next navigation. Combined with `skipWaiting:
        // false` this is safe: `clientsClaim` only applies on a first
        // activation, when there is no previous worker to conflict with, and
        // it never un-activates a waiting newer version. The effect is that a
        // user's very first visit is already offline-capable.
        clientsClaim: true,

        // Delete Workbox precaches from previous app versions on activate.
        cleanupOutdatedCaches: true,

        // Precache the built app shell. `globPatterns` is restricted to build
        // output types - no API, no uploads, nothing from the database.
        globPatterns: ['**/*.{js,css,html,ico,png,svg,webp,woff2}'],

        // Any in-scope navigation (e.g. /principal/attendance, or a hard
        // refresh on a deep link) falls back to the cached SPA shell when the
        // network is unavailable. This is what makes offline launches work.
        // It is only ever the empty HTML shell - never data.
        navigateFallback: 'index.html',

        // Never answer an API or media request with the HTML shell. Without
        // this a navigation to a path that looks like an asset could be
        // served index.html, which would surface as a confusing parse error.
        navigateFallbackDenylist: [
          /^\/api\/.*/i,
          /^\/media\/.*/i,
          /^\/docs/,
          /^\/.*\.[a-z0-9]{2,5}(\?.*)?$/i,
        ],

        // Runtime caching. Only two entries, both deliberate.
        runtimeCaching: [
          // 1. Authenticated ERP API: NETWORK ONLY, never cached.
          //    Stated explicitly so the policy is auditable in one place and so
          //    a future entry added above/below cannot accidentally start
          //    persisting students, marks, attendance or report cards into
          //    shared Cache Storage. This holds whether the API is on a
          //    different origin (today: localhost:8000 / backend-production-510f.up.railway.app) or
          //    same-origin behind one domain.
          {
            urlPattern: ({ url, sameOrigin }) =>
              sameOrigin && url.pathname.startsWith('/api/'),
            handler: 'NetworkOnly',
            method: 'GET',
          },

          // 2. The Inter webfont from Google's CDN: public, non-sensitive, and
          //    content-stable per URL. The app remains fully usable without it
          //    (the CSS stack falls back to system sans-serif), so a failure
          //    here is never fatal.
          {
            urlPattern: ({ url }) =>
              url.hostname === 'fonts.googleapis.com' ||
              url.hostname === 'fonts.gstatic.com',
            handler: 'StaleWhileRevalidate',
            options: {
              cacheName: 'scholaris-fonts',
              expiration: { maxEntries: 12, maxAgeSeconds: 60 * 60 * 24 * 365 },
              cacheableResponse: { statuses: [0, 200] },
            },
          },
        ],

        maximumFileSizeToCacheInBytes: 4 * 1024 * 1024,
      },

      devOptions: {
        // Off by default: a service worker in dev caches modules that Vite is
        // actively rewriting, which produces stale-code confusion. Enable with
        // `VITE_PWA_DEV=1 npm run dev` when specifically testing SW behaviour
        // against the dev server.
        enabled: false,
        type: 'module',
        navigateFallback: 'index.html',
      },
    }),
  ],
}))