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
  Tabs,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tooltip,
  Collapse,
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
  Info as InfoIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  CheckCircle as CheckCircleIcon,
  Cancel as CancelIcon,
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

const PLACEHOLDER_DESCRIPTIONS: Record<string, string> = {
  '{business_id}': 'Business ID from Yelp',
  '{lead_id}': 'Unique lead identifier',
  '{business_name}': 'Name of the business',
  '{customer_name}': 'Customer display name',
  '{timestamp}': 'Current date and time',
  '{phone}': 'Customer phone number',
  '{yelp_link}': 'Link to Yelp conversation',
  '{reason}': 'Reason for notification (Phone Found, Customer Reply, Phone Opt-in)'
};

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
  
  // SMS Scenario Settings (початкові значення будуть завантажені з backend)
  const [smsOnPhoneFound, setSmsOnPhoneFound] = useState<boolean>(true);
  const [smsOnCustomerReply, setSmsOnCustomerReply] = useState<boolean>(true);
  const [smsOnPhoneOptIn, setSmsOnPhoneOptIn] = useState<boolean>(true);
  
  // UI State
  const [activeTab, setActiveTab] = useState(0);
  const [showAdvanced, setShowAdvanced] = useState(false);
  
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

  const loadSMSScenarios = async () => {
    if (!businessId) return;
    
    try {
      const params = new URLSearchParams();
      params.append('business_id', businessId);
      
      console.log('[SMS-SCENARIOS] Loading SMS scenarios for business:', businessId);
      
      // Load settings for phone_available=false (Customer Reply + Phone Opt-in)
      const noPhoneResponse = await axios.get(`/settings/auto-response/?${params.toString()}&phone_available=false`);
      console.log('[SMS-SCENARIOS] No phone response:', noPhoneResponse.data);
      if (noPhoneResponse.data) {
        console.log('[SMS-SCENARIOS] Setting smsOnCustomerReply to:', noPhoneResponse.data.sms_on_customer_reply);
        console.log('[SMS-SCENARIOS] Setting smsOnPhoneOptIn to:', noPhoneResponse.data.sms_on_phone_opt_in);
        setSmsOnCustomerReply(noPhoneResponse.data.sms_on_customer_reply !== undefined ? noPhoneResponse.data.sms_on_customer_reply : true);
        setSmsOnPhoneOptIn(noPhoneResponse.data.sms_on_phone_opt_in !== undefined ? noPhoneResponse.data.sms_on_phone_opt_in : true);
      }
      
      // Load settings for phone_available=true (Phone Number Found)
      const phoneResponse = await axios.get(`/settings/auto-response/?${params.toString()}&phone_available=true`);
      console.log('[SMS-SCENARIOS] Phone response:', phoneResponse.data);
      if (phoneResponse.data) {
        console.log('[SMS-SCENARIOS] Setting smsOnPhoneFound to:', phoneResponse.data.sms_on_phone_found);
        setSmsOnPhoneFound(phoneResponse.data.sms_on_phone_found !== undefined ? phoneResponse.data.sms_on_phone_found : true);
      }
      
      console.log('[SMS-SCENARIOS] SMS scenarios loaded successfully');
    } catch (error) {
      console.error('[SMS-SCENARIOS] Failed to load SMS scenarios:', error);
      setError('Failed to load SMS scenario settings');
    }
  };

  const saveSMSScenarios = async (overrides?: {
    smsOnPhoneFound?: boolean;
    smsOnCustomerReply?: boolean;
    smsOnPhoneOptIn?: boolean;
  }) => {
    if (!businessId) return;
    
    // Використовуємо нові значення якщо передані, інакше поточні state
    const phoneFound = overrides?.smsOnPhoneFound !== undefined ? overrides.smsOnPhoneFound : smsOnPhoneFound;
    const customerReply = overrides?.smsOnCustomerReply !== undefined ? overrides.smsOnCustomerReply : smsOnCustomerReply;
    const phoneOptIn = overrides?.smsOnPhoneOptIn !== undefined ? overrides.smsOnPhoneOptIn : smsOnPhoneOptIn;
    
    try {
      const params = new URLSearchParams();
      params.append('business_id', businessId);
      
      console.log('[SMS-SCENARIOS] Saving SMS scenarios...');
      console.log('[SMS-SCENARIOS] - smsOnCustomerReply:', customerReply);
      console.log('[SMS-SCENARIOS] - smsOnPhoneOptIn:', phoneOptIn);
      console.log('[SMS-SCENARIOS] - smsOnPhoneFound:', phoneFound);
      
      // Save settings for phone_available=false (Customer Reply + Phone Opt-in)
      const noPhoneResult = await axios.put(`/settings/auto-response/?${params.toString()}&phone_available=false`, {
        sms_on_customer_reply: customerReply,
        sms_on_phone_opt_in: phoneOptIn,
      });
      console.log('[SMS-SCENARIOS] No phone settings saved:', noPhoneResult.data);
      
      // Save settings for phone_available=true (Phone Number Found)
      const phoneResult = await axios.put(`/settings/auto-response/?${params.toString()}&phone_available=true`, {
        sms_on_phone_found: phoneFound,
      });
      console.log('[SMS-SCENARIOS] Phone settings saved:', phoneResult.data);
      
      setSaved(true);
      console.log('[SMS-SCENARIOS] ✅ SMS scenarios saved successfully');
      
      // ✅ НЕ перезавантажуємо дані одразу - це викликає "стрибки" тумблера
      // Дані будуть перезавантажені при наступному завантаженні сторінки
    } catch (error) {
      console.error('[SMS-SCENARIOS] ❌ Failed to save SMS scenarios:', error);
      setError('Failed to save SMS scenarios');
    }
  };

  useEffect(() => {
    console.log('[NOTIFICATION-SETTINGS] useEffect triggered, businessId:', businessId);
    load();
    loadSMSSettings();
    loadSMSScenarios();
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

  const getScenarioIcon = (scenario: string) => {
    switch (scenario) {
      case 'phone_found': return '📞';
      case 'customer_reply': return '💬';
      case 'phone_opt_in': return '✅';
      default: return '📱';
    }
  };

  const getScenarioName = (scenario: string) => {
    switch (scenario) {
      case 'phone_found': return 'Phone Number Found';
      case 'customer_reply': return 'Customer Reply';
      case 'phone_opt_in': return 'Phone Opt-in';
      default: return 'All Scenarios';
    }
  };

  return (
    <Box sx={{ py: 2, backgroundColor: '#f9fafb', minHeight: '100vh' }}>
      <Container maxWidth="xl">
        {/* Header Bar */}
        <Paper elevation={1} sx={{ p: 2, mb: 3, backgroundColor: '#fff', border: '1px solid #e5e7eb' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <Typography variant="h5" sx={{ fontWeight: 600, color: '#1f2937', fontSize: '18px' }}>
                📱 Twilio SMS Notification Center
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 3 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Typography variant="body2" sx={{ color: '#6b7280', fontSize: '12px' }}>
                  Active: {items.length}
                </Typography>
                <FormControlLabel
                  control={
                    <Switch
                      checked={smsEnabled}
                      onChange={(e) => updateSMSSettings(e.target.checked)}
                      disabled={smsLoading}
                      size="small"
                      sx={{
                        '& .MuiSwitch-thumb': {
                          backgroundColor: smsEnabled ? '#4f46e5' : '#9ca3af',
                        },
                        '& .MuiSwitch-track': {
                          backgroundColor: smsEnabled ? '#c7d2fe' : '#e5e7eb',
                        },
                      }}
                    />
                  }
                  label={
                    <Typography variant="body2" sx={{ fontSize: '12px', fontWeight: 500 }}>
                      {smsEnabled ? 'Enabled' : 'Disabled'}
                    </Typography>
                  }
                  sx={{ m: 0 }}
                />
              </Box>
            </Box>
          </Box>
        </Paper>

        {/* Main Content Grid */}
        <Grid container spacing={3}>
          {/* Left Column - Scenarios */}
          <Grid item xs={12} lg={8}>
            <Paper elevation={1} sx={{ backgroundColor: '#fff', border: '1px solid #e5e7eb' }}>
              {/* Scenario Tabs */}
              <Box sx={{ borderBottom: 1, borderColor: '#e5e7eb' }}>
                <Tabs 
                  value={activeTab} 
                  onChange={(e, newValue) => setActiveTab(newValue)}
                  sx={{
                    '& .MuiTab-root': {
                      fontSize: '14px',
                      fontWeight: 500,
                      textTransform: 'none',
                      minHeight: 48,
                      px: 2,
                    },
                    '& .Mui-selected': {
                      color: '#4f46e5',
                    },
                  }}
                >
                  <Tab 
                    label={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <span>📞</span>
                        <span>Phone Number Found</span>
                      </Box>
                    } 
                  />
                  <Tab 
                    label={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <span>💬</span>
                        <span>Customer Reply</span>
                      </Box>
                    } 
                  />
                  <Tab 
                    label={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <span>✅</span>
                        <span>Phone Opt-in</span>
                      </Box>
                    } 
                  />
                </Tabs>
              </Box>

              {/* Tab Content */}
              <Box sx={{ p: 3 }}>
                {activeTab === 0 && (
                  <Box>
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                      <Typography variant="h6" sx={{ fontSize: '16px', fontWeight: 600, color: '#1f2937' }}>
                        📞 Phone Number Found
                      </Typography>
                      <FormControlLabel
                        control={
                          <Switch 
                            checked={smsOnPhoneFound} 
                            onChange={async (e) => {
                              const newValue = e.target.checked;
                              setSmsOnPhoneFound(newValue);
                              await saveSMSScenarios({ smsOnPhoneFound: newValue });
                            }}
                            size="small"
                            sx={{
                              '& .MuiSwitch-thumb': {
                                backgroundColor: smsOnPhoneFound ? '#4f46e5' : '#9ca3af',
                              },
                              '& .MuiSwitch-track': {
                                backgroundColor: smsOnPhoneFound ? '#c7d2fe' : '#e5e7eb',
                              },
                            }}
                          />
                        }
                        label={
                          <Typography variant="body2" sx={{ fontSize: '12px', fontWeight: 500 }}>
                            {smsOnPhoneFound ? 'Enabled' : 'Disabled'}
                          </Typography>
                        }
                        sx={{ m: 0 }}
                      />
                    </Box>
                    <Typography variant="body2" sx={{ color: '#6b7280', fontSize: '13px', mb: 2 }}>
                      Send SMS when the system finds a phone number in the customer's message text
                    </Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography variant="body2" sx={{ color: '#6b7280', fontSize: '12px' }}>
                        Triggers: phone_in_text=True, phone_in_additional_info=True
                      </Typography>
                      <Tooltip title="This scenario triggers when a phone number is detected in customer messages or additional info">
                        <InfoIcon sx={{ fontSize: 14, color: '#9ca3af' }} />
                      </Tooltip>
                    </Box>
                  </Box>
                )}

                {activeTab === 1 && (
                  <Box>
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                      <Typography variant="h6" sx={{ fontSize: '16px', fontWeight: 600, color: '#1f2937' }}>
                        💬 Customer Reply
                      </Typography>
                      <FormControlLabel
                        control={
                          <Switch 
                            checked={smsOnCustomerReply} 
                            onChange={async (e) => {
                              const newValue = e.target.checked;
                              setSmsOnCustomerReply(newValue);
                              await saveSMSScenarios({ smsOnCustomerReply: newValue });
                            }}
                            size="small"
                            sx={{
                              '& .MuiSwitch-thumb': {
                                backgroundColor: smsOnCustomerReply ? '#4f46e5' : '#9ca3af',
                              },
                              '& .MuiSwitch-track': {
                                backgroundColor: smsOnCustomerReply ? '#c7d2fe' : '#e5e7eb',
                              },
                            }}
                          />
                        }
                        label={
                          <Typography variant="body2" sx={{ fontSize: '12px', fontWeight: 500 }}>
                            {smsOnCustomerReply ? 'Enabled' : 'Disabled'}
                          </Typography>
                        }
                        sx={{ m: 0 }}
                      />
                    </Box>
                    <Typography variant="body2" sx={{ color: '#6b7280', fontSize: '13px', mb: 2 }}>
                      Send SMS when customer responds to messages (even without phone number)
                    </Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography variant="body2" sx={{ color: '#6b7280', fontSize: '12px' }}>
                        Triggers: Customer responds without phone number
                      </Typography>
                      <Tooltip title="This scenario triggers when a customer replies to messages, even if they don't provide a phone number">
                        <InfoIcon sx={{ fontSize: 14, color: '#9ca3af' }} />
                      </Tooltip>
                    </Box>
                  </Box>
                )}

                {activeTab === 2 && (
                  <Box>
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                      <Typography variant="h6" sx={{ fontSize: '16px', fontWeight: 600, color: '#1f2937' }}>
                        ✅ Phone Opt-in
                      </Typography>
                      <FormControlLabel
                        control={
                          <Switch 
                            checked={smsOnPhoneOptIn} 
                            onChange={async (e) => {
                              const newValue = e.target.checked;
                              setSmsOnPhoneOptIn(newValue);
                              await saveSMSScenarios({ smsOnPhoneOptIn: newValue });
                            }}
                            size="small"
                            sx={{
                              '& .MuiSwitch-thumb': {
                                backgroundColor: smsOnPhoneOptIn ? '#4f46e5' : '#9ca3af',
                              },
                              '& .MuiSwitch-track': {
                                backgroundColor: smsOnPhoneOptIn ? '#c7d2fe' : '#e5e7eb',
                              },
                            }}
                          />
                        }
                        label={
                          <Typography variant="body2" sx={{ fontSize: '12px', fontWeight: 500 }}>
                            {smsOnPhoneOptIn ? 'Enabled' : 'Disabled'}
                          </Typography>
                        }
                        sx={{ m: 0 }}
                      />
                    </Box>
                    <Typography variant="body2" sx={{ color: '#6b7280', fontSize: '13px', mb: 2 }}>
                      Send SMS when customer gives consent to use their phone number
                    </Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography variant="body2" sx={{ color: '#6b7280', fontSize: '12px' }}>
                        Triggers: phone_opt_in=True
                      </Typography>
                      <Tooltip title="This scenario triggers when a customer explicitly opts in to provide their phone number">
                        <InfoIcon sx={{ fontSize: 14, color: '#9ca3af' }} />
                      </Tooltip>
                    </Box>
                  </Box>
                )}
              </Box>
            </Paper>

            {/* Active Notifications Table */}
            <Paper elevation={1} sx={{ mt: 3, backgroundColor: '#fff', border: '1px solid #e5e7eb' }}>
              <Box sx={{ p: 2, borderBottom: '1px solid #e5e7eb' }}>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <Typography variant="h6" sx={{ fontSize: '16px', fontWeight: 600, color: '#1f2937' }}>
                    Active Notifications
                  </Typography>
                  <Typography variant="body2" sx={{ color: '#6b7280', fontSize: '12px' }}>
                    {items.length} configured
                  </Typography>
                </Box>
              </Box>

              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow sx={{ backgroundColor: '#f9fafb' }}>
                      <TableCell sx={{ fontSize: '12px', fontWeight: 600, py: 1 }}>Phone</TableCell>
                      <TableCell sx={{ fontSize: '12px', fontWeight: 600, py: 1 }}>Template</TableCell>
                      <TableCell sx={{ fontSize: '12px', fontWeight: 600, py: 1 }}>Scenario</TableCell>
                      <TableCell sx={{ fontSize: '12px', fontWeight: 600, py: 1, textAlign: 'center' }}>Actions</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {items.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={4} sx={{ textAlign: 'center', py: 4, color: '#9ca3af' }}>
                          <MessageIcon sx={{ fontSize: 32, mb: 1, opacity: 0.5 }} />
                          <Typography variant="body2" sx={{ fontSize: '13px' }}>
                            No notifications configured
                          </Typography>
                        </TableCell>
                      </TableRow>
                    ) : (
                      items.map((item) => (
                        <TableRow key={item.id} sx={{ '&:hover': { backgroundColor: '#f9fafb' } }}>
                          <TableCell sx={{ fontSize: '13px', py: 1 }}>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                              <PhoneIcon sx={{ fontSize: 16, color: '#4f46e5' }} />
                              {item.phone_number}
                            </Box>
                          </TableCell>
                          <TableCell sx={{ fontSize: '12px', py: 1, maxWidth: 300 }}>
                            <Typography 
                              variant="body2" 
                              sx={{ 
                                fontFamily: 'monospace',
                                fontSize: '12px',
                                overflow: 'hidden',
                                textOverflow: 'ellipsis',
                                whiteSpace: 'nowrap',
                              }}
                            >
                              {item.message_template}
                            </Typography>
                          </TableCell>
                          <TableCell sx={{ fontSize: '12px', py: 1 }}>
                            <Chip 
                              label="All Scenarios" 
                              size="small" 
                              sx={{ 
                                fontSize: '10px',
                                height: 20,
                                backgroundColor: '#e0e7ff',
                                color: '#3730a3',
                              }} 
                            />
                          </TableCell>
                          <TableCell sx={{ py: 1, textAlign: 'center' }}>
                            <Box sx={{ display: 'flex', justifyContent: 'center', gap: 0.5 }}>
                              <Tooltip title="Edit">
                                <IconButton
                                  size="small"
                                  onClick={() => handleEditOpen(item)}
                                  sx={{ color: '#4f46e5', p: 0.5 }}
                                >
                                  <EditIcon sx={{ fontSize: 16 }} />
                                </IconButton>
                              </Tooltip>
                              <Tooltip title="Delete">
                                <IconButton
                                  size="small"
                                  onClick={() => handleDelete(item.id)}
                                  sx={{ color: '#dc2626', p: 0.5 }}
                                >
                                  <DeleteIcon sx={{ fontSize: 16 }} />
                                </IconButton>
                              </Tooltip>
                            </Box>
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            </Paper>
          </Grid>

          {/* Right Column - Add Notification Form (Sticky) */}
          <Grid item xs={12} lg={4}>
            <Box sx={{ position: 'sticky', top: 20 }}>
              <Paper elevation={1} sx={{ backgroundColor: '#fff', border: '1px solid #e5e7eb' }}>
                <Box sx={{ p: 2, borderBottom: '1px solid #e5e7eb' }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <AddIcon sx={{ fontSize: 18, color: '#4f46e5' }} />
                    <Typography variant="h6" sx={{ fontSize: '16px', fontWeight: 600, color: '#1f2937' }}>
                      Add New Notification
                    </Typography>
                  </Box>
                </Box>

                <Box sx={{ p: 2 }}>
                  <TextField
                    fullWidth
                    label="Phone Number"
                    value={phone}
                    onChange={e => setPhone(e.target.value)}
                    size="small"
                    sx={{ mb: 2 }}
                    InputProps={{
                      startAdornment: (
                        <PhoneIcon sx={{ color: '#9ca3af', mr: 1, fontSize: 18 }} />
                      ),
                    }}
                  />

                  <TextField
                    inputRef={templateRef}
                    fullWidth
                    multiline
                    rows={3}
                    label="Message Template"
                    value={template}
                    onChange={e => setTemplate(e.target.value)}
                    size="small"
                    sx={{ mb: 2 }}
                  />

                  {/* Placeholders */}
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="body2" sx={{ color: '#6b7280', mb: 1, fontSize: '12px', fontWeight: 500 }}>
                      Placeholders:
                    </Typography>
                    <Box sx={{ 
                      display: 'flex', 
                      flexWrap: 'wrap', 
                      gap: 0.5,
                      maxHeight: 80,
                      overflowY: 'auto',
                      border: '1px solid #e5e7eb',
                      borderRadius: 1,
                      p: 1,
                    }}>
                      {PLACEHOLDERS.map(ph => (
                        <Chip
                          key={ph}
                          label={ph}
                          size="small"
                          variant="outlined"
                          clickable
                          onClick={() => insertPlaceholder(ph, 'new')}
                          sx={{
                            fontSize: '10px',
                            height: 20,
                            borderColor: '#4f46e5',
                            color: '#4f46e5',
                            fontFamily: 'monospace',
                            '&:hover': {
                              backgroundColor: '#e0e7ff',
                            },
                          }}
                        />
                      ))}
                    </Box>
                  </Box>

                  {/* Advanced Settings */}
                  <Box sx={{ mb: 2 }}>
                    <Button
                      size="small"
                      onClick={() => setShowAdvanced(!showAdvanced)}
                      endIcon={showAdvanced ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                      sx={{ 
                        fontSize: '12px',
                        textTransform: 'none',
                        color: '#6b7280',
                        p: 0,
                        minWidth: 'auto',
                      }}
                    >
                      Advanced Settings
                    </Button>
                    <Collapse in={showAdvanced}>
                      <Box sx={{ mt: 1, p: 2, backgroundColor: '#f9fafb', borderRadius: 1, border: '1px solid #e5e7eb' }}>
                        <Typography variant="body2" sx={{ color: '#6b7280', fontSize: '12px' }}>
                          Additional configuration options will be available here in future updates.
                        </Typography>
                      </Box>
                    </Collapse>
                  </Box>

                  <Button
                    fullWidth
                    variant="contained"
                    onClick={handleSave}
                    disabled={!phone || !template}
                    sx={{
                      backgroundColor: '#4f46e5',
                      '&:hover': {
                        backgroundColor: '#4338ca',
                      },
                      fontSize: '13px',
                      fontWeight: 500,
                      py: 1,
                    }}
                  >
                    Save Notification
                  </Button>
                </Box>
              </Paper>
            </Box>
          </Grid>
        </Grid>
      </Container>

      {/* Edit Dialog */}
      <Dialog 
        open={Boolean(editing)} 
        onClose={() => setEditing(null)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle sx={{ pb: 1, fontSize: '16px', fontWeight: 600 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <EditIcon sx={{ color: '#4f46e5', fontSize: 20 }} />
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
                <PhoneIcon sx={{ color: '#9ca3af', mr: 1, fontSize: 18 }} />
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
            <Typography variant="body2" sx={{ color: '#6b7280', mb: 1, fontSize: '12px', fontWeight: 500 }}>
              Available placeholders:
            </Typography>
            <Box sx={{ 
              display: 'flex', 
              flexWrap: 'wrap', 
              gap: 0.5,
              maxHeight: 80,
              overflowY: 'auto',
              border: '1px solid #e5e7eb',
              borderRadius: 1,
              p: 1,
            }}>
              {PLACEHOLDERS.map(ph => (
                <Chip
                  key={ph}
                  label={ph}
                  size="small"
                  variant="outlined"
                  clickable
                  onClick={() => insertPlaceholder(ph, 'edit')}
                  sx={{
                    fontSize: '10px',
                    height: 20,
                    borderColor: '#4f46e5',
                    color: '#4f46e5',
                    fontFamily: 'monospace',
                    '&:hover': {
                      backgroundColor: '#e0e7ff',
                    },
                  }}
                />
              ))}
            </Box>
          </Box>
        </DialogContent>

        <DialogActions sx={{ p: 2 }}>
          <Button 
            onClick={() => setEditing(null)} 
            color="inherit"
            sx={{ fontSize: '13px' }}
          >
            Cancel
          </Button>
          <Button
            variant="contained"
            onClick={handleUpdate}
            sx={{
              backgroundColor: '#4f46e5',
              '&:hover': {
                backgroundColor: '#4338ca',
              },
              fontSize: '13px',
            }}
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