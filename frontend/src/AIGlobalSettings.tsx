import React, { FC, useState, useEffect, useRef } from 'react';
import {
  Box,
  Card,
  CardContent,
  CardHeader,
  Typography,
  TextField,
  Button,
  Grid,
  Slider,
  FormControlLabel,
  Switch,
  Divider,
  Alert,
  Snackbar,
  CircularProgress,
  Chip,
  Paper,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Stack,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  FormHelperText,
  LinearProgress,
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  Save as SaveIcon,
  Preview as PreviewIcon,
  Psychology as AIIcon,
  Settings as SettingsIcon,
  Speed as SpeedIcon,
  MessageOutlined as MessageIcon,
  Business as BusinessIcon,
  Person as PersonIcon,
  Security as SecurityIcon,
  Refresh as RefreshIcon,
  CheckCircle as CheckIcon,
  Warning as WarningIcon,
  Info as InfoIcon,
  PlayArrow as TestIcon,
} from '@mui/icons-material';

interface AIGlobalSettingsData {
  id?: number;
  openai_model: string;
  base_system_prompt: string;
  max_message_length: number;
  default_temperature: number;
  always_include_business_name: boolean;
  always_use_customer_name: boolean;
  fallback_to_template: boolean;
  requests_per_minute: number;
  created_at?: string;
  updated_at?: string;
}

interface TestPreviewData {
  test_business_name: string;
  test_customer_name: string;
  test_services: string;
}

const AIGlobalSettings: FC = () => {
  // State for global settings
  const [settings, setSettings] = useState<AIGlobalSettingsData>({
    openai_model: 'gpt-4o',
    base_system_prompt: '',
    max_message_length: 160,
    default_temperature: 0.7,
    always_include_business_name: true,
    always_use_customer_name: true,
    fallback_to_template: true,
    requests_per_minute: 60,
  });

  // UI state
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' as 'success' | 'error' | 'info' });
  
  // Preview and test state
  const [previewMessage, setPreviewMessage] = useState('');
  const [showPreviewDialog, setShowPreviewDialog] = useState(false);
  const [testData, setTestData] = useState<TestPreviewData>({
    test_business_name: 'Priority Remodeling',
    test_customer_name: 'John Smith',
    test_services: 'kitchen remodeling'
  });

  // Reference to initial settings for change detection
  const initialSettings = useRef<AIGlobalSettingsData | null>(null);

  // Available OpenAI models
  const openaiModels = [
    { value: 'gpt-4o', label: 'GPT-4o (Recommended)', description: 'Latest and most capable model' },
    { value: 'gpt-4', label: 'GPT-4', description: 'High quality, slower' },
    { value: 'gpt-3.5-turbo', label: 'GPT-3.5 Turbo', description: 'Fast and cost-effective' },
  ];

  // Load settings on component mount
  useEffect(() => {
    loadSettings();
  }, []);

  // Track changes for unsaved indicator
  useEffect(() => {
    if (initialSettings.current) {
      const hasChanges = JSON.stringify(settings) !== JSON.stringify(initialSettings.current);
      setHasUnsavedChanges(hasChanges);
    }
  }, [settings]);

  const loadSettings = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/webhooks/ai/global-settings/');
      const data = await response.json();
      
      if (data.success) {
        setSettings(data.data);
        initialSettings.current = { ...data.data };
      } else {
        throw new Error(data.error || 'Failed to load settings');
      }
    } catch (error) {
      console.error('Error loading settings:', error);
      setSnackbar({
        open: true,
        message: 'Failed to load global AI settings',
        severity: 'error'
      });
    } finally {
      setLoading(false);
    }
  };

  const saveSettings = async () => {
    setSaving(true);
    try {
      const response = await fetch('/api/webhooks/ai/global-settings/', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(settings),
      });
      
      const data = await response.json();
      
      if (data.success) {
        initialSettings.current = { ...settings };
        setHasUnsavedChanges(false);
        setSnackbar({
          open: true,
          message: data.message || 'Global AI settings saved successfully!',
          severity: 'success'
        });
      } else {
        throw new Error(data.error || 'Failed to save settings');
      }
    } catch (error) {
      console.error('Error saving settings:', error);
      setSnackbar({
        open: true,
        message: 'Failed to save global AI settings',
        severity: 'error'
      });
    } finally {
      setSaving(false);
    }
  };

  const generateTestPreview = async () => {
    setPreviewLoading(true);
    try {
      const response = await fetch('/api/webhooks/ai/test-preview/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...testData,
          ...settings,
        }),
      });
      
      const data = await response.json();
      
      if (data.success) {
        setPreviewMessage(data.preview_message);
        setShowPreviewDialog(true);
      } else {
        throw new Error(data.error || 'Failed to generate preview');
      }
    } catch (error) {
      console.error('Error generating preview:', error);
      setSnackbar({
        open: true,
        message: 'Failed to generate AI preview',
        severity: 'error'
      });
    } finally {
      setPreviewLoading(false);
    }
  };

  const updateSettings = (field: keyof AIGlobalSettingsData, value: any) => {
    setSettings(prev => ({ ...prev, [field]: value }));
  };

  const resetToDefaults = () => {
    const defaultSettings: AIGlobalSettingsData = {
      openai_model: 'gpt-4o',
      base_system_prompt: 'You are a professional business communication assistant. Generate personalized, friendly, and professional greeting messages for potential customers who have inquired about services.',
      max_message_length: 160,
      default_temperature: 0.7,
      always_include_business_name: true,
      always_use_customer_name: true,
      fallback_to_template: true,
      requests_per_minute: 60,
    };
    setSettings(defaultSettings);
  };

  return (
    <Box sx={{ maxWidth: 1200, mx: 'auto', p: 3 }}>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <AIIcon sx={{ fontSize: 32, mr: 2, color: 'primary.main' }} />
          <Typography variant="h4" component="h1">
            Global AI Configuration
          </Typography>
          {hasUnsavedChanges && (
            <Chip
              label="Unsaved Changes"
              color="warning"
              size="small"
              icon={<WarningIcon />}
              sx={{ ml: 2 }}
            />
          )}
        </Box>
        <Typography variant="body1" color="text.secondary">
          Configure global AI settings that apply to all businesses when no custom prompts are specified.
        </Typography>
      </Box>

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
          <CircularProgress />
        </Box>
      ) : (
        <Grid container spacing={3}>
          {/* Main Configuration */}
          <Grid item xs={12} lg={8}>
            <Stack spacing={3}>
              
              {/* OpenAI Model Selection */}
              <Card>
                <CardHeader
                  title={
                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                      <SettingsIcon sx={{ mr: 1 }} />
                      OpenAI Model Configuration
                    </Box>
                  }
                />
                <CardContent>
                  <FormControl fullWidth>
                    <InputLabel>OpenAI Model</InputLabel>
                    <Select
                      value={settings.openai_model}
                      label="OpenAI Model"
                      onChange={(e) => updateSettings('openai_model', e.target.value)}
                    >
                      {openaiModels.map((model) => (
                        <MenuItem key={model.value} value={model.value}>
                          <Box>
                            <Typography variant="body1">{model.label}</Typography>
                            <Typography variant="caption" color="text.secondary">
                              {model.description}
                            </Typography>
                          </Box>
                        </MenuItem>
                      ))}
                    </Select>
                    <FormHelperText>
                      Choose the OpenAI model for message generation. GPT-4o is recommended for best results.
                    </FormHelperText>
                  </FormControl>
                </CardContent>
              </Card>

              {/* Global System Prompt */}
              <Card>
                <CardHeader
                  title={
                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                      <MessageIcon sx={{ mr: 1 }} />
                      Global System Prompt
                    </Box>
                  }
                />
                <CardContent>
                  <TextField
                    label="Base System Prompt"
                    multiline
                    rows={8}
                    fullWidth
                    value={settings.base_system_prompt}
                    onChange={(e) => updateSettings('base_system_prompt', e.target.value)}
                    helperText="This prompt defines the AI's role and behavior. Used when businesses don't have custom prompts."
                    sx={{ mb: 2 }}
                  />
                  
                  <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                    <Chip
                      label="Character count"
                      variant="outlined"
                      size="small"
                      color={settings.base_system_prompt.length > 1000 ? 'warning' : 'default'}
                    />
                    <Typography variant="caption" sx={{ alignSelf: 'center' }}>
                      {settings.base_system_prompt.length} characters
                    </Typography>
                  </Box>
                </CardContent>
              </Card>

              {/* Message Generation Settings */}
              <Card>
                <CardHeader
                  title={
                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                      <SpeedIcon sx={{ mr: 1 }} />
                      Message Generation Settings
                    </Box>
                  }
                />
                <CardContent>
                  <Grid container spacing={3}>
                    <Grid item xs={12} sm={6}>
                      <Typography gutterBottom>
                        Max Message Length: {settings.max_message_length} characters
                      </Typography>
                      <Slider
                        value={settings.max_message_length}
                        onChange={(_, value) => updateSettings('max_message_length', value)}
                        min={100}
                        max={500}
                        step={10}
                        marks={[
                          { value: 160, label: 'SMS (160)' },
                          { value: 300, label: 'Extended' },
                        ]}
                        valueLabelDisplay="auto"
                      />
                    </Grid>
                    
                    <Grid item xs={12} sm={6}>
                      <Typography gutterBottom>
                        Creativity Level: {settings.default_temperature}
                      </Typography>
                      <Slider
                        value={settings.default_temperature}
                        onChange={(_, value) => updateSettings('default_temperature', value)}
                        min={0}
                        max={1}
                        step={0.1}
                        marks={[
                          { value: 0.3, label: 'Conservative' },
                          { value: 0.7, label: 'Balanced' },
                          { value: 1.0, label: 'Creative' },
                        ]}
                        valueLabelDisplay="auto"
                      />
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>

              {/* Business Rules */}
              <Card>
                <CardHeader
                  title={
                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                      <BusinessIcon sx={{ mr: 1 }} />
                      Business Rules
                    </Box>
                  }
                />
                <CardContent>
                  <Stack spacing={2}>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={settings.always_include_business_name}
                          onChange={(e) => updateSettings('always_include_business_name', e.target.checked)}
                        />
                      }
                      label="Always include business name in messages"
                    />
                    
                    <FormControlLabel
                      control={
                        <Switch
                          checked={settings.always_use_customer_name}
                          onChange={(e) => updateSettings('always_use_customer_name', e.target.checked)}
                        />
                      }
                      label="Always use customer name when available"
                    />
                    
                    <FormControlLabel
                      control={
                        <Switch
                          checked={settings.fallback_to_template}
                          onChange={(e) => updateSettings('fallback_to_template', e.target.checked)}
                        />
                      }
                      label="Fallback to template message if AI fails"
                    />
                  </Stack>
                </CardContent>
              </Card>

              {/* Rate Limiting */}
              <Card>
                <CardHeader
                  title={
                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                      <SecurityIcon sx={{ mr: 1 }} />
                      Rate Limiting
                    </Box>
                  }
                />
                <CardContent>
                  <TextField
                    label="Requests per minute"
                    type="number"
                    value={settings.requests_per_minute}
                    onChange={(e) => updateSettings('requests_per_minute', parseInt(e.target.value) || 60)}
                    inputProps={{ min: 1, max: 300 }}
                    helperText="Maximum OpenAI API requests per minute across all businesses"
                    fullWidth
                  />
                </CardContent>
              </Card>

            </Stack>
          </Grid>

          {/* Sidebar */}
          <Grid item xs={12} lg={4}>
            <Stack spacing={3}>

              {/* Quick Actions */}
              <Card>
                <CardHeader title="Quick Actions" />
                <CardContent>
                  <Stack spacing={2}>
                    <Button
                      variant="contained"
                      startIcon={saving ? <CircularProgress size={20} /> : <SaveIcon />}
                      onClick={saveSettings}
                      disabled={saving || !hasUnsavedChanges}
                      fullWidth
                    >
                      {saving ? 'Saving...' : 'Save Global Settings'}
                    </Button>
                    
                    <Button
                      variant="outlined"
                      startIcon={previewLoading ? <CircularProgress size={20} /> : <TestIcon />}
                      onClick={generateTestPreview}
                      disabled={previewLoading}
                      fullWidth
                    >
                      {previewLoading ? 'Testing...' : 'Test AI Preview'}
                    </Button>
                    
                    <Button
                      variant="text"
                      startIcon={<RefreshIcon />}
                      onClick={resetToDefaults}
                      fullWidth
                    >
                      Reset to Defaults
                    </Button>
                  </Stack>
                </CardContent>
              </Card>

              {/* Test Data */}
              <Card>
                <CardHeader title="Test Configuration" />
                <CardContent>
                  <Stack spacing={2}>
                    <TextField
                      label="Test Business Name"
                      value={testData.test_business_name}
                      onChange={(e) => setTestData(prev => ({ ...prev, test_business_name: e.target.value }))}
                      size="small"
                      fullWidth
                    />
                    
                    <TextField
                      label="Test Customer Name"
                      value={testData.test_customer_name}
                      onChange={(e) => setTestData(prev => ({ ...prev, test_customer_name: e.target.value }))}
                      size="small"
                      fullWidth
                    />
                    
                    <TextField
                      label="Test Services"
                      value={testData.test_services}
                      onChange={(e) => setTestData(prev => ({ ...prev, test_services: e.target.value }))}
                      size="small"
                      fullWidth
                    />
                  </Stack>
                </CardContent>
              </Card>

              {/* Current Status */}
              <Card>
                <CardHeader title="Status" />
                <CardContent>
                  <Stack spacing={2}>
                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                      <CheckIcon color="success" sx={{ mr: 1 }} />
                      <Typography variant="body2">Global settings active</Typography>
                    </Box>
                    
                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                      <InfoIcon color="info" sx={{ mr: 1 }} />
                      <Typography variant="body2">
                        Model: {settings.openai_model}
                      </Typography>
                    </Box>
                    
                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                      <InfoIcon color="info" sx={{ mr: 1 }} />
                      <Typography variant="body2">
                        Max length: {settings.max_message_length} chars
                      </Typography>
                    </Box>
                  </Stack>
                </CardContent>
              </Card>

            </Stack>
          </Grid>
        </Grid>
      )}

      {/* Preview Dialog */}
      <Dialog
        open={showPreviewDialog}
        onClose={() => setShowPreviewDialog(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>AI Preview Result</DialogTitle>
        <DialogContent>
          <Paper sx={{ p: 3, mb: 2, backgroundColor: 'grey.50' }}>
            <Typography variant="h6" gutterBottom>Generated Message:</Typography>
            <Typography variant="body1" sx={{ fontFamily: 'monospace', whiteSpace: 'pre-wrap' }}>
              "{previewMessage}"
            </Typography>
          </Paper>
          
          <Typography variant="subtitle2" gutterBottom>Test Data Used:</Typography>
          <List dense>
            <ListItem>
              <ListItemText primary={`Business: ${testData.test_business_name}`} />
            </ListItem>
            <ListItem>
              <ListItemText primary={`Customer: ${testData.test_customer_name}`} />
            </ListItem>
            <ListItem>
              <ListItemText primary={`Services: ${testData.test_services}`} />
            </ListItem>
          </List>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowPreviewDialog(false)}>Close</Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar(prev => ({ ...prev, open: false }))}
      >
        <Alert severity={snackbar.severity} onClose={() => setSnackbar(prev => ({ ...prev, open: false }))}>
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default AIGlobalSettings; 