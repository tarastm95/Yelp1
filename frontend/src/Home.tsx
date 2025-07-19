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
} from '@mui/material';

// --- Material-UI Icons ---
import EventIcon from '@mui/icons-material/Event';
import SettingsIcon from '@mui/icons-material/Settings';
import VpnKeyIcon from '@mui/icons-material/VpnKey';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import ListAltIcon from '@mui/icons-material/ListAlt';

const Home: FC = () => {
  const [alertOpen, setAlertOpen] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const navigate = useNavigate();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));

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
    <Container maxWidth="lg" sx={{ mt: isMobile ? 2 : 4 }}>
      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '2fr 1fr' }, gap: 2 }}>
        <Grow in timeout={500}>
          <Box>
            <Card sx={{ p: 3, mb: 2 }}>
              <CardContent>
                <Typography variant="h4" gutterBottom>
                  Welcome to the Yelp Integration!
                </Typography>
                <Typography variant="body1" color="text.secondary">
                  This dashboard helps you manage your Yelp events, leads and automated responses. Select an action from the list to get started.
                </Typography>
              </CardContent>
            </Card>
          </Box>
        </Grow>
        <Grow in timeout={700}>
          <Box>
            <Card sx={{ p: 3, mb: 2 }}>
              <CardContent>
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
                      <ListItemText primary="Planned Tasks" />
                    </ListItemButton>
                  </ListItem>
                  <ListItem disablePadding>
                    <ListItemButton onClick={() => setDialogOpen(true)}>
                      <ListItemIcon>
                        <VpnKeyIcon />
                      </ListItemIcon>
                      <ListItemText primary="Authorize with Yelp" />
                    </ListItemButton>
                  </ListItem>
                </List>
              </CardContent>
            </Card>
          </Box>
        </Grow>
      </Box>
      <Snackbar
        open={alertOpen}
        onClose={handleCloseAlert}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
      >
        <Alert onClose={handleCloseAlert} severity="error" sx={{ width: '100%' }}>
          One or more refresh tokens expired. Please reauthorize.
        </Alert>
      </Snackbar>
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)}>
        <DialogTitle>Authorize with Yelp?</DialogTitle>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button onClick={() => { setDialogOpen(false); navigate('/auth'); }} autoFocus>
            Continue
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default Home;
