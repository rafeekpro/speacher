export interface TranscribeAudioOptions {
  file: Blob;
  provider: string;
  language: string;
  enable_diarization: string;
  max_speakers: string;
  include_timestamps: string;
}

export interface TranscribeResult {
  text: string;
  segments?: any[];
  [key: string]: any;
}

export interface AsyncTranscribeResponse {
  job_id: string;
}

export function transcribeAudio(formData: FormData): Promise<TranscribeResult>;
export function transcribeAudioAsync(formData: FormData): Promise<AsyncTranscribeResponse>;
export function checkHealth(): Promise<{ status: string }>;
