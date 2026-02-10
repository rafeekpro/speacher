import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Typography,
  TextField,
  Button,
  Grid,
  Alert,
  Snackbar,
  IconButton,
  InputAdornment,
  Switch,
  FormControlLabel,
  Chip,
  Divider,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  ListItemSecondaryAction,
  Collapse,
  Paper
} from '@mui/material';
import {
  Save as SaveIcon,
  Eye as VisibilityIcon,
  EyeOff as VisibilityOffIcon,
  Trash2 as DeleteIcon,
  ChevronDown as ExpandMoreIcon,
  ChevronUp as ExpandLessIcon,
  Cloud as CloudIcon,
  CheckCircle as CheckIcon,
  AlertTriangle as WarningIcon,
  Key as KeyIcon
} from 'lucide-react';
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const APIKeysSettings = () => {
  const [providers, setProviders] = useState([]);
  const [expandedProvider, setExpandedProvider] = useState(null);
  const [showPassword, setShowPassword] = useState({});
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);
  const [apiKeys, setApiKeys] = useState({
    aws: {
      access_key_id: '',
      secret_access_key: '',
      region: 'us-east-1',
      s3_bucket_name: ''
    },
    azure: {
      subscription_key: '',
      region: 'eastus',
      endpoint: ''
    },
    gcp: {
      credentials_json: '',
      project_id: '',
      gcs_bucket_name: ''
    }
  });

  const loadProviders = useCallback(async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/keys`);
      setProviders(response.data);
      
      // Load keys for each configured provider
      for (const provider of response.data) {
        if (provider.configured) {
          loadProviderKeys(provider.provider);
        }
      }
    } catch (error) {
      console.error('Error loading providers:', error);
    }
  }, []);

  useEffect(() => {
    loadProviders();
  }, [loadProviders]);

  const loadProviderKeys = async (provider) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/keys/${provider}`);
      if (response.data.configured) {
        setApiKeys(prev => ({
          ...prev,
          [provider]: response.data.keys
        }));
      }
    } catch (error) {
      console.error(`Error loading ${provider} keys:`, error);
    }
  };

  const handleSaveKeys = async (provider) => {
    setLoading(true);
    try {
      await axios.post(`${API_BASE_URL}/api/keys/${provider}`, {
        provider,
        keys: apiKeys[provider]
      });
      
      setMessage({ type: 'success', text: `${provider.toUpperCase()} API keys saved successfully!` });
      loadProviders();
    } catch (error) {
      setMessage({ type: 'error', text: `Failed to save ${provider} keys: ${error.message}` });
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteKeys = async (provider) => {
    if (!window.confirm(`Are you sure you want to delete ${provider.toUpperCase()} API keys?`)) {
      return;
    }

    setLoading(true);
    try {
      await axios.delete(`${API_BASE_URL}/api/keys/${provider}`);
      setApiKeys(prev => ({
        ...prev,
        [provider]: provider === 'aws' 
          ? { access_key_id: '', secret_access_key: '', region: 'us-east-1', s3_bucket_name: '' }
          : provider === 'azure'
          ? { subscription_key: '', region: 'eastus', endpoint: '' }
          : { credentials_json: '', project_id: '', gcs_bucket_name: '' }
      }));
      setMessage({ type: 'success', text: `${provider.toUpperCase()} API keys deleted!` });
      loadProviders();
    } catch (error) {
      setMessage({ type: 'error', text: `Failed to delete ${provider} keys: ${error.message}` });
    } finally {
      setLoading(false);
    }
  };

  const handleToggleProvider = async (provider, enabled) => {
    try {
      await axios.put(`${API_BASE_URL}/api/keys/${provider}/toggle?enabled=${enabled}`);
      loadProviders();
    } catch (error) {
      setMessage({ type: 'error', text: `Failed to toggle ${provider}: ${error.message}` });
    }
  };

  const togglePasswordVisibility = (field) => {
    setShowPassword(prev => ({ ...prev, [field]: !prev[field] }));
  };

  const handleInputChange = (provider, field, value) => {
    setApiKeys(prev => ({
      ...prev,
      [provider]: {
        ...prev[provider],
        [field]: value
      }
    }));
  };

  const getProviderIcon = (provider) => {
    const isConfigured = providers.find(p => p.provider === provider)?.configured;
    const isEnabled = providers.find(p => p.provider === provider)?.enabled;
    
    if (isConfigured && isEnabled) {
      return <CheckIcon className="text-green-500" size={20} />;
    } else if (isConfigured) {
      return <WarningIcon className="text-yellow-500" size={20} />;
    }
    return <CloudIcon className="text-gray-400" size={20} />;
  };

  const getProviderColor = (provider) => {
    switch (provider) {
      case 'aws': return '#FF9900';
      case 'azure': return '#0078D4';
      case 'gcp': return '#4285F4';
      default: return '#666';
    }
  };

  const renderProviderForm = (provider) => {
    switch (provider) {
      case 'aws':
        return (
          <Grid container spacing={2}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="AWS Access Key ID"
                value={apiKeys.aws.access_key_id}
                onChange={(e) => handleInputChange('aws', 'access_key_id', e.target.value)}
                variant="outlined"
                InputProps={{
                  startAdornment: <InputAdornment position="start"><KeyIcon size={20} /></InputAdornment>,
                }}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="AWS Secret Access Key"
                type={showPassword.aws_secret ? 'text' : 'password'}
                value={apiKeys.aws.secret_access_key}
                onChange={(e) => handleInputChange('aws', 'secret_access_key', e.target.value)}
                variant="outlined"
                InputProps={{
                  startAdornment: <InputAdornment position="start"><KeyIcon size={20} /></InputAdornment>,
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton onClick={() => togglePasswordVisibility('aws_secret')}>
                        {showPassword.aws_secret ? <VisibilityOffIcon size={20} /> : <VisibilityIcon size={20} />}
                      </IconButton>
                    </InputAdornment>
                  ),
                }}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="AWS Region"
                value={apiKeys.aws.region}
                onChange={(e) => handleInputChange('aws', 'region', e.target.value)}
                variant="outlined"
                placeholder="us-east-1"
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="S3 Bucket Name"
                value={apiKeys.aws.s3_bucket_name}
                onChange={(e) => handleInputChange('aws', 's3_bucket_name', e.target.value)}
                variant="outlined"
                placeholder="my-transcription-bucket"
                helperText="Unique S3 bucket name for storing audio files"
              />
            </Grid>
          </Grid>
        );

      case 'azure':
        return (
          <Grid container spacing={2}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Azure Subscription Key"
                type={showPassword.azure_key ? 'text' : 'password'}
                value={apiKeys.azure.subscription_key}
                onChange={(e) => handleInputChange('azure', 'subscription_key', e.target.value)}
                variant="outlined"
                InputProps={{
                  startAdornment: <InputAdornment position="start"><KeyIcon size={20} /></InputAdornment>,
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton onClick={() => togglePasswordVisibility('azure_key')}>
                        {showPassword.azure_key ? <VisibilityOffIcon size={20} /> : <VisibilityIcon size={20} />}
                      </IconButton>
                    </InputAdornment>
                  ),
                }}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Azure Region"
                value={apiKeys.azure.region}
                onChange={(e) => handleInputChange('azure', 'region', e.target.value)}
                variant="outlined"
                placeholder="eastus"
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Azure Endpoint (Optional)"
                value={apiKeys.azure.endpoint}
                onChange={(e) => handleInputChange('azure', 'endpoint', e.target.value)}
                variant="outlined"
                placeholder="https://eastus.api.cognitive.microsoft.com"
              />
            </Grid>
          </Grid>
        );

      case 'gcp':
        return (
          <Grid container spacing={2}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="GCP Service Account JSON"
                multiline
                rows={4}
                value={apiKeys.gcp.credentials_json}
                onChange={(e) => handleInputChange('gcp', 'credentials_json', e.target.value)}
                variant="outlined"
                placeholder='{"type": "service_account", "project_id": "...", ...}'
                InputProps={{
                  style: { fontFamily: 'monospace', fontSize: '0.9rem' }
                }}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="GCP Project ID"
                value={apiKeys.gcp.project_id}
                onChange={(e) => handleInputChange('gcp', 'project_id', e.target.value)}
                variant="outlined"
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="GCS Bucket Name"
                value={apiKeys.gcp.gcs_bucket_name}
                onChange={(e) => handleInputChange('gcp', 'gcs_bucket_name', e.target.value)}
                variant="outlined"
                placeholder="my-gcp-transcription-bucket"
                helperText="Google Cloud Storage bucket name for storing audio files"
              />
            </Grid>
          </Grid>
        );

      default:
        return null;
    }
  };

  return (
    <Box>
      <Typography variant="h5" gutterBottom sx={{ mb: 3 }}>
        API Keys Management
      </Typography>
      
      <Alert severity="info" sx={{ mb: 3 }}>
        Your API keys are encrypted and stored securely in the database. They are never exposed in logs or responses.
      </Alert>

      <List>
        {['aws', 'azure', 'gcp'].map((provider) => {
          const providerInfo = providers.find(p => p.provider === provider) || {};
          const isExpanded = expandedProvider === provider;
          
          return (
            <Paper key={provider} elevation={2} sx={{ mb: 2 }}>
              <ListItem>
                <ListItemIcon>
                  {getProviderIcon(provider)}
                </ListItemIcon>
                <ListItemText
                  primary={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography variant="h6" sx={{ color: getProviderColor(provider) }}>
                        {provider.toUpperCase()}
                      </Typography>
                      {providerInfo.configured && (
                        <>
                          <Chip 
                            label={providerInfo.enabled ? "Active" : "Disabled"} 
                            size="small"
                            color={providerInfo.enabled ? "success" : "default"}
                          />
                          <Chip
                            label={providerInfo.source === 'mongodb' ? '🗄️ MongoDB' : '📁 .env'}
                            size="small"
                            variant="outlined"
                            color={providerInfo.source === 'mongodb' ? 'primary' : 'secondary'}
                          />
                        </>
                      )}
                    </Box>
                  }
                  secondary={
                    providerInfo.configured 
                      ? `Last updated: ${new Date(providerInfo.updated_at).toLocaleDateString()}`
                      : 'Not configured'
                  }
                />
                <ListItemSecondaryAction>
                  <IconButton 
                    onClick={() => setExpandedProvider(isExpanded ? null : provider)}
                    edge="end"
                  >
                    {isExpanded ? <ExpandLessIcon size={20} /> : <ExpandMoreIcon size={20} />}
                  </IconButton>
                </ListItemSecondaryAction>
              </ListItem>
              
              <Collapse in={isExpanded}>
                <Box sx={{ p: 3, pt: 0 }}>
                  <Divider sx={{ mb: 3 }} />
                  
                  {renderProviderForm(provider)}
                  
                  <Box sx={{ mt: 3, display: 'flex', gap: 2, alignItems: 'center' }}>
                    <Button
                      variant="contained"
                      startIcon={<SaveIcon size={20} />}
                      onClick={() => handleSaveKeys(provider)}
                      disabled={loading}
                      sx={{
                        backgroundColor: getProviderColor(provider),
                        '&:hover': {
                          opacity: 0.8,
                        }
                      }}
                    >
                      Save Keys
                    </Button>
                    
                    {providerInfo.configured && (
                      <>
                        <Button
                          variant="outlined"
                          color="error"
                          startIcon={<DeleteIcon size={20} />}
                          onClick={() => handleDeleteKeys(provider)}
                          disabled={loading}
                        >
                          Delete Keys
                        </Button>
                        
                        <FormControlLabel
                          control={
                            <Switch
                              checked={providerInfo.enabled}
                              onChange={(e) => handleToggleProvider(provider, e.target.checked)}
                              color="primary"
                            />
                          }
                          label="Enabled"
                        />
                      </>
                    )}
                  </Box>
                </Box>
              </Collapse>
            </Paper>
          );
        })}
      </List>

      <Snackbar
        open={!!message}
        autoHideDuration={6000}
        onClose={() => setMessage(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        {message && (
          <Alert 
            onClose={() => setMessage(null)} 
            severity={message.type} 
            sx={{ width: '100%' }}
          >
            {message.text}
          </Alert>
        )}
      </Snackbar>
    </Box>
  );
};

export default APIKeysSettings;