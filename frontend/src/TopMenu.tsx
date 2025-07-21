import React from 'react';
import { useLocation } from 'react-router-dom';
import { AppBar, Toolbar, Button, Box } from '@mui/material';
import HomeIcon from '@mui/icons-material/Home';
import EventIcon from '@mui/icons-material/Event';
import BusinessIcon from '@mui/icons-material/Business';
import VpnKeyIcon from '@mui/icons-material/VpnKey';
import SubscriptionsIcon from '@mui/icons-material/Subscriptions';
import ChecklistIcon from '@mui/icons-material/Checklist';
import DescriptionIcon from '@mui/icons-material/Description';

const menuItems = [
  { text: 'Home', icon: <HomeIcon />, href: '/' },
  { text: 'Events', icon: <EventIcon />, href: '/events' },
  { text: 'Businesses', icon: <BusinessIcon />, href: '/businesses' },
  { text: 'Tokens', icon: <VpnKeyIcon />, href: '/tokens' },
  { text: 'Subscriptions', icon: <SubscriptionsIcon />, href: '/subscriptions' },
  { text: 'Tasks', icon: <ChecklistIcon />, href: '/tasks' },
  { text: 'Templates', icon: <DescriptionIcon />, href: '/templates' },
];

const TopMenu: React.FC = () => {
  const location = useLocation();

  return (
    <AppBar position="static" color="default" elevation={0}>
      <Toolbar>
        <Box sx={{ display: 'flex', gap: 2 }}>
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
      </Toolbar>
    </AppBar>
  );
};

export default TopMenu;
