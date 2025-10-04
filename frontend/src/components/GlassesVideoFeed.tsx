import { useEffect, useRef, useState } from "react";
import { Video, VideoOff } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

interface GlassesVideoFeedProps {
  isActive: boolean;
}

export const GlassesVideoFeed = ({ isActive }: GlassesVideoFeedProps) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [hasCamera, setHasCamera] = useState(false);

  useEffect(() => {
    if (isActive && videoRef.current) {
      startCamera();
    } else {
      stopCamera();
    }

    return () => stopCamera();
  }, [isActive]);

  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: 'environment',
          aspectRatio: 9 / 16 // Portrait mode
        },
        audio: false
      });

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        setHasCamera(true);
      }
    } catch (error) {
      console.error('Error accessing camera:', error);
      toast.error("Camera access denied", {
        description: "Please allow camera access to use this feature"
      });
      setHasCamera(false);
    }
  };

  const stopCamera = () => {
    if (videoRef.current && videoRef.current.srcObject) {
      const stream = videoRef.current.srcObject as MediaStream;
      stream.getTracks().forEach(track => track.stop());
      videoRef.current.srcObject = null;
      setHasCamera(false);
    }
  };

  return (
    <Card className="overflow-hidden bg-card shadow-card h-full">
      <div className="p-4 border-b border-border bg-gradient-card">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {isActive ? (
              <Video className="w-5 h-5 text-primary" />
            ) : (
              <VideoOff className="w-5 h-5 text-muted-foreground" />
            )}
            <h3 className="font-semibold text-foreground">Glasses View</h3>
          </div>
          {isActive && (
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-destructive rounded-full animate-pulse" />
              <span className="text-xs text-muted-foreground">Live</span>
            </div>
          )}
        </div>
      </div>

      <div className="relative bg-black aspect-[9/16] flex items-center justify-center">
        {isActive ? (
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="text-center p-6">
            <VideoOff className="w-16 h-16 text-muted-foreground mx-auto mb-4 opacity-50" />
            <p className="text-sm text-muted-foreground">
              Enable glasses sync to view camera feed
            </p>
          </div>
        )}

        {isActive && !hasCamera && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/80">
            <div className="text-center p-6">
              <VideoOff className="w-12 h-12 text-muted-foreground mx-auto mb-3" />
              <p className="text-sm text-white">Camera not accessible</p>
            </div>
          </div>
        )}
      </div>
    </Card>
  );
};
