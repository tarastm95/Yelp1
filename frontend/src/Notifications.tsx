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
  '{timestamp}',
  '{phone}'
] as const;
type Placeholder = typeof PLACEHOLDERS[number];

interface NotificationSetting {
  id: number;
  phone_number: string;
  message_template: string;
}

const Notifications: React.FC = () => {
  const [phone, setPhone] = useState('');
  const [template, setTemplate] = useState('');
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState('');
  const [items, setItems] = useState<NotificationSetting[]>([]);
  const [editing, setEditing] = useState<NotificationSetting | null>(null);
  const [editPhone, setEditPhone] = useState('');
  const [editTemplate, setEditTemplate] = useState('');
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
    axios.get<NotificationSetting[]>('/notifications/')
      .then(res => setItems(res.data))
      .catch(() => setItems([]));
  };

  useEffect(() => {
    load();
  }, []);

  const handleSave = async () => {
    if (items.some(i => i.phone_number === phone)) {
      setError('Phone number already exists');
      return;
    }
    try {
      await axios.post('/notifications/', {
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
      await axios.put(`/notifications/${editing.id}/`, {
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
      await axios.delete(`/notifications/${id}/`);
      load();
    } catch {
      setError('Failed to delete');
    }
  };

  return (
    <Box
      sx={{
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        py: 4,
      }}
    >
      <Container maxWidth="lg">
        {/* Header Section */}
        <Paper
          elevation={0}
          sx={{
            background: 'rgba(255, 255, 255, 0.95)',
            backdropFilter: 'blur(20px)',
            borderRadius: 4,
            p: 4,
            mb: 4,
            border: '1px solid rgba(255, 255, 255, 0.2)',
          }}
        >
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
              <Box
                sx={{
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  borderRadius: '50%',
                  p: 2,
                  mr: 3,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <NotificationsIcon sx={{ color: 'white', fontSize: 32 }} />
              </Box>
              <Box>
                <Typography variant="h3" sx={{ fontWeight: 800, color: '#1a1a1a', mb: 1 }}>
                  Notification Settings
                </Typography>
                <Typography variant="body1" sx={{ color: '#6b7280', maxWidth: 600 }}>
                  Configure SMS notifications to receive real-time updates about new leads and business activities. 
                  Use placeholders to personalize your messages automatically.
                </Typography>
              </Box>
            </Box>
          </Paper>

        <Grid container spacing={4}>
          {/* Existing Notifications */}
          <Grid item xs={12} lg={8}>
            <Paper
              elevation={0}
              sx={{
                background: 'rgba(255, 255, 255, 0.95)',
                backdropFilter: 'blur(20px)',
                borderRadius: 4,
                border: '1px solid rgba(255, 255, 255, 0.2)',
                overflow: 'hidden',
              }}
            >
                <Box
                  sx={{
                    background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
                    p: 3,
                  }}
                >
                  <Typography variant="h5" sx={{ color: 'white', fontWeight: 600 }}>
                    Active Notifications
                  </Typography>
                  <Typography variant="body2" sx={{ color: 'rgba(255, 255, 255, 0.8)', mt: 1 }}>
                    {items.length} notification{items.length !== 1 ? 's' : ''} configured
                  </Typography>
                </Box>

                <Box sx={{ p: 3 }}>
                  {items.length === 0 ? (
                    <Box
                      sx={{
                        textAlign: 'center',
                        py: 6,
                        color: '#6b7280',
                      }}
                    >
                      <MessageIcon sx={{ fontSize: 64, mb: 2, opacity: 0.3 }} />
                      <Typography variant="h6" sx={{ mb: 1 }}>
                        No notifications configured
                      </Typography>
                      <Typography variant="body2">
                        Add your first notification to get started
                      </Typography>
                    </Box>
                  ) : (
                    <Stack spacing={2}>
                      {items.map((item, index) => (
                          <Card key={item.id}
                            elevation={0}
                            sx={{
                              border: '1px solid rgba(0, 0, 0, 0.08)',
                              borderRadius: 3,
                              transition: 'all 0.3s ease',
                              '&:hover': {
                                boxShadow: '0 8px 24px rgba(0, 0, 0, 0.12)',
                                transform: 'translateY(-2px)',
                              },
                            }}
                          >
                            <CardContent sx={{ p: 3 }}>
                              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                                <Box sx={{ flex: 1 }}>
                                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                                    <PhoneIcon sx={{ color: '#667eea', mr: 1 }} />
                                    <Typography variant="h6" sx={{ fontWeight: 600 }}>
                                      {item.phone_number}
                                    </Typography>
                                  </Box>
                                  <Box
                                    sx={{
                                      background: '#f8fafc',
                                      borderRadius: 2,
                                      p: 2,
                                      border: '1px solid #e2e8f0',
                                    }}
                                  >
                                    <Typography variant="body2" sx={{ color: '#475569', fontFamily: 'monospace' }}>
                                      {item.message_template}
                                    </Typography>
                                  </Box>
                                </Box>
                                <Box sx={{ ml: 2 }}>
                                  <IconButton
                                    size="small"
                                    onClick={() => handleEditOpen(item)}
                                    sx={{
                                      color: '#667eea',
                                      '&:hover': {
                                        background: 'rgba(102, 126, 234, 0.1)',
                                      },
                                    }}
                                  >
                                    <EditIcon fontSize="small" />
                                  </IconButton>
                                  <IconButton
                                    size="small"
                                    onClick={() => handleDelete(item.id)}
                                    sx={{
                                      color: '#ef4444',
                                      ml: 1,
                                      '&:hover': {
                                        background: 'rgba(239, 68, 68, 0.1)',
                                      },
                                    }}
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
                </Box>
              </Paper>
          </Grid>

          {/* Add New Notification */}
          <Grid item xs={12} lg={4}>
            <Paper
              elevation={0}
              sx={{
                background: 'rgba(255, 255, 255, 0.95)',
                backdropFilter: 'blur(20px)',
                borderRadius: 4,
                border: '1px solid rgba(255, 255, 255, 0.2)',
                overflow: 'hidden',
              }}
            >
                <Box
                  sx={{
                    background: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
                    p: 3,
                  }}
                >
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <AddIcon sx={{ color: 'white', mr: 1 }} />
                    <Typography variant="h6" sx={{ color: 'white', fontWeight: 600 }}>
                      Add New Notification
                    </Typography>
                  </Box>
                </Box>

                <Box sx={{ p: 3 }}>
                  <TextField
                    fullWidth
                    label="Phone Number"
                    value={phone}
                    onChange={e => setPhone(e.target.value)}
                    margin="normal"
                    variant="outlined"
                    InputProps={{
                      startAdornment: (
                        <PhoneIcon sx={{ color: '#667eea', mr: 1 }} />
                      ),
                    }}
                    sx={{
                      '& .MuiOutlinedInput-root': {
                        borderRadius: 2,
                      },
                    }}
                  />

                  <TextField
                    inputRef={templateRef}
                    fullWidth
                    multiline
                    minRows={4}
                    label="Message Template"
                    value={template}
                    onChange={e => setTemplate(e.target.value)}
                    margin="normal"
                    variant="outlined"
                    sx={{
                      '& .MuiOutlinedInput-root': {
                        borderRadius: 2,
                      },
                    }}
                  />

                  <Box sx={{ mt: 2, mb: 3 }}>
                    <Typography variant="body2" sx={{ color: '#6b7280', mb: 1, fontWeight: 500 }}>
                      Quick Insert:
                    </Typography>
                    <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                      {PLACEHOLDERS.map(ph => (
                        <Chip
                          key={ph}
                          label={ph}
                          size="small"
                          variant="outlined"
                          clickable
                          onClick={() => insertPlaceholder(ph, 'new')}
                          icon={<SmartButtonIcon sx={{ fontSize: 16 }} />}
                          sx={{
                            borderColor: '#667eea',
                            color: '#667eea',
                            fontFamily: 'monospace',
                            fontSize: '0.75rem',
                            '&:hover': {
                              backgroundColor: 'rgba(102, 126, 234, 0.1)',
                              borderColor: '#5a67d8',
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
                    sx={{
                      py: 1.5,
                      borderRadius: 2,
                      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                      '&:hover': {
                        background: 'linear-gradient(135deg, #5a67d8 0%, #6b4190 100%)',
                        transform: 'translateY(-2px)',
                        boxShadow: '0 8px 24px rgba(102, 126, 234, 0.3)',
                      },
                      '&:disabled': {
                        background: '#e2e8f0',
                        color: '#94a3b8',
                      },
                    }}
                  >
                    Save Notification
                  </Button>
                </Box>
              </Paper>
          </Grid>
        </Grid>
      </Container>

      {/* Edit Dialog */}
      <Dialog 
        open={Boolean(editing)} 
        onClose={() => setEditing(null)}
        maxWidth="md"
        fullWidth
        PaperProps={{
          sx: {
            borderRadius: 4,
            overflow: 'hidden',
          },
        }}
      >
        <Box
          sx={{
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            p: 3,
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <EditIcon sx={{ color: 'white', mr: 1 }} />
              <Typography variant="h6" sx={{ color: 'white', fontWeight: 600 }}>
                Edit Notification
              </Typography>
            </Box>
            <IconButton
              onClick={() => setEditing(null)}
              sx={{ color: 'white' }}
            >
              <CloseIcon />
            </IconButton>
          </Box>
        </Box>

        <DialogContent sx={{ p: 3 }}>
          <TextField
            fullWidth
            label="Phone Number"
            value={editPhone}
            onChange={e => setEditPhone(e.target.value)}
            margin="normal"
            variant="outlined"
            InputProps={{
              startAdornment: (
                <PhoneIcon sx={{ color: '#667eea', mr: 1 }} />
              ),
            }}
            sx={{
              '& .MuiOutlinedInput-root': {
                borderRadius: 2,
              },
            }}
          />

          <TextField
            inputRef={editTemplateRef}
            fullWidth
            multiline
            minRows={4}
            label="Message Template"
            value={editTemplate}
            onChange={e => setEditTemplate(e.target.value)}
            margin="normal"
            variant="outlined"
            sx={{
              '& .MuiOutlinedInput-root': {
                borderRadius: 2,
              },
            }}
          />

          <Box sx={{ mt: 2 }}>
            <Typography variant="body2" sx={{ color: '#6b7280', mb: 1, fontWeight: 500 }}>
              Quick Insert:
            </Typography>
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
              {PLACEHOLDERS.map(ph => (
                <Chip
                  key={ph}
                  label={ph}
                  size="small"
                  variant="outlined"
                  clickable
                  onClick={() => insertPlaceholder(ph, 'edit')}
                  icon={<SmartButtonIcon sx={{ fontSize: 16 }} />}
                  sx={{
                    borderColor: '#667eea',
                    color: '#667eea',
                    fontFamily: 'monospace',
                    fontSize: '0.75rem',
                    '&:hover': {
                      backgroundColor: 'rgba(102, 126, 234, 0.1)',
                      borderColor: '#5a67d8',
                    },
                  }}
                />
              ))}
            </Stack>
          </Box>
        </DialogContent>

        <DialogActions sx={{ p: 3, pt: 0 }}>
          <Button
            onClick={() => setEditing(null)}
            sx={{
              color: '#6b7280',
              '&:hover': {
                background: 'rgba(107, 114, 128, 0.1)',
              },
            }}
          >
            Cancel
          </Button>
          <Button
            variant="contained"
            onClick={handleUpdate}
            startIcon={<SaveIcon />}
            sx={{
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              '&:hover': {
                background: 'linear-gradient(135deg, #5a67d8 0%, #6b4190 100%)',
                transform: 'translateY(-2px)',
                boxShadow: '0 8px 24px rgba(102, 126, 234, 0.3)',
              },
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
          sx={{
            width: '100%',
            borderRadius: 2,
            '& .MuiAlert-icon': {
              color: '#43e97b',
            },
          }}
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
          sx={{
            width: '100%',
            borderRadius: 2,
          }}
        >
          {error}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default Notifications;
