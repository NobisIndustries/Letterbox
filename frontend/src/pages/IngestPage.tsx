import { useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { uploadImages } from "@/api/client";
import { Camera, Images, Mail } from "lucide-react";

interface IngestPageProps {
  onJobCreated: (jobId: string) => void;
}

export function IngestPage({ onJobCreated }: IngestPageProps) {
  const cameraRef = useRef<HTMLInputElement>(null);
  const galleryRef = useRef<HTMLInputElement>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [previews, setPreviews] = useState<string[]>([]);
  const [uploading, setUploading] = useState(false);

  const addFiles = (newFiles: FileList | null) => {
    if (!newFiles) return;
    const arr = Array.from(newFiles);
    setFiles((prev) => [...prev, ...arr]);
    const newPreviews = arr.map((f) => URL.createObjectURL(f));
    setPreviews((prev) => [...prev, ...newPreviews]);
  };

  const removeFile = (index: number) => {
    URL.revokeObjectURL(previews[index]);
    setFiles((prev) => prev.filter((_, i) => i !== index));
    setPreviews((prev) => prev.filter((_, i) => i !== index));
  };

  const handleProcess = async () => {
    if (files.length === 0) return;
    setUploading(true);
    try {
      const res = await uploadImages(files);
      onJobCreated(res.job_id);
      previews.forEach((url) => URL.revokeObjectURL(url));
      setFiles([]);
      setPreviews([]);
    } finally {
      setUploading(false);
    }
  };

  const hasFiles = files.length > 0;

  return (
    <div className="flex flex-col items-center gap-6 p-4 max-w-lg mx-auto">
      {/* Branding */}
      <div className="flex flex-col items-center gap-1 pt-4">
        <div className="flex items-center gap-2">
          <Mail size={28} className="text-primary" />
          <span className="text-2xl font-bold tracking-tight">Letterbox</span>
        </div>
        <p className="text-xs text-muted-foreground tracking-widest uppercase">
          Scan · Extract · Archive
        </p>
      </div>

      {/* Hidden inputs */}
      <input
        ref={cameraRef}
        type="file"
        accept="image/*"
        capture="environment"
        multiple
        className="hidden"
        onChange={(e) => { addFiles(e.target.files); e.target.value = ""; }}
      />
      <input
        ref={galleryRef}
        type="file"
        accept="image/*"
        multiple
        className="hidden"
        onChange={(e) => { addFiles(e.target.files); e.target.value = ""; }}
      />

      {/* Capture buttons */}
      {!hasFiles ? (
        <div className="flex flex-col items-center gap-4 w-full">
          <div className="flex gap-3">
            <Button
              variant="default"
              className="flex flex-col h-20 w-28 gap-1 text-sm"
              onClick={() => cameraRef.current?.click()}
            >
              <Camera size={24} />
              Camera
            </Button>
            <Button
              variant="outline"
              className="flex flex-col h-20 w-28 gap-1 text-sm"
              onClick={() => galleryRef.current?.click()}
            >
              <Images size={24} />
              Gallery
            </Button>
          </div>
          <p className="text-xs text-muted-foreground">Photograph each page of the letter</p>
        </div>
      ) : (
        <>
          {/* Image grid */}
          <div className="grid grid-cols-3 gap-2 w-full max-w-md">
            {previews.map((url, i) => (
              <div key={i} className="relative">
                <img
                  src={url}
                  alt={`Page ${i + 1}`}
                  className="w-full aspect-[3/4] object-cover rounded-md border"
                />
                <button
                  onClick={() => removeFile(i)}
                  className="absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full bg-destructive text-white text-xs"
                >
                  ×
                </button>
              </div>
            ))}
          </div>

          {/* Action row */}
          <div className="flex gap-2 w-full max-w-md">
            <Button
              variant="outline"
              size="sm"
              className="gap-1"
              onClick={() => cameraRef.current?.click()}
            >
              <Camera size={14} /> Camera
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="gap-1"
              onClick={() => galleryRef.current?.click()}
            >
              <Images size={14} /> Gallery
            </Button>
            <Button
              className="flex-1"
              onClick={handleProcess}
              disabled={uploading}
            >
              {uploading
                ? "Uploading..."
                : `Process ${files.length} page${files.length > 1 ? "s" : ""}`}
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
