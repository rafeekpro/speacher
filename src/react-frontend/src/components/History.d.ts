import React from 'react';

export interface TranscriptionHistoryItem {
  id: string;
  text: string;
  provider: string;
  cost?: number;
  processingTime?: number;
  timestamp: string;
  fileName?: string;
  language?: string;
  diarization?: any;
  segments?: Array<{
    text: string;
    start?: number;
    end?: number;
    speaker?: string;
  }>;
}

export interface HistoryProps {
  onSelectTranscription: (transcription: TranscriptionHistoryItem) => void;
}

declare const History: React.FC<HistoryProps>;

export default History;