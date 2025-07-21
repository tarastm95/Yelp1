import React, { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Box, CircularProgress, Alert } from '@mui/material';
import axios from 'axios';

const YelpCallback: React.FC = () => {
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const code = params.get('code');
    const token = params.get('access_token');

    if (code) {
      // Authorization Code Flow
      axios.post('/yelp/auth/callback/', { code })
        .then(() => {
          setStatus('success');
          navigate('/events');
        })
        .catch(() => setStatus('error'));

    } else if (token) {
      // Implicit Flow
      setStatus('success');
      navigate('/events');

    } else {
      // neither code nor token — error
      setStatus('error');
    }
  }, [location.search, navigate]);

  if (status === 'loading') {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (status === 'error') {
    return (
      <Alert severity="error" sx={{ mt: 4 }}>
        Authentication failed: no <code>code</code> or <code>access_token</code> in URL
      </Alert>
    );
  }

  // status 'success' already navigated to /events, so render nothing here
  return null;
};

export default YelpCallback;
