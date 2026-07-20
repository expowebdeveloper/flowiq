import { useEffect, useRef, useState } from "react"
import { Camera, RefreshCw, Upload, X } from "lucide-react"
import { Button } from "@/components/ui/button"

interface SelfieCaptureProps {
  file: File | null
  onChange: (file: File | null) => void
}

export function SelfieCapture({ file, onChange }: SelfieCaptureProps) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const [cameraActive, setCameraActive] = useState(false)
  const [cameraError, setCameraError] = useState<string | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)

  useEffect(() => {
    if (!file) {
      setPreviewUrl(null)
      return
    }
    const url = URL.createObjectURL(file)
    setPreviewUrl(url)
    return () => URL.revokeObjectURL(url)
  }, [file])

  useEffect(() => {
    return () => {
      streamRef.current?.getTracks().forEach((t) => t.stop())
    }
  }, [])

  // The <video> element only mounts once cameraActive is true, so the stream
  // can't be attached inside startCamera() itself (the ref is still null at
  // that point) — attach it here once the element actually exists in the DOM.
  useEffect(() => {
    if (cameraActive && videoRef.current && streamRef.current) {
      videoRef.current.srcObject = streamRef.current
      videoRef.current.play().catch(() => {})
    }
  }, [cameraActive])

  async function startCamera() {
    setCameraError(null)
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user" } })
      streamRef.current = stream
      setCameraActive(true)
    } catch {
      setCameraError("Could not access camera. You can upload a photo instead.")
    }
  }

  function stopCamera() {
    streamRef.current?.getTracks().forEach((t) => t.stop())
    streamRef.current = null
    setCameraActive(false)
  }

  function capturePhoto() {
    const video = videoRef.current
    const canvas = canvasRef.current
    if (!video || !canvas) return

    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    const ctx = canvas.getContext("2d")
    ctx?.drawImage(video, 0, 0, canvas.width, canvas.height)

    canvas.toBlob((blob) => {
      if (!blob) return
      onChange(new File([blob], "selfie.jpg", { type: "image/jpeg" }))
    }, "image/jpeg", 0.9)

    stopCamera()
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const selected = e.target.files?.[0]
    if (selected) onChange(selected)
  }

  function retake() {
    onChange(null)
    startCamera()
  }

  if (previewUrl) {
    return (
      <div className="space-y-2">
        <div className="relative mx-auto w-fit overflow-hidden rounded-full border-2 border-border">
          <img src={previewUrl} alt="Selfie preview" className="size-32 object-cover" />
          <button
            type="button"
            onClick={() => onChange(null)}
            className="absolute right-1 top-1 rounded-full bg-background/80 p-1 text-muted-foreground hover:text-destructive"
            aria-label="Remove selfie"
          >
            <X className="size-4" />
          </button>
        </div>
        <div className="flex justify-center">
          <Button type="button" variant="outline" size="sm" onClick={retake}>
            <RefreshCw className="size-3.5" /> Retake
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {cameraActive ? (
        <div className="mx-auto w-fit space-y-2 text-center">
          <video
            ref={videoRef}
            className="mx-auto size-48 rounded-full border-2 border-border object-cover"
            muted
            playsInline
          />
          <canvas ref={canvasRef} className="hidden" />
          <div className="flex justify-center gap-2">
            <Button type="button" size="sm" onClick={capturePhoto}>
              <Camera className="size-3.5" /> Capture
            </Button>
            <Button type="button" variant="outline" size="sm" onClick={stopCamera}>
              Cancel
            </Button>
          </div>
        </div>
      ) : (
        <div className="flex flex-col items-center gap-2">
          <div className="flex size-32 items-center justify-center rounded-full border-2 border-dashed border-border text-muted-foreground">
            <Camera className="size-8" />
          </div>
          <div className="flex gap-2">
            <Button type="button" variant="outline" size="sm" onClick={startCamera}>
              <Camera className="size-3.5" /> Use camera
            </Button>
            <Button type="button" variant="outline" size="sm" onClick={() => fileInputRef.current?.click()}>
              <Upload className="size-3.5" /> Upload photo
            </Button>
          </div>
          {cameraError && <p className="text-xs text-destructive">{cameraError}</p>}
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={handleFileChange}
            className="hidden"
          />
        </div>
      )}
    </div>
  )
}
