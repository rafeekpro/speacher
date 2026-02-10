import React from 'react';

export interface AudioRecorderSettings {
  provider: string;
  language: string;
  enableDiarization: boolean;
  maxSpeakers: number;
  includeTimestamps: boolean;
  showCost: boolean;
}

export interface CurrentJob {
  id: string;
  fileName: string;
  audioBlob: Blob;
  timestamp: string;
}

export interface AudioRecorderProps {
  onAudioRecorded: (audioBlob: Blob, fileName?: string) => void | Promise<void>;
  isLoading: boolean;
  settings: AudioRecorderSettings;
  currentJob?: CurrentJob | null;
  onJobComplete?: (result: any) => void;
  onJobError?: (error: string) => void;
}

declare const AudioRecorder: React.FC<AudioRecorderProps>;

export default AudioRecorder;