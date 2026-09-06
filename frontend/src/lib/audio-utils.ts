export const getAudioDuration = (blob: Blob): Promise<number> => {
  return new Promise((resolve) => {
    const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
    const reader = new FileReader();
    
    reader.onload = async function() {
      try {
        const arrayBuffer = this.result as ArrayBuffer;
        const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
        resolve(audioBuffer.duration);
      } catch (e) {
        resolve(0);
      }
    };
    reader.readAsArrayBuffer(blob);
  });
};

export const compressAudio = async (blob: Blob): Promise<Blob> => {
  // Simple placeholder for compression if needed
  // In a real scenario, could use something like recorder-js or encode to lower bitrate WebM
  return blob;
};
