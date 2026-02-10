import React, { useState, useRef } from 'react';
import { Upload, File, X, AlertCircle, CheckCircle, Languages } from 'lucide-react';
import './FileUpload.css';
import TranscriptionProgress from './TranscriptionProgress';

const SUPPORTED_LANGUAGES = [
  { code: 'en-US', name: 'English (US)' },
  { code: 'en-GB', name: 'English (UK)' },
  { code: 'es-US', name: 'Spanish (US)' },
  { code: 'fr-FR', name: 'French' },
  { code: 'de-DE', name: 'German' },
  { code: 'it-IT', name: 'Italian' },
  { code: 'pt-BR', name: 'Portuguese (Brazil)' },
  { code: 'pl-PL', name: 'Polish' },
  { code: 'ru-RU', name: 'Russian' },
  { code: 'ja-JP', name: 'Japanese' },
  { code: 'ko-KR', name: 'Korean' },
  { code: 'zh-CN', name: 'Chinese (Mandarin)' }
];

const FileUpload = ({ onFilesUploaded, isLoading, settings, currentJob, onJobComplete, onJobError }) => {
  const [files, setFiles] = useState([]);
  const [dragActive, setDragActive] = useState(false);
  const [selectedLanguage, setSelectedLanguage] = useState(settings?.language || 'en-US');
  const fileInputRef = useRef(null);

  const supportedFormats = [
    '.wav', '.mp3', '.m4a', '.flac', '.ogg', '.webm', '.mp4', '.mpeg'
  ];

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFiles(e.dataTransfer.files);
    }
  };

  const handleChange = (e) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      handleFiles(e.target.files);
    }
  };

  const handleFiles = (fileList) => {
    const newFiles = Array.from(fileList).filter(file => {
      const extension = '.' + file.name.split('.').pop().toLowerCase();
      return supportedFormats.some(format => extension === format);
    });

    setFiles(prevFiles => [...prevFiles, ...newFiles.map(file => ({
      file,
      id: Math.random().toString(36).substr(2, 9),
      status: 'pending',
      progress: 0
    }))]);
  };

  const removeFile = (id) => {
    setFiles(files.filter(f => f.id !== id));
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  const processFiles = async () => {
    for (let fileItem of files) {
      if (fileItem.status !== 'pending') continue;

      // Update status to processing
      setFiles(prev => prev.map(f =>
        f.id === fileItem.id ? { ...f, status: 'processing' } : f
      ));

      try {
        // Pass selected language to the callback
        await onFilesUploaded(fileItem.file, fileItem.file.name, selectedLanguage);

        // Update status to completed
        setFiles(prev => prev.map(f =>
          f.id === fileItem.id ? { ...f, status: 'completed', progress: 100 } : f
        ));
      } catch (error) {
        // Update status to error
        setFiles(prev => prev.map(f =>
          f.id === fileItem.id ? { ...f, status: 'error', error: error.message } : f
        ));
      }
    }
  };

  const pendingFiles = files.filter(f => f.status === 'pending');
  const hasFiles = files.length > 0;

  return (
    <div className="file-upload">
      {/* Show TranscriptionProgress when there's an active job */}
      {currentJob && onJobComplete && onJobError && (
        <div className="progress-container">
          <TranscriptionProgress
            jobId={currentJob.id}
            onComplete={onJobComplete}
            onError={onJobError}
          />
        </div>
      )}

      <div
        className={`upload-zone ${dragActive ? 'drag-active' : ''}`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept={supportedFormats.join(',')}
          onChange={handleChange}
          className="file-input"
        />
        
        <Upload size={48} className="upload-icon" />
        <h3>Drag & Drop Audio Files</h3>
        <p>or</p>
        <button 
          className="browse-btn"
          onClick={() => fileInputRef.current?.click()}
        >
          Browse Files
        </button>
        <p className="supported-formats">
          Supported: WAV, MP3, M4A, FLAC, OGG, WebM
        </p>
      </div>

      {hasFiles && (
        <div className="files-list">
          <div className="files-header">
            <h3>Files ({files.length})</h3>
          </div>

          {/* Language Selector */}
          <div className="language-selector">
            <Languages size={20} className="language-icon" />
            <label htmlFor="language-select" className="language-label">
              Transcription Language:
            </label>
            <select
              id="language-select"
              className="language-dropdown"
              value={selectedLanguage}
              onChange={(e) => setSelectedLanguage(e.target.value)}
              disabled={isLoading}
            >
              {SUPPORTED_LANGUAGES.map(lang => (
                <option key={lang.code} value={lang.code}>
                  {lang.name}
                </option>
              ))}
            </select>
          </div>

          {pendingFiles.length > 0 && (
            <button
              className="process-all-btn"
              onClick={processFiles}
              disabled={isLoading}
            >
              Transcribe All ({pendingFiles.length})
            </button>
          )}
          
          {files.map(fileItem => (
            <div key={fileItem.id} className={`file-item ${fileItem.status}`}>
              <div className="file-info">
                <File size={20} />
                <div className="file-details">
                  <span className="file-name">{fileItem.file.name}</span>
                  <span className="file-size">{formatFileSize(fileItem.file.size)}</span>
                </div>
              </div>
              
              <div className="file-status">
                {fileItem.status === 'pending' && (
                  <button 
                    className="file-action"
                    onClick={() => removeFile(fileItem.id)}
                  >
                    <X size={16} />
                  </button>
                )}
                {fileItem.status === 'processing' && (
                  <div className="processing-indicator">
                    <div className="mini-spinner"></div>
                    Processing...
                  </div>
                )}
                {fileItem.status === 'completed' && (
                  <div className="status-indicator success">
                    <CheckCircle size={16} />
                    Completed
                  </div>
                )}
                {fileItem.status === 'error' && (
                  <div className="status-indicator error">
                    <AlertCircle size={16} />
                    Error
                  </div>
                )}
              </div>
              
              {fileItem.status === 'processing' && (
                <div className="progress-bar">
                  <div 
                    className="progress-fill"
                    style={{ width: `${fileItem.progress}%` }}
                  />
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      <div className="upload-tips">
        <h4>💡 Tips for Best Results</h4>
        <ul>
          <li>Use high-quality audio files (WAV or FLAC preferred)</li>
          <li>Ensure clear audio without background noise</li>
          <li>Files should be under 500MB</li>
          <li>Longer files may take more time to process</li>
        </ul>
      </div>
    </div>
  );
};

export default FileUpload;