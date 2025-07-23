import React from 'react';
import { useLocation } from 'react-router-dom';
import { 
  AppBar, 
  Toolbar, 
  Button, 
  Box, 
  Typography,
  Avatar,
  Chip,
  alpha
} from '@mui/material';
import HomeIcon from '@mui/icons-material/Home';
import EventIcon from '@mui/icons-material/Event';
import VpnKeyIcon from '@mui/icons-material/VpnKey';
import SubscriptionsIcon from '@mui/icons-material/Subscriptions';
import ChecklistIcon from '@mui/icons-material/Checklist';
import DescriptionIcon from '@mui/icons-material/Description';
import SettingsIcon from '@mui/icons-material/Settings';
import LoginIcon from '@mui/icons-material/Login';
import LogoutIcon from '@mui/icons-material/Logout';
import BusinessIcon from '@mui/icons-material/Business';
import NotificationsIcon from '@mui/icons-material/Notifications';

const menuItems = [
  { text: 'Home', icon: <HomeIcon />, href: '/', color: '#667eea' },
  { text: 'Events', icon: <EventIcon />, href: '/events', color: '#f093fb' },
  { text: 'Tokens&Business', icon: <VpnKeyIcon />, href: '/tokens', color: '#4facfe' },
  { text: 'Subscriptions', icon: <SubscriptionsIcon />, href: '/subscriptions', color: '#43e97b' },
  { text: 'Tasks', icon: <ChecklistIcon />, href: '/tasks', color: '#fa709a' },
  { text: 'Notifications', icon: <NotificationsIcon />, href: '/notifications', color: '#ffb74d' },
  { text: 'Auto-response Settings', icon: <SettingsIcon />, href: '/settings', color: '#764ba2' },
  { text: 'Authorize with Yelp', icon: <LoginIcon />, href: '/auth', color: '#ff7eb3' },
];

interface Props {
  onLogout: () => void;
}

const TopMenu: React.FC<Props> = ({ onLogout }) => {
  const location = useLocation();

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

        {/* Navigation Items */}
        <Box sx={{ 
          display: 'flex', 
          gap: 1, 
          flexGrow: 1,
          flexWrap: 'wrap',
          justifyContent: 'center'
        }}>
          {menuItems.map((item) => {
            const isActive = location.pathname === item.href;
            
            return (
              <Button
                key={item.text}
                component="a"
                href={item.href}
                startIcon={item.icon}
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
                  minWidth: 'auto',
                  
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
                  
                  // Animated gradient background on hover
                  '&::before': {
                    content: '""',
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    background: `linear-gradient(135deg, ${alpha(item.color, 0.3)} 0%, ${alpha(item.color, 0.1)} 100%)`,
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
                    transform: 'scale(1.1) rotate(5deg)',
                  }
                }}
              >
                {item.text}
              </Button>
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
