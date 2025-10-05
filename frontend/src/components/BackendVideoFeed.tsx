import { useEffect, useRef, useState } from "react";
import { Video, VideoOff, Wifi, WifiOff } from "lucide-react";
import { Card } from "@/components/ui/card";
import { toast } from "sonner";
import { io, Socket } from "socket.io-client";

interface BackendVideoFeedProps {
  isActive: boolean;
  backendUrl?: string;
}

export const BackendVideoFeed = ({ 
  isActive, 
  backendUrl = "http://localhost:5001" 
}: BackendVideoFeedProps) => {
  const imgRef = useRef<HTMLImageElement>(null);
  const socketRef = useRef<Socket | null>(null);
  
  const [isStreaming, setIsStreaming] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [streamError, setStreamError] = useState<string | null>(null);
  const [isInitializing, setIsInitializing] = useState(false);
  const [frameCount, setFrameCount] = useState(0);
  const [fps, setFps] = useState(0);
  
  const lastFrameTimeRef = useRef<number>(Date.now());
  const frameCountRef = useRef<number>(0);

  useEffect(() => {
    if (isActive) {
      connectToBackend();
    } else {
      disconnectFromBackend();
    }

    return () => {
      disconnectFromBackend();
    };
  }, [isActive, backendUrl]);

  const connectToBackend = () => {
    if (socketRef.current?.connected) {
      console.log('Already connected to backend');
      return;
    }

    setIsInitializing(true);
    setStreamError(null);

    try {
      console.log(`Connecting to backend: ${backendUrl}`);
      
      const socket = io(backendUrl, {
        transports: ['websocket', 'polling'],
        reconnection: true,
        reconnectionDelay: 1000,
        reconnectionAttempts: 5,
      });
      
      socketRef.current = socket;

      // Connection handlers
      socket.on('connect', () => {
        console.log('✅ Connected to backend video stream');
        setIsConnected(true);
        setIsInitializing(false);
        setStreamError(null);
        toast.success('Backend Connected', {
          description: 'Successfully connected to CV2 video stream'
        });
        
        // Request stream to start
        socket.emit('start_stream');
      });

      socket.on('disconnect', (reason) => {
        console.log('🔌 Disconnected from backend:', reason);
        setIsConnected(false);
        setIsStreaming(false);
        
        if (reason === 'io server disconnect') {
          // Server disconnected, try to reconnect
          socket.connect();
        }
      });

      socket.on('connect_error', (error) => {
        console.error('❌ Connection error:', error);
        setStreamError(`Connection failed: ${error.message}`);
        setIsInitializing(false);
        setIsConnected(false);
        
        toast.error('Connection Error', {
          description: 'Failed to connect to backend. Is the server running?'
        });
      });

      // Stream handlers
      socket.on('stream_started', (data: any) => {
        console.log('🎬 Stream started:', data);
        setIsStreaming(true);
        setIsInitializing(false);
        toast.success('Stream Started', {
          description: `Camera ${data.camera_id} - ${data.resolution} @ ${data.fps}fps`
        });
      });

      socket.on('stream_stopped', (data: any) => {
        console.log('🛑 Stream stopped:', data);
        setIsStreaming(false);
      });

      socket.on('stream_error', (data: { message: string }) => {
        console.error('❌ Stream error:', data.message);
        setStreamError(data.message);
        setIsStreaming(false);
        toast.error('Stream Error', {
          description: data.message
        });
      });

      // Video frame handler
      socket.on('video_frame', (data: { frame: string; timestamp: number; frame_count: number }) => {
        if (imgRef.current) {
          imgRef.current.src = `data:image/jpeg;base64,${data.frame}`;
          setFrameCount(data.frame_count);
          
          // Calculate FPS
          frameCountRef.current++;
          const now = Date.now();
          const elapsed = (now - lastFrameTimeRef.current) / 1000;
          
          if (elapsed >= 1.0) {
            const currentFps = frameCountRef.current / elapsed;
            setFps(Math.round(currentFps));
            frameCountRef.current = 0;
            lastFrameTimeRef.current = now;
          }
        }
      });

      socket.on('connection_status', (data: { status: string; streaming: boolean }) => {
        console.log('Connection status:', data);
        setIsConnected(data.status === 'connected');
        setIsStreaming(data.streaming);
      });

    } catch (error) {
      console.error('Error setting up socket connection:', error);
      setStreamError('Failed to initialize connection');
      setIsInitializing(false);
      toast.error('Connection Error', {
        description: 'Failed to initialize socket connection'
      });
    }
  };

  const disconnectFromBackend = () => {
    if (socketRef.current) {
      console.log('Disconnecting from backend...');
      socketRef.current.emit('stop_stream');
      socketRef.current.disconnect();
      socketRef.current = null;
    }
    
    setIsConnected(false);
    setIsStreaming(false);
    setIsInitializing(false);
    setStreamError(null);
    setFrameCount(0);
    setFps(0);
  };

  const handleRetry = () => {
    setStreamError(null);
    disconnectFromBackend();
    setTimeout(() => {
      if (isActive) {
        connectToBackend();
      }
    }, 500);
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
            <h3 className="font-semibold text-foreground">Backend CV2 Feed</h3>
          </div>
          
          <div className="flex items-center gap-3">
            {/* Connection Status */}
            {isActive && (
              <div className="flex items-center gap-2">
                {isConnected ? (
                  <Wifi className="w-4 h-4 text-green-500" />
                ) : (
                  <WifiOff className="w-4 h-4 text-red-500" />
                )}
                <span className="text-xs text-muted-foreground">
                  {isConnected ? 'Connected' : 'Disconnected'}
                </span>
              </div>
            )}
            
            {/* Stream Status */}
            {isActive && isStreaming && (
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                <span className="text-xs text-muted-foreground">
                  Streaming {fps > 0 && `@ ${fps} FPS`}
                </span>
              </div>
            )}
            
            {isActive && isInitializing && (
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-yellow-500 rounded-full animate-pulse" />
                <span className="text-xs text-muted-foreground">Starting...</span>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="relative bg-black aspect-[3.2/6] flex items-center justify-center">
        {isActive ? (
          <img
            ref={imgRef}
            alt="Backend CV2 Stream"
            className="w-full h-full object-cover"
            style={{ 
              display: isStreaming ? 'block' : 'none',
              imageRendering: 'auto'
            }}
          />
        ) : null}
        
        {!isActive ? (
          <div className="text-center p-6">
            <VideoOff className="w-16 h-16 text-muted-foreground mx-auto mb-4 opacity-50" />
            <p className="text-sm text-muted-foreground">
              Enable glasses sync to view backend feed
            </p>
          </div>
        ) : isInitializing ? (
          <div className="absolute inset-0 flex items-center justify-center bg-black/80">
            <div className="text-center p-6">
              <div className="w-12 h-12 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
              <p className="text-sm text-white">Connecting to backend...</p>
              <p className="text-xs text-gray-400 mt-2">{backendUrl}</p>
            </div>
          </div>
        ) : isActive && !isStreaming && streamError ? (
          <div className="absolute inset-0 flex items-center justify-center bg-black/80">
            <div className="text-center p-6 max-w-md">
              <VideoOff className="w-12 h-12 text-red-500 mx-auto mb-3" />
              <p className="text-sm text-white mb-2">Backend Stream Error</p>
              <p className="text-xs text-red-300 mb-4">{streamError}</p>
              <button
                onClick={handleRetry}
                className="px-4 py-2 bg-blue-600 text-white rounded text-xs hover:bg-blue-700 transition-colors"
              >
                Retry Connection
              </button>
              <p className="text-xs text-gray-400 mt-3">
                Make sure video_stream_server.py is running on port 5001
              </p>
            </div>
          </div>
        ) : isActive && isConnected && !isStreaming ? (
          <div className="absolute inset-0 flex items-center justify-center bg-black/80">
            <div className="text-center p-6">
              <div className="w-12 h-12 border-2 border-green-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
              <p className="text-sm text-white">Initializing camera...</p>
            </div>
          </div>
        ) : null}

        {/* Debug Info Overlay (optional) */}
        {isStreaming && fps > 0 && (
          <div className="absolute bottom-2 left-2 bg-black/60 px-2 py-1 rounded text-xs text-white">
            Frames: {frameCount} | FPS: {fps}
          </div>
        )}
      </div>
    </Card>
  );
};
