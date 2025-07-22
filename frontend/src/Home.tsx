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
import DashboardIcon from '@mui/icons-material/Dashboard';
import BusinessIcon from '@mui/icons-material/Business';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import ChatIcon from '@mui/icons-material/Chat';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';
import SubscriptionsIcon from '@mui/icons-material/Subscriptions';
import ChecklistIcon from '@mui/icons-material/Checklist';
import LoginIcon from '@mui/icons-material/Login';

const menuItems = [
  { 
    text: 'Events', 
    icon: <EventIcon />, 
    href: '/events',
    description: 'Monitor and manage your Yelp lead events in real-time',
    color: '#f093fb',
    gradient: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
    category: 'main'
  },
  { 
    text: 'Tokens & Business', 
    icon: <VpnKeyIcon />, 
    href: '/tokens',
    description: 'Check authorization status and business connections',
    color: '#4facfe',
    gradient: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
    category: 'main'
  },
  { 
    text: 'Subscriptions', 
    icon: <SubscriptionsIcon />, 
    href: '/subscriptions',
    description: 'Manage webhook subscriptions for real-time notifications',
    color: '#43e97b',
    gradient: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
    category: 'main'
  },
  { 
    text: 'Tasks', 
    icon: <ChecklistIcon />, 
    href: '/tasks',
    description: 'View scheduled operations and task logs',
    color: '#fa709a',
    gradient: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
    category: 'main'
  },
  { 
    text: 'Auto-response Settings', 
    icon: <SettingsIcon />, 
    href: '/settings',
    description: 'Configure automated messaging templates and responses',
    color: '#764ba2',
    gradient: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    category: 'main'
  },
  { 
    text: 'Authorize with Yelp', 
    icon: <LoginIcon />, 
    href: '/auth',
    description: 'Connect and authorize your Yelp business account',
    color: '#ff7eb3',
    gradient: 'linear-gradient(135deg, #ff7eb3 0%, #ff758c 100%)',
    isAction: true,
    category: 'auth'
  },
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
                animation: 'shimmer 3s ease-in-out infinite',
              },
              
              '@keyframes shimmer': {
                '0%': { 
                  transform: 'translateX(-100%)',
                  opacity: 0
                },
                '50%': {
                  opacity: 1
                },
                '100%': { 
                  transform: 'translateX(100%)',
                  opacity: 0
                }
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
              sx={{ mb: 4 }}
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
            
            <Button
              component={RouterLink}
              to="/events"
              variant="contained"
              size="large"
              startIcon={<DashboardIcon />}
              sx={{
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                borderRadius: 4,
                px: 4,
                py: 2,
                fontWeight: 700,
                fontSize: '1.1rem',
                textTransform: 'none',
                boxShadow: '0 8px 24px rgba(102, 126, 234, 0.3)',
                border: '2px solid rgba(255, 255, 255, 0.2)',
                
                '&:hover': {
                  background: 'linear-gradient(135deg, #5a6fd8 0%, #6b4190 100%)',
                  transform: 'translateY(-3px) scale(1.05)',
                  boxShadow: '0 12px 32px rgba(102, 126, 234, 0.4)',
                  border: '2px solid rgba(255, 255, 255, 0.3)',
                }
              }}
            >
              Go to Dashboard
            </Button>
          </Box>
        </Grow>

        {/* Main Actions Grid */}
        <Box sx={{ mb: 6 }}>
          {/* Primary Navigation */}
          <Typography
            variant="h4"
            sx={{
              fontWeight: 700,
              mb: 3,
              textAlign: 'center',
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              backgroundClip: 'text',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent'
            }}
          >
            Dashboard Navigation
          </Typography>
          
          <Grid container spacing={3} sx={{ mb: 4 }}>
            {menuItems.filter(item => item.category === 'main').map((item, index) => (
              <Grid item xs={12} sm={6} lg={4} key={item.text}>
                <Grow in timeout={700 + index * 100}>
                  <Card
                    sx={{
                      height: '100%',
                      minHeight: 180,
                      borderRadius: 4,
                      overflow: 'hidden',
                      position: 'relative',
                      transition: 'all 0.4s cubic-bezier(0.25, 0.8, 0.25, 1)',
                      cursor: 'pointer',
                      background: 'white',
                      border: '2px solid',
                      borderColor: 'grey.100',
                      
                      '&:hover': {
                        transform: 'translateY(-12px) scale(1.03)',
                        boxShadow: `0 25px 80px ${alpha(item.color, 0.4)}`,
                        borderColor: item.color,
                        
                        '& .card-gradient': {
                          opacity: 1,
                        },
                        
                        '& .card-content': {
                          color: 'white',
                        },
                        
                        '& .action-arrow': {
                          transform: 'translateX(12px) scale(1.2)',
                        },
                        
                        '& .card-icon': {
                          transform: 'scale(1.1) rotate(5deg)',
                          boxShadow: '0 8px 25px rgba(255,255,255,0.3)',
                        }
                      }
                    }}
                    component={RouterLink}
                    to={item.href}
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
                      <Box sx={{ display: 'flex', alignItems: 'flex-start', mb: 2 }}>
                        <Avatar
                          className="card-icon"
                          sx={{
                            background: item.gradient,
                            width: 64,
                            height: 64,
                            mr: 2,
                            boxShadow: 4,
                            transition: 'all 0.3s ease-in-out',
                            '& .MuiSvgIcon-root': {
                              fontSize: '2rem'
                            }
                          }}
                        >
                          {item.icon}
                        </Avatar>
                        
                        <Box sx={{ flex: 1, minWidth: 0 }}>
                          <Typography 
                            variant="h6" 
                            sx={{ 
                              fontWeight: 700,
                              mb: 1,
                              lineHeight: 1.2
                            }}
                          >
                            {item.text}
                          </Typography>
                        </Box>
                        
                        <ArrowForwardIcon 
                          className="action-arrow"
                          sx={{ 
                            transition: 'all 0.3s ease-in-out',
                            opacity: 0.6,
                            fontSize: '1.5rem'
                          }} 
                        />
                      </Box>
                      
                      <Typography 
                        variant="body2" 
                        sx={{ 
                          opacity: 0.8,
                          lineHeight: 1.6,
                          flex: 1,
                          fontSize: '0.9rem'
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

          {/* Authorization Section */}
          <Typography
            variant="h5"
            sx={{
              fontWeight: 600,
              mb: 2,
              textAlign: 'center',
              color: 'text.secondary'
            }}
          >
            Account Management
          </Typography>
          
          <Grid container justifyContent="center">
            <Grid item xs={12} sm={8} md={6} lg={4}>
              {menuItems.filter(item => item.category === 'auth').map((item, index) => (
                <Grow in timeout={1200} key={item.text}>
                  <Card
                    sx={{
                      borderRadius: 4,
                      overflow: 'hidden',
                      position: 'relative',
                      transition: 'all 0.4s cubic-bezier(0.25, 0.8, 0.25, 1)',
                      cursor: 'pointer',
                      background: 'white',
                      border: '2px solid',
                      borderColor: alpha(item.color, 0.3),
                      
                      '&:hover': {
                        transform: 'translateY(-8px) scale(1.02)',
                        boxShadow: `0 20px 60px ${alpha(item.color, 0.4)}`,
                        borderColor: item.color,
                        
                        '& .card-gradient': {
                          opacity: 1,
                        },
                        
                        '& .card-content': {
                          color: 'white',
                        },
                        
                        '& .action-arrow': {
                          transform: 'translateX(8px)',
                        },
                        
                        '& .auth-pulse': {
                          animation: 'pulse 1.5s infinite',
                        }
                      },
                      
                      '@keyframes pulse': {
                        '0%': { transform: 'scale(1)' },
                        '50%': { transform: 'scale(1.05)' },
                        '100%': { transform: 'scale(1)' }
                      }
                    }}
                    onClick={() => setDialogOpen(true)}
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
                        p: 4, 
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        textAlign: 'center',
                        position: 'relative',
                        zIndex: 2,
                        transition: 'color 0.4s ease-in-out'
                      }}
                    >
                      <Avatar
                        className="auth-pulse"
                        sx={{
                          background: item.gradient,
                          width: 72,
                          height: 72,
                          mb: 2,
                          boxShadow: 4,
                          '& .MuiSvgIcon-root': {
                            fontSize: '2.5rem'
                          }
                        }}
                      >
                        {item.icon}
                      </Avatar>
                      
                      <Typography 
                        variant="h6" 
                        sx={{ 
                          fontWeight: 700,
                          mb: 1
                        }}
                      >
                        {item.text}
                      </Typography>
                      
                      <Typography 
                        variant="body2" 
                        sx={{ 
                          opacity: 0.8,
                          lineHeight: 1.6,
                          mb: 2
                        }}
                      >
                        {item.description}
                      </Typography>
                      
                      <Chip
                        label="Action Required"
                        size="small"
                        color="warning"
                        variant="outlined"
                        sx={{ 
                          fontWeight: 600,
                          borderWidth: 2,
                          '&:hover': {
                            backgroundColor: 'warning.main',
                            color: 'white'
                          }
                        }}
                      />
                    </CardContent>
                  </Card>
                </Grow>
              ))}
            </Grid>
          </Grid>
        </Box>
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
