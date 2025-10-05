import { useEffect, useRef, useState } from "react";
import { Video, VideoOff } from "lucide-react";
import { Card } from "@/components/ui/card";
import { toast } from "sonner";

interface GlassesVideoFeedProps {
  isActive: boolean;
}

export const GlassesVideoFeed = ({ isActive }: GlassesVideoFeedProps) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [hasCamera, setHasCamera] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamError, setStreamError] = useState<string | null>(null);
  const [localStream, setLocalStream] = useState<MediaStream | null>(null);
  const [isInitializing, setIsInitializing] = useState(false);
  const initTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (isActive) {
      // Add a small delay to ensure the video element is rendered
      initTimeoutRef.current = setTimeout(() => {
        startLocalCamera();
      }, 100);
      
      return () => {
        if (initTimeoutRef.current) {
          clearTimeout(initTimeoutRef.current);
          initTimeoutRef.current = null;
        }
      };
    } else {
      stopLocalCamera();
    }

    return () => {
      stopLocalCamera();
      if (initTimeoutRef.current) {
        clearTimeout(initTimeoutRef.current);
        initTimeoutRef.current = null;
      }
    };
  }, [isActive]);

  const startLocalCamera = async () => {
    // Prevent multiple simultaneous initialization attempts
    if (isInitializing) {
      console.log('Camera initialization already in progress');
      return;
    }

    setIsInitializing(true);
    setIsStreaming(false);
    setStreamError(null);
    
    try {
      console.log('Starting local camera...');
      
      // Set a timeout for the entire camera initialization process
      const cameraTimeout = setTimeout(() => {
        console.error('Camera initialization timeout');
        setStreamError('Camera initialization timed out. Please try again.');
        setIsInitializing(false);
        setIsStreaming(false);
        toast.error('Camera Timeout', {
          description: 'Camera took too long to initialize. Please try again.'
        });
      }, 10000); // 10 second timeout
      
      // First try with environment camera (back camera)
      let stream: MediaStream;
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: {
            width: { ideal: 640 },
            height: { ideal: 480 },
            frameRate: { ideal: 30 },
            facingMode: 'environment'
          },
          audio: false
        });
        console.log('Back camera accessed successfully');
      } catch (environmentError) {
        console.log('Back camera not available, trying user camera:', environmentError);
        // Fallback to user camera (front camera) or any available camera
        stream = await navigator.mediaDevices.getUserMedia({
          video: {
            width: { ideal: 640 },
            height: { ideal: 480 },
            frameRate: { ideal: 30 }
          },
          audio: false
        });
        console.log('Front camera accessed successfully');
      }

      // Clear the timeout since we got the stream
      clearTimeout(cameraTimeout);

      setLocalStream(stream);
      setHasCamera(true);

      // Wait for video element to be available with retry logic
      const waitForVideoElement = (retries = 0) => {
        if (videoRef.current) {
          console.log('Video element found, assigning stream');
          videoRef.current.srcObject = stream;
          
          // Wait for the video to load metadata before marking as streaming
          const handleLoadedMetadata = async () => {
            console.log('Video metadata loaded');
            
            if (videoRef.current) {
              videoRef.current.removeEventListener('loadedmetadata', handleLoadedMetadata);
              
              // Ensure video plays
              try {
                await videoRef.current.play();
                console.log('Video play() successful');
                setIsStreaming(true);
                setIsInitializing(false);
              } catch (playError) {
                console.error('Video play() failed:', playError);
                setIsStreaming(true); // Still show video even if play fails
                setIsInitializing(false);
              }
            }
          };

          videoRef.current.addEventListener('loadedmetadata', handleLoadedMetadata);
          
          // Fallback: if metadata doesn't load within 5 seconds, force streaming state
          setTimeout(() => {
            if (isInitializing) {
              console.log('Video metadata timeout, forcing streaming state');
              setIsStreaming(true);
              setIsInitializing(false);
              if (videoRef.current) {
                videoRef.current.removeEventListener('loadedmetadata', handleLoadedMetadata);
              }
            }
          }, 5000);
          
          console.log('Camera stream assigned to video element');
        } else if (retries < 10) {
          console.log(`Video element not available, retrying... (${retries + 1}/10)`);
          setTimeout(() => waitForVideoElement(retries + 1), 200);
        } else {
          console.error('Video element not available after 10 retries');
          setStreamError('Video element not available. Please refresh the page.');
          setIsInitializing(false);
        }
      };

      waitForVideoElement();

    } catch (error) {
      console.error('Error accessing camera:', error);
      let errorMessage = 'Unknown error';
      
      if (error instanceof Error) {
        errorMessage = error.message;
        
        // Provide more specific error messages
        if (error.name === 'NotAllowedError') {
          errorMessage = 'Camera access denied. Please allow camera permissions.';
        } else if (error.name === 'NotFoundError') {
          errorMessage = 'No camera found on this device.';
        } else if (error.name === 'NotReadableError') {
          errorMessage = 'Camera is already in use by another application.';
        } else if (error.name === 'OverconstrainedError') {
          errorMessage = 'Camera constraints cannot be satisfied.';
        }
      }
      
      setStreamError(`Camera access error: ${errorMessage}`);
      setIsStreaming(false);
      setHasCamera(false);
      setIsInitializing(false);
      
      // Clear any pending timeouts
      if (cameraTimeout) {
        clearTimeout(cameraTimeout);
      }
      
      toast.error('Camera Access Error', {
        description: errorMessage
      });
    }
  };

  const stopLocalCamera = () => {
    if (localStream) {
      console.log('Stopping local camera...');
      localStream.getTracks().forEach(track => {
        track.stop();
        console.log('Stopped track:', track.kind);
      });
      setLocalStream(null);
    }
    
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    
    setIsStreaming(false);
    setHasCamera(false);
    setStreamError(null);
    setIsInitializing(false);
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
              <span className="text-xs text-muted-foreground">Camera Active</span>
            </div>
          )}
          {isActive && isInitializing && (
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-yellow-500 rounded-full animate-pulse" />
              <span className="text-xs text-muted-foreground">Starting...</span>
            </div>
          )}
          {isActive && !isStreaming && !isInitializing && streamError && (
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-red-500 rounded-full" />
              <span className="text-xs text-muted-foreground">Error</span>
            </div>
          )}
        </div>
      </div>

      <div className="relative bg-black aspect-[3.2/6] flex items-center justify-center">
        {isActive ? (
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            className="w-full h-full object-cover"
            style={{ maxWidth: '100%', maxHeight: '100%', opacity: isStreaming ? 1 : 0 }}
            onLoadedData={() => console.log('Video data loaded')}
            onCanPlay={() => console.log('Video can play')}
            onPlay={() => console.log('Video started playing')}
            onError={(e) => console.error('Video error:', e)}
          />
        ) : null}
        
        {!isActive ? (
          <div className="text-center p-6">
            <VideoOff className="w-16 h-16 text-muted-foreground mx-auto mb-4 opacity-50" />
            <p className="text-sm text-muted-foreground">
              Enable glasses sync to view camera
            </p>
          </div>
        ) : isInitializing ? (
          <div className="absolute inset-0 flex items-center justify-center bg-black/80">
            <div className="text-center p-6">
              <div className="w-12 h-12 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
              <p className="text-sm text-white">Starting camera...</p>
              <p className="text-xs text-gray-400 mt-2">This may take a few seconds</p>
            </div>
          </div>
        ) : isActive && !isStreaming && streamError ? (
          <div className="absolute inset-0 flex items-center justify-center bg-black/80">
            <div className="text-center p-6">
              <VideoOff className="w-12 h-12 text-red-500 mx-auto mb-3" />
              <p className="text-sm text-white mb-2">Camera Error</p>
              <p className="text-xs text-red-300">{streamError}</p>
              <button
                onClick={() => {
                  setStreamError(null);
                  startLocalCamera();
                }}
                className="mt-4 px-4 py-2 bg-blue-600 text-white rounded text-xs hover:bg-blue-700"
              >
                Try Again
              </button>
            </div>
          </div>
        ) : null}
      </div>
    </Card>
  );
};

