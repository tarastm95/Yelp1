import React, { FC, useEffect, useState } from 'react';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { cn } from '@/lib/utils';

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
      {/* Hero Section */}
      <Grow in timeout={500}>
        <Card 
          sx={{ 
            p: 4, 
            mb: 4,
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            color: 'white',
            textAlign: 'center',
            borderRadius: 3
          }}
        >
          <Typography variant="h3" gutterBottom sx={{ fontWeight: 700 }}>
            🎯 Yelp Integration Dashboard
          </Typography>
          <Typography variant="h6" sx={{ opacity: 0.9, maxWidth: '600px', mx: 'auto' }}>
            Manage your Yelp events, leads, and automated responses with ease. 
            Everything you need to grow your business in one place.
          </Typography>
        </Card>
      </Grow>

      {/* Quick Actions Grid */}
      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'repeat(2, 1fr)', lg: 'repeat(3, 1fr)' }, gap: 3, mb: 4 }}>
        <Grow in timeout={600}>
          <Card 
            component={RouterLink} 
            to="/events" 
            sx={{ 
              p: 3, 
              textDecoration: 'none',
              transition: 'all 0.3s ease',
              '&:hover': { 
                transform: 'translateY(-4px)', 
                boxShadow: '0 8px 32px rgba(0,0,0,0.12)' 
              }
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
              <Box sx={{ 
                p: 1.5, 
                borderRadius: 2, 
                backgroundColor: '#4f46e5',
                color: 'white',
                mr: 2
              }}>
                <EventIcon />
              </Box>
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                View Events
              </Typography>
            </Box>
            <Typography variant="body2" color="text.secondary">
              Browse and manage all your Yelp events and interactions
            </Typography>
          </Card>
        </Grow>

        <Grow in timeout={700}>
          <Card 
            component={RouterLink} 
            to="/settings" 
            sx={{ 
              p: 3, 
              textDecoration: 'none',
              transition: 'all 0.3s ease',
              '&:hover': { 
                transform: 'translateY(-4px)', 
                boxShadow: '0 8px 32px rgba(0,0,0,0.12)' 
              }
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
              <Box sx={{ 
                p: 1.5, 
                borderRadius: 2, 
                backgroundColor: '#10b981',
                color: 'white',
                mr: 2
              }}>
                <SettingsIcon />
              </Box>
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                Auto-Response
              </Typography>
            </Box>
            <Typography variant="body2" color="text.secondary">
              Configure automated responses to customer inquiries
            </Typography>
          </Card>
        </Grow>

        <Grow in timeout={800}>
          <Card 
            component={RouterLink} 
            to="/tokens" 
            sx={{ 
              p: 3, 
              textDecoration: 'none',
              transition: 'all 0.3s ease',
              '&:hover': { 
                transform: 'translateY(-4px)', 
                boxShadow: '0 8px 32px rgba(0,0,0,0.12)' 
              }
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
              <Box sx={{ 
                p: 1.5, 
                borderRadius: 2, 
                backgroundColor: '#f59e0b',
                color: 'white',
                mr: 2
              }}>
                <AccessTimeIcon />
              </Box>
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                Token Status
              </Typography>
            </Box>
            <Typography variant="body2" color="text.secondary">
              Monitor your API token status and expiration
            </Typography>
          </Card>
        </Grow>

        <Grow in timeout={900}>
          <Card 
            component={RouterLink} 
            to="/tasks" 
            sx={{ 
              p: 3, 
              textDecoration: 'none',
              transition: 'all 0.3s ease',
              '&:hover': { 
                transform: 'translateY(-4px)', 
                boxShadow: '0 8px 32px rgba(0,0,0,0.12)' 
              }
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
              <Box sx={{ 
                p: 1.5, 
                borderRadius: 2, 
                backgroundColor: '#ec4899',
                color: 'white',
                mr: 2
              }}>
                <ListAltIcon />
              </Box>
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                Planned Tasks
              </Typography>
            </Box>
            <Typography variant="body2" color="text.secondary">
              View and manage your scheduled tasks
            </Typography>
          </Card>
        </Grow>

        <Grow in timeout={1000}>
          <Card 
            onClick={() => setDialogOpen(true)}
            sx={{ 
              p: 3, 
              cursor: 'pointer',
              transition: 'all 0.3s ease',
              '&:hover': { 
                transform: 'translateY(-4px)', 
                boxShadow: '0 8px 32px rgba(0,0,0,0.12)' 
              }
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
              <Box sx={{ 
                p: 1.5, 
                borderRadius: 2, 
                backgroundColor: '#8b5cf6',
                color: 'white',
                mr: 2
              }}>
                <VpnKeyIcon />
              </Box>
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                Yelp Authorization
              </Typography>
            </Box>
            <Typography variant="body2" color="text.secondary">
              Connect your Yelp account for full access
            </Typography>
          </Card>
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
