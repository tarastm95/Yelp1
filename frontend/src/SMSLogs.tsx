import React, { useEffect, useMemo, useState, useRef, useCallback } from 'react';
import axios from 'axios';
import {
  Container,
  Box,
  Typography,
  Tabs,
  Tab,
  CircularProgress,
  Card,
  CardContent,
  Grid,
  Stack,
  Chip,
  Avatar,
  Button,
  Paper,
  Divider,
  Alert,
  Badge,
  IconButton,
  Snackbar,
  alpha,
  Tooltip,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
} from '@mui/material';

// Icons
import SmsIcon from '@mui/icons-material/Sms';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import BusinessIcon from '@mui/icons-material/Business';
import PersonIcon from '@mui/icons-material/Person';
import MessageIcon from '@mui/icons-material/Message';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import RefreshIcon from '@mui/icons-material/Refresh';
import PhoneIcon from '@mui/icons-material/Phone';
import NotificationsIcon from '@mui/icons-material/Notifications';
import ApiIcon from '@mui/icons-material/Api';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import MonetizationOnIcon from '@mui/icons-material/MonetizationOn';

interface SMSLog {
  id: number;
  sid: string;
  to_phone: string;
  from_phone: string;
  body: string;
  lead_id?: string | null;
  business_id?: string | null;
  business_name?: string | null;
  purpose: string;
  status: string;
  error_message?: string | null;
  price?: string | null;
  price_unit?: string | null;
  direction?: string | null;
  sent_at: string;
  twilio_created_at?: string | null;
  updated_at: string;
}

interface Business {
  business_id: string;
  name: string;
  time_zone?: string;
}

interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

const SMSLogs: React.FC = () => {
  const [smsLogs, setSmsLogs] = useState<SMSLog[]>([]);
  const [businesses, setBusinesses] = useState<Business[]>([]);
  const [selectedBusiness, setSelectedBusiness] = useState<string>(''); // '' means "All Businesses"
  const [selectedPurpose, setSelectedPurpose] = useState<string>(''); // '' means "All Purposes"
  const [selectedStatus, setSelectedStatus] = useState<string>(''); // '' means "All Statuses"
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  
  // Infinite scroll state
  const [currentPage, setCurrentPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  
  // Ref for scroll container
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  
  // Statistics state (separate from paginated data)
  const [statistics, setStatistics] = useState({
    successful: 0,
    failed: 0,
    pending: 0,
    total: 0,
    total_cost: 0.0
  });
  
  const [snackbar, setSnackbar] = useState<{open: boolean, message: string, severity: 'success' | 'error'}>({
    open: false,
    message: '',
    severity: 'success'
  });

  const loadData = async () => {
    setRefreshing(true);
    // Reset pagination state
    setCurrentPage(1);
    setHasMore(true);
    
    try {
      // Build query parameters for filtering
      const params = new URLSearchParams();
      params.append('page', '1');
      if (selectedBusiness) params.append('business_id', selectedBusiness);
      if (selectedPurpose) params.append('purpose', selectedPurpose);
      if (selectedStatus) params.append('status', selectedStatus);
      
      const [smsRes, businessesRes] = await Promise.all([
        axios.get<PaginatedResponse<SMSLog>>(`/sms-logs/?${params.toString()}`).catch(() => ({ data: { count: 0, next: null, previous: null, results: [] } })),
        axios.get<Business[]>('/businesses/').catch(() => ({ data: [] }))
      ]);

      setSmsLogs(smsRes.data.results);
      setBusinesses(businessesRes.data);
      
      // Update hasMore state based on API response
      setHasMore(!!smsRes.data.next);
      
      // Load statistics separately from a dedicated endpoint
      const statsParams = new URLSearchParams();
      if (selectedBusiness) statsParams.append('business_id', selectedBusiness);
      if (selectedPurpose) statsParams.append('purpose', selectedPurpose);
      if (selectedStatus) statsParams.append('status', selectedStatus);
      
      try {
        const statsRes = await axios.get(`/sms-logs/stats/?${statsParams.toString()}`);
        setStatistics(statsRes.data);
      } catch (statsError) {
        console.error('Failed to load SMS statistics:', statsError);
        // Fallback to default statistics
        setStatistics({
          successful: 0,
          failed: 0,
          pending: 0,
          total: 0,
          total_cost: 0.0
        });
      }
      
    } catch (error) {
      setSnackbar({
        open: true,
        message: 'Failed to load SMS data',
        severity: 'error'
      });
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const loadMoreSMS = async () => {
    if (loadingMore || !hasMore) return; // Prevent multiple simultaneous requests
    
    setLoadingMore(true);
    
    try {
      const nextPage = currentPage + 1;
      
      // Build query parameters for filtering
      const params = new URLSearchParams();
      params.append('page', nextPage.toString());
      if (selectedBusiness) params.append('business_id', selectedBusiness);
      if (selectedPurpose) params.append('purpose', selectedPurpose);
      if (selectedStatus) params.append('status', selectedStatus);
      
      const response = await axios.get<PaginatedResponse<SMSLog>>(
        `/sms-logs/?${params.toString()}`
      );
      
      const newSMS = response.data.results;
      const hasMoreData = !!response.data.next;
      
      // Append new SMS to existing list
      setSmsLogs(prev => [...prev, ...newSMS]);
      setCurrentPage(nextPage);
      setHasMore(hasMoreData);
      
    } catch (error) {
      console.error('Failed to load more SMS:', error);
      setSnackbar({
        open: true,
        message: 'Failed to load more SMS',
        severity: 'error'
      });
    } finally {
      setLoadingMore(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [selectedBusiness, selectedPurpose, selectedStatus]); // Re-load data when filters change

  // Scroll listener for infinite scroll
  const handleScroll = useCallback(() => {
    const container = scrollContainerRef.current;
    if (!container) return;
    
    const { scrollTop, scrollHeight, clientHeight } = container;
    const isNearBottom = scrollTop + clientHeight >= scrollHeight - 200; // 200px threshold
    
    if (isNearBottom && !loadingMore && hasMore) {
      loadMoreSMS();
    }
  }, [loadingMore, hasMore, loadMoreSMS]);

  useEffect(() => {
    const container = scrollContainerRef.current;
    if (container) {
      container.addEventListener('scroll', handleScroll);
      return () => container.removeEventListener('scroll', handleScroll);
    }
  }, [handleScroll]);

  const tzMap = useMemo(() => {
    const map: Record<string, string> = {};
    businesses.forEach(b => {
      if (b.time_zone) map[b.business_id] = b.time_zone;
    });
    return map;
  }, [businesses]);

  const bizNameMap = useMemo(() => {
    const map: Record<string, string> = {};
    businesses.forEach(b => {
      map[b.business_id] = b.name;
    });
    return map;
  }, [businesses]);

  const getBusinessName = (bid?: string | null) => {
    if (!bid) return 'Unknown Business';
    return bizNameMap[bid] || bid;
  };

  const formatDateTime = (dateStr: string, bizId?: string | null) => {
    if (!dateStr) return '—';
    const date = new Date(dateStr);
    const tz = bizId ? tzMap[bizId] : undefined;
    return tz
      ? date.toLocaleString(undefined, { timeZone: tz })
      : date.toLocaleString();
  };

  const getStatusInfo = (status: string) => {
    switch (status.toLowerCase()) {
      case 'sent':
      case 'delivered':
        return { color: 'success', icon: CheckCircleIcon, label: 'Sent' };
      case 'failed':
      case 'undelivered':
        return { color: 'error', icon: ErrorIcon, label: 'Failed' };
      default:
        return { color: 'default', icon: SmsIcon, label: status };
    }
  };

  const getPurposeInfo = (purpose: string) => {
    switch (purpose.toLowerCase()) {
      case 'notification':
        return { color: 'info', icon: NotificationsIcon, label: 'Notification' };
      case 'auto_response':
        return { color: 'primary', icon: AutoAwesomeIcon, label: 'Auto Response' };
      case 'api':
        return { color: 'secondary', icon: ApiIcon, label: 'API' };
      case 'manual':
        return { color: 'default', icon: PersonIcon, label: 'Manual' };
      default:
        return { color: 'default', icon: SmsIcon, label: purpose || 'Unknown' };
    }
  };

  // Use statistics from API instead of calculating from loaded SMS
  const totalSMS = statistics.total;
  const sentSMS = statistics.successful;
  const failedSMS = statistics.failed;
  const pendingSMS = statistics.pending;
  const totalCost = statistics.total_cost;

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
                <SmsIcon sx={{ fontSize: '2.5rem', color: 'white' }} />
              </Avatar>
              
              {/* Info */}
              <Box sx={{ flex: 1, textAlign: { xs: 'center', md: 'left' } }}>
                <Typography variant="h3" sx={{ fontWeight: 800, mb: 1 }}>
                  SMS Logs
                </Typography>
                
                <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ mb: 2 }}>
                  <Chip
                    icon={<SmsIcon />}
                    label="SMS Management"
                    sx={{
                      background: 'rgba(255, 255, 255, 0.2)',
                      color: 'white',
                      fontWeight: 600,
                      '& .MuiChip-icon': { color: 'white' }
                    }}
                  />
                  
                  <Chip
                    icon={<TrendingUpIcon />}
                    label={`${totalSMS} ${(selectedBusiness || selectedPurpose || selectedStatus) ? 'Filtered' : 'Total'} SMS`}
                    sx={{
                      background: 'rgba(255, 255, 255, 0.2)',
                      color: 'white',
                      fontWeight: 600,
                      '& .MuiChip-icon': { color: 'white' }
                    }}
                  />
                </Stack>
                
                <Typography variant="h6" sx={{ opacity: 0.9 }}>
                  {selectedBusiness 
                    ? `Viewing SMS for: ${businesses.find(b => b.business_id === selectedBusiness)?.name || selectedBusiness}`
                    : 'Track and monitor all SMS messages sent through the system'
                  }
                </Typography>
              </Box>
              
              {/* Refresh Button */}
              <Button
                onClick={loadData}
                startIcon={refreshing ? <CircularProgress size={20} color="inherit" /> : <RefreshIcon />}
                disabled={refreshing}
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
                {refreshing ? 'Refreshing...' : 'Refresh'}
              </Button>
            </Stack>
          </CardContent>
        </Card>

        {/* Filters */}
        <Card elevation={2} sx={{ borderRadius: 3, mb: 4 }}>
          <CardContent sx={{ p: 3 }}>
            <Stack direction={{ xs: 'column', md: 'row' }} spacing={3} alignItems="center">
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <Avatar
                  sx={{
                    width: 48,
                    height: 48,
                    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                    mr: 2
                  }}
                >
                  <SmsIcon sx={{ fontSize: '1.5rem', color: 'white' }} />
                </Avatar>
                <Box>
                  <Typography variant="h6" sx={{ fontWeight: 600, mb: 0.5 }}>
                    Filter SMS Logs
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Filter by business, purpose, or status
                  </Typography>
                </Box>
              </Box>
              
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ flex: 1 }}>
                {/* Business Filter */}
                <FormControl sx={{ minWidth: 200 }}>
                  <InputLabel id="business-filter-label">Business</InputLabel>
                  <Select
                    labelId="business-filter-label"
                    value={selectedBusiness}
                    label="Business"
                    onChange={(e) => setSelectedBusiness(e.target.value)}
                    sx={{ borderRadius: 2 }}
                  >
                    <MenuItem value="">
                      <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        <AutoAwesomeIcon sx={{ mr: 1, color: 'primary.main' }} />
                        <Typography sx={{ fontWeight: 600 }}>All Businesses</Typography>
                      </Box>
                    </MenuItem>
                    {businesses.map(business => (
                      <MenuItem key={business.business_id} value={business.business_id}>
                        <Box sx={{ display: 'flex', alignItems: 'center' }}>
                          <BusinessIcon sx={{ mr: 1, color: 'text.secondary' }} />
                          <Typography>{business.name}</Typography>
                        </Box>
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>

                {/* Purpose Filter */}
                <FormControl sx={{ minWidth: 150 }}>
                  <InputLabel id="purpose-filter-label">Purpose</InputLabel>
                  <Select
                    labelId="purpose-filter-label"
                    value={selectedPurpose}
                    label="Purpose"
                    onChange={(e) => setSelectedPurpose(e.target.value)}
                    sx={{ borderRadius: 2 }}
                  >
                    <MenuItem value="">All Purposes</MenuItem>
                    <MenuItem value="notification">
                      <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        <NotificationsIcon sx={{ mr: 1, color: 'info.main' }} />
                        Notification
                      </Box>
                    </MenuItem>
                    <MenuItem value="auto_response">
                      <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        <AutoAwesomeIcon sx={{ mr: 1, color: 'primary.main' }} />
                        Auto Response
                      </Box>
                    </MenuItem>
                    <MenuItem value="api">
                      <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        <ApiIcon sx={{ mr: 1, color: 'secondary.main' }} />
                        API
                      </Box>
                    </MenuItem>
                    <MenuItem value="manual">
                      <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        <PersonIcon sx={{ mr: 1, color: 'text.secondary' }} />
                        Manual
                      </Box>
                    </MenuItem>
                  </Select>
                </FormControl>

                {/* Status Filter */}
                <FormControl sx={{ minWidth: 120 }}>
                  <InputLabel id="status-filter-label">Status</InputLabel>
                  <Select
                    labelId="status-filter-label"
                    value={selectedStatus}
                    label="Status"
                    onChange={(e) => setSelectedStatus(e.target.value)}
                    sx={{ borderRadius: 2 }}
                  >
                    <MenuItem value="">All Status</MenuItem>
                    <MenuItem value="sent">
                      <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        <CheckCircleIcon sx={{ mr: 1, color: 'success.main' }} />
                        Sent
                      </Box>
                    </MenuItem>
                    <MenuItem value="failed">
                      <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        <ErrorIcon sx={{ mr: 1, color: 'error.main' }} />
                        Failed
                      </Box>
                    </MenuItem>
                  </Select>
                </FormControl>
              </Stack>
              
              {/* Active Filters Chips */}
              {(selectedBusiness || selectedPurpose || selectedStatus) && (
                <Stack direction="row" spacing={1} flexWrap="wrap">
                  {selectedBusiness && (
                    <Chip
                      label={`Business: ${businesses.find(b => b.business_id === selectedBusiness)?.name || selectedBusiness}`}
                      color="primary"
                      variant="outlined"
                      size="small"
                      onDelete={() => setSelectedBusiness('')}
                    />
                  )}
                  {selectedPurpose && (
                    <Chip
                      label={`Purpose: ${selectedPurpose}`}
                      color="primary"
                      variant="outlined"
                      size="small"
                      onDelete={() => setSelectedPurpose('')}
                    />
                  )}
                  {selectedStatus && (
                    <Chip
                      label={`Status: ${selectedStatus}`}
                      color="primary"
                      variant="outlined"
                      size="small"
                      onDelete={() => setSelectedStatus('')}
                    />
                  )}
                </Stack>
              )}
            </Stack>
          </CardContent>
        </Card>

        {/* Statistics Cards */}
        <Grid container spacing={3} sx={{ mb: 4 }}>
          <Grid item xs={12} md={3}>
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
                  <CheckCircleIcon sx={{ fontSize: '2rem', color: 'white' }} />
                </Avatar>
                
                <Typography variant="h4" sx={{ fontWeight: 700, mb: 1, color: 'success.main' }}>
                  {sentSMS}
                </Typography>
                
                <Typography variant="h6" sx={{ fontWeight: 600, mb: 1 }}>
                  Sent Successfully
                </Typography>
                
                <Typography variant="body2" color="text.secondary">
                  Successfully sent SMS ({pendingSMS} pending)
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={3}>
            <Card elevation={2} sx={{ borderRadius: 3, height: '100%' }}>
              <CardContent sx={{ p: 3, textAlign: 'center' }}>
                <Avatar
                  sx={{
                    width: 64,
                    height: 64,
                    mx: 'auto',
                    mb: 2,
                    background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)'
                  }}
                >
                  <ErrorIcon sx={{ fontSize: '2rem', color: 'white' }} />
                </Avatar>
                
                <Typography variant="h4" sx={{ fontWeight: 700, mb: 1, color: 'error.main' }}>
                  {failedSMS}
                </Typography>
                
                <Typography variant="h6" sx={{ fontWeight: 600, mb: 1 }}>
                  Failed
                </Typography>
                
                <Typography variant="body2" color="text.secondary">
                  Failed or undelivered SMS
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={3}>
            <Card elevation={2} sx={{ borderRadius: 3, height: '100%' }}>
              <CardContent sx={{ p: 3, textAlign: 'center' }}>
                <Avatar
                  sx={{
                    width: 64,
                    height: 64,
                    mx: 'auto',
                    mb: 2,
                    background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)'
                  }}
                >
                  <SmsIcon sx={{ fontSize: '2rem', color: 'white' }} />
                </Avatar>
                
                <Typography variant="h4" sx={{ fontWeight: 700, mb: 1, color: 'info.main' }}>
                  {totalSMS}
                </Typography>
                
                <Typography variant="h6" sx={{ fontWeight: 600, mb: 1 }}>
                  Total SMS
                </Typography>
                
                <Typography variant="body2" color="text.secondary">
                  All messages sent
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={3}>
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
                  <MonetizationOnIcon sx={{ fontSize: '2rem', color: 'white' }} />
                </Avatar>
                
                <Typography variant="h4" sx={{ fontWeight: 700, mb: 1, color: 'warning.main' }}>
                  ${totalCost.toFixed(3)}
                </Typography>
                
                <Typography variant="h6" sx={{ fontWeight: 600, mb: 1 }}>
                  Total Cost
                </Typography>
                
                <Typography variant="body2" color="text.secondary">
                  SMS expenses
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        {/* SMS List */}
        <Card elevation={2} sx={{ borderRadius: 3, mb: 4 }}>
          <CardContent sx={{ p: 3 }}>
            <Typography variant="h6" sx={{ fontWeight: 600, mb: 3 }}>
              SMS Messages ({totalSMS} total, {smsLogs.length} loaded)
            </Typography>
            
            {/* Scrollable container for SMS list */}
            <Box 
              ref={scrollContainerRef}
              sx={{
                maxHeight: '70vh',
                overflowY: 'auto',
                '&::-webkit-scrollbar': {
                  width: '8px',
                },
                '&::-webkit-scrollbar-track': {
                  background: '#f1f1f1',
                  borderRadius: '4px',
                },
                '&::-webkit-scrollbar-thumb': {
                  background: '#888',
                  borderRadius: '4px',
                },
                '&::-webkit-scrollbar-thumb:hover': {
                  background: '#555',
                },
              }}
            >
              {/* Empty State */}
              {smsLogs.length === 0 ? (
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
                <SmsIcon sx={{ fontSize: 64, color: 'grey.400', mb: 2 }} />
                
                <Typography variant="h6" color="text.secondary" sx={{ mb: 1 }}>
                  No SMS messages{(selectedBusiness || selectedPurpose || selectedStatus) ? ' for current filters' : ''}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {(selectedBusiness || selectedPurpose || selectedStatus)
                    ? 'Try adjusting your filters to see more results'
                    : 'No SMS messages have been sent yet'
                  }
                </Typography>
              </Paper>
            ) : (
              /* SMS List */
              <Stack spacing={3}>
                {smsLogs.map(sms => {
                  const statusInfo = getStatusInfo(sms.status);
                  const purposeInfo = getPurposeInfo(sms.purpose);
                  const StatusIcon = statusInfo.icon;
                  const PurposeIcon = purposeInfo.icon;
                  
                  return (
                    <Card
                      key={sms.id}
                      elevation={2}
                      sx={{
                        borderRadius: 3,
                        transition: 'all 0.3s ease-in-out',
                        border: '2px solid',
                        borderColor: `${statusInfo.color}.light`,
                        
                        '&:hover': {
                          transform: 'translateY(-2px)',
                          boxShadow: `0 8px 32px ${alpha(statusInfo.color === 'success' ? '#4caf50' : 
                                                         statusInfo.color === 'error' ? '#f44336' : '#666', 0.2)}`,
                          borderColor: `${statusInfo.color}.main`
                        }
                      }}
                    >
                      {/* Status Header */}
                      <Box sx={{ 
                        background: statusInfo.color === 'success' ? 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)' :
                                   statusInfo.color === 'error' ? 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)' :
                                   'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
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
                            <StatusIcon sx={{ color: 'white' }} />
                          </Avatar>
                          
                          <Box sx={{ flex: 1 }}>
                            <Typography variant="h6" sx={{ fontWeight: 700 }}>
                              SMS to {sms.to_phone}
                            </Typography>
                            <Typography variant="caption" sx={{ opacity: 0.9 }}>
                              SID: {sms.sid.slice(0, 16)}...
                            </Typography>
                          </Box>
                          
                          <Stack direction="row" spacing={1}>
                            <Chip
                              icon={<PurposeIcon />}
                              label={purposeInfo.label}
                              size="small"
                              sx={{
                                background: 'rgba(255, 255, 255, 0.2)',
                                color: 'white',
                                fontWeight: 600,
                                '& .MuiChip-icon': { color: 'white' }
                              }}
                            />
                            <Chip
                              label={statusInfo.label}
                              size="small"
                              sx={{
                                background: 'rgba(255, 255, 255, 0.2)',
                                color: 'white',
                                fontWeight: 600
                              }}
                            />
                          </Stack>
                        </Stack>
                      </Box>

                      <CardContent sx={{ p: 3 }}>
                        {/* Lead & Business Info */}
                        <Grid container spacing={2} sx={{ mb: 2 }}>
                          <Grid item xs={12} md={6}>
                            <Box sx={{ 
                              p: 2, 
                              backgroundColor: 'grey.50', 
                              borderRadius: 2,
                              border: '1px solid',
                              borderColor: 'grey.200'
                            }}>
                              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600, display: 'flex', alignItems: 'center' }}>
                                <PersonIcon sx={{ fontSize: 14, mr: 0.5 }} />
                                LEAD ID
                              </Typography>
                              <Typography variant="body2" sx={{ fontWeight: 600, mt: 0.5, fontFamily: 'monospace' }}>
                                {sms.lead_id || 'N/A'}
                              </Typography>
                            </Box>
                          </Grid>
                          
                          <Grid item xs={12} md={6}>
                            <Box sx={{ 
                              p: 2, 
                              backgroundColor: 'grey.50', 
                              borderRadius: 2,
                              border: '1px solid',
                              borderColor: 'grey.200'
                            }}>
                              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600, display: 'flex', alignItems: 'center' }}>
                                <BusinessIcon sx={{ fontSize: 14, mr: 0.5 }} />
                                BUSINESS
                              </Typography>
                              <Typography variant="body2" sx={{ fontWeight: 600, mt: 0.5 }}>
                                {sms.business_name || getBusinessName(sms.business_id)}
                              </Typography>
                            </Box>
                          </Grid>
                        </Grid>

                        {/* Message */}
                        <Box sx={{ mb: 2 }}>
                          <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600, display: 'flex', alignItems: 'center', mb: 1 }}>
                            <MessageIcon sx={{ fontSize: 14, mr: 0.5 }} />
                            MESSAGE ({sms.body.length} chars)
                          </Typography>
                          <Paper sx={{ p: 2, backgroundColor: 'grey.50', borderRadius: 2, maxHeight: 120, overflow: 'auto' }}>
                            <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                              {sms.body}
                            </Typography>
                          </Paper>
                        </Box>

                        {/* Error Message */}
                        {sms.error_message && (
                          <Box sx={{ mb: 2 }}>
                            <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600, display: 'flex', alignItems: 'center', mb: 1 }}>
                              <ErrorIcon sx={{ fontSize: 14, mr: 0.5 }} />
                              ERROR
                            </Typography>
                            <Paper sx={{ 
                              p: 2, 
                              backgroundColor: 'error.50', 
                              borderRadius: 2,
                              border: '1px solid',
                              borderColor: 'error.200'
                            }}>
                              <Typography variant="body2" sx={{ color: 'error.dark', fontFamily: 'monospace' }}>
                                {sms.error_message}
                              </Typography>
                            </Paper>
                          </Box>
                        )}

                        {/* Metadata */}
                        <Grid container spacing={2}>
                          <Grid item xs={12} md={4}>
                            <Box sx={{ 
                              p: 2, 
                              backgroundColor: 'grey.50', 
                              borderRadius: 2,
                              border: '1px solid',
                              borderColor: 'grey.200'
                            }}>
                              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600, display: 'flex', alignItems: 'center' }}>
                                <AccessTimeIcon sx={{ fontSize: 14, mr: 0.5 }} />
                                SENT AT
                              </Typography>
                              <Typography variant="body2" sx={{ fontWeight: 500, mt: 0.5 }}>
                                {formatDateTime(sms.sent_at, sms.business_id)}
                              </Typography>
                            </Box>
                          </Grid>
                          
                          <Grid item xs={12} md={4}>
                            <Box sx={{ 
                              p: 2, 
                              backgroundColor: 'grey.50', 
                              borderRadius: 2,
                              border: '1px solid',
                              borderColor: 'grey.200'
                            }}>
                              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600, display: 'flex', alignItems: 'center' }}>
                                <PhoneIcon sx={{ fontSize: 14, mr: 0.5 }} />
                                PHONE NUMBERS
                              </Typography>
                              <Typography variant="body2" sx={{ fontWeight: 500, mt: 0.5, fontSize: '0.85rem' }}>
                                From: {sms.from_phone}<br/>
                                To: {sms.to_phone}
                              </Typography>
                            </Box>
                          </Grid>
                          
                          {sms.price && (
                            <Grid item xs={12} md={4}>
                              <Box sx={{ 
                                p: 2, 
                                backgroundColor: 'grey.50', 
                                borderRadius: 2,
                                border: '1px solid',
                                borderColor: 'grey.200'
                              }}>
                                <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600, display: 'flex', alignItems: 'center' }}>
                                  <MonetizationOnIcon sx={{ fontSize: 14, mr: 0.5 }} />
                                  COST
                                </Typography>
                                <Typography variant="body2" sx={{ fontWeight: 500, mt: 0.5 }}>
                                  {sms.price} {sms.price_unit || 'USD'}
                                </Typography>
                              </Box>
                            </Grid>
                          )}
                        </Grid>
                      </CardContent>
                    </Card>
                  );
                })}
                
                {/* Loading indicator for infinite scroll */}
                {loadingMore && (
                  <Box sx={{ display: 'flex', justifyContent: 'center', py: 3 }}>
                    <CircularProgress size={24} />
                    <Typography variant="body2" sx={{ ml: 2, color: 'text.secondary' }}>
                      Loading more SMS...
                    </Typography>
                  </Box>
                )}
                
                {/* End of list indicator */}
                {smsLogs.length > 0 && !loadingMore && !hasMore && (
                  <Box sx={{ display: 'flex', justifyContent: 'center', py: 3 }}>
                    <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                      No more SMS to load
                    </Typography>
                  </Box>
                )}
              </Stack>
            )}
            </Box>
          </CardContent>
        </Card>

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

export default SMSLogs; 