import React from 'react';

export interface AppSettings {
  provider: string;
  language: string;
  enableDiarization: boolean;
  maxSpeakers: number;
  includeTimestamps: boolean;
  showCost: boolean;
}

export interface SettingsProps {
  settings: AppSettings;
  onSettingsChange: (settings: AppSettings) => void;
  onClose: () => void;
}

declare const Settings: React.FC<SettingsProps>;

export default Settings;