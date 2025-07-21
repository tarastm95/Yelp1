import React, { FC, useEffect, useState } from 'react';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
import axios from 'axios';

// --- Material-UI Imports ---
import {
  Container,
  Typography,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Snackbar,
  Alert,
  Card,
  CardContent,
  Dialog,
  DialogTitle,
  DialogActions,
  Button,
  useMediaQuery,
  useTheme,
  Grow,
  Box,
  Grid,
  Avatar,
  Chip,
  Paper,
  Divider,
  Stack,
  alpha,
  IconButton,
} from '@mui/material';

// --- Material-UI Icons ---
import EventIcon from '@mui/icons-material/Event';
import SettingsIcon from '@mui/icons-material/Settings';
import VpnKeyIcon from '@mui/icons-material/VpnKey';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import ListAltIcon from '@mui/icons-material/ListAlt';
import DashboardIcon from '@mui/icons-material/Dashboard';
import BusinessIcon from '@mui/icons-material/Business';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import SecurityIcon from '@mui/icons-material/Security';
import SpeedIcon from '@mui/icons-material/Speed';
import ChatIcon from '@mui/icons-material/Chat';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';

const menuItems = [
  { 
    text: 'View Events', 
    icon: <EventIcon />, 
    href: '/events',
    description: 'Monitor and manage your Yelp events',
    color: '#f093fb',
    gradient: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)'
  },
  { 
    text: 'Auto-response Settings', 
    icon: <SettingsIcon />, 
    href: '/settings',
    description: 'Configure automated messaging',
    color: '#4facfe',
    gradient: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)'
  },
  { 
    text: 'Token Status', 
    icon: <AccessTimeIcon />, 
    href: '/tokens',
    description: 'Check authorization status',
    color: '#43e97b',
    gradient: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)'
  },
  { 
    text: 'Planned Tasks', 
    icon: <ListAltIcon />, 
    href: '/tasks',
    description: 'View scheduled operations',
    color: '#fa709a',
    gradient: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)'
  },
  { 
    text: 'Authorize with Yelp', 
    icon: <VpnKeyIcon />, 
    href: '/auth',
    description: 'Connect your Yelp account',
    color: '#667eea',
    gradient: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    isAction: true
  },
];

const features = [
  {
    icon: <AutoAwesomeIcon />,
    title: 'Smart Automation',
    description: 'Intelligent response system that handles customer inquiries automatically'
  },
  {
    icon: <TrendingUpIcon />,
    title: 'Real-time Analytics',
    description: 'Track engagement metrics and response rates in real-time'
  },
  {
    icon: <SecurityIcon />,
    title: 'Secure Integration',
    description: 'Enterprise-grade security with encrypted data transmission'
  },
  {
    icon: <SpeedIcon />,
    title: 'Lightning Fast',
    description: 'Instant responses and lightning-fast processing capabilities'
  }
];

const Home: FC = () => {
  const [alertOpen, setAlertOpen] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const navigate = useNavigate();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  useEffect(() => {
    axios.get('/tokens/')
      .then(res => {
        const expired = res.data.some((t: any) => {
          if (!t.updated_at) return false;
          const refreshExpires = new Date(t.updated_at).getTime() + 365 * 86400 * 1000;
          return Date.now() >= refreshExpires;
        });
        if (!expired) return;

        const lastShown = localStorage.getItem('tokenAlertTime');
        if (!lastShown || Date.now() - Number(lastShown) > 5 * 3600 * 1000) {
          setAlertOpen(true);
        }
      })
      .catch(() => {});
  }, []);

  const handleCloseAlert = () => {
    localStorage.setItem('tokenAlertTime', String(Date.now()));
    setAlertOpen(false);
  };

  return (
    <Box sx={{ 
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)',
      pb: 6
    }}>
      <Container maxWidth="xl" sx={{ pt: 4 }}>
        {/* Hero Section */}
        <Grow in timeout={500}>
          <Box sx={{ textAlign: 'center', mb: 6 }}>
            <Box sx={{ 
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: 120,
              height: 120,
              borderRadius: '50%',
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              mb: 3,
              boxShadow: '0 20px 40px rgba(102, 126, 234, 0.3)',
              position: 'relative',
              overflow: 'hidden',
              
              '&::before': {
                content: '""',
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                background: 'linear-gradient(45deg, transparent 30%, rgba(255,255,255,0.2) 50%, transparent 70%)',
                transform: 'translateX(-100%)',
                animation: 'shimmer 2s infinite',
              },
              
              '@keyframes shimmer': {
                '0%': { transform: 'translateX(-100%)' },
                '100%': { transform: 'translateX(100%)' }
              }
            }}>
              <BusinessIcon sx={{ fontSize: 48, color: 'white' }} />
            </Box>
            
            <Typography 
              variant="h2" 
              sx={{ 
                fontWeight: 800,
                mb: 2,
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                backgroundClip: 'text',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                fontSize: { xs: '2.5rem', md: '3.5rem' }
              }}
            >
              Welcome to Yelp Integration
            </Typography>
            
            <Typography 
              variant="h5" 
              sx={{ 
                color: 'text.secondary',
                mb: 4,
                maxWidth: 600,
                mx: 'auto',
                lineHeight: 1.6,
                fontSize: { xs: '1.1rem', md: '1.5rem' }
              }}
            >
              Streamline your business operations with intelligent automation, 
              real-time analytics, and seamless Yelp integration
            </Typography>

            <Stack 
              direction={{ xs: 'column', sm: 'row' }} 
              spacing={2} 
              justifyContent="center"
              alignItems="center"
            >
              <Chip
                icon={<ChatIcon />}
                label="AI-Powered Responses"
                color="primary"
                variant="filled"
                sx={{ 
                  px: 2, 
                  py: 1,
                  fontSize: '0.9rem',
                  fontWeight: 600,
                  boxShadow: 2
                }}
              />
              <Chip
                icon={<TrendingUpIcon />}
                label="Real-time Analytics"
                color="secondary"
                variant="filled"
                sx={{ 
                  px: 2, 
                  py: 1,
                  fontSize: '0.9rem',
                  fontWeight: 600,
                  boxShadow: 2
                }}
              />
            </Stack>
          </Box>
        </Grow>

        {/* Main Actions Grid */}
        <Grid container spacing={3} sx={{ mb: 6 }}>
          {menuItems.map((item, index) => (
            <Grid item xs={12} sm={6} lg={4} key={item.text}>
              <Grow in timeout={700 + index * 100}>
                <Card
                  sx={{
                    height: '100%',
                    borderRadius: 4,
                    overflow: 'hidden',
                    position: 'relative',
                    transition: 'all 0.4s cubic-bezier(0.25, 0.8, 0.25, 1)',
                    cursor: 'pointer',
                    background: 'white',
                    border: '1px solid',
                    borderColor: 'grey.200',
                    
                    '&:hover': {
                      transform: 'translateY(-8px) scale(1.02)',
                      boxShadow: `0 20px 60px ${alpha(item.color, 0.3)}`,
                      borderColor: item.color,
                      
                      '& .card-gradient': {
                        opacity: 1,
                      },
                      
                      '& .card-content': {
                        color: 'white',
                      },
                      
                      '& .action-arrow': {
                        transform: 'translateX(8px)',
                      }
                    }
                  }}
                  component={item.isAction ? 'div' : RouterLink}
                  to={item.isAction ? undefined : item.href}
                  onClick={item.isAction ? () => setDialogOpen(true) : undefined}
                >
                  {/* Gradient Overlay */}
                  <Box
                    className="card-gradient"
                    sx={{
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      right: 0,
                      bottom: 0,
                      background: item.gradient,
                      opacity: 0,
                      transition: 'opacity 0.4s ease-in-out',
                      zIndex: 1
                    }}
                  />
                  
                  <CardContent 
                    className="card-content"
                    sx={{ 
                      p: 3, 
                      height: '100%',
                      display: 'flex',
                      flexDirection: 'column',
                      position: 'relative',
                      zIndex: 2,
                      transition: 'color 0.4s ease-in-out'
                    }}
                  >
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                      <Avatar
                        sx={{
                          background: item.gradient,
                          width: 56,
                          height: 56,
                          mr: 2,
                          boxShadow: 3
                        }}
                      >
                        {item.icon}
                      </Avatar>
                      
                      <Box sx={{ flex: 1 }}>
                        <Typography 
                          variant="h6" 
                          sx={{ 
                            fontWeight: 700,
                            mb: 0.5
                          }}
                        >
                          {item.text}
                        </Typography>
                        
                        {item.isAction && (
                          <Chip
                            label="Action Required"
                            size="small"
                            color="warning"
                            variant="outlined"
                          />
                        )}
                      </Box>
                      
                      <ArrowForwardIcon 
                        className="action-arrow"
                        sx={{ 
                          transition: 'transform 0.3s ease-in-out',
                          opacity: 0.7
                        }} 
                      />
                    </Box>
                    
                    <Typography 
                      variant="body2" 
                      sx={{ 
                        opacity: 0.8,
                        lineHeight: 1.6,
                        flex: 1
                      }}
                    >
                      {item.description}
                    </Typography>
                  </CardContent>
                </Card>
              </Grow>
            </Grid>
          ))}
        </Grid>

        {/* Features Section */}
        <Grow in timeout={1000}>
          <Paper
            elevation={0}
            sx={{
              borderRadius: 4,
              overflow: 'hidden',
              background: 'linear-gradient(135deg, white 0%, #f8f9ff 100%)',
              border: '1px solid',
              borderColor: 'grey.200'
            }}
          >
            <Box sx={{ p: 4 }}>
              <Typography
                variant="h4"
                align="center"
                sx={{
                  fontWeight: 700,
                  mb: 1,
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  backgroundClip: 'text',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent'
                }}
              >
                Powerful Features
              </Typography>
              
              <Typography
                variant="body1"
                align="center"
                color="text.secondary"
                sx={{ mb: 4, maxWidth: 600, mx: 'auto' }}
              >
                Everything you need to manage your Yelp integration efficiently
              </Typography>

              <Grid container spacing={3}>
                {features.map((feature, index) => (
                  <Grid item xs={12} sm={6} key={feature.title}>
                    <Box
                      sx={{
                        display: 'flex',
                        alignItems: 'flex-start',
                        p: 2,
                        borderRadius: 2,
                        transition: 'all 0.3s ease-in-out',
                        
                        '&:hover': {
                          backgroundColor: 'rgba(102, 126, 234, 0.05)',
                          transform: 'translateX(8px)',
                        }
                      }}
                    >
                      <Avatar
                        sx={{
                          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                          width: 48,
                          height: 48,
                          mr: 2,
                          mt: 0.5
                        }}
                      >
                        {feature.icon}
                      </Avatar>
                      
                      <Box>
                        <Typography
                          variant="h6"
                          sx={{ fontWeight: 600, mb: 1 }}
                        >
                          {feature.title}
                        </Typography>
                        
                        <Typography
                          variant="body2"
                          color="text.secondary"
                          sx={{ lineHeight: 1.6 }}
                        >
                          {feature.description}
                        </Typography>
                      </Box>
                    </Box>
                  </Grid>
                ))}
              </Grid>
            </Box>
          </Paper>
        </Grow>
      </Container>

      {/* Alerts and Dialogs */}
      <Snackbar
        open={alertOpen}
        onClose={handleCloseAlert}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
      >
        <Alert 
          onClose={handleCloseAlert} 
          severity="error" 
          sx={{ 
            width: '100%',
            borderRadius: 2,
            boxShadow: 3
          }}
        >
          One or more refresh tokens expired. Please reauthorize.
        </Alert>
      </Snackbar>
      
      <Dialog 
        open={dialogOpen} 
        onClose={() => setDialogOpen(false)}
        PaperProps={{
          sx: {
            borderRadius: 3,
            minWidth: 400
          }
        }}
      >
        <DialogTitle sx={{ 
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          color: 'white',
          textAlign: 'center'
        }}>
          <VpnKeyIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
          Authorize with Yelp?
        </DialogTitle>
        
        <DialogActions sx={{ p: 3, gap: 2 }}>
          <Button 
            onClick={() => setDialogOpen(false)}
            variant="outlined"
            sx={{ flex: 1, borderRadius: 2 }}
          >
            Cancel
          </Button>
          <Button 
            onClick={() => { setDialogOpen(false); navigate('/auth'); }} 
            variant="contained"
            sx={{ 
              flex: 1, 
              borderRadius: 2,
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
            }}
            autoFocus
          >
            Continue
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Home;
