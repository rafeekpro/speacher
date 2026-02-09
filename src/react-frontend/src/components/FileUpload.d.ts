import React from 'react';
import { CurrentJob } from './AudioRecorder';

export interface FileUploadSettings {
  provider: string;
  language: string;
  enableDiarization: boolean;
  maxSpeakers: number;
  includeTimestamps: boolean;
  showCost: boolean;
}

export interface FileUploadProps {
  onFilesUploaded: (audioBlob: Blob, fileName?: string) => void | Promise<void>;
  isLoading: boolean;
  settings: FileUploadSettings;
  currentJob?: CurrentJob | null;
  onJobComplete?: (result: any) => void;
  onJobError?: (error: string) => void;
}

declare const FileUpload: React.FC<FileUploadProps>;

export default FileUpload;