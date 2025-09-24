import React, { useEffect, useState, useCallback } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { 
  Box, 
  CircularProgress, 
  Alert, 
  LinearProgress, 
  Typography, 
  Paper,
  Card,
  CardContent,
  Button,
  IconButton,
  Chip,
  Fade,
  Grow,
  Tooltip,
  Stack,
  Divider
} from '@mui/material';
import { 
  Close as CloseIcon, 
  CheckCircle as CheckCircleIcon,
  Refresh as RefreshIcon,
  OpenInNew as OpenInNewIcon 
} from '@mui/icons-material';
import axios from 'axios';

interface ProcessingStatus {
  status: string;
  message: string;
  progress: number;
  last_updated: string | null;
  details: {
    total_businesses: number;
    businesses_processed: number;
    jobs: {
      running: number;
      completed: number;
      failed: number;
      total: number;
    };
  };
}

type CallbackStatus = 'loading' | 'processing_background' | 'success' | 'error';

const YelpCallback: React.FC = () => {
  const [status, setStatus] = useState<CallbackStatus>('loading');
  const [processingStatus, setProcessingStatus] = useState<ProcessingStatus | null>(null);
  const [errorMessage, setErrorMessage] = useState<string>('');
  const [showBackgroundOption, setShowBackgroundOption] = useState<boolean>(false);
  const [timeElapsed, setTimeElapsed] = useState<number>(0);
  const [canClose, setCanClose] = useState<boolean>(false);
  const location = useLocation();
  const navigate = useNavigate();

  const checkProcessingStatus = useCallback(async () => {
    try {
      const response = await axios.get<ProcessingStatus>('/oauth/processing-status/');
      const data = response.data;
      setProcessingStatus(data);

      // If processing is completed, navigate to events
      if (data.status === 'completed') {
        setTimeout(() => {
          navigate('/events');
        }, 2000); // Give user 2 seconds to see completion message
      }
      
      return data.status;
    } catch (error) {
      console.error('Failed to check processing status:', error);
      return null;
    }
  }, [navigate]);

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const code = params.get('code');
    const token = params.get('access_token');
    const processing = params.get('processing');
    const error = params.get('error');

    if (error) {
      setStatus('error');
      setErrorMessage(getErrorMessage(error));
      return;
    }

    if (code) {
      // Authorization Code Flow
      axios.post('/yelp/auth/callback/', { code })
        .then(() => {
          setStatus('success');
          navigate('/events');
        })
        .catch(() => {
          setStatus('error');
          setErrorMessage('Failed to process authorization code');
        });

    } else if (token && processing === 'background') {
      // Background Processing Flow
      setStatus('processing_background');
      
      // Start polling for status
      const pollStatus = async () => {
        const currentStatus = await checkProcessingStatus();
        
        // Continue polling if still processing
        if (currentStatus === 'processing') {
          setTimeout(pollStatus, 3000); // Poll every 3 seconds
        } else if (currentStatus === 'failed') {
          setStatus('error');
          setErrorMessage('Background processing failed');
        }
      };
      
      pollStatus();

    } else if (token) {
      // Implicit Flow (immediate success)
      setStatus('success');
      navigate('/events');

    } else {
      // neither code nor token — error
      setStatus('error');
      setErrorMessage('No authorization code or access token found in URL');
    }
  }, [location.search, navigate, checkProcessingStatus]);

  // Timer effect for elapsed time and background option
  useEffect(() => {
    if (status === 'processing_background') {
      const timer = setInterval(() => {
        setTimeElapsed(prev => {
          const newTime = prev + 1;
          
          // Show background option after 10 seconds
          if (newTime === 10) {
            setShowBackgroundOption(true);
          }
          
          // Allow closing after 15 seconds
          if (newTime === 15) {
            setCanClose(true);
          }
          
          return newTime;
        });
      }, 1000);

      return () => clearInterval(timer);
    }
  }, [status]);

  const handleContinueInBackground = () => {
    // Store processing state in localStorage for potential later check
    localStorage.setItem('yelpProcessingStatus', JSON.stringify({
      startTime: Date.now(),
      lastKnownProgress: processingStatus?.progress || 0
    }));
    
    // Navigate to events page
    navigate('/events');
  };

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const getErrorMessage = (errorType: string): string => {
    const errorMessages: Record<string, string> = {
      'token_exchange_failed': 'Failed to exchange authorization code for access token',
      'token_error': 'Invalid or missing access token',
      'background_job_failed': 'Failed to start background data processing',
      'token_request_failed': 'Network error during token request',
      'unexpected_error': 'An unexpected error occurred during authorization',
      'missing_params': 'Missing required authorization parameters',
      'invalid_state': 'Invalid or expired authorization state'
    };
    
    return errorMessages[errorType] || `Unknown error: ${errorType}`;
  };

  if (status === 'loading') {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
        <CircularProgress />
        <Typography variant="body1" sx={{ ml: 2, mt: 1 }}>
          Authorizing...
        </Typography>
      </Box>
    );
  }

  if (status === 'processing_background') {
    return (
      <Box sx={{ mt: 4, maxWidth: 700, mx: 'auto' }}>
        <Card elevation={3}>
          <CardContent sx={{ p: 4 }}>
            {/* Header with timer */}
            <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 3 }}>
              <Typography variant="h5" component="h1" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                🎉 Authorization Successful!
              </Typography>
              <Stack direction="row" alignItems="center" spacing={1}>
                <Chip 
                  label={formatTime(timeElapsed)} 
                  color="primary" 
                  variant="outlined"
                  size="small"
                />
                {canClose && (
                  <Tooltip title="Continue processing in background">
                    <IconButton onClick={handleContinueInBackground} size="small">
                      <CloseIcon />
                    </IconButton>
                  </Tooltip>
                )}
              </Stack>
            </Stack>
            
            <Typography variant="body1" color="text.secondary" paragraph>
              Your Yelp account has been connected successfully. We're now processing your business data in the background.
            </Typography>

            {/* Enhanced Progress Section */}
            {processingStatus ? (
              <Fade in={true}>
                <Box sx={{ mt: 3 }}>
                  {/* Main Progress Bar */}
                  <Box sx={{ mb: 3 }}>
                    <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
                      <Typography variant="body2" color="text.primary" fontWeight="medium">
                        {processingStatus.message}
                      </Typography>
                      <Typography variant="body2" color="primary" fontWeight="bold">
                        {processingStatus.progress}%
                      </Typography>
                    </Stack>
                    <LinearProgress 
                      variant="determinate" 
                      value={processingStatus.progress} 
                      sx={{ 
                        height: 12, 
                        borderRadius: 6,
                        backgroundColor: 'grey.200',
                        '& .MuiLinearProgress-bar': {
                          borderRadius: 6,
                          transition: 'transform 0.4s ease-in-out'
                        }
                      }}
                    />
                  </Box>

                  {/* Processing Details Cards */}
                  {processingStatus.details && (
                    <Grow in={true}>
                      <Paper 
                        elevation={1} 
                        sx={{ 
                          p: 3, 
                          mt: 2, 
                          backgroundColor: 'grey.50',
                          borderRadius: 2,
                          border: '1px solid',
                          borderColor: 'grey.200'
                        }}
                      >
                        <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 'bold', mb: 2 }}>
                          📊 Processing Details
                        </Typography>
                        
                        <Stack spacing={2}>
                          {/* Stats Grid */}
                          <Stack direction="row" spacing={2} flexWrap="wrap">
                            <Chip 
                              icon={<span>📋</span>}
                              label={`${processingStatus.details.total_businesses} Businesses Found`}
                              color="info"
                              variant="outlined"
                            />
                            <Chip 
                              icon={<CheckCircleIcon />}
                              label={`${processingStatus.details.businesses_processed} Processed`}
                              color="success"
                              variant="outlined"
                            />
                            <Chip 
                              icon={<RefreshIcon />}
                              label={`${processingStatus.details.jobs.running} Running`}
                              color="primary"
                              variant="outlined"
                            />
                            <Chip 
                              icon={<CheckCircleIcon />}
                              label={`${processingStatus.details.jobs.completed} Completed`}
                              color="success"
                              variant="outlined"
                            />
                            {processingStatus.details.jobs.failed > 0 && (
                              <Chip 
                                label={`${processingStatus.details.jobs.failed} Failed`}
                                color="warning"
                                variant="outlined"
                              />
                            )}
                          </Stack>

                          {/* Job Progress */}
                          <Box>
                            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
                              Jobs: {processingStatus.details.jobs.completed} / {processingStatus.details.jobs.total} completed
                            </Typography>
                            <LinearProgress 
                              variant="determinate" 
                              value={(processingStatus.details.jobs.completed / processingStatus.details.jobs.total) * 100} 
                              sx={{ height: 6, borderRadius: 3 }}
                            />
                          </Box>
                        </Stack>
                      </Paper>
                    </Grow>
                  )}

                  {/* Completion Alert */}
                  {processingStatus.status === 'completed' && (
                    <Grow in={true}>
                      <Alert 
                        severity="success" 
                        sx={{ mt: 2 }}
                        icon={<CheckCircleIcon />}
                      >
                        🎉 Processing completed! Redirecting to your leads...
                      </Alert>
                    </Grow>
                  )}
                </Box>
              </Fade>
            ) : (
              // Loading state while waiting for first status
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mt: 3 }}>
                <CircularProgress size={24} />
                <Typography variant="body2" color="text.secondary">
                  Initializing processing...
                </Typography>
              </Box>
            )}

            <Divider sx={{ my: 3 }} />

            {/* Action Buttons */}
            <Stack direction="column" spacing={2} alignItems="center">
              {showBackgroundOption && (
                <Fade in={true}>
                  <Button
                    variant="contained"
                    color="primary"
                    onClick={handleContinueInBackground}
                    startIcon={<OpenInNewIcon />}
                    sx={{ minWidth: 200 }}
                  >
                    Continue in Background
                  </Button>
                </Fade>
              )}
              
              <Typography variant="caption" color="text.secondary" textAlign="center">
                {!showBackgroundOption ? (
                  <>
                    Processing will continue automatically. You can close this page after{' '}
                    <strong>{15 - timeElapsed > 0 ? 15 - timeElapsed : 0}</strong> seconds.
                  </>
                ) : (
                  <>
                    ✅ You can now safely close this page. Processing continues in the background.<br/>
                    Return anytime to check your leads and data.
                  </>
                )}
              </Typography>
            </Stack>
          </CardContent>
        </Card>
      </Box>
    );
  }

  if (status === 'error') {
    return (
      <Box sx={{ mt: 4, maxWidth: 600, mx: 'auto' }}>
        <Alert severity="error">
          <Typography variant="h6" component="div" gutterBottom>
            Authorization Failed
          </Typography>
          <Typography variant="body2">
            {errorMessage}
          </Typography>
          <Typography variant="caption" sx={{ display: 'block', mt: 2 }}>
            Please try again or contact support if the problem persists.
          </Typography>
        </Alert>
      </Box>
    );
  }

  // status 'success' already navigated to /events, so render nothing here
  return null;
};

export default YelpCallback;
