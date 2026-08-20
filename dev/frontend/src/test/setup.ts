import '@testing-library/jest-dom/vitest';
import { afterEach } from 'vitest';
import { cleanup } from '@testing-library/react';

// Unmount + clean the DOM between tests -- vitest does not do this
// automatically the way Jest's testing-library preset does.
afterEach(() => {
  cleanup();
});

// jsdom implements neither `navigator.mediaDevices` nor `getUserMedia`.
// CameraCapture (src/components/CameraCapture.tsx) already handles a denied/
// unavailable camera gracefully -- it falls back to a file-upload input --
// but only if the call REJECTS; `navigator.mediaDevices` being `undefined`
// makes `navigator.mediaDevices?.getUserMedia(...)` short-circuit to
// `undefined`, and the component's own `.then()` on that throws. Stubbing a
// rejecting `getUserMedia` exercises the exact same denied-camera path real
// browsers hit in this test environment, and lets tray-page tests reach the
// upload-fallback input CameraCapture already renders.
Object.defineProperty(window.navigator, 'mediaDevices', {
  writable: true,
  value: {
    getUserMedia: () => Promise.reject(new Error('getUserMedia not available in jsdom')),
  },
});

// jsdom does not implement HTMLCanvasElement#getContext / toBlob -- CameraCapture
// only calls these from the live-camera capture button, which the stub above
// keeps tests away from (they use the upload-fallback input instead), but a
// stub keeps any incidental call from throwing rather than silently no-op-ing.
if (!HTMLCanvasElement.prototype.getContext) {
  HTMLCanvasElement.prototype.getContext = (() => null) as typeof HTMLCanvasElement.prototype.getContext;
}
