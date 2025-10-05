export interface LocationData {
  latitude: number;
  longitude: number;
  city?: string;
  country?: string;
  error?: string;
}

export const getCurrentLocation = (): Promise<LocationData> => {
  return new Promise((resolve) => {
    if (!navigator.geolocation) {
      resolve({
        latitude: 0,
        longitude: 0,
        error: 'Geolocation is not supported by this browser.'
      });
      return;
    }

    navigator.geolocation.getCurrentPosition(
      async (position) => {
        const { latitude, longitude } = position.coords;
        
        try {
          // Reverse geocoding to get city and country
          const response = await fetch(
            `https://api.bigdatacloud.net/data/reverse-geocode-client?latitude=${latitude}&longitude=${longitude}&localityLanguage=en`
          );
          
          if (response.ok) {
            const data = await response.json();
            resolve({
              latitude,
              longitude,
              city: data.city || data.locality,
              country: data.countryName
            });
          } else {
            resolve({
              latitude,
              longitude,
              city: 'Unknown',
              country: 'Unknown'
            });
          }
        } catch (error) {
          resolve({
            latitude,
            longitude,
            city: 'Unknown',
            country: 'Unknown'
          });
        }
      },
      (error) => {
        let errorMessage = 'Unable to retrieve your location.';
        
        switch (error.code) {
          case error.PERMISSION_DENIED:
            errorMessage = 'Location access denied by user.';
            break;
          case error.POSITION_UNAVAILABLE:
            errorMessage = 'Location information is unavailable.';
            break;
          case error.TIMEOUT:
            errorMessage = 'Location request timed out.';
            break;
        }
        
        resolve({
          latitude: 0,
          longitude: 0,
          error: errorMessage
        });
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 300000 // 5 minutes
      }
    );
  });
};

export const formatLocation = (location: LocationData): string => {
  if (location.error) {
    return location.error;
  }
  
  if (location.city) {
    return location.city;
  }
  
  return `${location.latitude.toFixed(4)}, ${location.longitude.toFixed(4)}`;
};
