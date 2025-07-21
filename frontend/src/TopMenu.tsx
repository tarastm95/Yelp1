import React from 'react';
import { useLocation } from 'react-router-dom';
import { AppBar, Toolbar, Button, Box } from '@mui/material';
import HomeIcon from '@mui/icons-material/Home';
import EventIcon from '@mui/icons-material/Event';
import VpnKeyIcon from '@mui/icons-material/VpnKey';
import SubscriptionsIcon from '@mui/icons-material/Subscriptions';
import ChecklistIcon from '@mui/icons-material/Checklist';
import DescriptionIcon from '@mui/icons-material/Description';
import SettingsIcon from '@mui/icons-material/Settings';
import LoginIcon from '@mui/icons-material/Login';
import LogoutIcon from '@mui/icons-material/Logout';

const menuItems = [
  { text: 'Home', icon: <HomeIcon />, href: '/' },
  { text: 'Events', icon: <EventIcon />, href: '/events' },
  { text: 'Tokens&Business', icon: <VpnKeyIcon />, href: '/tokens' },
  { text: 'Subscriptions', icon: <SubscriptionsIcon />, href: '/subscriptions' },
  { text: 'Tasks', icon: <ChecklistIcon />, href: '/tasks' },
  { text: 'Auto-response Settings', icon: <SettingsIcon />, href: '/settings' },
  { text: 'Authorize with Yelp', icon: <LoginIcon />, href: '/auth' },
];

interface Props {
  onLogout: () => void;
}

const TopMenu: React.FC<Props> = ({ onLogout }) => {
  const location = useLocation();

  return (
    <AppBar position="static" color="default" elevation={0}>
      <Toolbar>
        <Box sx={{ display: 'flex', gap: 2, flexGrow: 1 }}>
          {menuItems.map((item) => (
            <Button
              key={item.text}
              component="a"
              href={item.href}
              startIcon={item.icon}
              sx={{
                color: location.pathname === item.href ? 'primary.main' : 'inherit',
              }}
            >
              {item.text}
            </Button>
          ))}
        </Box>
        <Button
          startIcon={<LogoutIcon />}
          onClick={onLogout}
          sx={{ ml: 'auto', color: 'secondary.main' }}
        >
          Logout
        </Button>
      </Toolbar>
    </AppBar>
  );
};

export default TopMenu;
