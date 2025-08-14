import React, { FC } from 'react';
import { Link as RouterLink } from 'react-router-dom';

// --- Material-UI Imports ---
import {
  Container,
  Typography,
  Button,
  Grow,
  Box,
  Grid,
  Avatar,
  Fade,
} from '@mui/material';

// --- Material-UI Icons ---
import EventIcon from '@mui/icons-material/Event';
import SettingsIcon from '@mui/icons-material/Settings';
import VpnKeyIcon from '@mui/icons-material/VpnKey';
import BusinessIcon from '@mui/icons-material/Business';
import SubscriptionsIcon from '@mui/icons-material/Subscriptions';
import ChecklistIcon from '@mui/icons-material/Checklist';
import LoginIcon from '@mui/icons-material/Login';
import SmsIcon from '@mui/icons-material/Sms';
import Psychology from '@mui/icons-material/Psychology';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import WorkIcon from '@mui/icons-material/Work';
import MessageIcon from '@mui/icons-material/Message';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';
import PeopleIcon from '@mui/icons-material/People';

// Service Categories
const serviceCategories = {
  engage: {
    title: 'Digitize It Engage',
    subtitle: 'Lead Management & Customer Interaction',
    color: '#f093fb',
    icon: <PeopleIcon />,
    services: [
      {
        title: 'Events & Leads',
        description: 'Monitor customer events and manage leads in real-time',
        icon: <EventIcon />,
        href: '/events',
        color: '#dc2626'

      },
      {
        title: 'Tasks Management',
        description: 'View and manage scheduled operations and workflows',
        icon: <ChecklistIcon />,
        href: '/tasks',
        color: '#0ea5e9'

      },
      {
        title: 'SMS Communications',
        description: 'Track SMS interactions and message logs',
        icon: <SmsIcon />,
        href: '/sms-logs',
        color: '#10b981'

      }
    ]
  },
  console: {
    title: 'Digitize It Console',
    subtitle: 'Configuration & Automation Settings',
    color: '#43e97b',
    icon: <SettingsIcon />,
    services: [
      {
        title: 'Auto-Response Settings',
        description: 'Configure automated messaging templates and responses',
        icon: <MessageIcon />,
        href: '/settings',
        color: '#6366f1'

      },
      {
        title: 'AI Global Settings',
        description: 'Manage artificial intelligence configuration and behavior',
        icon: <Psychology />,
        href: '/ai-settings',
        color: '#8b5cf6'

      },
      {
        title: 'Time-Based Greetings',
        description: 'Set up time-sensitive automated greetings',
        icon: <AccessTimeIcon />,
        href: '/time-greetings',
        color: '#059669'

      },
      {
        title: 'Job Name Settings',
        description: 'Configure job titles and business mappings',
        icon: <WorkIcon />,
        href: '/job-mappings',
        color: '#8b5cf6'

      }
    ]
  },
  integration: {
    title: 'Integration Hub',
    subtitle: 'Business Connections & API Management',
    color: '#4facfe',
    icon: <BusinessIcon />,
    services: [
      {
        title: 'Business Tokens',
        description: 'Manage authorization tokens and business connections',
        icon: <VpnKeyIcon />,
        href: '/tokens',
        color: '#0ea5e9'

      },
      {
        title: 'Yelp Authorization',
        description: 'Connect and authorize your Yelp business account',
        icon: <LoginIcon />,
        href: '/auth',
        color: '#e11d48'

      },
      {
        title: 'Webhook Subscriptions',
        description: 'Manage webhook subscriptions for real-time notifications',
        icon: <SubscriptionsIcon />,
        href: '/subscriptions',
        color: '#10b981'

      }
    ]
  }
};

// Quick Actions
const quickActions = [
  {
    title: 'View Latest Events',
    description: 'Check recent customer interactions',
    icon: <EventIcon />,
    href: '/events',
    color: '#8b5cf6'
  },
  {
    title: 'Configure AI',
    description: 'Adjust AI response settings',
    icon: <Psychology />,
    href: '/ai-settings',
    color: '#6366f1'
  },
  {
    title: 'Check System Status',
    description: 'View tokens and connections',
    icon: <VpnKeyIcon />,
    href: '/tokens',
    color: '#0ea5e9'
  },
  {
    title: 'Manage Templates',
    description: 'Edit auto-response templates',
    icon: <MessageIcon />,
    href: '/settings',
    color: '#10b981'
  }
];



const Home: FC = () => {





  return (
    <Box sx={{ 
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #ffffff 0%, #f8fafc 50%, #e2e8f0 100%)',
      pb: 6
    }}>
      <Container maxWidth="xl" sx={{ pt: 4 }}>
        {/* Hero Section */}
        <Fade in timeout={800}>
            <Box sx={{ 
            textAlign: 'center', 
            mb: 6,
              position: 'relative',
              overflow: 'hidden',
            borderRadius: 4,
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            color: 'white',
            p: { xs: 4, md: 8 },
            boxShadow: '0 15px 40px rgba(102, 126, 234, 0.2)',
            border: '1px solid rgba(255, 255, 255, 0.1)'
          }}>
            {/* Animated Background Pattern */}
            <Box
              sx={{
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                background: 'url("data:image/svg+xml,%3Csvg width="60" height="60" viewBox="0 0 60 60" xmlns="http://www.w3.org/2000/svg"%3E%3Cg fill="none" fill-rule="evenodd"%3E%3Cg fill="%23ffffff" fill-opacity="0.1"%3E%3Ccircle cx="30" cy="30" r="2"/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")',
                opacity: 0.3,
                animation: 'float 6s ease-in-out infinite'
              }}
            />
            
            <Box sx={{ position: 'relative', zIndex: 1 }}>
              <Box sx={{ 
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: { xs: 100, md: 140 },
                height: { xs: 100, md: 140 },
                borderRadius: '50%',
                background: 'rgba(255, 255, 255, 0.15)',
                mb: 4,
                backdropFilter: 'blur(20px)',
                border: '3px solid rgba(255, 255, 255, 0.2)',
                boxShadow: '0 15px 35px rgba(0, 0, 0, 0.1)'
              }}>
                <AutoAwesomeIcon sx={{ fontSize: { xs: 50, md: 70 }, color: 'white' }} />
            </Box>
            
            <Typography 
              variant="h2" 
              sx={{ 
                fontWeight: 800,
                  mb: 3,
                  fontSize: { xs: '2.2rem', md: '4rem' },
                  color: 'white',
                  textShadow: '0 4px 8px rgba(0, 0, 0, 0.3)',
                  letterSpacing: '-0.02em'
                }}
              >
                Welcome to Digitize It Hub
            </Typography>
            
            <Typography 
              variant="h5" 
              sx={{ 
                  color: 'rgba(255, 255, 255, 0.85)',
                  mb: 0,
                  maxWidth: 650,
                mx: 'auto',
                  lineHeight: 1.5,
                  fontSize: { xs: '1.1rem', md: '1.4rem' },
                  fontWeight: 400,
                  textShadow: '0 2px 4px rgba(0, 0, 0, 0.2)'
                }}
              >
                Your complete business automation and customer engagement platform
            </Typography>


            </Box>
          </Box>
        </Fade>



        {/* Quick Actions */}
        <Grow in timeout={1200}>
        <Box sx={{ mb: 6 }}>
            <Typography variant="h4" sx={{
              fontWeight: 700,
              mb: 3,
              textAlign: 'center',
              background: 'linear-gradient(135deg, #1e293b 0%, #3b82f6 50%, #8b5cf6 100%)',
              backgroundClip: 'text',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent'
            }}>
              Quick Actions
          </Typography>
          
            <Grid container spacing={2}>
              {quickActions.map((action, index) => (
                <Grid item xs={6} md={3} key={action.title}>
                  <Box
                    component={RouterLink}
                    to={action.href}
                    sx={{
                      display: 'block',
                      background: 'linear-gradient(135deg, #ffffff 0%, #f8fafc 100%)',
                      border: '2px solid rgba(226, 232, 240, 0.6)',
                      borderRadius: 4,
                      textDecoration: 'none',
                      transition: 'all 0.3s ease-in-out',
                      cursor: 'pointer',
                      boxShadow: '0 4px 15px rgba(100, 116, 139, 0.08)',
                      '&:hover': {
                        transform: 'translateY(-5px) scale(1.03)',
                        boxShadow: '0 15px 35px rgba(59, 130, 246, 0.2)',
                        borderColor: action.color,
                        background: 'linear-gradient(135deg, #ffffff 0%, #f1f5f9 100%)'
                      }
                    }}
                  >
                    <Box sx={{ p: 2, textAlign: 'center' }}>
                      <Box sx={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        width: 56,
                        height: 56,
                        borderRadius: '50%',
                        background: `linear-gradient(135deg, ${action.color}15, ${action.color}25)`,
                        color: action.color,
                        mb: 1,
                        border: `2px solid ${action.color}30`,
                        boxShadow: `0 4px 12px ${action.color}20`
                      }}>
                        {action.icon}
                      </Box>
                      <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 0.5 }}>
                        {action.title}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {action.description}
                      </Typography>
                    </Box>
                  </Box>
                </Grid>
              ))}
            </Grid>
          </Box>
        </Grow>

        {/* Service Categories */}
        {Object.entries(serviceCategories).map(([key, category], categoryIndex) => (
          <Grow in timeout={1400 + categoryIndex * 200} key={key}>
            <Box sx={{ mb: 6 }}>
              {/* Category Header */}
              <Box sx={{
                background: 'linear-gradient(135deg, #ffffff 0%, #f8fafc 100%)',
                borderRadius: 4,
                p: 4,
                mb: 4,
                border: '2px solid rgba(226, 232, 240, 0.8)',
                boxShadow: '0 4px 20px rgba(100, 116, 139, 0.08)'
              }}>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <Avatar sx={{
                    background: `linear-gradient(135deg, ${category.color}, ${category.color}cc)`,
                    mr: 3,
                    width: 60,
                    height: 60,
                    boxShadow: `0 8px 20px ${category.color}40`,
                    border: '3px solid rgba(255, 255, 255, 0.9)'
                  }}>
                    {category.icon}
                  </Avatar>
                  <Box>
                    <Typography variant="h5" sx={{ fontWeight: 700, color: category.color }}>
                      {category.title}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {category.subtitle}
                    </Typography>
                  </Box>
                </Box>
              </Box>

              {/* Services Grid */}
              <Grid container spacing={3}>
                {category.services.map((service, serviceIndex) => (
                  <Grid item xs={12} md={6} lg={3} key={service.title}>
                    <Box
                      component={RouterLink}
                      to={service.href}
                      sx={{
                        display: 'block',
                        textDecoration: 'none',
                        height: 200,
                        background: `linear-gradient(135deg, ${service.color} 0%, ${service.color}dd 100%)`,
                        borderRadius: 3,
                        overflow: 'hidden',
                        position: 'relative',
                        transition: 'all 0.3s ease-in-out',
                        cursor: 'pointer',
                        boxShadow: '0 8px 25px rgba(0, 0, 0, 0.15)',
                        
                        '&:hover': {
                          transform: 'translateY(-8px)',
                          boxShadow: '0 15px 40px rgba(0, 0, 0, 0.25)',
                          
                          '& .service-button': {
                            gap: 1.5,
                            '& .arrow-icon': {
                              transform: 'translateX(4px)'
                            }
                          }
                        }
                      }}
                    >
                      <Box
                        sx={{
                          p: 3,
                          height: '100%',
                          display: 'flex',
                          flexDirection: 'column',
                          justifyContent: 'space-between'
                        }}
                      >
                      <Box>
                        <Typography 
                          variant="h6" 
                          sx={{ 
                            fontWeight: 700,
                            mb: 2,
                            color: 'white',
                            fontSize: '1.25rem',
                            lineHeight: 1.2
                          }}
                        >
                          {service.title}
                        </Typography>
                        
                        <Typography 
                          variant="body2" 
                          sx={{ 
                            color: 'rgba(255, 255, 255, 0.9)',
                            lineHeight: 1.5,
                            fontSize: '0.875rem',
                            mb: 2
                          }}
                        >
                          {service.description}
                        </Typography>
                      </Box>

                      <Button
                        className="service-button"
                        sx={{
                          alignSelf: 'flex-start',
                          color: 'rgba(255, 255, 255, 0.9)',
                          textTransform: 'none',
                          fontSize: '0.875rem',
                          fontWeight: 500,
                          display: 'flex',
                          alignItems: 'center',
                          gap: 1,
                          p: 0,
                          minWidth: 'auto',
                          transition: 'all 0.2s ease-in-out',
                          
                          '&:hover': {
                            backgroundColor: 'transparent',
                            color: 'white'
                          }
                        }}
                      >
                        Open
                        <ArrowForwardIcon 
                          className="arrow-icon"
                          sx={{ 
                            fontSize: '1rem',
                            transition: 'transform 0.2s ease-in-out'
                          }} 
                        />
                      </Button>
                      </Box>
                    </Box>
                </Grid>
              ))}
            </Grid>
        </Box>
          </Grow>
        ))}


      </Container>

      {/* Global Styles for Animations */}
      <style>{`
        @keyframes float {
          0%, 100% { transform: translateY(0px); }
          50% { transform: translateY(-10px); }
        }
        
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </Box>
  );
};

export default Home;