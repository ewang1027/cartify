/**
 * Utility functions for audio playback
 */

export const playAudioFromBase64 = (base64Audio: string): Promise<void> => {
  return new Promise((resolve, reject) => {
    try {
      // Convert base64 to blob
      const byteCharacters = atob(base64Audio);
      const byteNumbers = new Array(byteCharacters.length);
      
      for (let i = 0; i < byteCharacters.length; i++) {
        byteNumbers[i] = byteCharacters.charCodeAt(i);
      }
      
      const byteArray = new Uint8Array(byteNumbers);
      const blob = new Blob([byteArray], { type: 'audio/mpeg' });
      
      // Create audio element and play
      const audio = new Audio();
      audio.src = URL.createObjectURL(blob);
      
      audio.onended = () => {
        URL.revokeObjectURL(audio.src);
        resolve();
      };
      
      audio.onerror = () => {
        URL.revokeObjectURL(audio.src);
        reject(new Error('Audio playback failed'));
      };
      
      audio.play().catch(reject);
    } catch (error) {
      reject(error);
    }
  });
};

export const fetchSustainabilityComment = async (preference: 'low' | 'medium' | 'high') => {
  try {
    const response = await fetch('http://localhost:5002/api/sustainability-comment', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ preference }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error fetching sustainability comment:', error);
    throw error;
  }
};
