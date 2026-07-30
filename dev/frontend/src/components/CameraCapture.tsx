import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Camera, RefreshCw, Upload, Check } from 'lucide-react';
import { Button } from '@/components/ui/Button';

interface CameraCaptureProps {
  onConfirm: (blob: Blob, previewUrl: string) => void;
  captureLabel?: string;
  /** FixbySonnet1 Task 8: force the camera torch on for the duration of the
   * stream. Pill-scan capture ONLY -- NB08 (ADR 2026-07-15) found forced
   * illumination is the dominant lever for the imprint-OCR failure mode
   * behind most pill non-verifications; that evidence is pill-imprint
   * specific and does NOT extend to Rx-scan (a flat printed document, where
   * forced light risks glare/hotspot with no supporting study). Callers:
   * AnalyzePage passes `forceFlash={mode === 'pill'}`; Rx-scan passes
   * nothing. Silent no-op wherever a controllable torch isn't available
   * (most notably iOS Safari, which exposes no torch/flash web API at all)
   * -- never throws, never shows a "flash unsupported" notice (Muthu's
   * decision, this session). */
  forceFlash?: boolean;
}

const DEFAULT_ASPECT = 16 / 9;

/** getUserMedia viewfinder with capture/confirm/retake, falling back to file upload
 * when camera access is denied or unavailable (Priority 1D, point 9).
 *
 * FixbySonnet1 Task 2 (Bug #2): the live stream must be re-attached to the
 * <video> element every time the viewfinder is shown again -- capturing a
 * photo unmounts <video> (the preview branch renders instead); Retake
 * remounts a brand new <video> that never receives `srcObject` without this,
 * which is why Retake used to show a permanently black/frozen viewfinder.
 *
 * Task 3 (Bug #3): the viewfinder's aspect ratio now tracks the video's
 * actual `videoWidth`/`videoHeight` (instead of a fixed 16:9 box) and
 * renders `object-contain` so what the user sees matches what `capture()`
 * draws to the canvas, and phone rotation reflows correctly. */
export function CameraCapture({ onConfirm, captureLabel, forceFlash = false }: CameraCaptureProps) {
  const { t } = useTranslation();
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const [cameraReady, setCameraReady] = useState(false);
  const [cameraDenied, setCameraDenied] = useState(false);
  const [preview, setPreview] = useState<{ blob: Blob; url: string } | null>(null);
  const [videoAspect, setVideoAspect] = useState<number>(DEFAULT_ASPECT);

  const label = captureLabel ?? t('camera.captureDefault');

  // Best-effort torch off -- swallows every failure (rejected promise,
  // missing capability, dead track). Never leaves the phone's flashlight on
  // after the user leaves the capture screen or the stream is replaced.
  const stopTorch = useCallback((stream: MediaStream | null) => {
    if (!forceFlash || !stream) return;
    const track = stream.getVideoTracks()[0];
    if (!track) return;
    try {
      track
        .applyConstraints({ advanced: [{ torch: false } as MediaTrackConstraintSet] })
        .catch(() => {
          /* best-effort only */
        });
    } catch {
      /* best-effort only -- applyConstraints can throw synchronously too */
    }
  }, [forceFlash]);

  const applyTorch = useCallback((stream: MediaStream) => {
    if (!forceFlash) return;
    const track = stream.getVideoTracks()[0];
    if (!track) return;
    try {
      const capabilities = track.getCapabilities?.();
      if (capabilities && 'torch' in capabilities) {
        track
          .applyConstraints({ advanced: [{ torch: true } as MediaTrackConstraintSet] })
          .catch(() => {
            /* Silent no-op -- a rejected promise must never surface as an
               error or change the UI (e.g. hardware claims the capability
               but refuses the constraint). */
          });
      }
      // No 'torch' capability (most notably iOS Safari, which exposes no
      // torch/flash web API at all) -- silent no-op, camera behaves exactly
      // as it does today.
    } catch {
      /* Silent no-op -- getCapabilities()/applyConstraints() can throw
         synchronously on some browsers; must never break capture. */
    }
  }, [forceFlash]);

  // Acquire-or-reattach: runs on mount and every time the viewfinder is
  // shown again (preview -> null, i.e. Retake or the error screen's fresh
  // remount). Reuses the existing stream when it's still live; only calls
  // getUserMedia again if there is no stream yet or its track died (some
  // mobile browsers kill the track while the tab is backgrounded).
  useEffect(() => {
    if (preview !== null) return;
    let cancelled = false;

    const existingStream = streamRef.current;
    const existingTrack = existingStream?.getVideoTracks()[0];
    if (existingStream && existingTrack && existingTrack.readyState === 'live') {
      if (videoRef.current) videoRef.current.srcObject = existingStream;
      setCameraReady(true);
      return;
    }

    // Stream missing or dead -- replace it. Turn off torch + stop tracks on
    // whatever we had first (Task 8: never leave a stale stream's
    // flashlight on), then reacquire.
    if (existingStream) {
      stopTorch(existingStream);
      existingStream.getTracks().forEach((tr) => tr.stop());
      streamRef.current = null;
    }

    navigator.mediaDevices
      ?.getUserMedia({ video: { facingMode: 'environment' } })
      .then((stream) => {
        if (cancelled) {
          stopTorch(stream);
          stream.getTracks().forEach((tr) => tr.stop());
          return;
        }
        streamRef.current = stream;
        if (videoRef.current) videoRef.current.srcObject = stream;
        setCameraReady(true);
        setCameraDenied(false);
        applyTorch(stream);
      })
      .catch(() => {
        if (!cancelled) setCameraDenied(true);
      });

    return () => {
      cancelled = true;
    };
  }, [preview, applyTorch, stopTorch]);

  // Unmount-only cleanup -- stop the stream and (Task 8) turn off torch.
  useEffect(() => {
    return () => {
      stopTorch(streamRef.current);
      streamRef.current?.getTracks().forEach((tr) => tr.stop());
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Task 3: track the video's real aspect ratio so the container is honest
  // (no fixed 16:9 crop) and reflows on rotation.
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const updateAspect = () => {
      if (video.videoWidth && video.videoHeight) {
        setVideoAspect(video.videoWidth / video.videoHeight);
      }
    };
    video.addEventListener('loadedmetadata', updateAspect);
    window.addEventListener('resize', updateAspect);
    window.addEventListener('orientationchange', updateAspect);
    updateAspect();

    return () => {
      video.removeEventListener('loadedmetadata', updateAspect);
      window.removeEventListener('resize', updateAspect);
      window.removeEventListener('orientationchange', updateAspect);
    };
  }, [preview]);

  const capture = useCallback(() => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx?.drawImage(video, 0, 0, canvas.width, canvas.height);
    canvas.toBlob((blob) => {
      if (blob) setPreview({ blob, url: URL.createObjectURL(blob) });
    }, 'image/jpeg', 0.92);
  }, []);

  const retake = useCallback(() => {
    if (preview) URL.revokeObjectURL(preview.url);
    setPreview(null);
  }, [preview]);

  const handleFile = useCallback((file: File) => {
    setPreview({ blob: file, url: URL.createObjectURL(file) });
  }, []);

  if (preview) {
    return (
      <div className="space-y-4">
        <div className="rounded-2xl overflow-hidden border border-slate-200 bg-slate-50">
          <img src={preview.url} alt={t('camera.capturedPreviewAlt')} className="w-full max-h-96 object-contain" />
        </div>
        <div className="flex items-center justify-center gap-3">
          <Button variant="secondary" onClick={retake}>
            <RefreshCw className="h-4 w-4" />
            {t('camera.retake')}
          </Button>
          <Button onClick={() => onConfirm(preview.blob, preview.url)}>
            <Check className="h-4 w-4" />
            {t('camera.confirm')}
          </Button>
        </div>
      </div>
    );
  }

  if (cameraDenied) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 p-10 rounded-2xl border-2 border-dashed border-slate-200 bg-slate-50 text-center">
        <p className="text-sm text-slate-500 max-w-sm">{t('camera.deniedMessage')}</p>
        <Button onClick={() => fileInputRef.current?.click()} size="lg">
          <Upload className="h-4 w-4" />
          {t('camera.uploadAPhoto')}
        </Button>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          className="hidden"
          onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
        />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* maxWidth pairs with max-h-[70vh]: clamping only the height while
          w-full held the width broke the aspect ratio at desktop widths (a
          4:3 camera rendered in a 1.65 box, letterboxed with navy bars).
          Bounding the width by the same 70vh times the video's own ratio
          lets the box shrink instead of distort, so the frame matches the
          camera at every width. */}
      <div
        className="relative rounded-2xl overflow-hidden border border-slate-200 bg-slate-900 w-full max-h-[70vh] mx-auto"
        style={{ aspectRatio: videoAspect, maxWidth: `calc(70vh * ${videoAspect})` }}
      >
        <video ref={videoRef} autoPlay playsInline muted className="w-full h-full object-contain" />
        {!cameraReady && (
          <div className="absolute inset-0 flex items-center justify-center text-white/70 text-sm">
            {t('camera.startingCamera')}
          </div>
        )}
      </div>
      <canvas ref={canvasRef} className="hidden" />
      <div className="flex items-center justify-center">
        <button
          type="button"
          onClick={capture}
          disabled={!cameraReady}
          aria-label={label}
          className="h-16 w-16 min-h-[44px] min-w-[44px] rounded-full bg-teal-600 hover:bg-teal-700 disabled:opacity-50 text-white flex items-center justify-center shadow-lg transition-colors"
        >
          <Camera className="h-7 w-7" />
        </button>
      </div>
      <p className="text-center text-xs text-slate-400">
        {t('camera.or')}{' '}
        <button type="button" onClick={() => fileInputRef.current?.click()} className="text-teal-600 hover:underline">
          {t('camera.uploadInstead')}
        </button>
      </p>
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
      />
    </div>
  );
}
