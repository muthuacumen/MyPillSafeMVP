import { useEffect, useState } from 'react';
import { X, Loader2 } from 'lucide-react';
import { prescriptionsApi } from '@/api/prescriptions';

interface Props {
  prescriptionId: string;
  onClose: () => void;
}

export default function PrescriptionImageModal({ prescriptionId, onClose }: Props) {
  const [objectUrl, setObjectUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let url: string | null = null;
    prescriptionsApi
      .getImageBlob(prescriptionId)
      .then(({ data }) => {
        url = URL.createObjectURL(data);
        setObjectUrl(url);
      })
      .catch(() => setError('Could not load the prescription image.'));
    return () => {
      if (url) URL.revokeObjectURL(url);
    };
  }, [prescriptionId]);

  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4" onClick={onClose}>
      <div
        className="bg-white rounded-2xl max-w-2xl w-full max-h-[85vh] overflow-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100">
          <h3 className="font-semibold text-slate-900">Original Prescription</h3>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="h-9 w-9 rounded-lg flex items-center justify-center text-slate-400 hover:bg-slate-100"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="p-4 flex items-center justify-center min-h-[200px]">
          {error && <p className="text-sm text-danger-text">{error}</p>}
          {!error && !objectUrl && <Loader2 className="h-8 w-8 text-teal-600 animate-spin" />}
          {objectUrl && <img src={objectUrl} alt="Prescription label" className="max-w-full rounded-lg" />}
        </div>
      </div>
    </div>
  );
}
