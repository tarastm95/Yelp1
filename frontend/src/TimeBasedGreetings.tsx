import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  Grid,
  Alert,
  Paper,
  Divider,
  Stack,
  Chip,
} from '@mui/material';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import SaveIcon from '@mui/icons-material/Save';
import WbSunnyIcon from '@mui/icons-material/WbSunny';
import LightModeIcon from '@mui/icons-material/LightMode';
import Brightness3Icon from '@mui/icons-material/Brightness3';
import NightsStayIcon from '@mui/icons-material/NightsStay';
import axios from 'axios';

interface TimeBasedGreeting {
  id?: number;
  business?: string;
  morning_start: string;
  morning_end: string;
  afternoon_start: string;
  afternoon_end: string;
  evening_start: string;
  evening_end: string;
  morning_greeting: string;
  afternoon_greeting: string;
  evening_greeting: string;
  night_greeting: string;
}

interface Props {
  businessId?: string;
}

const TimeBasedGreetings: React.FC<Props> = ({ businessId }) => {
  const [greetings, setGreetings] = useState<TimeBasedGreeting>({
    morning_start: '05:00',
    morning_end: '12:00',
    afternoon_start: '12:00',
    afternoon_end: '17:00',
    evening_start: '17:00',
    evening_end: '21:00',
    morning_greeting: 'Good morning',
    afternoon_greeting: 'Good afternoon',
    evening_greeting: 'Good evening',
    night_greeting: 'Hello',
  });

  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const loadGreetings = async () => {
    try {
      const params = businessId ? { business_id: businessId } : {};
      const response = await axios.get('/api/time-greetings/', { params });
      setGreetings(response.data);
    } catch (error) {
      console.error('Error loading greetings:', error);
      setMessage({ type: 'error', text: 'Failed to load greeting settings' });
    }
  };

  const saveGreetings = async () => {
    setLoading(true);
    setMessage(null);

    try {
      const data = businessId ? { ...greetings, business_id: businessId } : greetings;
      await axios.post('/api/time-greetings/', data);
      setMessage({ type: 'success', text: 'Greeting settings saved successfully!' });
    } catch (error) {
      console.error('Error saving greetings:', error);
      setMessage({ type: 'error', text: 'Failed to save greeting settings' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadGreetings();
  }, [businessId]);

  const handleChange = (field: keyof TimeBasedGreeting, value: string) => {
    setGreetings(prev => ({ ...prev, [field]: value }));
  };

  // Get current greeting based on current time (for preview)
  const getCurrentGreeting = (): { greeting: string; period: string; icon: React.ReactNode } => {
    const now = new Date();
    const currentTime = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;
    
    if (currentTime >= greetings.morning_start && currentTime < greetings.morning_end) {
      return { 
        greeting: greetings.morning_greeting, 
        period: 'Morning', 
        icon: <WbSunnyIcon sx={{ color: '#FF9800', mr: 1 }} /> 
      };
    } else if (currentTime >= greetings.afternoon_start && currentTime < greetings.afternoon_end) {
      return { 
        greeting: greetings.afternoon_greeting, 
        period: 'Afternoon', 
        icon: <LightModeIcon sx={{ color: '#FFC107', mr: 1 }} /> 
      };
    } else if (currentTime >= greetings.evening_start && currentTime < greetings.evening_end) {
      return { 
        greeting: greetings.evening_greeting, 
        period: 'Evening', 
        icon: <Brightness3Icon sx={{ color: '#673AB7', mr: 1 }} /> 
      };
    } else {
      return { 
        greeting: greetings.night_greeting, 
        period: 'Night', 
        icon: <NightsStayIcon sx={{ color: '#3F51B5', mr: 1 }} /> 
      };
    }
  };

  const currentGreeting = getCurrentGreeting();

  return (
    <Box p={3} sx={{ maxWidth: 1200, mx: 'auto' }}>
      <Card elevation={4} sx={{ borderRadius: 3, overflow: 'hidden' }}>
        <Box sx={{ 
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', 
          color: 'white', 
          p: 3 
        }}>
          <Typography variant="h4" gutterBottom sx={{ display: 'flex', alignItems: 'center', fontWeight: 600 }}>
            <AccessTimeIcon sx={{ mr: 2, fontSize: 40 }} />
            Time-Based Greetings
            {businessId && (
              <Chip 
                label="Business-specific" 
                size="small" 
                sx={{ ml: 2, backgroundColor: 'rgba(255,255,255,0.2)', color: 'white' }} 
              />
            )}
          </Typography>
          <Typography variant="body1" sx={{ opacity: 0.9 }}>
            Configure dynamic greetings that change throughout the day
          </Typography>
        </Box>

        <CardContent sx={{ p: 4 }}>
          {message && (
            <Alert severity={message.type} sx={{ mb: 3 }} onClose={() => setMessage(null)}>
              {message.text}
            </Alert>
          )}

          {/* Live Preview */}
          <Paper 
            elevation={2} 
            sx={{ 
              p: 3, 
              mb: 4, 
              background: 'linear-gradient(45deg, #f5f7fa 0%, #c3cfe2 100%)',
              borderRadius: 2,
              textAlign: 'center'
            }}
          >
            <Typography variant="h6" gutterBottom sx={{ color: 'text.secondary' }}>
              🔮 Live Preview
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', mb: 2 }}>
              {currentGreeting.icon}
              <Chip 
                label={currentGreeting.period} 
                variant="outlined" 
                size="small" 
                sx={{ ml: 1 }}
              />
            </Box>
            <Typography variant="h5" sx={{ fontWeight: 600, color: '#2c3e50', mb: 1 }}>
              "{currentGreeting.greeting}"
            </Typography>
            <Typography variant="caption" color="text.secondary">
              This is what <code>{'{greetings}'}</code> will be replaced with right now
            </Typography>
          </Paper>

          <Grid container spacing={4}>
            {/* Time Periods Configuration */}
            <Grid item xs={12}>
              <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
                ⏰ Time Periods
              </Typography>
              
              <Grid container spacing={3}>
                {/* Morning */}
                <Grid item xs={12} md={6} lg={3}>
                  <Paper elevation={1} sx={{ p: 3, height: '100%', borderRadius: 2 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                      <WbSunnyIcon sx={{ color: '#FF9800', mr: 1 }} />
                      <Typography variant="h6" sx={{ color: '#FF9800', fontWeight: 600 }}>
                        Morning
                      </Typography>
                    </Box>
                    <Stack spacing={2}>
                      <TextField
                        fullWidth
                        type="time"
                        label="Start"
                        value={greetings.morning_start}
                        onChange={(e) => handleChange('morning_start', e.target.value)}
                        InputLabelProps={{ shrink: true }}
                        size="small"
                      />
                      <TextField
                        fullWidth
                        type="time"
                        label="End"
                        value={greetings.morning_end}
                        onChange={(e) => handleChange('morning_end', e.target.value)}
                        InputLabelProps={{ shrink: true }}
                        size="small"
                      />
                      <TextField
                        fullWidth
                        label="Greeting"
                        value={greetings.morning_greeting}
                        onChange={(e) => handleChange('morning_greeting', e.target.value)}
                        placeholder="Good morning"
                        size="small"
                      />
                    </Stack>
                  </Paper>
                </Grid>

                {/* Afternoon */}
                <Grid item xs={12} md={6} lg={3}>
                  <Paper elevation={1} sx={{ p: 3, height: '100%', borderRadius: 2 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                      <LightModeIcon sx={{ color: '#FFC107', mr: 1 }} />
                      <Typography variant="h6" sx={{ color: '#FFC107', fontWeight: 600 }}>
                        Afternoon
                      </Typography>
                    </Box>
                    <Stack spacing={2}>
                      <TextField
                        fullWidth
                        type="time"
                        label="Start"
                        value={greetings.afternoon_start}
                        onChange={(e) => handleChange('afternoon_start', e.target.value)}
                        InputLabelProps={{ shrink: true }}
                        size="small"
                      />
                      <TextField
                        fullWidth
                        type="time"
                        label="End"
                        value={greetings.afternoon_end}
                        onChange={(e) => handleChange('afternoon_end', e.target.value)}
                        InputLabelProps={{ shrink: true }}
                        size="small"
                      />
                      <TextField
                        fullWidth
                        label="Greeting"
                        value={greetings.afternoon_greeting}
                        onChange={(e) => handleChange('afternoon_greeting', e.target.value)}
                        placeholder="Good afternoon"
                        size="small"
                      />
                    </Stack>
                  </Paper>
                </Grid>

                {/* Evening */}
                <Grid item xs={12} md={6} lg={3}>
                  <Paper elevation={1} sx={{ p: 3, height: '100%', borderRadius: 2 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                      <Brightness3Icon sx={{ color: '#673AB7', mr: 1 }} />
                      <Typography variant="h6" sx={{ color: '#673AB7', fontWeight: 600 }}>
                        Evening
                      </Typography>
                    </Box>
                    <Stack spacing={2}>
                      <TextField
                        fullWidth
                        type="time"
                        label="Start"
                        value={greetings.evening_start}
                        onChange={(e) => handleChange('evening_start', e.target.value)}
                        InputLabelProps={{ shrink: true }}
                        size="small"
                      />
                      <TextField
                        fullWidth
                        type="time"
                        label="End"
                        value={greetings.evening_end}
                        onChange={(e) => handleChange('evening_end', e.target.value)}
                        InputLabelProps={{ shrink: true }}
                        size="small"
                      />
                      <TextField
                        fullWidth
                        label="Greeting"
                        value={greetings.evening_greeting}
                        onChange={(e) => handleChange('evening_greeting', e.target.value)}
                        placeholder="Good evening"
                        size="small"
                      />
                    </Stack>
                  </Paper>
                </Grid>

                {/* Night */}
                <Grid item xs={12} md={6} lg={3}>
                  <Paper elevation={1} sx={{ p: 3, height: '100%', borderRadius: 2 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                      <NightsStayIcon sx={{ color: '#3F51B5', mr: 1 }} />
                      <Typography variant="h6" sx={{ color: '#3F51B5', fontWeight: 600 }}>
                        Night
                      </Typography>
                    </Box>
                    <Stack spacing={2}>
                      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                        Used outside other time periods
                      </Typography>
                      <TextField
                        fullWidth
                        label="Greeting"
                        value={greetings.night_greeting}
                        onChange={(e) => handleChange('night_greeting', e.target.value)}
                        placeholder="Hello"
                        size="small"
                      />
                    </Stack>
                  </Paper>
                </Grid>
              </Grid>
            </Grid>

            {/* Save Button */}
            <Grid item xs={12}>
              <Box sx={{ textAlign: 'center', mt: 2 }}>
                <Button
                  variant="contained"
                  onClick={saveGreetings}
                  disabled={loading}
                  startIcon={<SaveIcon />}
                  size="large"
                  sx={{ 
                    px: 6, 
                    py: 1.5, 
                    borderRadius: 3,
                    background: 'linear-gradient(45deg, #667eea 30%, #764ba2 90%)',
                    '&:hover': {
                      background: 'linear-gradient(45deg, #5a6fd8 30%, #6a4190 90%)',
                    }
                  }}
                >
                  {loading ? 'Saving...' : 'Save Greeting Settings'}
                </Button>
              </Box>
            </Grid>
          </Grid>
        </CardContent>
      </Card>
    </Box>
  );
};

export default TimeBasedGreetings;