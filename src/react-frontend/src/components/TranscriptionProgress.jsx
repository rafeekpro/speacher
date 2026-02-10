import React, { useState, useEffect, useRef } from 'react';
import {
  Card,
  CardContent,
  Box,
  Typography,
  LinearProgress,
  Chip
} from '@mui/material';
import {
  Clock as ClockIcon,
  DollarSign as DollarIcon
} from 'lucide-react';

const TranscriptionProgress = ({ jobId, onComplete, onError }) => {
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState('initializing');
  const [timeRemaining, setTimeRemaining] = useState(null);
  const [costEstimate, setCostEstimate] = useState(null);
  const wsRef = useRef(null);

  useEffect(() => {
    if (!jobId) {
      return;
    }

    // Determine WebSocket URL based on environment
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsHost = process.env.REACT_APP_API_URL
      ? process.env.REACT_APP_API_URL.replace(/^https?:\/\//, '').replace(/^http?:\/\//, '')
      : window.location.host;
    const wsUrl = `${wsProtocol}//${wsHost}/ws/transcribe/${jobId}`;

    // Create WebSocket connection
    wsRef.current = new WebSocket(wsUrl);

    wsRef.current.onopen = () => {
      console.log('WebSocket connected for job:', jobId);
    };

    wsRef.current.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        // Update progress
        if (data.progress !== undefined) {
          setProgress(data.progress);
        }

        // Update status
        if (data.status) {
          setStatus(data.status);
        }

        // Update time remaining
        if (data.time_remaining !== undefined) {
          setTimeRemaining(data.time_remaining);
        }

        // Update cost estimate
        if (data.cost_estimate !== undefined) {
          setCostEstimate(data.cost_estimate);
        }

        // Handle completion
        if (data.status === 'completed' && data.result) {
          if (onComplete) {
            onComplete(data.result);
          }
          // Close WebSocket after completion
          if (wsRef.current) {
            wsRef.current.close();
          }
        }

        // Handle failure
        if (data.status === 'failed') {
          if (onError) {
            onError(data.error || 'Transcription failed');
          }
          // Close WebSocket after failure
          if (wsRef.current) {
            wsRef.current.close();
          }
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };

    wsRef.current.onerror = (error) => {
      console.error('WebSocket error:', error);
      if (onError) {
        onError('WebSocket connection error');
      }
    };

    wsRef.current.onclose = () => {
      console.log('WebSocket closed for job:', jobId);
    };

    // Cleanup function
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [jobId, onComplete, onError]);

  // Format time remaining
  const formatTimeRemaining = (seconds) => {
    if (seconds === null || seconds === undefined) {
      return 'Calculating...';
    }
    if (seconds < 60) {
      return `${Math.round(seconds)} sec`;
    } else {
      const mins = Math.floor(seconds / 60);
      const secs = Math.round(seconds % 60);
      return `${mins}m ${secs}s`;
    }
  };

  // Format cost estimate
  const formatCostEstimate = (cost) => {
    if (cost === null || cost === undefined) {
      return 'Calculating...';
    }
    return `$${cost.toFixed(4)}`;
  };

  return (
    <Card elevation={2}>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Transcription Progress
        </Typography>

        <Box sx={{ mt: 2 }}>
          {/* Status and Progress */}
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
            <Typography variant="body2" color="text.secondary">
              Status: <strong>{status.charAt(0).toUpperCase() + status.slice(1)}</strong>
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {progress}%
            </Typography>
          </Box>

          <LinearProgress
            variant="determinate"
            value={progress}
            sx={{
              height: 10,
              borderRadius: 5,
              mb: 2
            }}
          />

          {/* Time Remaining and Cost Estimate */}
          <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', justifyContent: 'center' }}>
            {timeRemaining !== null && (
              <Chip
                icon={<ClockIcon size={16} />}
                label={`~${formatTimeRemaining(timeRemaining)}`}
                size="small"
                color="primary"
                variant="outlined"
              />
            )}

            {costEstimate !== null && (
              <Chip
                icon={<DollarIcon size={16} />}
                label={`~${formatCostEstimate(costEstimate)}`}
                size="small"
                color="success"
                variant="outlined"
              />
            )}
          </Box>

          {/* Additional Information */}
          {status === 'processing' && (
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 2, textAlign: 'center' }}>
              Processing your audio file. This may take a few minutes depending on the file size.
            </Typography>
          )}

          {status === 'completed' && (
            <Typography variant="caption" color="success.main" sx={{ display: 'block', mt: 2, textAlign: 'center' }}>
              Transcription completed successfully!
            </Typography>
          )}

          {status === 'failed' && (
            <Typography variant="caption" color="error.main" sx={{ display: 'block', mt: 2, textAlign: 'center' }}>
              Transcription failed. Please try again.
            </Typography>
          )}
        </Box>
      </CardContent>
    </Card>
  );
};

export default TranscriptionProgress;
