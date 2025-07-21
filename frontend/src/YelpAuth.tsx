import React, { FC } from 'react';
import axios from 'axios';
import { Container, Box, Typography, Button, Paper } from '@mui/material';

const YelpAuth: FC = () => {
  const handleYelpLogin = async () => {
    try {
      const res = await axios.get<{ authorization_url: string }>('/yelp/auth/init/');
      window.location.href = res.data.authorization_url;
    } catch {
      window.alert('Failed to initiate Yelp authorization.');
    }
  };

  return (
    <Container maxWidth="xs" sx={{ mt: 8 }}>
      <Paper elevation={4} sx={{ p: 4, textAlign: 'center' }}>
        <Typography variant="h5" component="h1" gutterBottom>
          Yelp Authorization
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
          Click the button to log in with your Yelp account.
        </Typography>
        <Button
          variant="contained"
          color="primary"
          size="large"
          onClick={handleYelpLogin}
          sx={{ textTransform: 'none' }}
        >
          Log in with Yelp
        </Button>
      </Paper>
    </Container>
  );
};

export default YelpAuth;
