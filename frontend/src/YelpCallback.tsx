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
  CardContent
} from '@mui/material';
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
      <Box sx={{ mt: 4, maxWidth: 600, mx: 'auto' }}>
        <Card>
          <CardContent>
            <Typography variant="h5" component="h1" gutterBottom>
              🎉 Authorization Successful!
            </Typography>
            
            <Typography variant="body1" color="text.secondary" paragraph>
              Your Yelp account has been connected successfully. We're now processing your business data in the background.
            </Typography>

            {processingStatus && (
              <>
                <Box sx={{ mt: 3, mb: 2 }}>
                  <Typography variant="body2" gutterBottom>
                    {processingStatus.message}
                  </Typography>
                  <LinearProgress 
                    variant="determinate" 
                    value={processingStatus.progress} 
                    sx={{ height: 8, borderRadius: 4 }}
                  />
                  <Typography variant="caption" sx={{ mt: 1, display: 'block' }}>
                    {processingStatus.progress}% complete
                  </Typography>
                </Box>

                {processingStatus.details && (
                  <Paper sx={{ p: 2, mt: 2, backgroundColor: 'grey.50' }}>
                    <Typography variant="subtitle2" gutterBottom>
                      Processing Details:
                    </Typography>
                    <Typography variant="body2">
                      📋 Businesses found: {processingStatus.details.total_businesses}
                    </Typography>
                    <Typography variant="body2">
                      ✅ Businesses processed: {processingStatus.details.businesses_processed}
                    </Typography>
                    <Typography variant="body2">
                      🏃‍♂️ Jobs running: {processingStatus.details.jobs.running}
                    </Typography>
                    <Typography variant="body2">
                      ✅ Jobs completed: {processingStatus.details.jobs.completed}
                    </Typography>
                    {processingStatus.details.jobs.failed > 0 && (
                      <Typography variant="body2" color="warning.main">
                        ⚠️ Jobs failed: {processingStatus.details.jobs.failed}
                      </Typography>
                    )}
                  </Paper>
                )}

                {processingStatus.status === 'completed' && (
                  <Alert severity="success" sx={{ mt: 2 }}>
                    🎉 Processing completed! Redirecting to your leads...
                  </Alert>
                )}
              </>
            )}

            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 3 }}>
              You will be automatically redirected when processing is complete. 
              This usually takes 1-3 minutes depending on the amount of data.
            </Typography>
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
