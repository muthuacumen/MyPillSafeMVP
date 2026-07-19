import { useCallback, useEffect, useRef, useState } from 'react';
import { Camera, RefreshCw, Upload, Check } from 'lucide-react';
import { Button } from '@/components/ui/Button';

interface CameraCaptureProps {
  onConfirm: (blob: Blob, previewUrl: string) => void;
  captureLabel?: string;
}

/** getUserMedia viewfinder with capture/confirm/retake, falling back to file upload
 * when camera access is denied or unavailable (Priority 1D, point 9). */
export function CameraCapture({ onConfirm, captureLabel = 'Capture' }: CameraCaptureProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const [cameraReady, setCameraReady] = useState(false);
  const [cameraDenied, setCameraDenied] = useState(false);
  const [preview, setPreview] = useState<{ blob: Blob; url: string } | null>(null);

  useEffect(() => {
    let active = true;
    navigator.mediaDevices
      ?.getUserMedia({ video: { facingMode: 'environment' } })
      .then((stream) => {
        if (!active) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
        setCameraReady(true);
      })
      .catch(() => {
        if (active) setCameraDenied(true);
      });

    return () => {
      active = false;
      streamRef.current?.getTracks().forEach((t) => t.stop());
    };
  }, []);

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
          <img src={preview.url} alt="Captured photo preview" className="w-full max-h-96 object-contain" />
        </div>
        <div className="flex items-center justify-center gap-3">
          <Button variant="secondary" onClick={retake}>
            <RefreshCw className="h-4 w-4" />
            Retake
          </Button>
          <Button onClick={() => onConfirm(preview.blob, preview.url)}>
            <Check className="h-4 w-4" />
            Confirm
          </Button>
        </div>
      </div>
    );
  }

  if (cameraDenied) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 p-10 rounded-2xl border-2 border-dashed border-slate-200 bg-slate-50 text-center">
        <p className="text-sm text-slate-500 max-w-sm">
          Camera access was denied or isn&apos;t available. You can upload a photo instead.
        </p>
        <Button onClick={() => fileInputRef.current?.click()} size="lg">
          <Upload className="h-4 w-4" />
          Upload a Photo
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
      <div className="relative rounded-2xl overflow-hidden border border-slate-200 bg-slate-900 aspect-video">
        <video ref={videoRef} autoPlay playsInline muted className="w-full h-full object-cover" />
        {!cameraReady && (
          <div className="absolute inset-0 flex items-center justify-center text-white/70 text-sm">
            Starting camera…
          </div>
        )}
      </div>
      <canvas ref={canvasRef} className="hidden" />
      <div className="flex items-center justify-center">
        <button
          type="button"
          onClick={capture}
          disabled={!cameraReady}
          aria-label={captureLabel}
          className="h-16 w-16 min-h-[44px] min-w-[44px] rounded-full bg-teal-600 hover:bg-teal-700 disabled:opacity-50 text-white flex items-center justify-center shadow-lg transition-colors"
        >
          <Camera className="h-7 w-7" />
        </button>
      </div>
      <p className="text-center text-xs text-slate-400">
        or{' '}
        <button type="button" onClick={() => fileInputRef.current?.click()} className="text-teal-600 hover:underline">
          upload a photo instead
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
