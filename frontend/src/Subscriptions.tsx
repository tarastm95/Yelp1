import React, { useEffect, useState } from 'react';
import axios from 'axios';
import {
  Container,
  Typography,
  Box,
  TextField,
  Button,
  Paper,
  CircularProgress,
  Card,
  CardContent,
  Grid,
  Stack,
  Chip,
  Avatar,
  Divider,
  Alert,
  Snackbar,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  alpha,
  Fade,
  IconButton,
} from '@mui/material';
import BusinessInfoCard from './BusinessInfoCard';

// Icons
import NotificationsIcon from '@mui/icons-material/Notifications';
import AddIcon from '@mui/icons-material/Add';
import BusinessIcon from '@mui/icons-material/Business';
import DeleteIcon from '@mui/icons-material/Delete';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import WebhookIcon from '@mui/icons-material/Webhook';
import SubscriptionsIcon from '@mui/icons-material/Subscriptions';
import RefreshIcon from '@mui/icons-material/Refresh';
import InfoIcon from '@mui/icons-material/Info';
import CloseIcon from '@mui/icons-material/Close';
import WarningIcon from '@mui/icons-material/Warning';

interface Subscription {
  business_id: string;
  subscribed_at: string;
}

interface Business {
  business_id: string;
  name: string;
  location?: string;
  details?: any;
}

const Subscriptions: React.FC = () => {
  const [subs, setSubs] = useState<Subscription[]>([]);
  const [businesses, setBusinesses] = useState<Business[]>([]);
  const [loading, setLoading] = useState(true);
  const [newBiz, setNewBiz] = useState('');
  const [subscribing, setSubscribing] = useState(false);
  const [unsubscribing, setUnsubscribing] = useState<string | null>(null);
  const [snackbar, setSnackbar] = useState<{open: boolean, message: string, severity: 'success' | 'error'}>({
    open: false,
    message: '',
    severity: 'success'
  });
  const [confirmDialog, setConfirmDialog] = useState<{open: boolean, businessId: string}>({
    open: false,
    businessId: ''
  });

  const loadSubs = () => {
    setLoading(true);
    axios
      .get<{ subscriptions: Subscription[] }>('/businesses/subscriptions/?subscription_type=WEBHOOK')
      .then(res => {
        setSubs(res.data.subscriptions || []);
        if (res.data.subscriptions?.length > 0) {
          setSnackbar({
            open: true,
            message: `Loaded ${res.data.subscriptions.length} subscription(s)`,
            severity: 'success'
          });
        }
        // Load businesses info after loading subscriptions
        loadBusinesses();
      })
      .catch(() => {
        setSubs([]);
        setSnackbar({
          open: true,
          message: 'Failed to load subscriptions',
          severity: 'error'
        });
      })
      .finally(() => setLoading(false));
  };

  const loadBusinesses = () => {
    axios
      .get<Business[]>('/businesses/')
      .then(res => {
        setBusinesses(res.data || []);
      })
      .catch(() => {
        setBusinesses([]);
      });
  };

  useEffect(() => {
    loadSubs();
    loadBusinesses();
  }, []);

  const getBusinessInfo = (businessId: string): Business | null => {
    return businesses.find(b => b.business_id === businessId) || null;
  };

  const handleSubscribe = async () => {
    if (!newBiz.trim()) {
      setSnackbar({
        open: true,
        message: 'Please enter a valid Business ID',
        severity: 'error'
      });
      return;
    }

    // Check if already subscribed
    if (subs.some(s => s.business_id === newBiz.trim())) {
      setSnackbar({
        open: true,
        message: 'Already subscribed to this business',
        severity: 'error'
      });
      return;
    }

    setSubscribing(true);
    try {
      await axios.post('/businesses/subscriptions/', {
        subscription_types: ['WEBHOOK'],
        business_ids: [newBiz.trim()],
      });
      
      setNewBiz('');
      loadSubs();
      loadBusinesses(); // Refresh businesses to get new business info
      setSnackbar({
        open: true,
        message: 'Successfully subscribed to webhook notifications',
        severity: 'success'
      });
    } catch (error) {
      setSnackbar({
        open: true,
        message: 'Failed to subscribe. Please check the Business ID.',
        severity: 'error'
      });
    } finally {
      setSubscribing(false);
    }
  };

  const handleUnsubscribeClick = (businessId: string) => {
    setConfirmDialog({
      open: true,
      businessId
    });
  };

  const handleUnsubscribeConfirm = async () => {
    const businessId = confirmDialog.businessId;
    setUnsubscribing(businessId);
    setConfirmDialog({ open: false, businessId: '' });

    try {
      await axios.delete('/businesses/subscriptions/', {
        data: { subscription_types: ['WEBHOOK'], business_ids: [businessId] },
      });
      
      loadSubs();
      setSnackbar({
        open: true,
        message: 'Successfully unsubscribed from webhook notifications',
        severity: 'success'
      });
    } catch (error) {
      setSnackbar({
        open: true,
        message: 'Failed to unsubscribe',
        severity: 'error'
      });
    } finally {
      setUnsubscribing(null);
    }
  };

  if (loading) {
    return (
      <Box sx={{ 
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)',
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center' 
      }}>
        <CircularProgress size={48} />
      </Box>
    );
  }

  return (
    <Box sx={{ 
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)',
      pb: 6
    }}>
      <Container maxWidth="xl" sx={{ pt: 4 }}>
        {/* Hero Section */}
        <Card 
          elevation={4}
          sx={{ 
            borderRadius: 4,
            overflow: 'hidden',
            mb: 4,
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            color: 'white',
            position: 'relative'
          }}
        >
          <Box
            sx={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              background: 'url("data:image/svg+xml,%3Csvg width="60" height="60" viewBox="0 0 60 60" xmlns="http://www.w3.org/2000/svg"%3E%3Cg fill="none" fill-rule="evenodd"%3E%3Cg fill="%23ffffff" fill-opacity="0.05"%3E%3Ccircle cx="30" cy="30" r="2"/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")',
              opacity: 0.3
            }}
          />
          
          <CardContent sx={{ p: 4, position: 'relative', zIndex: 1 }}>
            <Stack direction={{ xs: 'column', md: 'row' }} spacing={3} alignItems="center">
              {/* Icon */}
              <Avatar
                sx={{
                  width: 100,
                  height: 100,
                  background: 'rgba(255, 255, 255, 0.2)',
                  backdropFilter: 'blur(10px)',
                  border: '4px solid rgba(255, 255, 255, 0.3)',
                  boxShadow: '0 8px 32px rgba(0, 0, 0, 0.1)'
                }}
              >
                <SubscriptionsIcon sx={{ fontSize: '2.5rem', color: 'white' }} />
              </Avatar>
              
              {/* Info */}
              <Box sx={{ flex: 1, textAlign: { xs: 'center', md: 'left' } }}>
                <Typography variant="h3" sx={{ fontWeight: 800, mb: 1 }}>
                  Webhook Subscriptions
                </Typography>
                
                <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ mb: 2 }}>
                  <Chip
                    icon={<WebhookIcon />}
                    label="Real-time Notifications"
                    sx={{
                      background: 'rgba(255, 255, 255, 0.2)',
                      color: 'white',
                      fontWeight: 600,
                      '& .MuiChip-icon': { color: 'white' }
                    }}
                  />
                  
                  <Chip
                    icon={<CheckCircleIcon />}
                    label={`${subs.length} Active Subscription${subs.length !== 1 ? 's' : ''}`}
                    sx={{
                      background: subs.length > 0 
                        ? 'rgba(76, 175, 80, 0.8)' 
                        : 'rgba(158, 158, 158, 0.8)',
                      color: 'white',
                      fontWeight: 600,
                      '& .MuiChip-icon': { color: 'white' }
                    }}
                  />
                </Stack>
                
                <Typography variant="h6" sx={{ opacity: 0.9 }}>
                  Manage your business webhook subscriptions for real-time event notifications
                </Typography>
              </Box>
              
              {/* Refresh Button */}
              <Button
                onClick={loadSubs}
                startIcon={<RefreshIcon />}
                disabled={loading}
                sx={{
                  background: 'rgba(255, 255, 255, 0.2)',
                  backdropFilter: 'blur(10px)',
                  borderRadius: 3,
                  px: 3,
                  py: 1.5,
                  fontWeight: 600,
                  color: 'white',
                  border: '1px solid rgba(255, 255, 255, 0.3)',
                  
                  '&:hover': {
                    background: 'rgba(255, 255, 255, 0.3)',
                    transform: 'translateY(-2px)',
                    boxShadow: '0 8px 24px rgba(255, 255, 255, 0.2)',
                  },
                  
                  '&:disabled': {
                    background: 'rgba(255, 255, 255, 0.1)',
                    color: 'rgba(255, 255, 255, 0.6)'
                  }
                }}
              >
                Refresh
              </Button>
            </Stack>
          </CardContent>
        </Card>

        {/* Add New Subscription */}
        <Card elevation={2} sx={{ borderRadius: 3, mb: 4 }}>
          <Box sx={{ 
            background: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
            p: 2,
            color: 'white'
          }}>
            <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', fontWeight: 600 }}>
              <AddIcon sx={{ mr: 1 }} />
              Add New Subscription
            </Typography>
          </Box>
          
          <CardContent sx={{ p: 3 }}>
            <Grid container spacing={3} alignItems="center">
              <Grid item xs={12} md={8}>
                <TextField
                  fullWidth
                  label="Business ID"
                  placeholder="Enter Yelp Business ID (e.g., abc123def456)"
                  value={newBiz}
                  onChange={e => setNewBiz(e.target.value)}
                  disabled={subscribing}
                  sx={{
                    '& .MuiOutlinedInput-root': {
                      borderRadius: 2,
                      backgroundColor: 'grey.50',
                      '&:hover': {
                        backgroundColor: 'grey.100'
                      },
                      '&.Mui-focused': {
                        backgroundColor: 'white'
                      }
                    }
                  }}
                  InputProps={{
                    startAdornment: (
                      <BusinessIcon sx={{ mr: 1, color: 'grey.500' }} />
                    )
                  }}
                />
              </Grid>
              
              <Grid item xs={12} md={4}>
                <Button
                  variant="contained"
                  onClick={handleSubscribe}
                  disabled={subscribing || !newBiz.trim()}
                  startIcon={subscribing ? <CircularProgress size={20} color="inherit" /> : <AddIcon />}
                  fullWidth
                  sx={{
                    background: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
                    borderRadius: 2,
                    py: 1.5,
                    fontWeight: 600,
                    fontSize: '1rem',
                    textTransform: 'none',
                    boxShadow: '0 4px 16px rgba(67, 233, 123, 0.3)',
                    
                    '&:hover': {
                      background: 'linear-gradient(135deg, #3ad570 0%, #32e6cc 100%)',
                      transform: 'translateY(-2px)',
                      boxShadow: '0 6px 20px rgba(67, 233, 123, 0.4)'
                    },
                    
                    '&:disabled': {
                      background: 'grey.300',
                      color: 'grey.600',
                      transform: 'none',
                      boxShadow: 'none'
                    }
                  }}
                >
                  {subscribing ? 'Subscribing...' : 'Subscribe to Webhooks'}
                </Button>
              </Grid>
            </Grid>
            
            <Alert 
              severity="info" 
              sx={{ mt: 2, borderRadius: 2 }}
              icon={<InfoIcon />}
            >
              Webhooks will notify you in real-time when events occur for the specified business. 
              Make sure you have the correct Business ID from Yelp.
            </Alert>
          </CardContent>
        </Card>

        {/* Statistics Cards */}
        <Grid container spacing={3} sx={{ mb: 4 }}>
          <Grid item xs={12} md={4}>
            <Card elevation={2} sx={{ borderRadius: 3, height: '100%' }}>
              <CardContent sx={{ p: 3, textAlign: 'center' }}>
                <Avatar
                  sx={{
                    width: 64,
                    height: 64,
                    mx: 'auto',
                    mb: 2,
                    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
                  }}
                >
                  <SubscriptionsIcon sx={{ fontSize: '2rem', color: 'white' }} />
                </Avatar>
                
                <Typography variant="h4" sx={{ fontWeight: 700, mb: 1, color: 'primary.main' }}>
                  {subs.length}
                </Typography>
                
                <Typography variant="h6" sx={{ fontWeight: 600, mb: 1 }}>
                  Total Subscriptions
                </Typography>
                
                <Typography variant="body2" color="text.secondary">
                  Active webhook subscriptions
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={4}>
            <Card elevation={2} sx={{ borderRadius: 3, height: '100%' }}>
              <CardContent sx={{ p: 3, textAlign: 'center' }}>
                <Avatar
                  sx={{
                    width: 64,
                    height: 64,
                    mx: 'auto',
                    mb: 2,
                    background: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)'
                  }}
                >
                  <NotificationsIcon sx={{ fontSize: '2rem', color: 'white' }} />
                </Avatar>
                
                <Typography variant="h4" sx={{ fontWeight: 700, mb: 1, color: 'success.main' }}>
                  Real-time
                </Typography>
                
                <Typography variant="h6" sx={{ fontWeight: 600, mb: 1 }}>
                  Notifications
                </Typography>
                
                <Typography variant="body2" color="text.secondary">
                  Instant event delivery
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={4}>
            <Card elevation={2} sx={{ borderRadius: 3, height: '100%' }}>
              <CardContent sx={{ p: 3, textAlign: 'center' }}>
                <Avatar
                  sx={{
                    width: 64,
                    height: 64,
                    mx: 'auto',
                    mb: 2,
                    background: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)'
                  }}
                >
                  <WebhookIcon sx={{ fontSize: '2rem', color: 'white' }} />
                </Avatar>
                
                <Typography variant="h4" sx={{ fontWeight: 700, mb: 1, color: 'warning.main' }}>
                  WEBHOOK
                </Typography>
                
                <Typography variant="h6" sx={{ fontWeight: 600, mb: 1 }}>
                  Type
                </Typography>
                
                <Typography variant="body2" color="text.secondary">
                  Event notification method
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        {/* Subscriptions List */}
        {subs.length === 0 ? (
          <Paper 
            sx={{ 
              p: 6, 
              textAlign: 'center', 
              backgroundColor: 'grey.50',
              borderRadius: 3,
              border: '2px dashed',
              borderColor: 'grey.300'
            }}
          >
            <SubscriptionsIcon sx={{ fontSize: 64, color: 'grey.400', mb: 2 }} />
            <Typography variant="h6" color="text.secondary" sx={{ mb: 1 }}>
              No active subscriptions
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              Add your first business subscription to start receiving webhook notifications
            </Typography>
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={() => document.querySelector('input[placeholder*="Business ID"]')?.focus()}
              sx={{
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                borderRadius: 2,
                px: 4,
                py: 1.5,
                fontWeight: 600,
                '&:hover': {
                  background: 'linear-gradient(135deg, #5a6fd8 0%, #6b4190 100%)',
                  transform: 'translateY(-2px)',
                  boxShadow: 3
                }
              }}
            >
              Add Subscription
            </Button>
          </Paper>
        ) : (
          <Grid container spacing={3}>
            {subs.map(subscription => {
              const subscriptionDate = new Date(subscription.subscribed_at);
              const isRecent = Date.now() - subscriptionDate.getTime() < 24 * 60 * 60 * 1000; // Last 24 hours
              const businessInfo = getBusinessInfo(subscription.business_id);
              
              return (
                <Grid item xs={12} md={6} lg={4} key={subscription.business_id}>
                  <Card
                    elevation={2}
                    sx={{
                      borderRadius: 3,
                      position: 'relative',
                      transition: 'all 0.3s ease-in-out',
                      border: '2px solid',
                      borderColor: 'success.light',
                      background: 'white',
                      
                      '&:hover': {
                        transform: 'translateY(-4px)',
                        boxShadow: '0 8px 32px rgba(76, 175, 80, 0.2)',
                        borderColor: 'success.main'
                      }
                    }}
                  >
                    {/* Status Header */}
                    <Box sx={{ 
                      background: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
                      p: 2,
                      color: 'white'
                    }}>
                      <Stack direction="row" alignItems="center" spacing={2}>
                        <Avatar
                          sx={{
                            background: 'rgba(255, 255, 255, 0.2)',
                            backdropFilter: 'blur(10px)',
                            width: 40,
                            height: 40
                          }}
                        >
                          <WebhookIcon sx={{ color: 'white' }} />
                        </Avatar>
                        
                        <Box sx={{ flex: 1 }}>
                          <Typography variant="h6" sx={{ fontWeight: 700 }}>
                            Business Webhook
                          </Typography>
                          <Typography variant="caption" sx={{ opacity: 0.9 }}>
                            Active subscription
                          </Typography>
                        </Box>
                        
                        {isRecent && (
                          <Chip
                            label="NEW"
                            size="small"
                            sx={{
                              background: 'rgba(255, 255, 255, 0.2)',
                              color: 'white',
                              fontWeight: 600,
                              animation: 'pulse 2s infinite'
                            }}
                          />
                        )}
                      </Stack>
                    </Box>

                    <CardContent sx={{ p: 3 }}>
                      {/* Business Information */}
                      {businessInfo ? (
                        <Box sx={{ mb: 3 }}>
                          <BusinessInfoCard business={businessInfo} />
                        </Box>
                      ) : (
                        <Box sx={{ 
                          p: 2, 
                          backgroundColor: 'grey.50', 
                          borderRadius: 2,
                          border: '1px solid',
                          borderColor: 'grey.200',
                          mb: 2
                        }}>
                          <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
                            BUSINESS ID
                          </Typography>
                          <Typography variant="body1" sx={{ fontWeight: 600, mt: 0.5, fontFamily: 'monospace' }}>
                            {subscription.business_id}
                          </Typography>
                        </Box>
                      )}

                      <Divider sx={{ my: 2 }} />

                      {/* Subscription Date */}
                      <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1 }}>
                        <AccessTimeIcon sx={{ fontSize: 16, color: 'grey.500' }} />
                        <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
                          SUBSCRIBED ON
                        </Typography>
                      </Stack>
                      
                      <Typography variant="body2" sx={{ fontWeight: 500, mb: 3 }}>
                        {subscriptionDate.toLocaleDateString('en-US', {
                          year: 'numeric',
                          month: 'long',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit'
                        })}
                      </Typography>

                      <Divider sx={{ my: 2 }} />

                      {/* Actions */}
                      <Button
                        variant="outlined"
                        color="error"
                        startIcon={unsubscribing === subscription.business_id ? <CircularProgress size={16} color="inherit" /> : <DeleteIcon />}
                        onClick={() => handleUnsubscribeClick(subscription.business_id)}
                        disabled={unsubscribing === subscription.business_id}
                        fullWidth
                        sx={{
                          borderRadius: 2,
                          py: 1.5,
                          fontWeight: 600,
                          textTransform: 'none',
                          borderColor: 'error.light',
                          
                          '&:hover': {
                            borderColor: 'error.main',
                            backgroundColor: 'error.50',
                            transform: 'translateY(-1px)'
                          }
                        }}
                      >
                        {unsubscribing === subscription.business_id ? 'Unsubscribing...' : 'Unsubscribe'}
                      </Button>
                    </CardContent>
                  </Card>
                </Grid>
              );
            })}
          </Grid>
        )}

        {/* Confirmation Dialog */}
        <Dialog
          open={confirmDialog.open}
          onClose={() => setConfirmDialog({ open: false, businessId: '' })}
          maxWidth="sm"
          fullWidth
          PaperProps={{
            sx: {
              borderRadius: 3,
              boxShadow: '0 24px 48px rgba(0, 0, 0, 0.15)'
            }
          }}
        >
          <DialogTitle sx={{ 
            background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
            color: 'white',
            display: 'flex',
            alignItems: 'center'
          }}>
            <WarningIcon sx={{ mr: 1 }} />
            Confirm Unsubscribe
            <IconButton
              onClick={() => setConfirmDialog({ open: false, businessId: '' })}
              sx={{ ml: 'auto', color: 'white' }}
            >
              <CloseIcon />
            </IconButton>
          </DialogTitle>
          
          <DialogContent sx={{ p: 3 }}>
            <Typography variant="body1" sx={{ mb: 2 }}>
              Are you sure you want to unsubscribe from webhook notifications for this business?
            </Typography>
            
            <Box sx={{ 
              p: 2, 
              backgroundColor: 'grey.50', 
              borderRadius: 2,
              border: '1px solid',
              borderColor: 'grey.200'
            }}>
              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
                BUSINESS ID
              </Typography>
              <Typography variant="body1" sx={{ fontWeight: 600, fontFamily: 'monospace' }}>
                {confirmDialog.businessId}
              </Typography>
            </Box>
            
            <Alert severity="warning" sx={{ mt: 2, borderRadius: 2 }}>
              You will no longer receive real-time notifications for events from this business.
            </Alert>
          </DialogContent>
          
          <DialogActions sx={{ p: 3, pt: 0 }}>
            <Button
              onClick={() => setConfirmDialog({ open: false, businessId: '' })}
              variant="outlined"
              sx={{ borderRadius: 2, fontWeight: 600 }}
            >
              Cancel
            </Button>
            <Button
              onClick={handleUnsubscribeConfirm}
              variant="contained"
              color="error"
              sx={{
                borderRadius: 2,
                fontWeight: 600,
                background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
                '&:hover': {
                  background: 'linear-gradient(135deg, #e082ea 0%, #e4485b 100%)'
                }
              }}
            >
              Unsubscribe
            </Button>
          </DialogActions>
        </Dialog>

        {/* Snackbar for notifications */}
        <Snackbar
          open={snackbar.open}
          autoHideDuration={4000}
          onClose={() => setSnackbar(prev => ({ ...prev, open: false }))}
          anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
        >
          <Alert 
            onClose={() => setSnackbar(prev => ({ ...prev, open: false }))}
            severity={snackbar.severity}
            sx={{ borderRadius: 2, boxShadow: 3 }}
          >
            {snackbar.message}
          </Alert>
        </Snackbar>
      </Container>
    </Box>
  );
};

export default Subscriptions;
