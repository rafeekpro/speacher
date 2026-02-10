import React, { useState, useEffect, useCallback } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import './App.css';
import {
  Box,
  Chip,
  Alert,
  Snackbar,
  CircularProgress,
  Backdrop,
  Typography
} from '@mui/material';
import {
  CheckCircle as CheckIcon,
  AlertCircle as ErrorIcon
} from 'lucide-react';

// Context and Layout
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { Layout } from './components/layout';

// Components
import AudioRecorder from './components/AudioRecorder';
import FileUpload from './components/FileUpload';
import TranscriptionResults from './components/TranscriptionResults';
import History from './components/History';
import Statistics from './components/Statistics';
import Settings from './components/Settings';
import APIKeysSettings from './components/APIKeysSettings';
import FileManagement from './components/FileManagement';
import { LoginForm } from './components/auth/LoginForm';
import { RegisterForm } from './components/auth/RegisterForm';

// Services
import { transcribeAudio, transcribeAudioAsync, checkHealth } from './services/api';

// Utils
import { setupAxiosInterceptors } from './utils/axiosInterceptors';

// Create MUI theme
const theme = createTheme({
  palette: {
    primary: {
      main: '#667eea',
      light: '#8b9bf0',
      dark: '#4c5cd8',
    },
    secondary: {
      main: '#764ba2',
      light: '#9166bc',
      dark: '#5a3a7e',
    },
    success: {
      main: '#48bb78',
    },
    warning: {
      main: '#ed8936',
    },
    error: {
      main: '#f56565',
    },
    background: {
      default: '#f5f5f5',
      paper: '#ffffff',
    },
  },
  typography: {
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
    h4: {
      fontWeight: 700,
    },
  },
  shape: {
    borderRadius: 12,
  },
  components: {
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          fontWeight: 600,
        },
      },
    },
    MuiTab: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          fontWeight: 600,
        },
      },
    },
  },
});

// Protected Route Component
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
};

// Dashboard component (new)
const Dashboard: React.FC<{
  transcriptions: any[];
  backendStatus: string;
  providers: any[];
}> = ({ transcriptions, backendStatus, providers }) => {
  const navigate = useNavigate();

  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold mb-4">Dashboard</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div className="bg-white p-6 rounded-lg shadow cursor-pointer hover:shadow-lg transition-shadow"
             onClick={() => navigate('/record')}>
          <h2 className="text-xl font-semibold mb-2">Start Recording</h2>
          <p className="text-gray-600">Record audio directly from your microphone</p>
        </div>
        <div className="bg-white p-6 rounded-lg shadow cursor-pointer hover:shadow-lg transition-shadow"
             onClick={() => navigate('/upload')}>
          <h2 className="text-xl font-semibold mb-2">Upload Files</h2>
          <p className="text-gray-600">Upload audio files for transcription</p>
        </div>
        <div className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-xl font-semibold mb-2">Recent Transcriptions</h2>
          <p className="text-gray-600">
            {transcriptions.length > 0
              ? `${transcriptions.length} transcription(s) in current session`
              : 'No transcriptions yet'}
          </p>
        </div>
        <div className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-xl font-semibold mb-2">Backend Status</h2>
          <div className="flex items-center gap-2">
            {backendStatus === 'healthy' ? (
              <CheckIcon className="text-green-500" size={20} />
            ) : (
              <ErrorIcon className="text-red-500" size={20} />
            )}
            <span className={backendStatus === 'healthy' ? 'text-green-600' : 'text-red-600'}>
              {backendStatus === 'healthy' ? 'Connected' : 'Disconnected'}
            </span>
          </div>
        </div>
        <div className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-xl font-semibold mb-2">Configured Providers</h2>
          <div className="flex flex-wrap gap-2 mt-2">
            {providers.filter(p => p.configured).map(provider => (
              <Chip
                key={provider.provider}
                label={provider.provider.toUpperCase()}
                size="small"
                color={provider.enabled ? "success" : "default"}
                variant="outlined"
              />
            ))}
            {providers.filter(p => p.configured).length === 0 && (
              <p className="text-gray-500 text-sm">No providers configured</p>
            )}
          </div>
        </div>
        <div className="bg-white p-6 rounded-lg shadow cursor-pointer hover:shadow-lg transition-shadow"
             onClick={() => navigate('/statistics')}>
          <h2 className="text-xl font-semibold mb-2">View Statistics</h2>
          <p className="text-gray-600">Analyze your transcription usage and costs</p>
        </div>
      </div>
    </div>
  );
};

// Main App Content Component
function AppContent() {
  const navigate = useNavigate();
  const [transcriptions, setTranscriptions] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [currentJob, setCurrentJob] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [backendStatus, setBackendStatus] = useState('checking');
  const [configuredProviders, setConfiguredProviders] = useState<any[]>([]);
  const [providers, setProviders] = useState<any[]>([]);
  const [settings, setSettings] = useState({
    provider: 'azure',
    language: 'en-US',
    enableDiarization: true,
    maxSpeakers: 4,
    includeTimestamps: true,
    showCost: true
  });

  const checkBackendHealth = useCallback(async () => {
    const health = await checkHealth();
    setBackendStatus(health.status === 'healthy' ? 'healthy' : 'unhealthy');
  }, []);

  const loadConfiguredProviders = useCallback(async () => {
    try {
      const response = await fetch('/api/keys');
      if (response.ok) {
        const providersData = await response.json();
        setProviders(providersData);
        const configured = providersData.filter((p: any) => p.configured && p.enabled);
        setConfiguredProviders(configured);
        
        // If current provider is not configured, switch to first configured one
        if (!configured.find((p: any) => p.provider === settings.provider)) {
          if (configured.length > 0) {
            setSettings(prev => ({ ...prev, provider: configured[0].provider }));
          }
        }
      }
    } catch (error) {
      console.error('Failed to load configured providers:', error);
    }
  }, [settings.provider]);

  useEffect(() => {
    // Initialize axios interceptors on mount
    const cleanupInterceptors = setupAxiosInterceptors();

    // Check backend health on mount
    checkBackendHealth();
    loadConfiguredProviders();
    const interval = setInterval(() => {
      checkBackendHealth();
      loadConfiguredProviders();
    }, 30000); // Check every 30s

    return () => {
      clearInterval(interval);
      cleanupInterceptors();
    };
  }, [checkBackendHealth, loadConfiguredProviders]);

  const handleAudioRecorded = async (audioBlob: Blob, fileName: string = 'recording.wav', selectedLanguage?: string) => {
    // Check if provider is configured
    if (configuredProviders.length === 0) {
      setError('No providers configured. Please configure API keys in Settings.');
      return;
    }

    if (!configuredProviders.find((p: any) => p.provider === settings.provider)) {
      setError(`${settings.provider.toUpperCase()} is not configured. Please configure API keys in Settings.`);
      return;
    }

    setIsLoading(true);
    setError(null);

    // Use selected language if provided (from FileUpload), otherwise use settings
    const language = selectedLanguage || settings.language;

    console.log('Sending transcription request:');
    console.log('- File:', fileName, 'Type:', audioBlob.type, 'Size:', audioBlob.size);
    console.log('- Provider:', settings.provider);
    console.log('- Language:', language);

    try {
      const formData = new FormData();
      formData.append('file', audioBlob, fileName);
      formData.append('provider', settings.provider);
      formData.append('language', language);
      formData.append('enable_diarization', String(settings.enableDiarization));
      formData.append('max_speakers', String(settings.maxSpeakers));
      formData.append('include_timestamps', settings.includeTimestamps ? "1" : "0");

      // Use async endpoint
      const { job_id } = await transcribeAudioAsync(formData);

      // Store job information
      setCurrentJob({
        id: job_id,
        fileName: fileName,
        audioBlob: audioBlob,
        timestamp: new Date().toISOString()
      });

      setIsLoading(false);
    } catch (err: any) {
      // Extract error message from response
      let errorMessage = 'Failed to transcribe audio';
      if (err.response) {
        const errorData = await err.response.json().catch(() => null);
        if (errorData && errorData.detail) {
          errorMessage = errorData.detail;
        } else if (err.response.status === 400) {
          errorMessage = 'Invalid request. Please check your API keys configuration.';
        } else if (err.response.status === 401) {
          errorMessage = 'Authentication failed. Please check your API keys.';
        } else if (err.response.status === 403) {
          errorMessage = 'Access denied. Please check your API keys permissions.';
        }
      } else if (err.message) {
        errorMessage = err.message;
      }
      setError(errorMessage);
      setIsLoading(false);
      setCurrentJob(null);
    }
  };

  const handleJobComplete = (result: any) => {
    console.log('Job completed:', result);

    // Create transcription object from result
    const newTranscription = {
      ...result,
      timestamp: currentJob?.timestamp || new Date().toISOString(),
      fileName: currentJob?.fileName || 'transcription.wav',
      audioUrl: currentJob?.audioBlob instanceof Blob ? URL.createObjectURL(currentJob.audioBlob) : null
    };

    setTranscriptions([newTranscription, ...transcriptions]);
    setCurrentJob(null);

    // Navigate to results page after successful transcription
    navigate('/results');
  };

  const handleJobError = (error: string) => {
    console.error('Job failed:', error);
    setError(error);
    setCurrentJob(null);
  };

  return (
    <>
      <Routes>
        {/* Public routes */}
        <Route path="/login" element={<LoginForm onSuccess={() => navigate('/dashboard')} />} />
        <Route path="/register" element={<RegisterForm onSuccess={() => navigate('/dashboard')} />} />

        {/* Default redirect */}
        <Route path="/" element={<Navigate to="/dashboard" replace />} />

        {/* Protected routes */}
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <Dashboard
                transcriptions={transcriptions}
                backendStatus={backendStatus}
                providers={providers}
              />
            </ProtectedRoute>
          }
        />
        <Route
          path="/record"
          element={
            <ProtectedRoute>
              <Box sx={{ p: 3 }}>
                <AudioRecorder
                  onAudioRecorded={handleAudioRecorded}
                  isLoading={isLoading}
                  settings={settings}
                  currentJob={currentJob}
                  onJobComplete={handleJobComplete}
                  onJobError={handleJobError}
                />
              </Box>
            </ProtectedRoute>
          }
        />
        <Route
          path="/upload"
          element={
            <ProtectedRoute>
              <Box sx={{ p: 3 }}>
                <FileUpload
                  onFilesUploaded={handleAudioRecorded}
                  isLoading={isLoading}
                  settings={settings}
                  currentJob={currentJob}
                  onJobComplete={handleJobComplete}
                  onJobError={handleJobError}
                />
              </Box>
            </ProtectedRoute>
          }
        />
        <Route
          path="/results"
          element={
            <ProtectedRoute>
              <Box sx={{ p: 3 }}>
                <TranscriptionResults
                  transcriptions={transcriptions}
                />
              </Box>
            </ProtectedRoute>
          }
        />
        <Route
          path="/history"
          element={
            <ProtectedRoute>
              <Box sx={{ p: 3 }}>
                <History
                  onSelectTranscription={(t: any) => {
                    setTranscriptions([t, ...transcriptions]);
                    navigate('/results');
                  }}
                />
              </Box>
            </ProtectedRoute>
          }
        />
        <Route
          path="/statistics"
          element={
            <ProtectedRoute>
              <Box sx={{ p: 3 }}>
                <Statistics />
              </Box>
            </ProtectedRoute>
          }
        />
        <Route
          path="/settings"
          element={
            <ProtectedRoute>
              <Box sx={{ p: 3 }}>
                <Settings
                  settings={settings}
                  onSettingsChange={setSettings}
                  onClose={() => navigate('/dashboard')}
                />
              </Box>
            </ProtectedRoute>
          }
        />
        <Route
          path="/api-keys"
          element={
            <ProtectedRoute>
              <Box sx={{ p: 3 }}>
                <APIKeysSettings />
              </Box>
            </ProtectedRoute>
          }
        />
        <Route
          path="/files"
          element={
            <ProtectedRoute>
              <Box sx={{ p: 3 }}>
                <FileManagement />
              </Box>
            </ProtectedRoute>
          }
        />
      </Routes>

      {/* Error Snackbar */}
      <Snackbar 
        open={!!error} 
        autoHideDuration={6000} 
        onClose={() => setError(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert onClose={() => setError(null)} severity="error" sx={{ width: '100%' }}>
          {error}
        </Alert>
      </Snackbar>

      {/* Loading Backdrop */}
      <Backdrop
        sx={{ color: '#fff', zIndex: (theme) => theme.zIndex.drawer + 1 }}
        open={isLoading}
      >
        <CircularProgress color="inherit" />
      </Backdrop>

      {/* Footer with API Keys Source Info */}
      <Box 
        component="footer" 
        sx={{ 
          mt: 4, 
          py: 2, 
          px: 3, 
          backgroundColor: 'background.paper',
          borderTop: 1,
          borderColor: 'divider',
          textAlign: 'center'
        }}
      >
        <Typography variant="caption" color="text.secondary">
          Configuration Source: API keys are loaded from .env file (environment variables) or MongoDB database
        </Typography>
        {providers && providers.length > 0 && (
          <Box sx={{ mt: 1 }}>
            {providers.filter((p: any) => p.configured).map((provider: any) => (
              <Chip
                key={provider.provider}
                label={`${provider.provider.toUpperCase()}: ${provider.source === 'mongodb' ? 'MongoDB' : '.env'}`}
                size="small"
                variant="outlined"
                sx={{ mx: 0.5 }}
              />
            ))}
          </Box>
        )}
      </Box>
    </>
  );
}

// Main App Component with Router and Providers
function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <BrowserRouter>
        <AuthProvider>
          <Layout>
            <AppContent />
          </Layout>
        </AuthProvider>
      </BrowserRouter>
    </ThemeProvider>
  );
}

export default App;