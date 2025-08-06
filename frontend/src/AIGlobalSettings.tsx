import React, { FC, useState, useEffect, useRef } from 'react';
import {
  Box,
  Card,
  CardContent,
  CardHeader,
  Typography,
  TextField,
  Button,
  FormControlLabel,
  Switch,
  Divider,
  Alert,
  Snackbar,
  CircularProgress,
  Chip,
  Paper,
  Stack,
  IconButton,
  Tooltip,
  LinearProgress,
} from '@mui/material';
import {
  Save as SaveIcon,
  Settings as SettingsIcon,
  Speed as SpeedIcon,
  Business as BusinessIcon,
  Person as PersonIcon,
  Refresh as RefreshIcon,
  Info as InfoIcon,
} from '@mui/icons-material';
import axios from 'axios';

interface AIGlobalSettingsData {
  id?: number;
  // 🔑 Критичні системні налаштування
  base_system_prompt: string;           // Fallback промпт
  always_include_business_name: boolean; // Глобальне правило
  always_use_customer_name: boolean;    // Глобальне правило
  fallback_to_template: boolean;        // Fallback поведінка
  requests_per_minute: number;          // Rate limiting
  created_at?: string;
  updated_at?: string;
  // 🚫 Приховані поля (тепер доступні per-business):
  // openai_model: string;           // → Business AI Settings
  // max_message_length: number;     // → Business AI Settings
  // default_temperature: number;    // → Business AI Settings
}

const AIGlobalSettings: FC = () => {
  // State for global settings
  const [settings, setSettings] = useState<AIGlobalSettingsData>({
    // 🔑 Критичні системні налаштування
    base_system_prompt: '',
    always_include_business_name: true,
    always_use_customer_name: true,
    fallback_to_template: true,
    requests_per_minute: 60,
  });

  // UI state
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [snackbar, setSnackbar] = useState({ 
    open: false, 
    message: '', 
    severity: 'success' as 'success' | 'error' | 'info' 
  });

  const initialSettings = useRef<AIGlobalSettingsData | null>(null);

  // Load global settings
  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    setLoading(true);
    try {
      const response = await axios.get<{success: boolean, data: AIGlobalSettingsData}>('/ai/global-settings/');
      
      if (response.data.success) {
        const data = response.data.data;
        setSettings(data);
        initialSettings.current = { ...data };
        setHasUnsavedChanges(false);
        showSnackbar('Global AI settings loaded successfully', 'success');
      } else {
        throw new Error('Failed to load settings');
      }
    } catch (error) {
      console.error('Error loading global AI settings:', error);
      showSnackbar('Failed to load global AI settings', 'error');
    } finally {
      setLoading(false);
    }
  };

  const saveSettings = async () => {
    setSaving(true);
    try {
      const response = await axios.put<{success: boolean, data: AIGlobalSettingsData}>('/ai/global-settings/', settings);
      
      if (response.data.success) {
        const data = response.data.data;
        setSettings(data);
        initialSettings.current = { ...data };
        setHasUnsavedChanges(false);
        showSnackbar('Global AI settings saved successfully', 'success');
      } else {
        throw new Error('Failed to save settings');
      }
    } catch (error) {
      console.error('Error saving global AI settings:', error);
      showSnackbar('Failed to save global AI settings', 'error');
    } finally {
      setSaving(false);
    }
  };

  const showSnackbar = (message: string, severity: 'success' | 'error' | 'info') => {
    setSnackbar({ open: true, message, severity });
  };

  const handleSettingChange = (field: keyof AIGlobalSettingsData, value: any) => {
    setSettings(prev => ({
      ...prev,
      [field]: value
    }));
    setHasUnsavedChanges(true);
  };

  const handleReset = () => {
    if (initialSettings.current) {
      setSettings({ ...initialSettings.current });
      setHasUnsavedChanges(false);
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ maxWidth: 1000, margin: '0 auto', p: 3 }}>
      {/* Header */}
      <Card sx={{ mb: 3, background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', color: 'white' }}>
        <CardHeader
          avatar={<SettingsIcon sx={{ fontSize: 40 }} />}
          title={
            <Typography variant="h4" component="h1" fontWeight="bold">
              🌍 Global AI Configuration
            </Typography>
          }
          subheader={
            <Typography variant="subtitle1" sx={{ color: 'rgba(255,255,255,0.9)', mt: 1 }}>
              System-wide AI settings and fallback configuration
            </Typography>
          }
        />
      </Card>

      {/* Notice about per-business settings */}
      <Alert severity="info" sx={{ mb: 3 }}>
        <Typography variant="body2">
          <strong>📢 Note:</strong> OpenAI Model, Temperature, and Max Message Length are now configurable 
          per-business in the individual business settings. This page manages system-wide fallback settings.
        </Typography>
      </Alert>

      {/* Core System Settings */}
      <Card sx={{ mb: 3 }}>
        <CardHeader
          title={
            <Stack direction="row" alignItems="center" spacing={1}>
              <SettingsIcon color="primary" />
              <Typography variant="h6">Core System Settings</Typography>
            </Stack>
          }
          subheader="Essential system-wide configuration"
        />
        <CardContent>
          <Stack spacing={3}>
            {/* Base System Prompt */}
            <Box>
              <Typography variant="subtitle2" gutterBottom>
                📝 Fallback System Prompt
              </Typography>
              <TextField
                fullWidth
                multiline
                rows={6}
                value={settings.base_system_prompt}
                onChange={(e) => handleSettingChange('base_system_prompt', e.target.value)}
                placeholder="Enter the fallback system prompt for AI when businesses don't have custom prompts..."
                helperText="Used when businesses don't have custom prompts configured"
                variant="outlined"
              />
            </Box>

            {/* Rate Limiting */}
            <Box>
              <Typography variant="subtitle2" gutterBottom>
                🚦 Rate Limiting
              </Typography>
              <TextField
                type="number"
                value={settings.requests_per_minute}
                onChange={(e) => handleSettingChange('requests_per_minute', parseInt(e.target.value) || 0)}
                label="Requests per minute"
                helperText="Maximum AI API requests per minute (system-wide)"
                inputProps={{ min: 1, max: 1000 }}
                sx={{ width: 250 }}
              />
              <Box sx={{ mt: 1 }}>
                <Chip 
                  icon={<SpeedIcon />}
                  label={`Current: ${settings.requests_per_minute} req/min`}
                  color={settings.requests_per_minute <= 60 ? 'success' : 'warning'}
                  size="small"
                />
              </Box>
            </Box>
          </Stack>
        </CardContent>
      </Card>

      {/* Business Rules */}
      <Card sx={{ mb: 3 }}>
        <CardHeader
          title={
            <Stack direction="row" alignItems="center" spacing={1}>
              <BusinessIcon color="primary" />
              <Typography variant="h6">Global Business Rules</Typography>
            </Stack>
          }
          subheader="Universal rules applied to all AI-generated messages"
        />
        <CardContent>
          <Stack spacing={2}>
            <FormControlLabel
              control={
                <Switch
                  checked={settings.always_include_business_name}
                  onChange={(e) => handleSettingChange('always_include_business_name', e.target.checked)}
                  color="primary"
                />
              }
              label={
                <Box>
                  <Typography variant="body1">Always include business name</Typography>
                  <Typography variant="caption" color="text.secondary">
                    Ensure all AI messages include the business name for branding
                  </Typography>
                </Box>
              }
            />

            <FormControlLabel
              control={
                <Switch
                  checked={settings.always_use_customer_name}
                  onChange={(e) => handleSettingChange('always_use_customer_name', e.target.checked)}
                  color="primary"
                />
              }
              label={
                <Box>
                  <Typography variant="body1">Always use customer name</Typography>
                  <Typography variant="caption" color="text.secondary">
                    Include customer names when available for personalization
                  </Typography>
                </Box>
              }
            />

            <FormControlLabel
              control={
                <Switch
                  checked={settings.fallback_to_template}
                  onChange={(e) => handleSettingChange('fallback_to_template', e.target.checked)}
                  color="primary"
                />
              }
              label={
                <Box>
                  <Typography variant="body1">Fallback to template on AI failure</Typography>
                  <Typography variant="caption" color="text.secondary">
                    Use template messages when AI generation fails
                  </Typography>
                </Box>
              }
            />
          </Stack>
        </CardContent>
      </Card>

      {/* Migration Notice */}
      <Paper sx={{ p: 3, mb: 3, backgroundColor: 'primary.50', border: '1px solid', borderColor: 'primary.200' }}>
        <Stack direction="row" spacing={2} alignItems="flex-start">
          <InfoIcon color="primary" />
          <Box>
            <Typography variant="h6" color="primary" gutterBottom>
              🚀 Enhanced Business-Specific AI Settings
            </Typography>
            <Typography variant="body2" color="text.secondary">
              AI Model, Temperature, and Max Message Length settings have been moved to individual business configurations 
              for better flexibility. Configure these in your business-specific settings for optimal results.
            </Typography>
          </Box>
        </Stack>
      </Paper>

      {/* Action Buttons */}
      <Stack direction="row" spacing={2} justifyContent="space-between" alignItems="center">
        <Stack direction="row" spacing={2}>
          <Button
            variant="contained"
            startIcon={saving ? <CircularProgress size={20} color="inherit" /> : <SaveIcon />}
            onClick={saveSettings}
            disabled={!hasUnsavedChanges || saving}
            size="large"
          >
            {saving ? 'Saving...' : 'Save Settings'}
          </Button>

          {hasUnsavedChanges && (
            <Button
              variant="outlined"
              startIcon={<RefreshIcon />}
              onClick={handleReset}
              disabled={saving}
            >
              Reset Changes
            </Button>
          )}
        </Stack>

        <Tooltip title="Reload settings from server">
          <IconButton onClick={loadSettings} disabled={loading || saving}>
            <RefreshIcon />
          </IconButton>
        </Tooltip>
      </Stack>

      {/* Status Chips */}
      <Stack direction="row" spacing={1} sx={{ mt: 2 }}>
        <Chip 
          label={hasUnsavedChanges ? "Unsaved Changes" : "All Changes Saved"} 
          color={hasUnsavedChanges ? "warning" : "success"} 
          size="small" 
        />
        <Chip 
          label={`${settings.requests_per_minute} req/min limit`} 
          color="info" 
          size="small" 
        />
      </Stack>

      {/* Snackbar */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar(prev => ({ ...prev, open: false }))}
      >
        <Alert 
          onClose={() => setSnackbar(prev => ({ ...prev, open: false }))} 
          severity={snackbar.severity}
          sx={{ width: '100%' }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default AIGlobalSettings;