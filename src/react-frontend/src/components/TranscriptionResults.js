import React, { useState } from 'react';
import { Download, Copy, Check, Clock, DollarSign, User } from 'lucide-react';
import './TranscriptionResults.css';

const TranscriptionResults = ({ transcriptions }) => {
  const [copiedId, setCopiedId] = useState(null);

  const copyToClipboard = (transcript, id) => {
    let textToCopy = '';
    
    // If there are speaker segments, format them nicely
    if (transcript.speakers && transcript.speakers.length > 0) {
      textToCopy = "=== FULL TRANSCRIPT ===\n\n";
      textToCopy += transcript.transcript + "\n\n";
      textToCopy += "=== SPEAKER SEGMENTS ===\n\n";
      transcript.speakers.forEach((speaker) => {
        if (speaker.text && speaker.text.trim()) {
          textToCopy += `${speaker.speaker}: ${speaker.text}\n\n`;
        }
      });
    } else {
      // No speaker segments, just copy the main transcript
      textToCopy = transcript.transcript;
    }
    
    navigator.clipboard.writeText(textToCopy);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const downloadTranscript = (transcript, format = 'txt') => {
    let content = '';
    let mimeType = 'text/plain';
    let extension = 'txt';

    if (format === 'json') {
      content = JSON.stringify(transcript, null, 2);
      mimeType = 'application/json';
      extension = 'json';
    } else if (format === 'srt') {
      content = generateSRT(transcript);
      extension = 'srt';
    } else {
      // For TXT format, include speaker segments if available
      if (transcript.speakers && transcript.speakers.length > 0) {
        // Add main transcript first
        content = "=== FULL TRANSCRIPT ===\n\n";
        content += transcript.transcript + "\n\n";
        
        // Add speaker segments
        content += "=== SPEAKER SEGMENTS ===\n\n";
        transcript.speakers.forEach((speaker, idx) => {
          if (speaker.text && speaker.text.trim()) {
            const startTime = speaker.start_time ? formatTime(speaker.start_time) : '';
            const endTime = speaker.end_time ? formatTime(speaker.end_time) : '';
            const timeRange = startTime && endTime ? ` [${startTime} - ${endTime}]` : '';
            content += `${speaker.speaker}${timeRange}:\n${speaker.text}\n\n`;
          }
        });
      } else {
        // No speaker segments, just use the main transcript
        content = transcript.transcript;
      }
    }

    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `transcript_${new Date().toISOString()}.${extension}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const generateSRT = (transcript) => {
    let srt = '';
    
    if (transcript.speakers && transcript.speakers.length > 0) {
      // Generate SRT from speaker segments
      transcript.speakers.forEach((speaker, idx) => {
        if (speaker.text && speaker.text.trim()) {
          const startTime = formatSRTTime(speaker.start_time || 0);
          const endTime = formatSRTTime(speaker.end_time || (speaker.start_time + 5));
          
          srt += `${idx + 1}\n`;
          srt += `${startTime} --> ${endTime}\n`;
          srt += `[${speaker.speaker}] ${speaker.text}\n\n`;
        }
      });
    } else {
      // Fallback to simple SRT with full transcript
      srt = '1\n';
      srt += '00:00:00,000 --> ';
      const duration = transcript.duration || 10;
      const minutes = Math.floor(duration / 60);
      const seconds = Math.floor(duration % 60);
      srt += `00:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')},000\n`;
      srt += transcript.transcript + '\n';
    }
    
    return srt;
  };

  const formatSRTTime = (seconds) => {
    const hours = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    const millis = Math.floor((seconds % 1) * 1000);
    
    return `${hours.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')},${millis.toString().padStart(3, '0')}`;
  };

  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleString();
  };

  if (transcriptions.length === 0) {
    return (
      <div className="no-results">
        <p>No transcriptions yet. Record some audio to get started!</p>
      </div>
    );
  }

  return (
    <div className="transcription-results">
      {transcriptions.map((transcript, index) => (
        <div key={transcript.id || index} className="transcription-card">
          <div className="transcription-header">
            <span className="timestamp">
              <Clock size={14} />
              {formatTimestamp(transcript.timestamp)}
            </span>
            <div className="metadata">
              <span className="provider">{transcript.provider?.toUpperCase()}</span>
              <span className="language">{transcript.language}</span>
              {transcript.duration && (
                <span className="duration">
                  {Math.round(transcript.duration)}s
                </span>
              )}
              {transcript.cost_estimate && (
                <span className="cost">
                  <DollarSign size={14} />
                  {transcript.cost_estimate.toFixed(4)}
                </span>
              )}
            </div>
          </div>

          <div className="transcription-content">
            {transcript.speakers && transcript.speakers.length > 0 ? (
              // Show speaker segments as main content when diarization is enabled
              <div className="speakers-section">
                <h4>
                  <User size={16} />
                  Speaker Segments ({transcript.speakers.length})
                </h4>
                <div className="speakers-list">
                  {transcript.speakers.map((speaker, idx) => (
                    <div key={idx} className="speaker-segment">
                      <div className="speaker-header">
                        <span className="speaker-label">{speaker.speaker}</span>
                        {speaker.start_time && speaker.end_time && (
                          <span className="segment-time">
                            {speaker.start_time} - {speaker.end_time}
                          </span>
                        )}
                      </div>
                      <p className="speaker-text">{speaker.text}</p>
                    </div>
                  ))}
                </div>
                {transcript.transcript && (
                  <details className="full-transcript-section">
                    <summary>View full transcript (raw text)</summary>
                    <p className="transcript-text">{transcript.transcript}</p>
                  </details>
                )}
              </div>
            ) : (
              // No speaker segments - show full transcript as main content
              <p className="transcript-text">{transcript.transcript}</p>
            )}
          </div>

          <div className="transcription-actions">
            <button
              className="action-btn"
              onClick={() => copyToClipboard(transcript, transcript.id || index)}
            >
              {copiedId === (transcript.id || index) ? <Check size={16} /> : <Copy size={16} />}
              {copiedId === (transcript.id || index) ? 'Copied!' : 'Copy'}
            </button>
            
            <button
              className="action-btn"
              onClick={() => downloadTranscript(transcript, 'txt')}
            >
              <Download size={16} />
              TXT
            </button>
            
            <button
              className="action-btn"
              onClick={() => downloadTranscript(transcript, 'json')}
            >
              <Download size={16} />
              JSON
            </button>
            
            <button
              className="action-btn"
              onClick={() => downloadTranscript(transcript, 'srt')}
            >
              <Download size={16} />
              SRT
            </button>

            {transcript.audioUrl && (
              <audio controls className="audio-player">
                <source src={transcript.audioUrl} type="audio/webm" />
                Your browser does not support the audio element.
              </audio>
            )}
          </div>
        </div>
      ))}
    </div>
  );
};

export default TranscriptionResults;