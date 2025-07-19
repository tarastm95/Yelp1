import React, { FC, useState } from 'react';
import { Container, Paper, TextField, Button, Typography, Box } from '@mui/material';
import { useNavigate } from 'react-router-dom';

interface Props {
  onLogin: () => void;
}

const LoginPage: FC<Props> = ({ onLogin }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (username === 'yelp admin' && password === 'GAndmPrQgVDVGdnQG') {
      localStorage.setItem('isAuthenticated', 'true');
      onLogin();
      navigate('/');
    } else {
      setError('Invalid credentials');
    }
  };

  return (
    <Container maxWidth="xs" sx={{ mt: 8 }}>
      <Paper sx={{ p: 4 }}>
        <Typography variant="h5" component="h1" align="center" gutterBottom>
          Login
        </Typography>
        {error && (
          <Typography color="error" variant="body2" sx={{ mb: 1 }}>
            {error}
          </Typography>
        )}
        <Box component="form" onSubmit={handleSubmit}>
          <TextField
            label="Username"
            fullWidth
            margin="normal"
            value={username}
            onChange={e => setUsername(e.target.value)}
          />
          <TextField
            label="Password"
            type="password"
            fullWidth
            margin="normal"
            value={password}
            onChange={e => setPassword(e.target.value)}
          />
          <Button type="submit" variant="contained" fullWidth sx={{ mt: 2 }}>
            Log in
          </Button>
        </Box>
      </Paper>
    </Container>
  );
};

export default LoginPage;
