import { useEffect, useRef, useState } from "react";
import { Video, VideoOff } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { io, Socket } from "socket.io-client";

interface GlassesVideoFeedProps {
  isActive: boolean;
}

export const GlassesVideoFeed = ({ isActive }: GlassesVideoFeedProps) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [hasCamera, setHasCamera] = useState(false);
  const [socket, setSocket] = useState<Socket | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamError, setStreamError] = useState<string | null>(null);

  useEffect(() => {
    if (isActive) {
      initializeWebSocket();
    } else {
      disconnectWebSocket();
    }

    return () => {
      disconnectWebSocket();
      stopCamera();
    };
  }, [isActive]);

  const initializeWebSocket = () => {
    const newSocket = io('http://localhost:5002');
    
    newSocket.on('connect', () => {
      console.log('Connected to WebSocket server');
      setIsStreaming(true);
      setStreamError(null);
      newSocket.emit('start_stream');
    });

    newSocket.on('disconnect', () => {
      console.log('Disconnected from WebSocket server');
      setIsStreaming(false);
    });

    newSocket.on('video_frame', (data) => {
      displayFrame(data.frame);
    });

    newSocket.on('stream_error', (data) => {
      console.error('Stream error:', data.message);
      setStreamError(data.message);
      toast.error('Streaming error', {
        description: data.message
      });
    });

    newSocket.on('stream_started', (data) => {
      console.log('Stream started:', data.message);
      setIsStreaming(true);
      setStreamError(null);
    });

    newSocket.on('stream_stopped', (data) => {
      console.log('Stream stopped:', data.message);
      setIsStreaming(false);
    });

    setSocket(newSocket);
  };

  const disconnectWebSocket = () => {
    if (socket) {
      socket.emit('stop_stream');
      socket.disconnect();
      setSocket(null);
      setIsStreaming(false);
    }
  };

  const displayFrame = (frameData: string) => {
    if (canvasRef.current) {
      const canvas = canvasRef.current;
      const ctx = canvas.getContext('2d');
      
      if (ctx) {
        const img = new Image();
        img.onload = () => {
          // Set canvas size to match image
          canvas.width = img.width;
          canvas.height = img.height;
          
          // Draw the image
          ctx.drawImage(img, 0, 0);
        };
        img.src = `data:image/jpeg;base64,${frameData}`;
      }
    }
  };

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
          {isActive && isStreaming && (
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              <span className="text-xs text-muted-foreground">Live Stream</span>
            </div>
          )}
          {isActive && !isStreaming && (
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-yellow-500 rounded-full animate-pulse" />
              <span className="text-xs text-muted-foreground">Connecting...</span>
            </div>
          )}
        </div>
      </div>

      <div className="relative bg-black aspect-[9/16] flex items-center justify-center">
        {isActive && isStreaming ? (
          <canvas
            ref={canvasRef}
            className="w-full h-full object-cover"
            style={{ maxWidth: '100%', maxHeight: '100%' }}
          />
        ) : isActive && !isStreaming && streamError ? (
          <div className="absolute inset-0 flex items-center justify-center bg-black/80">
            <div className="text-center p-6">
              <VideoOff className="w-12 h-12 text-red-500 mx-auto mb-3" />
              <p className="text-sm text-white mb-2">Stream Error</p>
              <p className="text-xs text-red-300">{streamError}</p>
            </div>
          </div>
        ) : isActive && !isStreaming ? (
          <div className="absolute inset-0 flex items-center justify-center bg-black/80">
            <div className="text-center p-6">
              <div className="w-12 h-12 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
              <p className="text-sm text-white">Connecting to stream...</p>
            </div>
          </div>
        ) : (
          <div className="text-center p-6">
            <VideoOff className="w-16 h-16 text-muted-foreground mx-auto mb-4 opacity-50" />
            <p className="text-sm text-muted-foreground">
              Enable glasses sync to view stream
            </p>
          </div>
        )}
      </div>
    </Card>
  );
};
