import React, { FC, useEffect, useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
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
  Paper,
  Snackbar,
  Alert,
  Box,
} from '@mui/material';

// --- Material-UI Icons ---
import EventIcon from '@mui/icons-material/Event';
import SettingsIcon from '@mui/icons-material/Settings';
import VpnKeyIcon from '@mui/icons-material/VpnKey';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import ListAltIcon from '@mui/icons-material/ListAlt';

const Home: FC = () => {
  const [alertOpen, setAlertOpen] = useState(false);

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
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(to right, #e1f5fe, #e3f2fd)',
        py: 8,
      }}
    >
      <Container maxWidth="md">
        <Paper
          elevation={6}
          sx={{ p: 4, borderRadius: 3, backgroundColor: 'rgba(255,255,255,0.9)' }}
        >
          <Typography variant="h4" component="h1" gutterBottom>
            Welcome to the Yelp Integration Dashboard!
          </Typography>
        <Typography variant="body1" color="text.secondary" paragraph>
          This dashboard helps you manage your Yelp events, leads, and automated responses.
          Select an action from the list below to get started.
        </Typography>
        <List>
          <ListItem disablePadding>
            <ListItemButton component={RouterLink} to="/events">
              <ListItemIcon>
                <EventIcon />
              </ListItemIcon>
              <ListItemText primary="View Events" />
            </ListItemButton>
          </ListItem>
        <ListItem disablePadding>
          <ListItemButton component={RouterLink} to="/settings">
            <ListItemIcon>
              <SettingsIcon />
            </ListItemIcon>
            <ListItemText primary="Auto-response Settings" />
          </ListItemButton>
        </ListItem>
        <ListItem disablePadding>
          <ListItemButton component={RouterLink} to="/tokens">
            <ListItemIcon>
              <AccessTimeIcon />
            </ListItemIcon>
            <ListItemText primary="Token Status" />
          </ListItemButton>
        </ListItem>
        <ListItem disablePadding>
          <ListItemButton component={RouterLink} to="/tasks">
            <ListItemIcon>
              <ListAltIcon />
            </ListItemIcon>
            <ListItemText primary="Celery Tasks" />
          </ListItemButton>
        </ListItem>
          <ListItem disablePadding>
            <ListItemButton component={RouterLink} to="/auth">
              <ListItemIcon>
                <VpnKeyIcon />
              </ListItemIcon>
              <ListItemText primary="Authorize with Yelp" />
            </ListItemButton>
          </ListItem>
        </List>
      </Paper>
      <Snackbar
        open={alertOpen}
        onClose={handleCloseAlert}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
      >
        <Alert onClose={handleCloseAlert} severity="error" sx={{ width: '100%' }}>
          One or more refresh tokens expired. Please reauthorize.
        </Alert>
      </Snackbar>
    </Container>
    </Box>
  );
};

export default Home;
