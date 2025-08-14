import React, { FC, useEffect, useState } from 'react';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
import axios from 'axios';

// --- Material-UI Imports ---
import {
  Container,
  Typography,
  Card,
  CardContent,
  Button,
  useMediaQuery,
  useTheme,
  Grow,
  Box,
  Grid,
  Avatar,
  Chip,
  Paper,
  Stack,
  alpha,
  IconButton,
  LinearProgress,
  Tooltip,
  Badge,
  Skeleton,
  Fade,
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
import SmsIcon from '@mui/icons-material/Sms';
import Psychology from '@mui/icons-material/Psychology';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import WorkIcon from '@mui/icons-material/Work';
import NotificationsIcon from '@mui/icons-material/Notifications';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import WarningIcon from '@mui/icons-material/Warning';
import ErrorIcon from '@mui/icons-material/Error';
import LaunchIcon from '@mui/icons-material/Launch';
import RefreshIcon from '@mui/icons-material/Refresh';
import TimelineIcon from '@mui/icons-material/Timeline';
import PeopleIcon from '@mui/icons-material/People';
import MessageIcon from '@mui/icons-material/Message';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';

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
        color: '#f093fb',
        gradient: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
        stats: { label: 'Active Events', value: 0 }
      },
      {
        title: 'Tasks Management',
        description: 'View and manage scheduled operations and workflows',
        icon: <ChecklistIcon />,
        href: '/tasks',
        color: '#fa709a',
        gradient: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
        stats: { label: 'Active Tasks', value: 0 }
      },
      {
        title: 'SMS Communications',
        description: 'Track SMS interactions and message logs',
        icon: <SmsIcon />,
        href: '/sms-logs',
        color: '#4facfe',
        gradient: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
        stats: { label: 'SMS Sent', value: 0 }
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
        color: '#764ba2',
        gradient: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        stats: { label: 'Templates', value: 0 }
      },
      {
        title: 'AI Global Settings',
        description: 'Manage artificial intelligence configuration and behavior',
        icon: <Psychology />,
        href: '/ai-settings',
        color: '#667eea',
        gradient: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        stats: { label: 'AI Models', value: 0 }
      },
      {
        title: 'Time-Based Greetings',
        description: 'Set up time-sensitive automated greetings',
        icon: <AccessTimeIcon />,
        href: '/time-greetings',
        color: '#43e97b',
        gradient: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
        stats: { label: 'Active Rules', value: 0 }
      },
      {
        title: 'Job Name Settings',
        description: 'Configure job titles and business mappings',
        icon: <WorkIcon />,
        href: '/job-mappings',
        color: '#f093fb',
        gradient: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
        stats: { label: 'Mappings', value: 0 }
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
        color: '#4facfe',
        gradient: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
        stats: { label: 'Active Tokens', value: 0 }
      },
      {
        title: 'Yelp Authorization',
        description: 'Connect and authorize your Yelp business account',
        icon: <LoginIcon />,
        href: '/auth',
        color: '#ff7eb3',
        gradient: 'linear-gradient(135deg, #ff7eb3 0%, #ff758c 100%)',
        stats: { label: 'Connected', value: 0 }
      },
      {
        title: 'Webhook Subscriptions',
        description: 'Manage webhook subscriptions for real-time notifications',
        icon: <SubscriptionsIcon />,
        href: '/subscriptions',
        color: '#43e97b',
        gradient: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
        stats: { label: 'Subscriptions', value: 0 }
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
    color: '#f093fb'
  },
  {
    title: 'Configure AI',
    description: 'Adjust AI response settings',
    icon: <Psychology />,
    href: '/ai-settings',
    color: '#667eea'
  },
  {
    title: 'Check System Status',
    description: 'View tokens and connections',
    icon: <VpnKeyIcon />,
    href: '/tokens',
    color: '#4facfe'
  },
  {
    title: 'Manage Templates',
    description: 'Edit auto-response templates',
    icon: <MessageIcon />,
    href: '/settings',
    color: '#764ba2'
  }
];

interface DashboardStats {
  totalLeads: number;
  totalEvents: number;
  totalTasks: number;
  totalSMS: number;
  systemHealth: 'healthy' | 'warning' | 'error';
  lastUpdated: string;
}

const Home: FC = () => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const navigate = useNavigate();

  // State management
  const [stats, setStats] = useState<DashboardStats>({
    totalLeads: 0,
    totalEvents: 0,
    totalTasks: 0,
    totalSMS: 0,
    systemHealth: 'healthy',
    lastUpdated: new Date().toISOString()
  });
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // Load dashboard data
  const loadDashboardData = async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    
    try {
      // Simulate API calls - replace with actual endpoints
      const [eventsRes, tasksRes, tokensRes] = await Promise.allSettled([
        axios.get('/processed_leads?limit=1').catch(() => ({ data: { count: 0 } })),
        axios.get('/task-logs?limit=1').catch(() => ({ data: { count: 0 } })),
        axios.get('/tokens/').catch(() => ({ data: [] }))
      ]);

      const newStats: DashboardStats = {
        totalLeads: eventsRes.status === 'fulfilled' ? eventsRes.value?.data?.count || 0 : 0,
        totalEvents: eventsRes.status === 'fulfilled' ? eventsRes.value?.data?.count || 0 : 0,
        totalTasks: tasksRes.status === 'fulfilled' ? tasksRes.value?.data?.count || 0 : 0,
        totalSMS: Math.floor(Math.random() * 1000), // Placeholder
        systemHealth: tokensRes.status === 'fulfilled' && tokensRes.value?.data?.length > 0 ? 'healthy' : 'warning',
        lastUpdated: new Date().toISOString()
      };

      setStats(newStats);
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
      setStats(prev => ({ ...prev, systemHealth: 'error' }));
    } finally {
      setLoading(false);
      if (isRefresh) setRefreshing(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
  }, []);

  const handleRefresh = () => {
    loadDashboardData(true);
  };

  const getHealthColor = () => {
    switch (stats.systemHealth) {
      case 'healthy': return '#43e97b';
      case 'warning': return '#fbbf24';
      case 'error': return '#f87171';
      default: return '#43e97b';
    }
  };

  const getHealthIcon = () => {
    switch (stats.systemHealth) {
      case 'healthy': return <CheckCircleIcon />;
      case 'warning': return <WarningIcon />;
      case 'error': return <ErrorIcon />;
      default: return <CheckCircleIcon />;
    }
  };

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
            background: 'linear-gradient(135deg, #fafbfc 0%, #ffffff 100%)',
            color: 'text.primary',
            p: { xs: 3, md: 6 },
            boxShadow: '0 8px 32px rgba(100, 116, 139, 0.12)',
            border: '1px solid rgba(226, 232, 240, 0.8)'
          }}>
            {/* Animated Background Pattern */}
            <Box
              sx={{
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                background: 'url("data:image/svg+xml,%3Csvg width="60" height="60" viewBox="0 0 60 60" xmlns="http://www.w3.org/2000/svg"%3E%3Cg fill="none" fill-rule="evenodd"%3E%3Cg fill="%23e2e8f0" fill-opacity="0.4"%3E%3Ccircle cx="30" cy="30" r="1"/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")',
                opacity: 0.5,
                animation: 'float 6s ease-in-out infinite'
              }}
            />
            
            <Box sx={{ position: 'relative', zIndex: 1 }}>
              <Box sx={{ 
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: { xs: 80, md: 120 },
                height: { xs: 80, md: 120 },
                borderRadius: '50%',
                background: 'linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%)',
                mb: 3,
                boxShadow: '0 10px 25px rgba(59, 130, 246, 0.3)',
                border: '3px solid rgba(59, 130, 246, 0.1)'
              }}>
                <AutoAwesomeIcon sx={{ fontSize: { xs: 40, md: 60 }, color: 'white' }} />
              </Box>
              
              <Typography 
                variant="h2" 
                sx={{ 
                  fontWeight: 800,
                  mb: 2,
                  fontSize: { xs: '2rem', md: '3.5rem' },
                  background: 'linear-gradient(135deg, #1e293b 0%, #3b82f6 50%, #8b5cf6 100%)',
                  backgroundClip: 'text',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent'
                }}
              >
                Welcome to Digitize It Hub
              </Typography>
              
              <Typography 
                variant="h5" 
                sx={{ 
                  opacity: 0.9,
                  mb: 4,
                  maxWidth: 600,
                  mx: 'auto',
                  lineHeight: 1.6,
                  fontSize: { xs: '1.1rem', md: '1.5rem' }
                }}
              >
                Your complete business automation and customer engagement platform
              </Typography>

              {/* System Status */}
              <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', mb: 3 }}>
                <Chip
                  icon={getHealthIcon()}
                  label={`System ${stats.systemHealth === 'healthy' ? 'Operational' : stats.systemHealth === 'warning' ? 'Warning' : 'Error'}`}
                  sx={{
                    background: 'rgba(255, 255, 255, 0.9)',
                    color: getHealthColor(),
                    border: `2px solid ${getHealthColor()}`,
                    fontWeight: 600,
                    backdropFilter: 'blur(10px)',
                    boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)'
                  }}
                />
                <Tooltip title="Refresh Status">
                  <IconButton 
                    onClick={handleRefresh}
                    disabled={refreshing}
                    sx={{ 
                      ml: 2, 
                      color: '#3b82f6',
                      background: 'rgba(59, 130, 246, 0.1)',
                      border: '1px solid rgba(59, 130, 246, 0.2)',
                      '&:hover': {
                        background: 'rgba(59, 130, 246, 0.2)'
                      }
                    }}
                  >
                    <RefreshIcon sx={{ 
                      animation: refreshing ? 'spin 1s linear infinite' : 'none'
                    }} />
                  </IconButton>
                </Tooltip>
              </Box>
            </Box>
          </Box>
        </Fade>

        {/* Dashboard Stats */}
        <Grow in timeout={1000}>
          <Grid container spacing={3} sx={{ mb: 6 }}>
            {[
              { label: 'Total Leads', value: stats.totalLeads, icon: <PeopleIcon />, color: '#f093fb' },
              { label: 'Active Events', value: stats.totalEvents, icon: <EventIcon />, color: '#4facfe' },
              { label: 'Running Tasks', value: stats.totalTasks, icon: <ChecklistIcon />, color: '#fa709a' },
              { label: 'SMS Sent', value: stats.totalSMS, icon: <SmsIcon />, color: '#43e97b' }
            ].map((stat, index) => (
              <Grid item xs={6} md={3} key={stat.label}>
                <Card sx={{
                  background: 'linear-gradient(135deg, #ffffff 0%, #f8fafc 100%)',
                  border: '2px solid rgba(59, 130, 246, 0.1)',
                  borderRadius: 4,
                  overflow: 'hidden',
                  position: 'relative',
                  transition: 'all 0.3s ease-in-out',
                  boxShadow: '0 4px 20px rgba(100, 116, 139, 0.08)',
                  '&:hover': {
                    transform: 'translateY(-8px)',
                    boxShadow: '0 20px 40px rgba(59, 130, 246, 0.15)',
                    borderColor: stat.color
                  }
                }}>
                  <CardContent sx={{ p: 3, textAlign: 'center' }}>
                    <Box sx={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      width: 70,
                      height: 70,
                      borderRadius: '50%',
                      background: `linear-gradient(135deg, ${stat.color}15, ${stat.color}25)`,
                      mb: 2,
                      color: stat.color,
                      border: `2px solid ${stat.color}30`,
                      boxShadow: `0 4px 15px ${stat.color}20`
                    }}>
                      {stat.icon}
                    </Box>
                    <Typography variant="h4" sx={{ fontWeight: 700, color: stat.color, mb: 1 }}>
                      {loading ? <Skeleton width={60} /> : stat.value.toLocaleString()}
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 500 }}>
                      {stat.label}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </Grow>

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
                  <Card 
                    component={RouterLink}
                    to={action.href}
                    sx={{
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
                    <CardContent sx={{ p: 2, textAlign: 'center' }}>
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
                    </CardContent>
                  </Card>
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
                    <Card sx={{
                      height: '100%',
                      background: 'linear-gradient(135deg, #ffffff 0%, #fafbfc 100%)',
                      border: '2px solid rgba(226, 232, 240, 0.6)',
                      borderRadius: 4,
                      overflow: 'hidden',
                      position: 'relative',
                      transition: 'all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1)',
                      cursor: 'pointer',
                      boxShadow: '0 4px 20px rgba(100, 116, 139, 0.08)',
                      
                      '&:hover': {
                        transform: 'translateY(-10px)',
                        boxShadow: '0 25px 50px rgba(59, 130, 246, 0.2)',
                        borderColor: service.color,
                        background: 'linear-gradient(135deg, #ffffff 0%, #f1f5f9 100%)',
                        
                        '& .service-icon': {
                          transform: 'scale(1.1)',
                          boxShadow: `0 10px 25px ${service.color}40`,
                        },
                        '& .service-arrow': {
                          transform: 'translateX(8px)',
                          color: service.color
                        },
                        '& .service-stats': {
                          background: `${service.color}15`,
                          borderColor: service.color
                        }
                      }
                    }}
                    component={RouterLink}
                    to={service.href}
                  >
                    <CardContent 
                      sx={{ 
                        p: 4, 
                        height: '100%',
                        display: 'flex',
                        flexDirection: 'column',
                        position: 'relative'
                      }}
                    >
                      <Box sx={{ display: 'flex', alignItems: 'flex-start', mb: 2 }}>
                        <Avatar
                          className="service-icon"
                          sx={{
                            background: `linear-gradient(135deg, ${service.color}, ${service.color}cc)`,
                            width: 64,
                            height: 64,
                            mr: 2,
                            boxShadow: `0 8px 20px ${service.color}30`,
                            border: '3px solid rgba(255, 255, 255, 0.9)',
                            transition: 'all 0.3s ease-in-out'
                          }}
                        >
                          {service.icon}
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
                            {service.title}
                          </Typography>
                          <ArrowForwardIcon 
                            className="service-arrow"
                            sx={{ 
                              position: 'absolute',
                              top: 20,
                              right: 20,
                              transition: 'all 0.3s ease-in-out',
                              opacity: 0.4,
                              fontSize: '1.5rem',
                              color: 'text.secondary'
                            }} 
                          />
                        </Box>
                      </Box>
                      
                      <Typography 
                        variant="body2" 
                        sx={{ 
                          opacity: 0.8,
                          lineHeight: 1.6,
                          flex: 1,
                          mb: 2
                        }}
                      >
                        {service.description}
                      </Typography>

                      {/* Service Stats */}
                      <Box sx={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        mt: 'auto'
                      }}>
                        <Typography variant="caption" sx={{ opacity: 0.7 }}>
                          {service.stats.label}
                        </Typography>
                        <Chip
                          className="service-stats"
                          label={loading ? '...' : service.stats.value}
                          size="small"
                          sx={{
                            background: 'rgba(226, 232, 240, 0.5)',
                            color: 'text.secondary',
                            fontWeight: 600,
                            border: '2px solid rgba(226, 232, 240, 0.8)',
                            transition: 'all 0.3s ease-in-out'
                          }}
                        />
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
            </Box>
          </Grow>
        ))}

        {/* System Information Footer */}
        <Fade in timeout={2000}>
          <Box sx={{
            textAlign: 'center',
            p: 4,
            background: 'linear-gradient(135deg, #ffffff 0%, #f8fafc 100%)',
            borderRadius: 4,
            border: '2px solid rgba(226, 232, 240, 0.8)',
            boxShadow: '0 4px 20px rgba(100, 116, 139, 0.08)'
          }}>
            <Typography variant="body2" color="text.secondary">
              Last updated: {new Date(stats.lastUpdated).toLocaleString()} • 
              System Status: <span style={{ color: getHealthColor(), fontWeight: 600 }}>
                {stats.systemHealth.charAt(0).toUpperCase() + stats.systemHealth.slice(1)}
              </span>
            </Typography>
          </Box>
        </Fade>
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