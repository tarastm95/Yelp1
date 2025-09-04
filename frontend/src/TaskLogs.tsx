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
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Snackbar,
  alpha,
  Tooltip,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
} from '@mui/material';

// Icons
import TaskIcon from '@mui/icons-material/Task';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ScheduleIcon from '@mui/icons-material/Schedule';
import CancelIcon from '@mui/icons-material/Cancel';
import ErrorIcon from '@mui/icons-material/Error';
import BusinessIcon from '@mui/icons-material/Business';
import PersonIcon from '@mui/icons-material/Person';
import MessageIcon from '@mui/icons-material/Message';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import RefreshIcon from '@mui/icons-material/Refresh';
import DeleteIcon from '@mui/icons-material/Delete';
import WarningIcon from '@mui/icons-material/Warning';
import InfoIcon from '@mui/icons-material/Info';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import PauseIcon from '@mui/icons-material/Pause';
import CloseIcon from '@mui/icons-material/Close';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';

interface TaskLog {
  task_id: string;
  name: string;
  args: any[];
  eta: string | null;
  status: string;
  result?: string | null;
  traceback?: string | null;
  business_id?: string | null;
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

const TaskLogs: React.FC = () => {
  const [completedTasks, setCompletedTasks] = useState<TaskLog[]>([]);
  const [scheduledTasks, setScheduledTasks] = useState<TaskLog[]>([]);
  const [canceledTasks, setCanceledTasks] = useState<TaskLog[]>([]);
  const [businesses, setBusinesses] = useState<Business[]>([]);
  const [selectedBusiness, setSelectedBusiness] = useState<string>(''); // '' means "All Businesses"
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [canceling, setCanceling] = useState<string | null>(null);
  
  // Infinite scroll state
  const [completedPage, setCompletedPage] = useState(1);
  const [scheduledPage, setScheduledPage] = useState(1);
  const [canceledPage, setCanceledPage] = useState(1);
  const [hasMoreCompleted, setHasMoreCompleted] = useState(true);
  const [hasMoreScheduled, setHasMoreScheduled] = useState(true);
  const [hasMoreCanceled, setHasMoreCanceled] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [tab, setTab] = useState<'completed' | 'scheduled' | 'canceled'>('completed');
  
  // Ref for scroll container
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  
  // Statistics state (separate from paginated data)
  const [statistics, setStatistics] = useState({
    successful: 0,
    failed: 0,
    scheduled: 0,
    canceled: 0,
    total: 0
  });
  
  const [confirmDialog, setConfirmDialog] = useState<{open: boolean, task: TaskLog | null}>({
    open: false,
    task: null
  });
  const [errorDialog, setErrorDialog] = useState<{open: boolean, task: TaskLog | null}>({
    open: false,
    task: null
  });
  const [snackbar, setSnackbar] = useState<{open: boolean, message: string, severity: 'success' | 'error'}>({
    open: false,
    message: '',
    severity: 'success'
  });

  const loadData = async () => {
    setRefreshing(true);
    // Reset pagination state
    setCompletedPage(1);
    setScheduledPage(1);
    setCanceledPage(1);
    setHasMoreCompleted(true);
    setHasMoreScheduled(true);
    setHasMoreCanceled(true);
    
    try {
      // Build query parameters for business filtering
      const businessParam = selectedBusiness ? `&business_id=${selectedBusiness}` : '';
      
      const [completedRes, scheduledRes, canceledRes, businessesRes] = await Promise.all([
        axios.get<PaginatedResponse<TaskLog>>(`/tasks/?page=1&status=success,failure${businessParam}`).catch(() => ({ data: { count: 0, next: null, previous: null, results: [] } })),
        axios.get<PaginatedResponse<TaskLog>>(`/tasks/?page=1&status=scheduled${businessParam}`).catch(() => ({ data: { count: 0, next: null, previous: null, results: [] } })),
        axios.get<PaginatedResponse<TaskLog>>(`/tasks/?page=1&status=canceled${businessParam}`).catch(() => ({ data: { count: 0, next: null, previous: null, results: [] } })),
        axios.get<Business[]>('/businesses/').catch(() => ({ data: [] }))
      ]);

      setCompletedTasks(completedRes.data.results);
      setScheduledTasks(scheduledRes.data.results);
      setCanceledTasks(canceledRes.data.results);
      setBusinesses(businessesRes.data);
      
      // Update hasMore state based on API response
      setHasMoreCompleted(!!completedRes.data.next);
      setHasMoreScheduled(!!scheduledRes.data.next);
      setHasMoreCanceled(!!canceledRes.data.next);
      
      // Load statistics separately from a dedicated endpoint
      const statsBusinessParam = selectedBusiness ? `?business_id=${selectedBusiness}` : '';
      try {
        const statsRes = await axios.get(`/tasks/stats/${statsBusinessParam}`);
        setStatistics(statsRes.data);
      } catch (statsError) {
        console.error('Failed to load task statistics:', statsError);
        // Fallback to default statistics
        setStatistics({
          successful: 0,
          failed: 0,
          scheduled: 0,
          canceled: 0,
          total: 0
        });
      }
      
    } catch (error) {
      setSnackbar({
        open: true,
        message: 'Failed to load task data',
        severity: 'error'
      });
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const loadMoreTasks = async () => {
    if (loadingMore) return; // Prevent multiple simultaneous requests
    
    const currentTab = tab;
    let nextPage: number;
    let hasMore: boolean;
    let status: string;
    
    // Determine which tab and page to load
    switch (currentTab) {
      case 'completed':
        if (!hasMoreCompleted) return;
        nextPage = completedPage + 1;
        hasMore = hasMoreCompleted;
        status = 'success,failure';
        break;
      case 'scheduled':
        if (!hasMoreScheduled) return;
        nextPage = scheduledPage + 1;
        hasMore = hasMoreScheduled;
        status = 'scheduled';
        break;
      case 'canceled':
        if (!hasMoreCanceled) return;
        nextPage = canceledPage + 1;
        hasMore = hasMoreCanceled;
        status = 'canceled';
        break;
      default:
        return;
    }
    
    setLoadingMore(true);
    
    try {
      const businessParam = selectedBusiness ? `&business_id=${selectedBusiness}` : '';
      const response = await axios.get<PaginatedResponse<TaskLog>>(
        `/tasks/?page=${nextPage}&status=${status}${businessParam}`
      );
      
      const newTasks = response.data.results;
      const hasMoreData = !!response.data.next;
      
      // Update the appropriate state based on current tab
      switch (currentTab) {
        case 'completed':
          setCompletedTasks(prev => [...prev, ...newTasks]);
          setCompletedPage(nextPage);
          setHasMoreCompleted(hasMoreData);
          break;
        case 'scheduled':
          setScheduledTasks(prev => [...prev, ...newTasks]);
          setScheduledPage(nextPage);
          setHasMoreScheduled(hasMoreData);
          break;
        case 'canceled':
          setCanceledTasks(prev => [...prev, ...newTasks]);
          setCanceledPage(nextPage);
          setHasMoreCanceled(hasMoreData);
          break;
      }
      
    } catch (error) {
      console.error('Failed to load more tasks:', error);
      setSnackbar({
        open: true,
        message: 'Failed to load more tasks',
        severity: 'error'
      });
    } finally {
      setLoadingMore(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [selectedBusiness]); // Re-load data when selected business changes

  // Scroll listener for infinite scroll
  const handleScroll = useCallback(() => {
    const container = scrollContainerRef.current;
    if (!container) return;
    
    const { scrollTop, scrollHeight, clientHeight } = container;
    const isNearBottom = scrollTop + clientHeight >= scrollHeight - 200; // 200px threshold
    
    if (isNearBottom && !loadingMore) {
      let hasMore = false;
      switch (tab) {
        case 'completed':
          hasMore = hasMoreCompleted;
          break;
        case 'scheduled':
          hasMore = hasMoreScheduled;
          break;
        case 'canceled':
          hasMore = hasMoreCanceled;
          break;
      }
      
      if (hasMore) {
        loadMoreTasks();
      }
    }
  }, [tab, loadingMore, hasMoreCompleted, hasMoreScheduled, hasMoreCanceled, loadMoreTasks]);

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

  const formatEta = (eta: string | null, bizId?: string | null) => {
    if (!eta) return '—';
    const date = new Date(eta);
    const tz = bizId ? tzMap[bizId] : undefined;
    return tz
      ? date.toLocaleString(undefined, { timeZone: tz })
      : date.toLocaleString();
  };

  const getLeadId = (args: any[] | undefined) => {
    if (!Array.isArray(args) || args.length === 0) return '';
    return String(args[0]);
  };

  const getMessage = (args: any[] | undefined) => {
    if (!Array.isArray(args) || args.length < 2) return '';
    return String(args[1]);
  };

  const getTaskStatusInfo = (status: string) => {
    switch (status.toLowerCase()) {
      case 'success':
        return { color: 'success', icon: CheckCircleIcon, label: 'Success' };
      case 'failure':
        return { color: 'error', icon: ErrorIcon, label: 'Failed' };
      case 'scheduled':
        return { color: 'info', icon: ScheduleIcon, label: 'Scheduled' };
      case 'revoked':
      case 'canceled':
        return { color: 'warning', icon: CancelIcon, label: 'Canceled' };
      default:
        return { color: 'default', icon: InfoIcon, label: status };
    }
  };

  const handleCancelTask = (task: TaskLog) => {
    setConfirmDialog({ open: true, task });
  };

  const confirmCancelTask = async () => {
    if (!confirmDialog.task) return;
    
    const taskId = confirmDialog.task.task_id;
    setCanceling(taskId);
    setConfirmDialog({ open: false, task: null });

    try {
      await axios.post(`/tasks/${taskId}/cancel/`, { reason: 'Cancelled via UI' });
      setScheduledTasks(tasks => tasks.filter(t => t.task_id !== taskId));
      
      // Update statistics after canceling a task
      setStatistics(prev => ({
        ...prev,
        scheduled: prev.scheduled - 1,
        canceled: prev.canceled + 1
      }));
      
      setSnackbar({
        open: true,
        message: 'Task successfully canceled',
        severity: 'success'
      });
    } catch (error) {
      setSnackbar({
        open: true,
        message: 'Failed to cancel task',
        severity: 'error'
      });
    } finally {
      setCanceling(null);
    }
  };

  const handleErrorDetails = (task: TaskLog) => {
    setErrorDialog({ open: true, task });
  };

  const getTimeUntilExecution = (eta: string | null) => {
    if (!eta) return null;
    const now = new Date();
    const etaDate = new Date(eta);
    const diff = etaDate.getTime() - now.getTime();
    
    if (diff <= 0) return 'Overdue';
    
    const minutes = Math.floor(diff / (1000 * 60));
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);
    
    if (days > 0) return `in ${days}d ${hours % 24}h`;
    if (hours > 0) return `in ${hours}h ${minutes % 60}m`;
    return `in ${minutes}m`;
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

  const currentTasks = tab === 'completed' ? completedTasks : 
                     tab === 'scheduled' ? scheduledTasks : canceledTasks;

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
                <TaskIcon sx={{ fontSize: '2.5rem', color: 'white' }} />
              </Avatar>
              
              {/* Info */}
              <Box sx={{ flex: 1, textAlign: { xs: 'center', md: 'left' } }}>
                <Typography variant="h3" sx={{ fontWeight: 800, mb: 1 }}>
                  Task Management
                </Typography>
                
                <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ mb: 2 }}>
                  <Chip
                    icon={<AutoAwesomeIcon />}
                    label="Automated Workflows"
                    sx={{
                      background: 'rgba(255, 255, 255, 0.2)',
                      color: 'white',
                      fontWeight: 600,
                      '& .MuiChip-icon': { color: 'white' }
                    }}
                  />
                  
                  <Chip
                    icon={<TrendingUpIcon />}
                    label={`${statistics.total} ${selectedBusiness ? 'Filtered' : 'Total'} Tasks`}
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
                    ? `Viewing tasks for: ${businesses.find(b => b.business_id === selectedBusiness)?.name || selectedBusiness}`
                    : 'Monitor and manage your automated task execution pipeline'
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

        {/* Business Filter */}
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
                  <BusinessIcon sx={{ fontSize: '1.5rem', color: 'white' }} />
                </Avatar>
                <Box>
                  <Typography variant="h6" sx={{ fontWeight: 600, mb: 0.5 }}>
                    Filter by Business
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    View tasks for all businesses or filter by specific business
                  </Typography>
                </Box>
              </Box>
              
              <FormControl sx={{ minWidth: 300 }}>
                <InputLabel id="business-filter-label">Business</InputLabel>
                <Select
                  labelId="business-filter-label"
                  value={selectedBusiness}
                  label="Business"
                  onChange={(e) => setSelectedBusiness(e.target.value)}
                  sx={{
                    borderRadius: 2,
                    '& .MuiOutlinedInput-root': {
                      '&:hover fieldset': {
                        borderColor: 'primary.main',
                      },
                    },
                  }}
                >
                  <MenuItem value="">
                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                      <AutoAwesomeIcon sx={{ mr: 1, color: 'primary.main' }} />
                      <Typography sx={{ fontWeight: 600 }}>All Businesses</Typography>
                    </Box>
                  </MenuItem>
                  {businesses.map(business => (
                    <MenuItem key={business.business_id} value={business.business_id}>
                      <Box sx={{ display: 'flex', alignItems: 'center', width: '100%' }}>
                        <BusinessIcon sx={{ mr: 1, color: 'text.secondary' }} />
                        <Box sx={{ flex: 1 }}>
                          <Typography sx={{ fontWeight: 500 }}>
                            {business.name}
                          </Typography>
                          {business.time_zone && (
                            <Typography variant="caption" color="text.secondary">
                              {business.time_zone}
                            </Typography>
                          )}
                        </Box>
                      </Box>
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              
              {selectedBusiness && (
                <Chip
                  label={`Filtered: ${businesses.find(b => b.business_id === selectedBusiness)?.name || selectedBusiness}`}
                  color="primary"
                  variant="outlined"
                  onDelete={() => setSelectedBusiness('')}
                  sx={{
                    fontWeight: 600,
                    borderRadius: 2,
                    '& .MuiChip-deleteIcon': {
                      color: 'primary.main'
                    }
                  }}
                />
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
                  {statistics.successful}
                </Typography>
                
                <Typography variant="h6" sx={{ fontWeight: 600, mb: 1 }}>
                  Successful
                </Typography>
                
                <Typography variant="body2" color="text.secondary">
                  Completed successfully
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
                  <ScheduleIcon sx={{ fontSize: '2rem', color: 'white' }} />
                </Avatar>
                
                <Typography variant="h4" sx={{ fontWeight: 700, mb: 1, color: 'info.main' }}>
                  {statistics.scheduled}
                </Typography>
                
                <Typography variant="h6" sx={{ fontWeight: 600, mb: 1 }}>
                  Scheduled
                </Typography>
                
                <Typography variant="body2" color="text.secondary">
                  Waiting to execute
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
                  {statistics.failed}
                </Typography>
                
                <Typography variant="h6" sx={{ fontWeight: 600, mb: 1 }}>
                  Failed
                </Typography>
                
                <Typography variant="body2" color="text.secondary">
                  Execution errors
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
                  <CancelIcon sx={{ fontSize: '2rem', color: 'white' }} />
                </Avatar>
                
                <Typography variant="h4" sx={{ fontWeight: 700, mb: 1, color: 'warning.main' }}>
                  {statistics.canceled}
                </Typography>
                
                <Typography variant="h6" sx={{ fontWeight: 600, mb: 1 }}>
                  Canceled
                </Typography>
                
                <Typography variant="body2" color="text.secondary">
                  Manually stopped
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        {/* Tabs Section */}
        <Card elevation={2} sx={{ borderRadius: 3, mb: 4 }}>
          <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
            <Tabs 
              value={tab} 
              onChange={(_, v) => setTab(v)}
              sx={{
                px: 2,
                '& .MuiTab-root': {
                  py: 2,
                  fontWeight: 600,
                  fontSize: '1rem',
                  textTransform: 'none',
                  minHeight: 'auto',
                  transition: 'all 0.3s ease',
                  
                  '&.Mui-selected': {
                    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                    color: 'white',
                    borderRadius: 2,
                    transform: 'translateY(-2px)',
                    boxShadow: '0 4px 12px rgba(102, 126, 234, 0.3)',
                    mx: 1,
                    my: 1
                  },
                  
                  '&:hover:not(.Mui-selected)': {
                    backgroundColor: 'grey.100',
                    borderRadius: 2,
                    mx: 1,
                    my: 1
                  }
                },
                '& .MuiTabs-indicator': {
                  display: 'none'
                }
              }}
            >
              <Tab 
                label={
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <Badge badgeContent={statistics.successful + statistics.failed} color="primary" sx={{ mr: 1 }}>
                      <CheckCircleIcon />
                    </Badge>
                    <Typography sx={{ ml: 1 }}>Completed</Typography>
                  </Box>
                } 
                value="completed" 
              />
              <Tab 
                label={
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <Badge badgeContent={statistics.scheduled} color="info" sx={{ mr: 1 }}>
                      <ScheduleIcon />
                    </Badge>
                    <Typography sx={{ ml: 1 }}>Scheduled</Typography>
                  </Box>
                } 
                value="scheduled" 
              />
              <Tab 
                label={
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <Badge badgeContent={statistics.canceled} color="warning" sx={{ mr: 1 }}>
                      <CancelIcon />
                    </Badge>
                    <Typography sx={{ ml: 1 }}>Canceled</Typography>
                  </Box>
                } 
                value="canceled" 
              />
            </Tabs>
          </Box>
          
          <CardContent 
            ref={scrollContainerRef}
            sx={{ 
              p: 3, 
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
            {currentTasks.length === 0 ? (
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
                {tab === 'completed' && <CheckCircleIcon sx={{ fontSize: 64, color: 'grey.400', mb: 2 }} />}
                {tab === 'scheduled' && <ScheduleIcon sx={{ fontSize: 64, color: 'grey.400', mb: 2 }} />}
                {tab === 'canceled' && <CancelIcon sx={{ fontSize: 64, color: 'grey.400', mb: 2 }} />}
                
                <Typography variant="h6" color="text.secondary" sx={{ mb: 1 }}>
                  No {tab} tasks{selectedBusiness ? ' for this business' : ''}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {selectedBusiness 
                    ? `No ${tab} tasks found for ${businesses.find(b => b.business_id === selectedBusiness)?.name || 'this business'}`
                    : tab === 'completed' && 'No tasks have been completed yet' ||
                      tab === 'scheduled' && 'No tasks are currently scheduled' ||
                      tab === 'canceled' && 'No tasks have been canceled'
                  }
                </Typography>
              </Paper>
            ) : (
              /* Tasks List */
              <Stack spacing={3}>
                {currentTasks.map(task => {
                  const statusInfo = getTaskStatusInfo(task.status);
                  const StatusIcon = statusInfo.icon;
                  const timeUntil = getTimeUntilExecution(task.eta);
                  const leadId = getLeadId(task.args);
                  const message = getMessage(task.args);
                  const businessName = getBusinessName(task.business_id);
                  const isOverdue = timeUntil === 'Overdue';
                  
                  return (
                    <Card
                      key={task.task_id}
                      elevation={2}
                      sx={{
                        borderRadius: 3,
                        position: 'relative',
                        transition: 'all 0.3s ease-in-out',
                        border: '2px solid',
                        borderColor: `${statusInfo.color}.light`,
                        width: '100%',
                        
                        '&:hover': {
                          transform: 'translateY(-4px)',
                          boxShadow: `0 8px 32px ${alpha(statusInfo.color === 'success' ? '#4caf50' : 
                                                         statusInfo.color === 'error' ? '#f44336' :
                                                         statusInfo.color === 'info' ? '#2196f3' :
                                                         statusInfo.color === 'warning' ? '#ff9800' : '#666', 0.2)}`,
                          borderColor: `${statusInfo.color}.main`
                        }
                      }}
                    >
                      {/* Status Header */}
                      <Box sx={{ 
                        background: statusInfo.color === 'success' ? 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)' :
                                   statusInfo.color === 'error' ? 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)' :
                                   statusInfo.color === 'info' ? 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)' :
                                   statusInfo.color === 'warning' ? 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)' :
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
                              {task.name}
                            </Typography>
                            <Typography variant="caption" sx={{ opacity: 0.9 }}>
                              Task ID: {task.task_id.slice(0, 8)}...
                            </Typography>
                          </Box>
                          
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
                                {leadId || 'N/A'}
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
                                {businessName}
                              </Typography>
                            </Box>
                          </Grid>
                        </Grid>

                        {/* Message */}
                        {message && (
                          <Box sx={{ mb: 2 }}>
                            <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600, display: 'flex', alignItems: 'center', mb: 1 }}>
                              <MessageIcon sx={{ fontSize: 14, mr: 0.5 }} />
                              MESSAGE
                            </Typography>
                            <Paper sx={{ p: 2, backgroundColor: 'grey.50', borderRadius: 2 }}>
                              <Typography variant="body2" sx={{ fontStyle: 'italic' }}>
                                "{message}"
                              </Typography>
                            </Paper>
                          </Box>
                        )}

                        {/* Task Result */}
                        {task.result && (
                          <Box sx={{ mb: 2 }}>
                            <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600, display: 'flex', alignItems: 'center', mb: 1 }}>
                              <InfoIcon sx={{ fontSize: 14, mr: 0.5 }} />
                              RESULT
                            </Typography>
                            <Paper sx={{ 
                              p: 2, 
                              backgroundColor: task.status === 'FAILURE' ? 'error.50' : task.status === 'SUCCESS' ? 'success.50' : 'grey.50', 
                              borderRadius: 2,
                              border: '1px solid',
                              borderColor: task.status === 'FAILURE' ? 'error.200' : task.status === 'SUCCESS' ? 'success.200' : 'grey.200',
                              maxHeight: 120,
                              overflow: 'auto'
                            }}>
                              <Typography 
                                variant="body2" 
                                sx={{ 
                                  fontFamily: 'monospace',
                                  fontSize: '0.85rem',
                                  whiteSpace: 'pre-wrap',
                                  color: task.status === 'FAILURE' ? 'error.dark' : task.status === 'SUCCESS' ? 'success.dark' : 'text.primary'
                                }}
                              >
                                {task.result}
                              </Typography>
                            </Paper>
                          </Box>
                        )}

                        {/* Execution Time */}
                        <Box sx={{ mb: 2 }}>
                          <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600, display: 'flex', alignItems: 'center', mb: 1 }}>
                            <AccessTimeIcon sx={{ fontSize: 14, mr: 0.5 }} />
                            {tab === 'scheduled' ? 'SCHEDULED FOR' : 'EXECUTED AT'}
                          </Typography>
                          <Stack direction="row" justifyContent="space-between" alignItems="center">
                            <Typography variant="body2" sx={{ fontWeight: 500 }}>
                              {formatEta(task.eta, task.business_id)}
                            </Typography>
                            {tab === 'scheduled' && timeUntil && (
                              <Chip
                                label={timeUntil}
                                size="small"
                                color={isOverdue ? 'error' : 'info'}
                                sx={{ fontWeight: 600 }}
                              />
                            )}
                          </Stack>
                        </Box>

                        <Divider sx={{ my: 2 }} />

                        {/* Actions */}
                        <Stack direction="row" spacing={1} justifyContent="flex-end">
                          {tab === 'scheduled' && (
                            <Button
                              variant="outlined"
                              color="error"
                              size="small"
                              startIcon={canceling === task.task_id ? <CircularProgress size={16} color="inherit" /> : <DeleteIcon />}
                              onClick={() => handleCancelTask(task)}
                              disabled={canceling === task.task_id}
                              sx={{
                                borderRadius: 2,
                                fontWeight: 600,
                                textTransform: 'none'
                              }}
                            >
                              {canceling === task.task_id ? 'Canceling...' : 'Cancel'}
                            </Button>
                          )}
                          
                          {(task.status === 'FAILURE' || task.traceback) && (
                            <Button
                              variant="outlined"
                              color="error"
                              size="small"
                              startIcon={<ErrorIcon />}
                              onClick={() => handleErrorDetails(task)}
                              sx={{
                                borderRadius: 2,
                                fontWeight: 600,
                                textTransform: 'none'
                              }}
                            >
                              View Error
                            </Button>
                          )}
                        </Stack>
                      </CardContent>
                    </Card>
                  );
                })}
                
                {/* Loading indicator for infinite scroll */}
                {loadingMore && (
                  <Box sx={{ display: 'flex', justifyContent: 'center', py: 3 }}>
                    <CircularProgress size={24} />
                    <Typography variant="body2" sx={{ ml: 2, color: 'text.secondary' }}>
                      Loading more tasks...
                    </Typography>
                  </Box>
                )}
                
                {/* End of list indicator */}
                {currentTasks.length > 0 && !loadingMore && (
                  (tab === 'completed' && !hasMoreCompleted) ||
                  (tab === 'scheduled' && !hasMoreScheduled) ||
                  (tab === 'canceled' && !hasMoreCanceled)
                ) && (
                  <Box sx={{ display: 'flex', justifyContent: 'center', py: 3 }}>
                    <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                      No more tasks to load
                    </Typography>
                  </Box>
                )}
              </Stack>
            )}
          </CardContent>
        </Card>

        {/* Cancel Confirmation Dialog */}
        <Dialog
          open={confirmDialog.open}
          onClose={() => setConfirmDialog({ open: false, task: null })}
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
            Cancel Task
            <IconButton
              onClick={() => setConfirmDialog({ open: false, task: null })}
              sx={{ ml: 'auto', color: 'white' }}
            >
              <CloseIcon />
            </IconButton>
          </DialogTitle>
          
          <DialogContent sx={{ p: 3 }}>
            <Typography variant="body1" sx={{ mb: 2 }}>
              Are you sure you want to cancel this scheduled task?
            </Typography>
            
            {confirmDialog.task && (
              <Box sx={{ 
                p: 2, 
                backgroundColor: 'grey.50', 
                borderRadius: 2,
                border: '1px solid',
                borderColor: 'grey.200'
              }}>
                <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
                  TASK
                </Typography>
                <Typography variant="body1" sx={{ fontWeight: 600 }}>
                  {confirmDialog.task.name}
                </Typography>
                <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600, mt: 1, display: 'block' }}>
                  SCHEDULED FOR
                </Typography>
                <Typography variant="body2">
                  {formatEta(confirmDialog.task.eta, confirmDialog.task.business_id)}
                </Typography>
              </Box>
            )}
            
            <Alert severity="warning" sx={{ mt: 2, borderRadius: 2 }}>
              This action cannot be undone. The task will be permanently canceled.
            </Alert>
          </DialogContent>
          
          <DialogActions sx={{ p: 3, pt: 0 }}>
            <Button
              onClick={() => setConfirmDialog({ open: false, task: null })}
              variant="outlined"
              sx={{ borderRadius: 2, fontWeight: 600 }}
            >
              Keep Task
            </Button>
            <Button
              onClick={confirmCancelTask}
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
              Cancel Task
            </Button>
          </DialogActions>
        </Dialog>

        {/* Error Details Dialog */}
        <Dialog
          open={errorDialog.open}
          onClose={() => setErrorDialog({ open: false, task: null })}
          maxWidth="md"
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
            <ErrorIcon sx={{ mr: 1 }} />
            Task Error Details
            <IconButton
              onClick={() => setErrorDialog({ open: false, task: null })}
              sx={{ ml: 'auto', color: 'white' }}
            >
              <CloseIcon />
            </IconButton>
          </DialogTitle>
          
          <DialogContent sx={{ p: 3 }}>
            {errorDialog.task && (
              <>
                <Box sx={{ 
                  p: 2, 
                  backgroundColor: 'grey.50', 
                  borderRadius: 2,
                  border: '1px solid',
                  borderColor: 'grey.200',
                  mb: 3
                }}>
                  <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
                    TASK
                  </Typography>
                  <Typography variant="body1" sx={{ fontWeight: 600 }}>
                    {errorDialog.task.name}
                  </Typography>
                  <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600, mt: 1, display: 'block' }}>
                    TASK ID
                  </Typography>
                  <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                    {errorDialog.task.task_id}
                  </Typography>
                </Box>

                {errorDialog.task.result && (
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                      Error Result:
                    </Typography>
                    <Paper sx={{ 
                      p: 2, 
                      backgroundColor: 'error.50', 
                      borderRadius: 2,
                      border: '1px solid',
                      borderColor: 'error.200'
                    }}>
                      <Typography variant="body2" sx={{ fontFamily: 'monospace', whiteSpace: 'pre-wrap' }}>
                        {errorDialog.task.result}
                      </Typography>
                    </Paper>
                  </Box>
                )}

                {errorDialog.task.traceback && (
                  <Box>
                    <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                      Stack Trace:
                    </Typography>
                    <Paper sx={{ 
                      p: 2, 
                      backgroundColor: 'error.50', 
                      borderRadius: 2,
                      border: '1px solid',
                      borderColor: 'error.200',
                      maxHeight: 300,
                      overflow: 'auto'
                    }}>
                      <Typography variant="body2" sx={{ fontFamily: 'monospace', whiteSpace: 'pre-wrap', fontSize: '0.8rem' }}>
                        {errorDialog.task.traceback}
                      </Typography>
                    </Paper>
                  </Box>
                )}
              </>
            )}
          </DialogContent>
          
          <DialogActions sx={{ p: 3, pt: 0 }}>
            <Button
              onClick={() => setErrorDialog({ open: false, task: null })}
              variant="contained"
              sx={{ borderRadius: 2, fontWeight: 600 }}
            >
              Close
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

export default TaskLogs;
