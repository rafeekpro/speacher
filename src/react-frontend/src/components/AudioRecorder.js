import React, { useState, useRef, useEffect } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  IconButton,
  Typography,
  LinearProgress,
  Chip,
  Stack,
  Paper,
  Tooltip
} from '@mui/material';
import {
  Mic as MicIcon,
  Square as StopIcon,
  Play as PlayIcon,
  Pause as PauseIcon,
  Download as DownloadIcon,
  Trash2 as DeleteIcon,
  Upload as UploadIcon,
  Circle as RecordIcon
} from 'lucide-react';
import WaveSurfer from 'wavesurfer.js';
import AudioVisualizer from './AudioVisualizer';
import { convertWebMToWav } from '../utils/audioConverter';
import TranscriptionProgress from './TranscriptionProgress';

const AudioRecorder = ({ onAudioRecorded, isLoading, settings, currentJob, onJobComplete, onJobError }) => {
  const [isRecording, setIsRecording] = useState(false);
  const [audioBlob, setAudioBlob] = useState(null);
  const [audioUrl, setAudioUrl] = useState(null);
  const [duration, setDuration] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentStream, setCurrentStream] = useState(null);
  
  const mediaRecorderRef = useRef(null);
  const streamRef = useRef(null);
  const chunksRef = useRef([]);
  const timerRef = useRef(null);
  const wavesurferRef = useRef(null);
  const waveformRef = useRef(null);

  useEffect(() => {
    // Initialize WaveSurfer when we have audio
    if (audioUrl && waveformRef.current && !wavesurferRef.current) {
      wavesurferRef.current = WaveSurfer.create({
        container: waveformRef.current,
        waveColor: '#667eea',
        progressColor: '#764ba2',
        cursorColor: '#667eea',
        barWidth: 3,
        barRadius: 3,
        responsive: true,
        height: 80,
        normalize: true,
        backend: 'WebAudio'
      });

      wavesurferRef.current.load(audioUrl);
      
      wavesurferRef.current.on('finish', () => {
        setIsPlaying(false);
      });
    }

    return () => {
      if (wavesurferRef.current) {
        wavesurferRef.current.destroy();
        wavesurferRef.current = null;
      }
    };
  }, [audioUrl]);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        } 
      });
      
      streamRef.current = stream;
      setCurrentStream(stream); // Set stream for visualizer
      
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm'
      });
      
      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];
      
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };
      
      mediaRecorder.onstop = async () => {
        const webmBlob = new Blob(chunksRef.current, { type: 'audio/webm' });
        
        try {
          // Convert WebM to WAV
          const wavBlob = await convertWebMToWav(webmBlob);
          const audioUrl = URL.createObjectURL(wavBlob);
          
          setAudioBlob(wavBlob);
          setAudioUrl(audioUrl);
        } catch (error) {
          console.error('Error converting audio:', error);
          // Fallback to WebM
          const audioUrl = URL.createObjectURL(webmBlob);
          setAudioBlob(webmBlob);
          setAudioUrl(audioUrl);
        }
        
        setIsRecording(false);
        
        // Clean up waveform for new recording
        if (wavesurferRef.current) {
          wavesurferRef.current.destroy();
          wavesurferRef.current = null;
        }
      };
      
      mediaRecorder.start(100); // Collect data every 100ms
      setIsRecording(true);
      setDuration(0);
      
      // Start duration timer
      timerRef.current = setInterval(() => {
        setDuration(prev => prev + 1);
      }, 1000);
      
    } catch (error) {
      console.error('Error accessing microphone:', error);
      alert('Unable to access microphone. Please check permissions.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
      
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
      
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
      
      setIsRecording(false);
    }
  };

  const togglePlayback = () => {
    if (wavesurferRef.current) {
      if (isPlaying) {
        wavesurferRef.current.pause();
      } else {
        wavesurferRef.current.play();
      }
      setIsPlaying(!isPlaying);
    }
  };

  const clearRecording = () => {
    setAudioBlob(null);
    setAudioUrl(null);
    setDuration(0);
    setIsPlaying(false);
    
    if (wavesurferRef.current) {
      wavesurferRef.current.destroy();
      wavesurferRef.current = null;
    }
  };

  const downloadRecording = () => {
    if (audioBlob) {
      const url = URL.createObjectURL(audioBlob);
      const a = document.createElement('a');
      a.href = url;
      // Use .wav extension since we convert to WAV
      a.download = `recording_${new Date().toISOString()}.wav`;
      a.click();
      URL.revokeObjectURL(url);
    }
  };

  const submitForTranscription = () => {
    if (audioBlob && onAudioRecorded) {
      onAudioRecorded(audioBlob, `recording_${new Date().toISOString()}.wav`);
    }
  };

  const formatDuration = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <Card elevation={2}>
      <CardContent>
        <Typography variant="h5" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <MicIcon className="text-blue-600" size={24} />
          Audio Recorder
        </Typography>

        {/* Show TranscriptionProgress when there's an active job */}
        {currentJob && onJobComplete && onJobError && (
          <Box sx={{ mt: 3 }}>
            <TranscriptionProgress
              jobId={currentJob.id}
              onComplete={onJobComplete}
              onError={onJobError}
            />
          </Box>
        )}

        <Box sx={{ mt: 3 }}>
          {!isRecording && !audioBlob && (
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <Button
                variant="contained"
                size="large"
                startIcon={<MicIcon size={20} />}
                onClick={startRecording}
                disabled={isLoading}
                sx={{
                  borderRadius: 3,
                  px: 4,
                  py: 1.5,
                  backgroundColor: 'primary.main',
                  '&:hover': {
                    backgroundColor: 'primary.dark',
                  }
                }}
              >
                Start Recording
              </Button>
              
              <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
                Click to start recording from your microphone
              </Typography>
            </Box>
          )}
          
          {isRecording && (
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <Stack direction="row" spacing={2} justifyContent="center" alignItems="center">
                <Button
                  variant="contained"
                  color="error"
                  size="large"
                  startIcon={<StopIcon size={20} />}
                  onClick={stopRecording}
                  sx={{ borderRadius: 3, px: 4, py: 1.5 }}
                >
                  Stop Recording
                </Button>
                
                <Chip
                  icon={<RecordIcon className="text-red-500 animate-pulse" size={16} />}
                  label={formatDuration(duration)}
                  color="error"
                  variant="outlined"
                  sx={{ px: 2, fontSize: '1.1rem' }}
                />
              </Stack>
              
              {/* Audio Visualizer */}
              <AudioVisualizer stream={currentStream} isRecording={isRecording} />
              
              <LinearProgress 
                color="error" 
                sx={{ mt: 3, height: 6, borderRadius: 3 }}
                variant="indeterminate"
              />
            </Box>
          )}
          
          {audioBlob && !isRecording && (
            <Box>
              <Paper 
                ref={waveformRef} 
                elevation={0} 
                sx={{ 
                  p: 2, 
                  mb: 3, 
                  backgroundColor: 'grey.50',
                  borderRadius: 2,
                  minHeight: 100
                }}
              />
              
              <Stack direction="row" spacing={2} justifyContent="center" alignItems="center">
                <IconButton
                  color="primary"
                  onClick={togglePlayback}
                  size="large"
                  sx={{
                    backgroundColor: 'primary.main',
                    color: 'white',
                    '&:hover': {
                      backgroundColor: 'primary.dark',
                    }
                  }}
                >
                  {isPlaying ? <PauseIcon size={24} /> : <PlayIcon size={24} />}
                </IconButton>
                
                <Chip 
                  label={formatDuration(duration)} 
                  color="primary" 
                  variant="outlined"
                  sx={{ px: 2 }}
                />
                
                <Tooltip title="Download recording">
                  <IconButton color="primary" onClick={downloadRecording}>
                    <DownloadIcon size={24} />
                  </IconButton>
                </Tooltip>
                
                <Tooltip title="Delete recording">
                  <IconButton color="error" onClick={clearRecording}>
                    <DeleteIcon size={24} />
                  </IconButton>
                </Tooltip>
                
                <Button
                  variant="contained"
                  startIcon={<UploadIcon size={20} />}
                  onClick={submitForTranscription}
                  disabled={isLoading}
                  sx={{
                    ml: 2,
                    borderRadius: 3,
                    px: 3,
                    backgroundColor: 'success.main',
                    '&:hover': {
                      backgroundColor: 'success.dark',
                    }
                  }}
                >
                  {isLoading ? 'Processing...' : 'Transcribe'}
                </Button>
              </Stack>
              
              {settings && (
                <Box sx={{ mt: 3, display: 'flex', gap: 1, flexWrap: 'wrap', justifyContent: 'center' }}>
                  <Chip label={`Provider: ${settings.provider?.toUpperCase()}`} size="small" />
                  <Chip label={`Language: ${settings.language}`} size="small" />
                  {settings.enableDiarization && <Chip label="Speaker Diarization" size="small" color="primary" />}
                </Box>
              )}
            </Box>
          )}
        </Box>
      </CardContent>
    </Card>
  );
};

export default AudioRecorder;