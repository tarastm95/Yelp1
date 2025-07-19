import React from 'react';
import { useLocation } from 'react-router-dom';
import {
  Drawer,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Toolbar,
  Divider,
} from '@mui/material';
import HomeIcon from '@mui/icons-material/Home';
import EventIcon from '@mui/icons-material/Event';
import BusinessIcon from '@mui/icons-material/Business';
import VpnKeyIcon from '@mui/icons-material/VpnKey';
import SubscriptionsIcon from '@mui/icons-material/Subscriptions';
import ChecklistIcon from '@mui/icons-material/Checklist';
import DescriptionIcon from '@mui/icons-material/Description';
import SettingsIcon from '@mui/icons-material/Settings';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import ListIcon from '@mui/icons-material/List';

const drawerWidth = 240;

const menuItems = [
  { text: 'Home', icon: <HomeIcon />, href: '/home' },
  { text: 'Events', icon: <EventIcon />, href: '/events' },
  { text: 'Businesses', icon: <BusinessIcon />, href: '/businesses' },
  { text: 'Tokens', icon: <VpnKeyIcon />, href: '/tokens' },
  { text: 'Subscriptions', icon: <SubscriptionsIcon />, href: '/subscriptions' },
  { text: 'Tasks', icon: <ChecklistIcon />, href: '/tasks' },
  { text: 'Templates', icon: <DescriptionIcon />, href: '/templates' },
  { text: 'View Events', icon: <EventIcon />, href: '/view-events' },
  { text: 'Auto-response Settings', icon: <SettingsIcon />, href: '/auto-response-settings' },
  { text: 'Token Status', icon: <AccessTimeIcon />, href: '/token-status' },
  { text: 'Planned Tasks', icon: <ListIcon />, href: '/planned-tasks' },
  { text: 'Authorize with Yelp', icon: <VpnKeyIcon />, href: '/authorize-yelp' },
];

const Sidebar: React.FC = () => {
  const location = useLocation();

  return (
    <Drawer
      variant="permanent"
      sx={{
        width: drawerWidth,
        flexShrink: 0,
        [`& .MuiDrawer-paper`]: { width: drawerWidth, boxSizing: 'border-box' },
      }}
    >
      <Toolbar />
      <Divider />
      <List>
        {menuItems.map(item => (
          <ListItemButton
            key={item.text}
            component="a"
            href={item.href}
            selected={location.pathname === item.href}
            sx={{
              '&.Mui-selected': {
                bgcolor: 'rgba(0,0,0,0.08)',
                '& .MuiListItemIcon-root, & .MuiListItemText-primary': {
                  color: 'primary.main',
                },
              },
            }}
          >
            <ListItemIcon>{item.icon}</ListItemIcon>
            <ListItemText primary={item.text} />
          </ListItemButton>
        ))}
      </List>
    </Drawer>
  );
};

export default Sidebar;
