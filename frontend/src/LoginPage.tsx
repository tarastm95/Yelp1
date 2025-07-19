import React, { FC, useState } from 'react';
import { Container, Paper, TextField, Button, Typography, Box, InputAdornment, IconButton } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import VisibilityIcon from '@mui/icons-material/Visibility';
import VisibilityOffIcon from '@mui/icons-material/VisibilityOff';
import PersonIcon from '@mui/icons-material/Person';
import LockIcon from '@mui/icons-material/Lock';

interface Props {
  onLogin: () => void;
}

const LoginPage: FC<Props> = ({ onLogin }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [showPassword, setShowPassword] = useState(false);
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
    <Box 
      sx={{ 
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        p: 2
      }}
    >
      <Container maxWidth="sm">
        <Box sx={{ textAlign: 'center', mb: 4 }}>
          <Typography 
            variant="h2" 
            sx={{ 
              color: 'white', 
              fontWeight: 700, 
              mb: 1,
              textShadow: '0 2px 4px rgba(0,0,0,0.3)'
            }}
          >
            🎯 Yelp Dashboard
          </Typography>
          <Typography 
            variant="h6" 
            sx={{ 
              color: 'rgba(255,255,255,0.9)',
              textShadow: '0 1px 2px rgba(0,0,0,0.2)'
            }}
          >
            Welcome back! Please sign in to continue.
          </Typography>
        </Box>

        <Paper 
          elevation={10}
          sx={{ 
            p: 4, 
            borderRadius: 3,
            backdropFilter: 'blur(10px)',
            background: 'rgba(255,255,255,0.95)'
          }}
        >
          <Typography 
            variant="h5" 
            component="h1" 
            align="center" 
            gutterBottom
            sx={{ fontWeight: 600, color: '#1f2937', mb: 3 }}
          >
            Sign In
          </Typography>
          
          {error && (
            <Box 
              sx={{ 
                p: 2, 
                mb: 2, 
                borderRadius: 2,
                backgroundColor: '#fee2e2',
                border: '1px solid #fecaca'
              }}
            >
              <Typography color="#dc2626" variant="body2" sx={{ fontWeight: 500 }}>
                {error}
              </Typography>
            </Box>
          )}
          
          <Box component="form" onSubmit={handleSubmit}>
            <TextField
              label="Username"
              fullWidth
              margin="normal"
              value={username}
              onChange={e => setUsername(e.target.value)}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <PersonIcon sx={{ color: '#6b7280' }} />
                  </InputAdornment>
                ),
              }}
              sx={{
                '& .MuiOutlinedInput-root': {
                  borderRadius: 2,
                },
              }}
            />
            
            <TextField
              label="Password"
              type={showPassword ? 'text' : 'password'}
              fullWidth
              margin="normal"
              value={password}
              onChange={e => setPassword(e.target.value)}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <LockIcon sx={{ color: '#6b7280' }} />
                  </InputAdornment>
                ),
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton
                      onClick={() => setShowPassword(!showPassword)}
                      edge="end"
                    >
                      {showPassword ? <VisibilityOffIcon /> : <VisibilityIcon />}
                    </IconButton>
                  </InputAdornment>
                ),
              }}
              sx={{
                '& .MuiOutlinedInput-root': {
                  borderRadius: 2,
                },
              }}
            />
            
            <Button 
              type="submit" 
              variant="contained" 
              fullWidth 
              sx={{ 
                mt: 3, 
                py: 1.5,
                borderRadius: 2,
                fontWeight: 600,
                fontSize: '1rem',
                background: 'linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%)',
                '&:hover': {
                  background: 'linear-gradient(135deg, #4338ca 0%, #6d28d9 100%)',
                  transform: 'translateY(-1px)',
                  boxShadow: '0 4px 12px rgba(79, 70, 229, 0.4)',
                },
                transition: 'all 0.2s ease'
              }}
            >
              Sign In
            </Button>
          </Box>
        </Paper>
        
        <Box sx={{ textAlign: 'center', mt: 3 }}>
          <Typography 
            variant="body2" 
            sx={{ 
              color: 'rgba(255,255,255,0.8)',
              textShadow: '0 1px 2px rgba(0,0,0,0.2)'
            }}
          >
            Secure access to your Yelp business dashboard
          </Typography>
        </Box>
      </Container>
    </Box>
  );
};

export default LoginPage;
