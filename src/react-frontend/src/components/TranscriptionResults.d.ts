import React from 'react';

export interface Transcription {
  id?: string;
  text: string;
  provider: string;
  cost?: number;
  processingTime?: number;
  timestamp: string;
  fileName?: string;
  audioUrl?: string | null;
  language?: string;
  diarization?: any;
  segments?: Array<{
    text: string;
    start?: number;
    end?: number;
    speaker?: string;
  }>;
}

export interface TranscriptionResultsProps {
  transcriptions: Transcription[];
}

declare const TranscriptionResults: React.FC<TranscriptionResultsProps>;

export default TranscriptionResults;