import React, { useState, useEffect } from 'react';
import { Trash2, RefreshCw, Edit, Search } from 'lucide-react';
import './FileManagement.css';

interface S3File {
  filename: string;
  size: number;
  upload_date: string;
}

interface FileManagementProps {
  onFileDeleted?: (filename: string) => void;
  onFileRetranscribed?: (filename: string) => void;
}

const FileManagement: React.FC<FileManagementProps> = ({
  onFileDeleted,
  onFileRetranscribed
}) => {
  const [files, setFiles] = useState<S3File[]>([]);
  const [filteredFiles, setFilteredFiles] = useState<S3File[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [editingFile, setEditingFile] = useState<S3File | null>(null);
  const [newFilename, setNewFilename] = useState('');
  const [actionLoading, setActionLoading] = useState<{ [key: string]: boolean }>({});

  // Fetch S3 files on component mount
  useEffect(() => {
    fetchFiles();
  }, []);

  // Filter files based on search term
  useEffect(() => {
    if (searchTerm.trim() === '') {
      setFilteredFiles(files);
    } else {
      const filtered = files.filter(file =>
        file.filename.toLowerCase().includes(searchTerm.toLowerCase())
      );
      setFilteredFiles(filtered);
    }
  }, [searchTerm, files]);

  const fetchFiles = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/files');
      if (!response.ok) {
        throw new Error('Failed to fetch files');
      }
      const data = await response.json();
      setFiles(data.files || []);
      setFilteredFiles(data.files || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load files');
      console.error('Error fetching files:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (filename: string) => {
    if (!window.confirm(`Are you sure you want to delete "${filename}"?`)) {
      return;
    }

    setActionLoading(prev => ({ ...prev, [filename]: true }));
    setError(null);

    try {
      const response = await fetch(`/api/files/${encodeURIComponent(filename)}`, {
        method: 'DELETE'
      });

      if (!response.ok) {
        throw new Error('Failed to delete file');
      }

      // Remove file from state
      setFiles(files.filter(f => f.filename !== filename));
      if (onFileDeleted) {
        onFileDeleted(filename);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete file');
      console.error('Error deleting file:', err);
    } finally {
      setActionLoading(prev => ({ ...prev, [filename]: false }));
    }
  };

  const handleRetranscribe = async (filename: string) => {
    setActionLoading(prev => ({ ...prev, [`${filename}-retranscribe`]: true }));
    setError(null);

    try {
      const response = await fetch(`/api/files/${encodeURIComponent(filename)}/retranscribe`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          language: 'en-US' // Default language, could be made configurable
        })
      });

      if (!response.ok) {
        throw new Error('Failed to retranscribe file');
      }

      const result = await response.json();

      if (onFileRetranscribed) {
        onFileRetranscribed(filename);
      }

      // Show success message
      alert(`File "${filename}" has been queued for retranscription.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to retranscribe file');
      console.error('Error retranscribing file:', err);
    } finally {
      setActionLoading(prev => ({ ...prev, [`${filename}-retranscribe`]: false }));
    }
  };

  const handleEditStart = (file: S3File) => {
    setEditingFile(file);
    setNewFilename(file.filename);
  };

  const handleEditCancel = () => {
    setEditingFile(null);
    setNewFilename('');
  };

  const handleEditSave = async () => {
    if (!editingFile || !newFilename.trim()) {
      return;
    }

    setActionLoading(prev => ({ ...prev, [`${editingFile.filename}-edit`]: true }));
    setError(null);

    try {
      const response = await fetch(`/api/files/${encodeURIComponent(editingFile.filename)}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          new_filename: newFilename.trim()
        })
      });

      if (!response.ok) {
        throw new Error('Failed to rename file');
      }

      // Update file in state
      setFiles(files.map(f =>
        f.filename === editingFile.filename
          ? { ...f, filename: newFilename.trim() }
          : f
      ));

      handleEditCancel();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to rename file');
      console.error('Error renaming file:', err);
    } finally {
      setActionLoading(prev => ({ ...prev, [`${editingFile.filename}-edit`]: false }));
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  const formatDate = (dateString: string): string => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="file-management">
      <div className="file-management-header">
        <h2>S3 File Management</h2>
        <button
          onClick={fetchFiles}
          className="refresh-btn"
          disabled={loading}
          aria-label="Refresh file list"
        >
          <RefreshCw size={20} className={loading ? 'spinning' : ''} />
          Refresh
        </button>
      </div>

      {/* Search Bar */}
      <div className="search-container">
        <Search size={20} className="search-icon" />
        <input
          type="text"
          placeholder="Search files..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="search-input"
          aria-label="Search files"
        />
      </div>

      {/* Error Message */}
      {error && (
        <div className="error-message" role="alert">
          {error}
          <button
            onClick={() => setError(null)}
            className="error-close"
            aria-label="Close error message"
          >
            ×
          </button>
        </div>
      )}

      {/* Loading Spinner */}
      {loading && (
        <div className="loading-container">
          <div className="spinner" aria-label="Loading files"></div>
          <p>Loading files...</p>
        </div>
      )}

      {/* File Table */}
      {!loading && (
        <>
          {filteredFiles.length === 0 ? (
            <div className="no-files">
              {searchTerm ? 'No files match your search.' : 'No files in S3 storage.'}
            </div>
          ) : (
            <div className="table-container">
              <table className="files-table">
                <thead>
                  <tr>
                    <th>Filename</th>
                    <th>Size</th>
                    <th>Upload Date</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredFiles.map((file) => (
                    <tr key={file.filename}>
                      <td className="filename-cell">
                        {editingFile?.filename === file.filename ? (
                          <input
                            type="text"
                            value={newFilename}
                            onChange={(e) => setNewFilename(e.target.value)}
                            className="filename-input"
                            autoFocus
                            onKeyDown={(e) => {
                              if (e.key === 'Enter') handleEditSave();
                              if (e.key === 'Escape') handleEditCancel();
                            }}
                          />
                        ) : (
                          <span className="filename-text">{file.filename}</span>
                        )}
                      </td>
                      <td>{formatFileSize(file.size)}</td>
                      <td>{formatDate(file.upload_date)}</td>
                      <td className="actions-cell">
                        {editingFile?.filename === file.filename ? (
                          <>
                            <button
                              onClick={handleEditSave}
                              className="action-btn save-btn"
                              disabled={actionLoading[`${file.filename}-edit`]}
                              aria-label="Save filename"
                            >
                              {actionLoading[`${file.filename}-edit`] ? 'Saving...' : 'Save'}
                            </button>
                            <button
                              onClick={handleEditCancel}
                              className="action-btn cancel-btn"
                              aria-label="Cancel edit"
                            >
                              Cancel
                            </button>
                          </>
                        ) : (
                          <>
                            <button
                              onClick={() => handleEditStart(file)}
                              className="action-btn edit-btn"
                              disabled={actionLoading[file.filename]}
                              title="Edit filename"
                              aria-label={`Edit ${file.filename}`}
                            >
                              <Edit size={16} />
                            </button>
                            <button
                              onClick={() => handleRetranscribe(file.filename)}
                              className="action-btn retranscribe-btn"
                              disabled={actionLoading[`${file.filename}-retranscribe`]}
                              title="Re-transcribe file"
                              aria-label={`Re-transcribe ${file.filename}`}
                            >
                              <RefreshCw size={16} className={actionLoading[`${file.filename}-retranscribe`] ? 'spinning' : ''} />
                            </button>
                            <button
                              onClick={() => handleDelete(file.filename)}
                              className="action-btn delete-btn"
                              disabled={actionLoading[file.filename]}
                              title="Delete file"
                              aria-label={`Delete ${file.filename}`}
                            >
                              <Trash2 size={16} />
                            </button>
                          </>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {/* File Count */}
      {!loading && filteredFiles.length > 0 && (
        <div className="file-count">
          Showing {filteredFiles.length} file{filteredFiles.length !== 1 ? 's' : ''}
          {searchTerm && ` (filtered from ${files.length} total)`}
        </div>
      )}
    </div>
  );
};

export default FileManagement;
