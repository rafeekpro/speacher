import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || '';

export const transcribeAudio = async (formData) => {
  try {
    const response = await axios.post(
      `${API_BASE_URL}/api/transcribe`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data'
        },
        timeout: 300000 // 5 minutes timeout for large files
      }
    );

    return response.data;
  } catch (error) {
    if (error.code === 'ECONNABORTED') {
      throw new Error('Transcription timed out. Large files may take several minutes. Please try again or check the History page later.');
    } else if (error.response) {
      throw new Error(error.response.data.detail || 'Server error');
    } else if (error.request) {
      throw new Error('No response from server. Please check if the backend is running.');
    } else {
      throw new Error('Failed to send request');
    }
  }
};

export const getTranscriptionHistory = async (limit = 50) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/api/history`, {
      params: { limit }
    });
    return response.data;
  } catch (error) {
    throw new Error('Failed to fetch history');
  }
};

export const getTranscriptionById = async (id) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/api/transcription/${id}`);
    return response.data;
  } catch (error) {
    throw new Error('Failed to fetch transcription');
  }
};

export const deleteTranscription = async (id) => {
  try {
    const response = await axios.delete(`${API_BASE_URL}/api/transcription/${id}`);
    return response.data;
  } catch (error) {
    throw new Error('Failed to delete transcription');
  }
};

export const getStatistics = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/api/stats`);
    return response.data;
  } catch (error) {
    throw new Error('Failed to fetch statistics');
  }
};

export const checkHealth = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/health`);
    return response.data;
  } catch (error) {
    return { status: 'unhealthy', error: error.message };
  }
};

export const getProviders = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/api/keys`);
    return response.data;
  } catch (error) {
    console.error('Failed to fetch providers:', error);
    return [];
  }
};

export const getS3Files = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/api/files`);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Failed to fetch S3 files');
  }
};

export const deleteS3File = async (filename) => {
  try {
    const response = await axios.delete(`${API_BASE_URL}/api/files/${encodeURIComponent(filename)}`);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Failed to delete file');
  }
};

export const retranscribeFile = async (filename, language = 'en-US', enableDiarization = true, maxSpeakers = 4) => {
  try {
    const formData = new FormData();
    formData.append('language', language);
    formData.append('enable_diarization', String(enableDiarization));
    formData.append('max_speakers', String(maxSpeakers));

    const response = await axios.post(
      `${API_BASE_URL}/api/files/${encodeURIComponent(filename)}/retranscribe`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data'
        },
        timeout: 600000 // 10 minutes timeout for re-transcription
      }
    );
    return response.data;
  } catch (error) {
    if (error.code === 'ECONNABORTED') {
      throw new Error('Re-transcription timed out. Please try again or check the History page later.');
    }
    throw new Error(error.response?.data?.detail || 'Failed to retranscribe file');
  }
};

export const renameS3File = async (filename, newFilename) => {
  try {
    const response = await axios.patch(
      `${API_BASE_URL}/api/files/${encodeURIComponent(filename)}`,
      { new_filename: newFilename }
    );
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Failed to rename file');
  }
};