import React, { useState } from 'react';
import { useLocation } from 'react-router-dom';
import { 
  AppBar, 
  Toolbar, 
  Button, 
  Box, 
  Typography,
  Avatar,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  Divider,
  alpha
} from '@mui/material';
import {
  Home as HomeIcon,
  Event as EventIcon,
  VpnKey as VpnKeyIcon,
  Subscriptions as SubscriptionsIcon,
  Checklist as ChecklistIcon,
  Settings as SettingsIcon,
  Login as LoginIcon,
  Logout as LogoutIcon,
  Business as BusinessIcon,
  Dashboard as DashboardIcon,
  ManageAccounts as ManageAccountsIcon,
  Tune as TuneIcon,
  Api as IntegrationIcon,
  ExpandMore as ExpandMoreIcon,
  Sms as SmsIcon,
  Psychology as AIIcon,
  AccessTime as AccessTimeIcon,
  Work as WorkIcon,
} from '@mui/icons-material';

// Grouping menu items logically
const menuGroups = {
  dashboard: {
    title: 'Dashboard',
    icon: <DashboardIcon />,
    color: '#667eea',
    items: [
      { text: 'Home', icon: <HomeIcon />, href: '/', color: '#667eea' },
    ]
  },
  leads: {
    title: 'Lead Management',
    icon: <ManageAccountsIcon />,
    color: '#f093fb',
    items: [
      { text: 'Events', icon: <EventIcon />, href: '/events', color: '#f093fb' },
      { text: 'Tasks', icon: <ChecklistIcon />, href: '/tasks', color: '#fa709a' },
      { text: 'SMS Logs', icon: <SmsIcon />, href: '/sms-logs', color: '#4facfe' },
    ]
  },
  config: {
    title: 'Configuration',
    icon: <TuneIcon />,
    color: '#43e97b',
    items: [
      { text: 'Auto-response Settings', icon: <SettingsIcon />, href: '/settings', color: '#764ba2' },
      { text: 'Global AI Settings', icon: <AIIcon />, href: '/ai-settings', color: '#667eea' },
      { text: 'Time-based Greetings', icon: <AccessTimeIcon />, href: '/time-greetings', color: '#43e97b' },
      { text: 'Job Name Settings', icon: <WorkIcon />, href: '/job-mappings', color: '#f093fb' },
    ]
  },
  integration: {
    title: 'Integration',
    icon: <IntegrationIcon />,
    color: '#4facfe',
    items: [
      { text: 'Tokens & Business', icon: <VpnKeyIcon />, href: '/tokens', color: '#4facfe' },
      { text: 'Authorize with Yelp', icon: <LoginIcon />, href: '/auth', color: '#ff7eb3' },
      { text: 'Subscriptions', icon: <SubscriptionsIcon />, href: '/subscriptions', color: '#43e97b' },
    ]
  }
};

interface Props {
  onLogout: () => void;
}

const TopMenu: React.FC<Props> = ({ onLogout }) => {
  const location = useLocation();
  const [anchorEls, setAnchorEls] = useState<{[key: string]: HTMLElement | null}>({});

  const handleMenuOpen = (groupKey: string, event: React.MouseEvent<HTMLElement>) => {
    setAnchorEls(prev => ({
      ...prev,
      [groupKey]: event.currentTarget
    }));
  };

  const handleMenuClose = (groupKey: string) => {
    setAnchorEls(prev => ({
      ...prev,
      [groupKey]: null
    }));
  };

  const isGroupActive = (groupKey: string) => {
    const group = menuGroups[groupKey as keyof typeof menuGroups];
    return group.items.some(item => location.pathname === item.href);
  };

  const getActiveItem = () => {
    for (const [groupKey, group] of Object.entries(menuGroups)) {
      const activeItem = group.items.find(item => location.pathname === item.href);
      if (activeItem) {
        return { groupKey, item: activeItem, group };
      }
    }
    return null;
  };

  const activeInfo = getActiveItem();

  return (
    <AppBar 
      position="static" 
      elevation={0}
      sx={{
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        boxShadow: '0 8px 32px rgba(102, 126, 234, 0.3)',
        borderBottom: '1px solid rgba(255, 255, 255, 0.1)'
      }}
    >
      <Toolbar sx={{ py: 1, px: 3 }}>
        {/* Logo/Brand Section */}
        <Box sx={{ display: 'flex', alignItems: 'center', mr: 4 }}>
          <Avatar
            sx={{
              width: 40,
              height: 40,
              background: 'linear-gradient(135deg, #fff 0%, #f8f9ff 100%)',
              color: 'primary.main',
              mr: 2,
              boxShadow: '0 4px 12px rgba(0,0,0,0.15)'
            }}
          >
            <BusinessIcon sx={{ fontSize: 24 }} />
          </Avatar>
          <Box>
            <Typography 
              variant="h6" 
              sx={{ 
                fontWeight: 700,
                color: 'white',
                textShadow: '0 2px 4px rgba(0,0,0,0.1)'
              }}
            >
              Yelp Integration
            </Typography>
            <Typography 
              variant="caption" 
              sx={{ 
                color: 'rgba(255,255,255,0.8)',
                fontSize: '0.7rem',
                lineHeight: 1
              }}
            >
              Dashboard
            </Typography>
          </Box>
        </Box>

        {/* Active Page Indicator */}
        {activeInfo && (
          <Box sx={{ 
            display: 'flex', 
            alignItems: 'center', 
            mr: 4,
            background: 'rgba(255, 255, 255, 0.15)',
            borderRadius: 2,
            px: 2,
            py: 0.5,
            backdropFilter: 'blur(10px)',
            border: '1px solid rgba(255, 255, 255, 0.2)'
          }}>
            <Box sx={{ color: 'white', mr: 1, fontSize: 18 }}>
              {activeInfo.item.icon}
            </Box>
            <Typography 
              variant="body2" 
              sx={{ 
                color: 'white',
                fontWeight: 600,
                fontSize: '0.875rem'
              }}
            >
              {activeInfo.item.text}
            </Typography>
          </Box>
        )}

        {/* Navigation Dropdowns */}
        <Box sx={{ 
          display: 'flex', 
          gap: 1, 
          flexGrow: 1,
          justifyContent: 'center'
        }}>
          {Object.entries(menuGroups).map(([groupKey, group]) => {
            const isActive = isGroupActive(groupKey);
            const isOpen = Boolean(anchorEls[groupKey]);
            
            return (
              <Box key={groupKey}>
                <Button
                  onClick={(e) => handleMenuOpen(groupKey, e)}
                  endIcon={<ExpandMoreIcon sx={{ 
                    transition: 'transform 0.2s ease-in-out',
                    transform: isOpen ? 'rotate(180deg)' : 'rotate(0deg)'
                  }} />}
                  startIcon={group.icon}
                  sx={{
                    color: 'white',
                    fontWeight: isActive ? 700 : 500,
                    borderRadius: 2,
                    px: 2,
                    py: 1,
                    position: 'relative',
                    overflow: 'hidden',
                    transition: 'all 0.3s ease-in-out',
                    textTransform: 'none',
                    fontSize: '0.875rem',
                    
                    // Active state
                    ...(isActive && {
                      backgroundColor: 'rgba(255, 255, 255, 0.2)',
                      backdropFilter: 'blur(10px)',
                      boxShadow: '0 4px 15px rgba(255, 255, 255, 0.1)',
                      transform: 'translateY(-2px)',
                    }),
                    
                    // Hover effects
                    '&:hover': {
                      backgroundColor: isActive 
                        ? 'rgba(255, 255, 255, 0.25)' 
                        : 'rgba(255, 255, 255, 0.15)',
                      transform: 'translateY(-2px)',
                      boxShadow: '0 6px 20px rgba(255, 255, 255, 0.15)',
                      
                      '&::before': {
                        opacity: 1,
                      }
                    },
                    
                    // Animated gradient background
                    '&::before': {
                      content: '""',
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      right: 0,
                      bottom: 0,
                      background: `linear-gradient(135deg, ${alpha(group.color, 0.3)} 0%, ${alpha(group.color, 0.1)} 100%)`,
                      opacity: isActive ? 0.7 : 0,
                      transition: 'opacity 0.3s ease-in-out',
                      zIndex: -1,
                      borderRadius: 'inherit'
                    },
                    
                    // Icon styling
                    '& .MuiButton-startIcon': {
                      color: 'inherit',
                      transition: 'transform 0.2s ease-in-out',
                    },
                    
                    '&:hover .MuiButton-startIcon': {
                      transform: 'scale(1.1)',
                    }
                  }}
                >
                  {group.title}
                </Button>

                <Menu
                  anchorEl={anchorEls[groupKey]}
                  open={isOpen}
                  onClose={() => handleMenuClose(groupKey)}
                  PaperProps={{
                    sx: {
                      borderRadius: 3,
                      minWidth: 220,
                      background: 'rgba(255, 255, 255, 0.95)',
                      backdropFilter: 'blur(20px)',
                      border: '1px solid rgba(255, 255, 255, 0.2)',
                      boxShadow: '0 8px 32px rgba(0, 0, 0, 0.12)',
                      mt: 1,
                      '& .MuiMenuItem-root': {
                        borderRadius: 2,
                        mx: 1,
                        my: 0.5,
                        transition: 'all 0.2s ease-in-out',
                        position: 'relative',
                        overflow: 'hidden',
                        
                        '&:hover': {
                          backgroundColor: `${alpha(group.color, 0.1)}`,
                          transform: 'translateX(4px)',
                          
                          '&::before': {
                            opacity: 1,
                          }
                        },
                        
                        '&::before': {
                          content: '""',
                          position: 'absolute',
                          left: 0,
                          top: 0,
                          bottom: 0,
                          width: 3,
                          background: group.color,
                          opacity: 0,
                          transition: 'opacity 0.2s ease-in-out',
                        }
                      }
                    }
                  }}
                  transformOrigin={{ horizontal: 'center', vertical: 'top' }}
                  anchorOrigin={{ horizontal: 'center', vertical: 'bottom' }}
                >
                  {group.items.map((item, index) => {
                    const isItemActive = location.pathname === item.href;
                    
                    return (
                      <MenuItem
                        key={item.text}
                        component="a"
                        href={item.href}
                        onClick={() => handleMenuClose(groupKey)}
                        sx={{
                          fontWeight: isItemActive ? 600 : 400,
                          ...(isItemActive && {
                            backgroundColor: `${alpha(item.color, 0.15)}`,
                            color: item.color,
                            '&::before': {
                              opacity: 1,
                              background: item.color,
                            }
                          })
                        }}
                      >
                        <ListItemIcon sx={{ 
                          color: isItemActive ? item.color : 'inherit',
                          transition: 'color 0.2s ease-in-out'
                        }}>
                          {item.icon}
                        </ListItemIcon>
                        <ListItemText 
                          primary={item.text}
                          primaryTypographyProps={{
                            fontSize: '0.875rem',
                            fontWeight: isItemActive ? 600 : 400
                          }}
                        />
                      </MenuItem>
                    );
                  })}
                </Menu>
              </Box>
            );
          })}
        </Box>

        {/* Logout Section */}
        <Box sx={{ ml: 2 }}>
          <Button
            onClick={onLogout}
            startIcon={<LogoutIcon />}
            sx={{
              color: 'white',
              fontWeight: 600,
              borderRadius: 2,
              px: 3,
              py: 1,
              background: 'linear-gradient(135deg, rgba(244, 67, 54, 0.8) 0%, rgba(233, 30, 99, 0.8) 100%)',
              border: '1px solid rgba(255, 255, 255, 0.2)',
              backdropFilter: 'blur(10px)',
              transition: 'all 0.3s ease-in-out',
              textTransform: 'none',
              boxShadow: '0 4px 15px rgba(244, 67, 54, 0.3)',
              
              '&:hover': {
                background: 'linear-gradient(135deg, rgba(244, 67, 54, 1) 0%, rgba(233, 30, 99, 1) 100%)',
                transform: 'translateY(-2px)',
                boxShadow: '0 6px 20px rgba(244, 67, 54, 0.4)',
                
                '& .MuiButton-startIcon': {
                  transform: 'rotate(-10deg) scale(1.1)',
                }
              },
              
              '& .MuiButton-startIcon': {
                transition: 'transform 0.2s ease-in-out',
              }
            }}
          >
            Logout
          </Button>
        </Box>
      </Toolbar>
    </AppBar>
  );
};

export default TopMenu;
