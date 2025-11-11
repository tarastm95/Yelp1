import React, { useEffect, useState } from 'react';
import axios from 'axios';
import {
  Container,
  Paper,
  Typography,
  Button,
  Snackbar,
  Alert,
  Box,
  Stack,
  IconButton,
  Card,
  CardContent,
  Grid,
  Divider,
  Switch,
  FormControlLabel,
  Chip,
  CircularProgress,
  Tooltip,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  TextField,
} from '@mui/material';
import {
  WhatsApp as WhatsAppIcon,
  Refresh as RefreshIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Info as InfoIcon,
  Delete as DeleteIcon,
} from '@mui/icons-material';

interface TwilioContentTemplate {
  sid: string;
  friendly_name: string;
  language: string;
  variables: Record<string, string>;
  types: {
    'twilio/text'?: {
      body: string;
    };
  };
  date_created: string;
  date_updated: string;
}

interface WhatsAppNotificationSetting {
  id: number;
  business_id: string;
  content_sid: string;
  content_name: string;
  enabled: boolean;
  variable_mapping: Record<string, string>;
  created_at: string;
  updated_at: string;
}

interface Props {
  businessId?: string;
}

// Available placeholders for WhatsApp templates
const AVAILABLE_PLACEHOLDERS = [
  { key: 'business_id', label: 'Business ID from Yelp', example: 'S4VbIKUr_s7FecEH72n_cA' },
  { key: 'lead_id', label: 'Lead ID (unique identifier)', example: 'NR3EPAbJ2_2VxpYvfs9ELQ' },
  { key: 'business_name', label: 'Business name', example: 'Priority Remodeling' },
  { key: 'customer_name', label: 'Customer display name', example: 'John Doe' },
  { key: 'phone', label: 'Customer phone number', example: '6266022922' },
  { key: 'yelp_link', label: 'Yelp conversation link', example: 'https://biz.yelp.com/...' },
  { key: 'reason', label: 'Reason for notification', example: 'Customer Reply' },
  { key: 'timestamp', label: 'Current date and time', example: '2025-10-25 14:30:00' },
] as const;

const WhatsAppNotificationSettings: React.FC<Props> = ({ businessId }) => {
  const [templates, setTemplates] = useState<TwilioContentTemplate[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<string>('');
  const [templateDetails, setTemplateDetails] = useState<TwilioContentTemplate | null>(null);
  const [loading, setLoading] = useState(false);
  const [saved, setSaved] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');
  const [error, setError] = useState('');
  const [whatsappSettings, setWhatsappSettings] = useState<WhatsAppNotificationSetting[]>([]);
  const [whatsappEnabled, setWhatsappEnabled] = useState(false);
  const [variableMapping, setVariableMapping] = useState<Record<string, string>>({});
  const [phoneNumber, setPhoneNumber] = useState('');

  // Load Twilio Content Templates
  const loadTemplates = async () => {
    if (!businessId) return;
    
    setLoading(true);
    try {
      const response = await axios.get(`/twilio-content-templates/?business_id=${businessId}`);
      setTemplates(response.data.contents || []);
      console.log('[WHATSAPP] Loaded templates:', response.data.contents);
    } catch (err: any) {
      console.error('[WHATSAPP] Failed to load templates:', err);
      setError(err.response?.data?.error || 'Failed to load WhatsApp templates');
    } finally {
      setLoading(false);
    }
  };

  // Load template details
  const loadTemplateDetails = async (contentSid: string) => {
    if (!businessId || !contentSid) return;
    
    setLoading(true);
    try {
      const response = await axios.get(`/twilio-content-templates/${contentSid}/?business_id=${businessId}`);
      setTemplateDetails(response.data);
      
      // Extract variables from template body
      const body = response.data.types?.['twilio/text']?.body || '';
      const variableMatches = body.match(/\{\{(\d+)\}\}/g) || [];
      const variableNumbers = variableMatches.map((m: string) => m.replace(/\{\{|\}\}/g, ''));
      
      // Create default mapping based on common patterns
      const defaultMapping: Record<string, string> = {};
      const commonMappings = ['business_id', 'reason', 'lead_id', 'phone', 'business_name', 'customer_name', 'yelp_link', 'timestamp'];
      
      variableNumbers.forEach((varNum: string, index: number) => {
        if (index < commonMappings.length) {
          defaultMapping[varNum] = commonMappings[index];
        }
      });
      
      setVariableMapping(defaultMapping);
      console.log('[WHATSAPP] Loaded template details:', response.data);
      console.log('[WHATSAPP] Default mapping:', defaultMapping);
    } catch (err: any) {
      console.error('[WHATSAPP] Failed to load template details:', err);
      setError(err.response?.data?.error || 'Failed to load template details');
    } finally {
      setLoading(false);
    }
  };

  // Load WhatsApp notification settings
  const loadWhatsAppSettings = async () => {
    if (!businessId) return;
    
    try {
      const response = await axios.get(`/whatsapp-notifications/?business_id=${businessId}`);
      setWhatsappSettings(response.data || []);
      
      // Check if any setting is enabled
      const hasEnabled = response.data.some((s: WhatsAppNotificationSetting) => s.enabled);
      setWhatsappEnabled(hasEnabled);
      
      console.log('[WHATSAPP] Loaded settings:', response.data);
    } catch (err: any) {
      console.error('[WHATSAPP] Failed to load settings:', err);
    }
  };

  useEffect(() => {
    if (businessId) {
      loadTemplates();
      loadWhatsAppSettings();
    }
  }, [businessId]);

  useEffect(() => {
    if (selectedTemplate) {
      loadTemplateDetails(selectedTemplate);
    }
  }, [selectedTemplate]);

  const handleSaveTemplate = async () => {
    if (!businessId || !selectedTemplate || !templateDetails) {
      setError('Please select a template');
      return;
    }
    
    if (!phoneNumber || phoneNumber.trim() === '') {
      setError('Please enter a phone number');
      return;
    }
    
    setLoading(true);
    try {
      const response = await axios.post(`/whatsapp-notifications/?business_id=${businessId}`, {
        phone_number: phoneNumber.trim(),
        use_content_template: true,
        content_sid: selectedTemplate,
        content_name: templateDetails.friendly_name,
        message_template: '',  // Empty for Content Templates
        variable_mapping: variableMapping,
      });

      console.log('[WHATSAPP] Template saved:', response.data);
      setSuccessMessage('WhatsApp template added successfully!');
      setSaved(true);
      loadWhatsAppSettings();
      setSelectedTemplate('');
      setTemplateDetails(null);
      setVariableMapping({});
      setPhoneNumber('');
    } catch (err: any) {
      console.error('[WHATSAPP] Failed to save template:', err);
      const errorMessage = err.response?.data?.detail
        || err.response?.data?.error 
        || JSON.stringify(err.response?.data) 
        || 'Failed to save template';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleToggleEnabled = async (settingId: number, currentEnabled: boolean) => {
    setLoading(true);
    try {
      await axios.patch(`/whatsapp-notifications/${settingId}/`, {
        enabled: !currentEnabled,
      });

      console.log('[WHATSAPP] Setting toggled');
      loadWhatsAppSettings();
    } catch (err: any) {
      console.error('[WHATSAPP] Failed to toggle setting:', err);
      setError(err.response?.data?.error || 'Failed to update setting');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteSetting = async (settingId: number) => {
    // Find the setting to show its name in confirmation
    const setting = whatsappSettings.find(s => s.id === settingId);
    const templateName = setting?.content_name || 'this template';
    
    if (!window.confirm(`Are you sure you want to delete "${templateName}"?\n\nThis action cannot be undone.`)) {
      return;
    }

    setLoading(true);
    try {
      await axios.delete(`/whatsapp-notifications/${settingId}/`);
      console.log('[WHATSAPP] Setting deleted');
      setSuccessMessage(`Template "${templateName}" deleted successfully!`);
      setSaved(true);
      loadWhatsAppSettings();
    } catch (err: any) {
      console.error('[WHATSAPP] Failed to delete setting:', err);
      const errorMessage = err.response?.data?.detail
        || err.response?.data?.error 
        || 'Failed to delete template';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box sx={{ py: 2, backgroundColor: '#f9fafb', minHeight: '100vh' }}>
      <Container maxWidth="xl">
        {/* Header Bar */}
        <Paper elevation={1} sx={{ p: 2, mb: 3, backgroundColor: '#fff', border: '1px solid #e5e7eb' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <WhatsAppIcon sx={{ color: '#25D366', fontSize: 28 }} />
              <Typography variant="h5" sx={{ fontWeight: 600, color: '#1f2937', fontSize: '18px' }}>
                📱 Twilio WhatsApp Notification Center
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 3 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Typography variant="body2" sx={{ color: '#6b7280', fontSize: '12px' }}>
                  Active: {whatsappSettings.filter(s => s.enabled).length}
                </Typography>
                <FormControlLabel
                  control={
                    <Switch
                      checked={whatsappEnabled}
                      disabled
                      size="small"
                      sx={{
                        '& .MuiSwitch-thumb': {
                          backgroundColor: whatsappEnabled ? '#25D366' : '#9ca3af',
                        },
                        '& .MuiSwitch-track': {
                          backgroundColor: whatsappEnabled ? '#c7f7dc' : '#e5e7eb',
                        },
                      }}
                    />
                  }
                  label={
                    <Typography variant="body2" sx={{ fontSize: '12px', fontWeight: 500 }}>
                      {whatsappEnabled ? 'Enabled' : 'Disabled'}
                    </Typography>
                  }
                  sx={{ m: 0 }}
                />
              </Box>
              <IconButton
                onClick={() => {
                  loadTemplates();
                  loadWhatsAppSettings();
                }}
                disabled={loading}
                size="small"
                sx={{
                  backgroundColor: '#f3f4f6',
                  '&:hover': {
                    backgroundColor: '#e5e7eb',
                  },
                }}
              >
                <RefreshIcon fontSize="small" />
              </IconButton>
            </Box>
          </Box>
        </Paper>

        {/* Main Content Grid */}
        <Grid container spacing={3}>
          {/* Left Column - Add New Template */}
          <Grid item xs={12} lg={6}>
            <Paper elevation={1} sx={{ backgroundColor: '#fff', border: '1px solid #e5e7eb', p: 3 }}>
              <Typography variant="h6" sx={{ fontSize: '16px', fontWeight: 600, color: '#1f2937', mb: 2 }}>
                Add WhatsApp Notification Template
              </Typography>

              <Stack spacing={3}>
                <FormControl fullWidth>
                  <InputLabel>Select Twilio Content Template</InputLabel>
                  <Select
                    value={selectedTemplate}
                    onChange={(e) => setSelectedTemplate(e.target.value)}
                    label="Select Twilio Content Template"
                    disabled={loading}
                  >
                    <MenuItem value="">
                      <em>None</em>
                    </MenuItem>
                    {templates.map((template) => (
                      <MenuItem key={template.sid} value={template.sid}>
                        {template.friendly_name} ({template.language})
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>

                <TextField
                  fullWidth
                  label="Phone Number (WhatsApp)"
                  value={phoneNumber}
                  onChange={(e) => setPhoneNumber(e.target.value)}
                  placeholder="+380XXXXXXXXX"
                  disabled={loading}
                  helperText="Enter phone number in international format (e.g., +380501234567)"
                  InputProps={{
                    startAdornment: (
                      <Box sx={{ mr: 1, display: 'flex', alignItems: 'center' }}>
                        <WhatsAppIcon sx={{ color: '#25D366', fontSize: 20 }} />
                      </Box>
                    ),
                  }}
                />

                {templateDetails && (
                  <Card variant="outlined" sx={{ backgroundColor: '#f9fafb' }}>
                    <CardContent>
                      <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                        Template Preview
                      </Typography>
                      <Typography variant="body2" sx={{ color: '#6b7280', mb: 2, whiteSpace: 'pre-wrap' }}>
                        {templateDetails.types['twilio/text']?.body || 'No content available'}
                          </Typography>

                      {Object.keys(variableMapping).length > 0 && (
                        <>
                          <Divider sx={{ my: 2 }} />
                          <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                            Variable Mapping
                    </Typography>
                          <Typography variant="caption" sx={{ color: '#6b7280', display: 'block', mb: 2 }}>
                            Map template variables to lead data fields
                      </Typography>
                          <Stack spacing={2}>
                            {Object.keys(variableMapping).sort((a, b) => parseInt(a) - parseInt(b)).map((varNum) => (
                              <Box key={varNum}>
                                <Typography variant="caption" sx={{ color: '#6b7280', mb: 0.5, display: 'block' }}>
                                  Variable {`{{${varNum}}}`}
                                </Typography>
                                <FormControl fullWidth size="small">
                                  <Select
                                    value={variableMapping[varNum] || ''}
                                    onChange={(e) => setVariableMapping({
                                      ...variableMapping,
                                      [varNum]: e.target.value
                                    })}
                                    displayEmpty
                                  >
                                    <MenuItem value="">
                                      <em>Select field</em>
                                    </MenuItem>
                                    {AVAILABLE_PLACEHOLDERS.map((placeholder) => (
                                      <MenuItem key={placeholder.key} value={placeholder.key}>
                                        <Box>
                                          <Typography variant="body2">{placeholder.label}</Typography>
                                          <Typography variant="caption" sx={{ color: '#6b7280' }}>
                                            Example: {placeholder.example}
                                          </Typography>
                    </Box>
                                      </MenuItem>
                                    ))}
                                  </Select>
                                </FormControl>
                  </Box>
                            ))}
                          </Stack>
                        </>
                      )}
                    </CardContent>
                  </Card>
                )}

                <Button
                  variant="contained"
                  onClick={handleSaveTemplate}
                  disabled={loading || !selectedTemplate}
                  startIcon={loading ? <CircularProgress size={20} /> : null}
                            sx={{
                    backgroundColor: '#25D366',
                    '&:hover': {
                      backgroundColor: '#1ea952',
                    },
                    fontSize: '13px',
                  }}
                >
                  Add Template
                </Button>
              </Stack>
            </Paper>
          </Grid>

          {/* Right Column - Active Templates */}
          <Grid item xs={12} lg={6}>
            <Paper elevation={1} sx={{ backgroundColor: '#fff', border: '1px solid #e5e7eb', p: 3 }}>
              <Typography variant="h6" sx={{ fontSize: '16px', fontWeight: 600, color: '#1f2937', mb: 2 }}>
                Active WhatsApp Notifications
                          </Typography>

              {loading && whatsappSettings.length === 0 ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
                  <CircularProgress />
                    </Box>
              ) : whatsappSettings.length === 0 ? (
                <Box sx={{ textAlign: 'center', py: 4 }}>
                  <Typography variant="body2" sx={{ color: '#6b7280' }}>
                    No WhatsApp notifications configured yet.
                    </Typography>
                    </Box>
              ) : (
                <Stack spacing={2}>
                  {whatsappSettings.map((setting) => (
                    <Card key={setting.id} variant="outlined">
                      <CardContent>
                        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
                          <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                            {setting.content_name}
                      </Typography>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <FormControlLabel
                        control={
                          <Switch 
                                  checked={setting.enabled}
                                  onChange={() => handleToggleEnabled(setting.id, setting.enabled)}
                            size="small"
                            sx={{
                              '& .MuiSwitch-thumb': {
                                      backgroundColor: setting.enabled ? '#25D366' : '#9ca3af',
                              },
                              '& .MuiSwitch-track': {
                                      backgroundColor: setting.enabled ? '#c7f7dc' : '#e5e7eb',
                              },
                            }}
                          />
                        }
                              label=""
                        sx={{ m: 0 }}
                      />
                            <Tooltip title="Delete template">
                              <IconButton
                                onClick={() => handleDeleteSetting(setting.id)}
                              size="small" 
                              sx={{ 
                                  color: '#ef4444',
                                  '&:hover': {
                                    backgroundColor: '#fee2e2',
                                  }
                                }}
                              >
                                <DeleteIcon fontSize="small" />
                                </IconButton>
                              </Tooltip>
                            </Box>
                  </Box>
                        <Typography variant="caption" sx={{ color: '#6b7280', display: 'block', mb: 1 }}>
                          Content SID: {setting.content_sid}
                    </Typography>
                        
                        {setting.phone_number && (
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 1 }}>
                            <WhatsAppIcon sx={{ color: '#25D366', fontSize: 16 }} />
                            <Typography variant="caption" sx={{ color: '#25D366', fontWeight: 600 }}>
                              {setting.phone_number}
                                </Typography>
                            </Box>
                          )}
                        
                        {setting.variable_mapping && Object.keys(setting.variable_mapping).length > 0 && (
                          <Box sx={{ mt: 1, mb: 1 }}>
                            <Typography variant="caption" sx={{ color: '#6b7280', display: 'block', mb: 0.5 }}>
                              Variable Mapping:
                            </Typography>
                            <Stack direction="row" spacing={0.5} flexWrap="wrap" sx={{ gap: 0.5 }}>
                              {Object.entries(setting.variable_mapping).sort(([a], [b]) => parseInt(a) - parseInt(b)).map(([varNum, field]) => (
                                  <Chip 
                                  key={varNum}
                                  label={`{{${varNum}}} → ${field}`}
                                    size="small" 
                                    sx={{ 
                                    backgroundColor: '#f3f4f6',
                                    color: '#374151',
                                    fontSize: '11px',
                                    height: '20px',
                                    fontFamily: 'monospace',
                                  }}
                                />
                              ))}
                            </Stack>
                            </Box>
                        )}
                        
                            <Chip
                          label={setting.enabled ? 'Active' : 'Inactive'}
                              size="small"
                          icon={setting.enabled ? <CheckCircleIcon /> : <ErrorIcon />}
                              sx={{
                            backgroundColor: setting.enabled ? '#dcfce7' : '#fee2e2',
                            color: setting.enabled ? '#166534' : '#991b1b',
                          }}
                        />
                      </CardContent>
                    </Card>
                  ))}
                </Stack>
              )}
              </Paper>
          </Grid>
        </Grid>

        {/* Info Section */}
        <Paper elevation={1} sx={{ mt: 3, p: 3, backgroundColor: '#eff6ff', border: '1px solid #bfdbfe' }}>
          <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2 }}>
            <InfoIcon sx={{ color: '#3b82f6', mt: 0.5 }} />
            <Box>
              <Typography variant="subtitle2" sx={{ fontWeight: 600, color: '#1e40af', mb: 1 }}>
                About WhatsApp Notifications
            </Typography>
              <Typography variant="body2" sx={{ color: '#1e40af', mb: 1 }}>
                WhatsApp notifications use Twilio Content Templates. These templates must be created and approved in your Twilio account before they can be used here.
              </Typography>
              <Typography variant="body2" sx={{ color: '#1e40af' }}>
                Variables in templates (like {`{{1}}`}, {`{{2}}`}, etc.) will be automatically mapped to lead data when sending notifications.
              </Typography>
            </Box>
          </Box>
        </Paper>
      </Container>

      {/* Success Snackbar */}
      <Snackbar
        open={saved}
        autoHideDuration={3000}
        onClose={() => {
          setSaved(false);
          setSuccessMessage('');
        }}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert
          onClose={() => {
            setSaved(false);
            setSuccessMessage('');
          }}
          severity="success"
          sx={{ width: '100%' }}
        >
          {successMessage || 'Operation completed successfully!'}
        </Alert>
      </Snackbar>

      {/* Error Snackbar */}
      <Snackbar
        open={!!error}
        autoHideDuration={3000}
        onClose={() => setError('')}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert
          onClose={() => setError('')}
          severity="error"
          sx={{ width: '100%' }}
        >
          {error}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default WhatsAppNotificationSettings;
