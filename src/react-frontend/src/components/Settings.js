import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  IconButton,
  Tabs,
  Tab,
  Divider,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Switch,
  FormControlLabel,
  Slider,
  TextField,
  Button,
  Paper
} from '@mui/material';
import {
  X as CloseIcon,
  Settings as SettingsIcon,
  Languages as TranslateIcon,
  Key as KeyIcon,
  SlidersHorizontal as TuneIcon
} from 'lucide-react';
import APIKeysSettings from './APIKeysSettings';

function TabPanel({ children, value, index, ...other }) {
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`settings-tabpanel-${index}`}
      aria-labelledby={`settings-tab-${index}`}
      {...other}
    >
      {value === index && (
        <Box sx={{ py: 2 }}>
          {children}
        </Box>
      )}
    </div>
  );
}

const Settings = ({ settings, onSettingsChange, onClose }) => {
  const [activeTab, setActiveTab] = useState(0);
  const [configuredProviders, setConfiguredProviders] = useState([]);
  
  const languages = [
    { code: 'en-US', name: 'English (US)' },
    { code: 'pl-PL', name: 'Polish' },
    { code: 'de-DE', name: 'German' },
    { code: 'es-ES', name: 'Spanish' },
    { code: 'fr-FR', name: 'French' },
    { code: 'it-IT', name: 'Italian' },
    { code: 'pt-PT', name: 'Portuguese' },
    { code: 'nl-NL', name: 'Dutch' },
    { code: 'ru-RU', name: 'Russian' },
    { code: 'zh-CN', name: 'Chinese' },
    { code: 'ja-JP', name: 'Japanese' },
    { code: 'ko-KR', name: 'Korean' },
    { code: 'ar-SA', name: 'Arabic' },
    { code: 'hi-IN', name: 'Hindi' },
    { code: 'sv-SE', name: 'Swedish' },
    { code: 'da-DK', name: 'Danish' },
    { code: 'fi-FI', name: 'Finnish' },
    { code: 'no-NO', name: 'Norwegian' },
    { code: 'cs-CZ', name: 'Czech' },
    { code: 'tr-TR', name: 'Turkish' }
  ];

  const providers = [
    { value: 'aws', name: 'Amazon Transcribe', color: '#FF9900' },
    { value: 'azure', name: 'Azure Speech Services', color: '#0078D4' },
    { value: 'gcp', name: 'Google Cloud Speech', color: '#4285F4' }
  ];

  useEffect(() => {
    loadConfiguredProviders();
  }, []);

  const loadConfiguredProviders = async () => {
    try {
      const response = await fetch('/api/keys');
      if (response.ok) {
        const providers = await response.json();
        setConfiguredProviders(providers);
      }
    } catch (error) {
      console.error('Failed to load providers:', error);
    }
  };

  const handleChange = (field, value) => {
    onSettingsChange({
      ...settings,
      [field]: value
    });
  };

  return (
    <Box sx={{ width: 400, p: 3 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h5" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <SettingsIcon size={24} />
          Settings
        </Typography>
        <IconButton onClick={onClose}>
          <CloseIcon size={24} />
        </IconButton>
      </Box>
      
      <Divider sx={{ mb: 2 }} />
      
      {/* Tabs */}
      <Tabs 
        value={activeTab} 
        onChange={(e, newValue) => setActiveTab(newValue)}
        variant="fullWidth"
        sx={{ mb: 2 }}
      >
        <Tab icon={<TuneIcon size={20} />} label="General" />
        <Tab icon={<KeyIcon size={20} />} label="API Keys" />
        <Tab icon={<TranslateIcon size={20} />} label="Advanced" />
      </Tabs>
      
      {/* General Settings */}
      <TabPanel value={activeTab} index={0}>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
          {/* Provider Selection */}
          <FormControl fullWidth>
            <InputLabel>Cloud Provider</InputLabel>
            <Select
              value={settings.provider}
              label="Cloud Provider"
              onChange={(e) => handleChange('provider', e.target.value)}
            >
              {providers.map(provider => {
                const providerConfig = configuredProviders.find(p => p.provider === provider.value);
                const isConfigured = providerConfig?.configured && providerConfig?.enabled;
                
                return (
                  <MenuItem 
                    key={provider.value} 
                    value={provider.value}
                    disabled={!isConfigured}
                  >
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, width: '100%' }}>
                      <Box
                        sx={{
                          width: 12,
                          height: 12,
                          borderRadius: '50%',
                          backgroundColor: isConfigured ? provider.color : '#ccc'
                        }}
                      />
                      <span style={{ flex: 1 }}>{provider.name}</span>
                      {!isConfigured && (
                        <Typography variant="caption" color="text.secondary">
                          (Not configured)
                        </Typography>
                      )}
                    </Box>
                  </MenuItem>
                );
              })}
            </Select>
          </FormControl>
          
          {/* Language Selection */}
          <FormControl fullWidth>
            <InputLabel>Language</InputLabel>
            <Select
              value={settings.language}
              label="Language"
              onChange={(e) => handleChange('language', e.target.value)}
            >
              {languages.map(lang => (
                <MenuItem key={lang.code} value={lang.code}>
                  {lang.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          
          {/* Transcription Options */}
          <Paper elevation={0} sx={{ p: 2, backgroundColor: 'grey.50' }}>
            <Typography variant="subtitle2" gutterBottom>
              Transcription Options
            </Typography>
            
            <FormControlLabel
              control={
                <Switch
                  checked={settings.enableDiarization || false}
                  onChange={(e) => handleChange('enableDiarization', e.target.checked)}
                />
              }
              label="Enable Speaker Diarization"
            />
            
            {settings.enableDiarization && (
              <Box sx={{ mt: 2 }}>
                <Typography variant="body2" gutterBottom>
                  Max Speakers: {settings.maxSpeakers || 4}
                </Typography>
                <Slider
                  value={settings.maxSpeakers || 4}
                  onChange={(e, value) => handleChange('maxSpeakers', value)}
                  min={2}
                  max={10}
                  marks
                  valueLabelDisplay="auto"
                />
              </Box>
            )}
            
            <FormControlLabel
              control={
                <Switch
                  checked={settings.includeTimestamps || false}
                  onChange={(e) => handleChange('includeTimestamps', e.target.checked)}
                />
              }
              label="Include Timestamps"
            />
            
            <FormControlLabel
              control={
                <Switch
                  checked={settings.showCost || false}
                  onChange={(e) => handleChange('showCost', e.target.checked)}
                />
              }
              label="Show Cost Estimates"
            />
          </Paper>
          
          {/* Audio Quality */}
          <Paper elevation={0} sx={{ p: 2, backgroundColor: 'grey.50' }}>
            <Typography variant="subtitle2" gutterBottom>
              Audio Processing
            </Typography>
            
            <FormControlLabel
              control={
                <Switch
                  checked={settings.enableNoiseSuppression !== false}
                  onChange={(e) => handleChange('enableNoiseSuppression', e.target.checked)}
                />
              }
              label="Noise Suppression"
            />
            
            <FormControlLabel
              control={
                <Switch
                  checked={settings.enableEchoCancellation !== false}
                  onChange={(e) => handleChange('enableEchoCancellation', e.target.checked)}
                />
              }
              label="Echo Cancellation"
            />
            
            <FormControlLabel
              control={
                <Switch
                  checked={settings.enableAutoGainControl !== false}
                  onChange={(e) => handleChange('enableAutoGainControl', e.target.checked)}
                />
              }
              label="Auto Gain Control"
            />
          </Paper>
        </Box>
      </TabPanel>
      
      {/* API Keys Settings */}
      <TabPanel value={activeTab} index={1}>
        <APIKeysSettings />
      </TabPanel>
      
      {/* Advanced Settings */}
      <TabPanel value={activeTab} index={2}>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
          {/* Confidence Threshold */}
          <Box>
            <Typography variant="body2" gutterBottom>
              Confidence Threshold: {((settings.confidenceThreshold || 0.8) * 100).toFixed(0)}%
            </Typography>
            <Slider
              value={settings.confidenceThreshold || 0.8}
              onChange={(e, value) => handleChange('confidenceThreshold', value)}
              min={0.5}
              max={1}
              step={0.05}
              valueLabelDisplay="auto"
              valueLabelFormat={(value) => `${(value * 100).toFixed(0)}%`}
            />
          </Box>
          
          {/* Profanity Filter */}
          <FormControlLabel
            control={
              <Switch
                checked={settings.enableProfanityFilter || false}
                onChange={(e) => handleChange('enableProfanityFilter', e.target.checked)}
              />
            }
            label="Enable Profanity Filter"
          />
          
          {/* Custom Vocabulary */}
          <TextField
            fullWidth
            multiline
            rows={3}
            label="Custom Vocabulary"
            placeholder="Enter custom words separated by commas"
            value={settings.customVocabulary || ''}
            onChange={(e) => handleChange('customVocabulary', e.target.value)}
            helperText="Add technical terms, names, or industry-specific words"
          />
          
          {/* Export Format */}
          <FormControl fullWidth>
            <InputLabel>Default Export Format</InputLabel>
            <Select
              value={settings.exportFormat || 'txt'}
              label="Default Export Format"
              onChange={(e) => handleChange('exportFormat', e.target.value)}
            >
              <MenuItem value="txt">Plain Text (.txt)</MenuItem>
              <MenuItem value="srt">Subtitles (.srt)</MenuItem>
              <MenuItem value="vtt">WebVTT (.vtt)</MenuItem>
              <MenuItem value="json">JSON (.json)</MenuItem>
              <MenuItem value="docx">Word Document (.docx)</MenuItem>
            </Select>
          </FormControl>
          
          {/* Save Settings Button */}
          <Button
            variant="contained"
            fullWidth
            onClick={() => {
              // Save settings to localStorage
              localStorage.setItem('speecherSettings', JSON.stringify(settings));
              onClose();
            }}
            sx={{
              mt: 2,
              backgroundColor: 'primary.main',
              '&:hover': {
                backgroundColor: 'primary.dark',
              }
            }}
          >
            Save Settings
          </Button>
        </Box>
      </TabPanel>
    </Box>
  );
};

export default Settings;