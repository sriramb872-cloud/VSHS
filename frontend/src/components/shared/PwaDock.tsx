// src/components/shared/PwaDock.tsx
import React from 'react';
import PWAInstallPrompt from './PWAInstallPrompt';
import PWAUpdatePrompt from './PWAUpdatePrompt';

/**
 * Fixed dock for the two PWA prompts.
 *
 * Both cards live here so they can never overlap each other, and the position
 * is chosen to stay clear of everything already on screen:
 *  * bottom-4 (16px) clears the mobile bottom navigation (64px tall) by
 *    clearing nothing - instead the dock is offset to the LEFT, and the
 *    bottom nav is centred/edge-to-edge, so the cards sit above it via
 *    `bottom-20` on small screens.
 *  * the pet widget is anchored bottom-RIGHT, so the dock is bottom-LEFT.
 *  * `pointer-events-none` on the wrapper plus `pointer-events-auto` on the
 *    cards means the empty dock area never swallows taps meant for the page.
 */
export const PwaDock: React.FC = () => (
  <div
    aria-live="off"
    className="pointer-events-none fixed bottom-20 left-3 z-[70] flex flex-col gap-2 sm:bottom-6 sm:left-6"
  >
    <div className="pointer-events-auto">
      <PWAUpdatePrompt />
    </div>
    <div className="pointer-events-auto">
      <PWAInstallPrompt />
    </div>
  </div>
);

export default PwaDock;
