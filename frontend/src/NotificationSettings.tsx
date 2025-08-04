import React, { useEffect, useState, useRef } from 'react';
import axios from 'axios';
import {
  Container,
  Paper,
  Typography,
  TextField,
  Button,
  Snackbar,
  Alert,
  Box,
  Stack,
  Chip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Card,
  CardContent,
  Grid,
  Divider,
  Switch,
  FormControlLabel,
  FormGroup,
} from '@mui/material';
import {
  Edit as EditIcon,
  Delete as DeleteIcon,
  Notifications as NotificationsIcon,
  Phone as PhoneIcon,
  Message as MessageIcon,
  Add as AddIcon,
  Save as SaveIcon,
  Close as CloseIcon,
  SmartButton as SmartButtonIcon,
} from '@mui/icons-material';

const PLACEHOLDERS = [
  '{business_id}',
  '{lead_id}',
  '{business_name}',
  '{customer_name}',
  '{timestamp}',
  '{phone}',
  '{yelp_link}',
  '{reason}'
] as const;
type Placeholder = typeof PLACEHOLDERS[number];

interface NotificationSetting {
  id: number;
  phone_number: string;
  message_template: string;
}

interface Props {
  businessId?: string;
}

const NotificationSettings: React.FC<Props> = ({ businessId }) => {
  const [phone, setPhone] = useState('');
  const [template, setTemplate] = useState('');
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState('');
  const [items, setItems] = useState<NotificationSetting[]>([]);
  const [editing, setEditing] = useState<NotificationSetting | null>(null);
  const [editPhone, setEditPhone] = useState('');
  const [editTemplate, setEditTemplate] = useState('');
  const [smsEnabled, setSmsEnabled] = useState<boolean>(false);
  const [smsLoading, setSmsLoading] = useState<boolean>(false);
  const [businessName, setBusinessName] = useState<string>('');
  const templateRef = useRef<HTMLTextAreaElement | null>(null);
  const editTemplateRef = useRef<HTMLTextAreaElement | null>(null);

  const insertPlaceholder = (ph: Placeholder, target: 'new' | 'edit') => {
    const ref = target === 'new' ? templateRef.current : editTemplateRef.current;
    let base = target === 'new' ? template : editTemplate;
    const setter = target === 'new' ? setTemplate : setEditTemplate;
    if (!ref) return;
    const start = ref.selectionStart ?? 0;
    const end = ref.selectionEnd ?? 0;
    const updated = base.slice(0, start) + ph + base.slice(end);
    setter(updated);
    setTimeout(() => {
      ref.focus();
      ref.setSelectionRange(start + ph.length, start + ph.length);
    }, 0);
  };

  const load = () => {
    const params = new URLSearchParams();
    if (businessId) params.append('business_id', businessId);
    axios.get<NotificationSetting[]>(`/notifications/?${params.toString()}`)
      .then(res => setItems(res.data))
      .catch(() => setItems([]));
  };

  const loadSMSSettings = async () => {
    if (!businessId) {
      // Business ID is required - no global settings support
      setSmsEnabled(false);
      setBusinessName('Business Required');
      setError('Business ID is required. SMS notifications are only available for specific businesses.');
      return;
    }
    
    try {
      const params = new URLSearchParams();
      params.append('business_id', businessId);
      const response = await axios.get(`/business-sms-settings/?${params.toString()}`);
      setSmsEnabled(response.data.sms_notifications_enabled);
      setBusinessName(response.data.business_name || businessId);
    } catch (error) {
      console.error('Failed to load SMS settings:', error);
      setSmsEnabled(false);
      setBusinessName(businessId);
    }
  };

  const updateSMSSettings = async (enabled: boolean) => {
    if (!businessId) return;
    
    setSmsLoading(true);
    try {
      const params = new URLSearchParams();
      params.append('business_id', businessId);
      await axios.put(`/business-sms-settings/?${params.toString()}`, {
        sms_notifications_enabled: enabled
      });
      setSmsEnabled(enabled);
      setSaved(true);
    } catch (error) {
      console.error('Failed to update SMS settings:', error);
      setError('Failed to update SMS settings');
    } finally {
      setSmsLoading(false);
    }
  };

  useEffect(() => {
    load();
    loadSMSSettings();
  }, [businessId]);

  const handleSave = async () => {
    if (!businessId) {
      setError('Business ID is required. SMS notifications are only available for specific businesses.');
      return;
    }
    
    if (items.some(i => i.phone_number === phone)) {
      setError('Phone number already exists');
      return;
    }
    
    try {
      const params = new URLSearchParams();
      params.append('business_id', businessId);
      await axios.post(`/notifications/?${params.toString()}`, {
        phone_number: phone,
        message_template: template,
      });
      setSaved(true);
      setPhone('');
      setTemplate('');
      load();
    } catch {
      setError('Failed to save settings');
    }
  };

  const handleEditOpen = (item: NotificationSetting) => {
    setEditing(item);
    setEditPhone(item.phone_number);
    setEditTemplate(item.message_template);
  };

  const handleUpdate = async () => {
    if (!editing) return;
    try {
      const params = new URLSearchParams();
      if (businessId) params.append('business_id', businessId);
      await axios.put(`/notifications/${editing.id}/?${params.toString()}`, {
        phone_number: editPhone,
        message_template: editTemplate,
      });
      setEditing(null);
      setSaved(true);
      load();
    } catch {
      setError('Failed to update settings');
    }
  };

  const handleDelete = async (id: number) => {
    try {
      const params = new URLSearchParams();
      if (businessId) params.append('business_id', businessId);
      await axios.delete(`/notifications/${id}/?${params.toString()}`);
      load();
    } catch {
      setError('Failed to delete');
    }
  };

  return (
    <Box sx={{ py: 2 }}>
      <Container maxWidth="lg">
        {/* Section Header */}
        <Box sx={{ mb: 4, textAlign: 'center' }}>
          <Typography variant="h4" sx={{ fontWeight: 700, color: '#1a1a1a', mb: 1 }}>
            📱 SMS Notification Center
          </Typography>
          <Typography variant="body1" sx={{ color: '#666', maxWidth: 600, mx: 'auto' }}>
            Configure automated SMS notifications to stay informed about new leads and important business events in real-time
          </Typography>
        </Box>

        {/* SMS Enable/Disable Toggle */}
        {businessId && (
          <Paper elevation={2} sx={{ p: 3, mb: 3, border: '2px solid #e8f5e8' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <Box sx={{ 
                  width: 40, 
                  height: 40, 
                  borderRadius: '50%', 
                  backgroundColor: smsEnabled ? '#4caf50' : '#f5f5f5',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  mr: 2
                }}>
                  <NotificationsIcon sx={{ 
                    fontSize: 20, 
                    color: smsEnabled ? 'white' : '#999' 
                  }} />
                </Box>
                <Box>
                  <Typography variant="h6" sx={{ fontWeight: 600, color: '#1a1a1a' }}>
                    SMS Notifications for {businessName}
                  </Typography>
                  <Typography variant="body2" sx={{ color: '#666' }}>
                    {smsEnabled 
                      ? 'SMS notifications are active - you will receive alerts for new leads' 
                      : 'SMS notifications are disabled - no SMS alerts will be sent'
                    }
                  </Typography>
                </Box>
              </Box>
              <FormGroup>
                <FormControlLabel
                  control={
                    <Switch
                      checked={smsEnabled}
                      onChange={(e) => updateSMSSettings(e.target.checked)}
                      disabled={smsLoading}
                      color="success"
                      size="medium"
                    />
                  }
                  label={smsEnabled ? 'Enabled' : 'Disabled'}
                  labelPlacement="start"
                  sx={{ m: 0 }}
                />
              </FormGroup>
            </Box>
          </Paper>
        )}

        {/* Header Section */}
        <Paper elevation={2} sx={{ p: 3, mb: 3, border: '2px solid #e3f2fd' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
            <NotificationsIcon sx={{ fontSize: 28, color: '#1976d2', mr: 2 }} />
            <Box>
              <Typography variant="h5" sx={{ fontWeight: 600, color: '#1a1a1a', mb: 0.5 }}>
                Notification Settings
              </Typography>
              <Typography variant="body2" sx={{ color: '#666' }}>
                Configure SMS notifications to receive real-time updates about new leads
              </Typography>
            </Box>
          </Box>
        </Paper>

        {/* Show notification settings only if SMS is enabled OR it's global settings */}
        {(!businessId || smsEnabled) ? (
          <Grid container spacing={3}>
          {/* Add New Notification */}
          <Grid item xs={12} md={4}>
            <Paper elevation={2} sx={{ p: 3 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
                <AddIcon sx={{ fontSize: 20, color: '#1976d2', mr: 1 }} />
                <Typography variant="h6" sx={{ fontWeight: 600 }}>
                  Add New Notification
                </Typography>
              </Box>

              <TextField
                fullWidth
                label="Phone Number"
                value={phone}
                onChange={e => setPhone(e.target.value)}
                margin="normal"
                variant="outlined"
                size="small"
                InputProps={{
                  startAdornment: (
                    <PhoneIcon sx={{ color: '#666', mr: 1, fontSize: 20 }} />
                  ),
                }}
              />

              <TextField
                inputRef={templateRef}
                fullWidth
                multiline
                rows={4}
                label="Message Template"
                value={template}
                onChange={e => setTemplate(e.target.value)}
                margin="normal"
                variant="outlined"
                size="small"
              />

              <Box sx={{ mt: 2, mb: 2 }}>
                <Typography variant="body2" sx={{ color: '#666', mb: 1, fontWeight: 500 }}>
                  Available placeholders:
                </Typography>
                <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
                  {PLACEHOLDERS.map(ph => (
                    <Chip
                      key={ph}
                      label={ph}
                      size="small"
                      variant="outlined"
                      clickable
                      onClick={() => insertPlaceholder(ph, 'new')}
                      sx={{
                        borderColor: '#1976d2',
                        color: '#1976d2',
                        fontFamily: 'monospace',
                        fontSize: '0.75rem',
                        '&:hover': {
                          backgroundColor: '#e3f2fd',
                        },
                      }}
                    />
                  ))}
                </Stack>
              </Box>

              <Button
                fullWidth
                variant="contained"
                onClick={handleSave}
                startIcon={<SaveIcon />}
                disabled={!phone || !template}
                sx={{ mt: 2 }}
              >
                Save Notification
              </Button>
            </Paper>
          </Grid>

          {/* Existing Notifications */}
          <Grid item xs={12} md={8}>
            <Paper elevation={2} sx={{ p: 3 }}>
              <Box sx={{ mb: 3 }}>
                <Typography variant="h6" sx={{ fontWeight: 600, mb: 1 }}>
                  Active Notifications
                </Typography>
                <Typography variant="body2" sx={{ color: '#666' }}>
                  {items.length} notification{items.length !== 1 ? 's' : ''} configured
                </Typography>
              </Box>

              <Divider sx={{ mb: 2 }} />

              {items.length === 0 ? (
                <Box sx={{ textAlign: 'center', py: 4, color: '#999' }}>
                  <MessageIcon sx={{ fontSize: 48, mb: 1, opacity: 0.5 }} />
                  <Typography variant="body1" sx={{ mb: 0.5 }}>
                    No notifications configured
                  </Typography>
                  <Typography variant="body2">
                    Add your first notification to get started
                  </Typography>
                </Box>
              ) : (
                <Stack spacing={2}>
                  {items.map((item) => (
                    <Card 
                      key={item.id}
                      variant="outlined"
                      sx={{ 
                        border: '1px solid #e0e0e0',
                        '&:hover': {
                          boxShadow: 1,
                        },
                      }}
                    >
                      <CardContent sx={{ p: 2 }}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                          <Box sx={{ flex: 1 }}>
                            <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                              <PhoneIcon sx={{ color: '#1976d2', mr: 1, fontSize: 18 }} />
                              <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                                {item.phone_number}
                              </Typography>
                            </Box>
                            <Box
                              sx={{
                                background: '#f5f5f5',
                                borderRadius: 1,
                                p: 1.5,
                                border: '1px solid #e0e0e0',
                              }}
                            >
                              <Typography 
                                variant="body2" 
                                sx={{ 
                                  color: '#444', 
                                  fontFamily: 'monospace',
                                  fontSize: '0.875rem',
                                  lineHeight: 1.4,
                                }}
                              >
                                {item.message_template}
                              </Typography>
                            </Box>
                          </Box>
                          <Box sx={{ ml: 2, display: 'flex', gap: 0.5 }}>
                            <IconButton
                              size="small"
                              onClick={() => handleEditOpen(item)}
                              sx={{ color: '#1976d2' }}
                            >
                              <EditIcon fontSize="small" />
                            </IconButton>
                            <IconButton
                              size="small"
                              onClick={() => handleDelete(item.id)}
                              sx={{ color: '#d32f2f' }}
                            >
                              <DeleteIcon fontSize="small" />
                            </IconButton>
                          </Box>
                        </Box>
                      </CardContent>
                    </Card>
                  ))}
                </Stack>
              )}
            </Paper>
          </Grid>
        </Grid>
        ) : (
          <Box sx={{ textAlign: 'center', py: 4, color: '#999' }}>
            <MessageIcon sx={{ fontSize: 48, mb: 1, opacity: 0.5 }} />
            <Typography variant="body1" sx={{ mb: 0.5 }}>
              SMS notifications are currently disabled for this business.
            </Typography>
            <Typography variant="body2">
              Please enable SMS notifications in the settings above to configure your notifications.
            </Typography>
          </Box>
        )}
      </Container>

      {/* Edit Dialog */}
      <Dialog 
        open={Boolean(editing)} 
        onClose={() => setEditing(null)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle sx={{ pb: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <EditIcon sx={{ color: '#1976d2', mr: 1 }} />
            Edit Notification
          </Box>
        </DialogTitle>

        <DialogContent sx={{ pt: 1 }}>
          <TextField
            fullWidth
            label="Phone Number"
            value={editPhone}
            onChange={e => setEditPhone(e.target.value)}
            margin="normal"
            variant="outlined"
            size="small"
            InputProps={{
              startAdornment: (
                <PhoneIcon sx={{ color: '#666', mr: 1, fontSize: 20 }} />
              ),
            }}
          />

          <TextField
            inputRef={editTemplateRef}
            fullWidth
            multiline
            rows={4}
            label="Message Template"
            value={editTemplate}
            onChange={e => setEditTemplate(e.target.value)}
            margin="normal"
            variant="outlined"
            size="small"
          />

          <Box sx={{ mt: 2 }}>
            <Typography variant="body2" sx={{ color: '#666', mb: 1, fontWeight: 500 }}>
              Available placeholders:
            </Typography>
            <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
              {PLACEHOLDERS.map(ph => (
                <Chip
                  key={ph}
                  label={ph}
                  size="small"
                  variant="outlined"
                  clickable
                  onClick={() => insertPlaceholder(ph, 'edit')}
                  sx={{
                    borderColor: '#1976d2',
                    color: '#1976d2',
                    fontFamily: 'monospace',
                    fontSize: '0.75rem',
                    '&:hover': {
                      backgroundColor: '#e3f2fd',
                    },
                  }}
                />
              ))}
            </Stack>
          </Box>
        </DialogContent>

        <DialogActions sx={{ p: 2 }}>
          <Button onClick={() => setEditing(null)} color="inherit">
            Cancel
          </Button>
          <Button
            variant="contained"
            onClick={handleUpdate}
            startIcon={<SaveIcon />}
          >
            Save Changes
          </Button>
        </DialogActions>
      </Dialog>

      {/* Success Snackbar */}
      <Snackbar
        open={saved}
        autoHideDuration={3000}
        onClose={() => setSaved(false)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert
          onClose={() => setSaved(false)}
          severity="success"
          sx={{ width: '100%' }}
        >
          Notification settings saved successfully!
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

export default NotificationSettings;
