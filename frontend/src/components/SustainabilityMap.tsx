import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { MapPin, Leaf, TrendingUp } from "lucide-react";
import { getCurrentLocation, LocationData } from "@/utils/locationUtils";
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

// Fix for default markers in react-leaflet
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png",
  iconUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png",
  shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png",
});

interface MapLocation {
  id: string;
  name: string;
  latitude: number;
  longitude: number;
  sustainabilityScore: number;
  isCurrentLocation: boolean;
  address?: string;
}

interface SustainabilityMapProps {
  currentSustainabilityScore: number;
}

// Boston area coordinates for generating nearby locations
const BOSTON_CENTER = {
  latitude: 42.3601,
  longitude: -71.0589
};

const BOSTON_LOCATIONS = [
  { name: "Back Bay", latitude: 42.3503, longitude: -71.0743 },
  { name: "North End", latitude: 42.3647, longitude: -71.0542 },
  { name: "South End", latitude: 42.3431, longitude: -71.0683 },
  { name: "Beacon Hill", latitude: 42.3587, longitude: -71.0672 },
  { name: "Downtown", latitude: 42.3551, longitude: -71.0656 },
  { name: "Fenway", latitude: 42.3467, longitude: -71.0972 },
  { name: "Cambridge", latitude: 42.3736, longitude: -71.1097 },
  { name: "Somerville", latitude: 42.3876, longitude: -71.0995 },
];

export const SustainabilityMap = ({ currentSustainabilityScore }: SustainabilityMapProps) => {
  const [userLocation, setUserLocation] = useState<LocationData | null>(null);
  const [mapLocations, setMapLocations] = useState<MapLocation[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Generate random sustainability scores for other locations
  const generateRandomScore = (baseScore: number) => {
    const variation = Math.random() * 20 - 10; // ±10 points variation
    return Math.max(0, Math.min(100, Math.round(baseScore + variation)));
  };

  // Get user location and generate nearby locations
  useEffect(() => {
    const initializeMap = async () => {
      try {
        const locationData = await getCurrentLocation();
        if (locationData.error) {
          // Fallback to Boston center if location access fails
          const fallbackLocation: LocationData = {
            latitude: BOSTON_CENTER.latitude,
            longitude: BOSTON_CENTER.longitude,
            city: "Boston",
            country: "United States"
          };
          setUserLocation(fallbackLocation);
          generateMapLocations(fallbackLocation);
        } else {
          setUserLocation(locationData);
          generateMapLocations(locationData);
        }
      } catch (error) {
        console.error('Error initializing map:', error);
        // Fallback to Boston center
        const fallbackLocation: LocationData = {
          latitude: BOSTON_CENTER.latitude,
          longitude: BOSTON_CENTER.longitude,
          city: "Boston",
          country: "United States"
        };
        setUserLocation(fallbackLocation);
        generateMapLocations(fallbackLocation);
      } finally {
        setIsLoading(false);
      }
    };

    initializeMap();
  }, []);

  // Update current location's sustainability score when it changes
  useEffect(() => {
    if (mapLocations.length > 0) {
      setMapLocations(prev => 
        prev.map(location => 
          location.isCurrentLocation 
            ? { ...location, sustainabilityScore: currentSustainabilityScore }
            : location
        )
      );
    }
  }, [currentSustainabilityScore, mapLocations.length]);

  const generateMapLocations = (userLocationData: LocationData) => {
    const locations: MapLocation[] = [];

    // Add current user location with dynamic sustainability score
    locations.push({
      id: 'current',
      name: 'Your Location',
      latitude: userLocationData.latitude,
      longitude: userLocationData.longitude,
      sustainabilityScore: currentSustainabilityScore,
      isCurrentLocation: true,
      address: userLocationData.city ? `${userLocationData.city}, MA` : 'Boston, MA'
    });

    // Add Somerville and Beacon Hill with random percentages
    const fixedLocations = [
      { name: "Somerville", latitude: 42.3876, longitude: -71.0995 },
      { name: "Beacon Hill", latitude: 42.3587, longitude: -71.0672 }
    ];

    fixedLocations.forEach((location, index) => {
      locations.push({
        id: `nearby-${index}`,
        name: location.name,
        latitude: location.latitude,
        longitude: location.longitude,
        sustainabilityScore: generateRandomScore(50), // Random score around 50%
        isCurrentLocation: false,
        address: `${location.name}, Boston, MA`
      });
    });

    setMapLocations(locations);
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return "text-green-600 bg-green-50 border-green-200";
    if (score >= 60) return "text-yellow-600 bg-yellow-50 border-yellow-200";
    return "text-red-600 bg-red-50 border-red-200";
  };

  const getScoreBadge = (score: number) => {
    if (score >= 80) return "Excellent";
    if (score >= 60) return "Good";
    if (score >= 40) return "Fair";
    return "Poor";
  };

  // Create custom icons for markers
  const createCustomIcon = (score: number, isCurrentLocation: boolean) => {
    const color = score >= 80 ? "green" : score >= 60 ? "orange" : "red";
    const size = isCurrentLocation ? 40 : 30;
    
    return L.divIcon({
      className: 'custom-marker',
      html: `
        <div style="
          width: ${size}px; 
          height: ${size}px; 
          background-color: ${color}; 
          border: 3px solid white; 
          border-radius: 50%; 
          display: flex; 
          align-items: center; 
          justify-content: center; 
          font-size: 12px; 
          font-weight: bold; 
          color: white; 
          box-shadow: 0 2px 4px rgba(0,0,0,0.3);
          ${isCurrentLocation ? 'animation: pulse 2s infinite;' : ''}
        ">
          ${score}%
        </div>
      `,
      iconSize: [size, size],
      iconAnchor: [size/2, size/2]
    });
  };

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MapPin className="w-5 h-5 text-blue-500" />
            Sustainability Map
          </CardTitle>
          <CardDescription>
            Loading your local sustainability data...
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <MapPin className="w-5 h-5 text-blue-500" />
          Sustainability Map
        </CardTitle>
        <CardDescription>
          Local sustainability scores around your area
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* Interactive Map */}
          <div className="rounded-lg border border-border overflow-hidden min-h-[400px]">
            {mapLocations.length > 0 && (
              <MapContainer
                center={[userLocation?.latitude || BOSTON_CENTER.latitude, userLocation?.longitude || BOSTON_CENTER.longitude]}
                zoom={13}
                style={{ height: '400px', width: '100%' }}
                className="z-0"
              >
                <TileLayer
                  attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />
                
                {mapLocations.map((location) => (
                  <Marker
                    key={location.id}
                    position={[location.latitude, location.longitude]}
                    icon={createCustomIcon(location.sustainabilityScore, location.isCurrentLocation)}
                  >
                    <Popup>
                      <div className="p-2 min-w-[200px]">
                        <div className="flex items-center gap-2 mb-2">
                          <h3 className="font-semibold text-gray-900">{location.name}</h3>
                          {location.isCurrentLocation && (
                            <Badge variant="secondary" className="text-xs">Current</Badge>
                          )}
                        </div>
                        <p className="text-sm text-gray-600 mb-2">{location.address}</p>
                        <div className="flex items-center justify-between">
                          <div className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium border ${getScoreColor(location.sustainabilityScore)}`}>
                            <Leaf className="w-3 h-3" />
                            {location.sustainabilityScore}%
                          </div>
                          <span className="text-xs text-gray-500">{getScoreBadge(location.sustainabilityScore)}</span>
                        </div>
                        <p className="text-xs text-gray-400 mt-2">
                          {location.latitude.toFixed(4)}, {location.longitude.toFixed(4)}
                        </p>
                      </div>
                    </Popup>
                  </Marker>
                ))}
              </MapContainer>
            )}
          </div>

          {/* Location Details */}
          <div className="grid gap-3">
            {mapLocations.map((location) => (
              <div
                key={location.id}
                className={`flex items-center justify-between p-4 rounded-lg border transition-colors ${
                  location.isCurrentLocation 
                    ? 'bg-primary/5 border-primary/20' 
                    : 'bg-card border-border hover:border-primary/20'
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className={`w-3 h-3 rounded-full ${
                    location.isCurrentLocation ? 'bg-blue-500' : 'bg-green-500'
                  }`} />
                  <div>
                    <div className="flex items-center gap-2">
                      <h4 className="font-medium text-foreground">{location.name}</h4>
                      {location.isCurrentLocation && (
                        <Badge variant="secondary" className="text-xs">Current</Badge>
                      )}
                    </div>
                    <p className="text-sm text-muted-foreground">{location.address}</p>
                    <p className="text-xs text-muted-foreground">
                      {location.latitude.toFixed(4)}, {location.longitude.toFixed(4)}
                    </p>
                  </div>
                </div>
                
                <div className="text-right">
                  <div className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium border ${getScoreColor(location.sustainabilityScore)}`}>
                    <Leaf className="w-3 h-3" />
                    {location.sustainabilityScore}%
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    {getScoreBadge(location.sustainabilityScore)}
                  </p>
                </div>
              </div>
            ))}
          </div>

          {/* Map Legend */}
          <div className="flex items-center justify-between text-xs text-muted-foreground pt-4 border-t border-border">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-1">
                <div className="w-3 h-3 rounded-full bg-blue-500" />
                <span>Your Location</span>
              </div>
              <div className="flex items-center gap-1">
                <div className="w-3 h-3 rounded-full bg-green-500" />
                <span>Nearby Areas</span>
              </div>
            </div>
            <div className="flex items-center gap-1">
              <TrendingUp className="w-3 h-3" />
              <span>Scores update dynamically</span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
