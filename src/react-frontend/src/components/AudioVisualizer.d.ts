import React from 'react';

export interface AudioVisualizerProps {
  stream: MediaStream | null;
}

declare const AudioVisualizer: React.FC<AudioVisualizerProps>;

export default AudioVisualizer;