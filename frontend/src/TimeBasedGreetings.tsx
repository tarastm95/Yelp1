import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Grid,
  Alert,
  Paper,
  Divider,
  Stack,
  Switch,
  FormControlLabel,
} from '@mui/material';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import SaveIcon from '@mui/icons-material/Save';
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
  morning_formal: string;
  morning_casual: string;
  afternoon_formal: string;
  afternoon_casual: string;
  evening_formal: string;
  evening_casual: string;
  night_greeting: string;
  default_style: string;
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
    morning_formal: 'Good morning',
    morning_casual: 'Morning!',
    afternoon_formal: 'Good afternoon',
    afternoon_casual: 'Hi',
    evening_formal: 'Good evening',
    evening_casual: 'Evening!',
    night_greeting: 'Hello',
    default_style: 'formal',
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
  const getCurrentGreeting = (): string => {
    const now = new Date();
    const currentTime = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;
    
    if (currentTime >= greetings.morning_start && currentTime < greetings.morning_end) {
      return greetings.default_style === 'casual' ? greetings.morning_casual : greetings.morning_formal;
    } else if (currentTime >= greetings.afternoon_start && currentTime < greetings.afternoon_end) {
      return greetings.default_style === 'casual' ? greetings.afternoon_casual : greetings.afternoon_formal;
    } else if (currentTime >= greetings.evening_start && currentTime < greetings.evening_end) {
      return greetings.default_style === 'casual' ? greetings.evening_casual : greetings.evening_formal;
    } else {
      return greetings.night_greeting;
    }
  };

  return (
    <Box p={3}>
      <Card elevation={3}>
        <CardContent>
          <Typography variant="h5" gutterBottom sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
            <AccessTimeIcon sx={{ mr: 1, color: 'primary.main' }} />
            Time-Based Greetings Configuration
            {businessId && (
              <Typography variant="body2" sx={{ ml: 2, color: 'text.secondary' }}>
                (Business-specific)
              </Typography>
            )}
          </Typography>

          {message && (
            <Alert severity={message.type} sx={{ mb: 3 }} onClose={() => setMessage(null)}>
              {message.text}
            </Alert>
          )}

          {/* Preview Section */}
          <Paper elevation={1} sx={{ p: 2, mb: 3, backgroundColor: 'primary.50' }}>
            <Typography variant="h6" gutterBottom>
              Current Greeting Preview
            </Typography>
            <Typography variant="body1" sx={{ fontWeight: 600, color: 'primary.main' }}>
              {getCurrentGreeting()}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              This is what {'{greetings}'} will be replaced with right now
            </Typography>
          </Paper>

          <Grid container spacing={3}>
            {/* Time Ranges */}
            <Grid item xs={12}>
              <Typography variant="h6" gutterBottom>
                Time Ranges
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={6} md={3}>
                  <TextField
                    fullWidth
                    type="time"
                    label="Morning Start"
                    value={greetings.morning_start}
                    onChange={(e) => handleChange('morning_start', e.target.value)}
                    InputLabelProps={{ shrink: true }}
                  />
                </Grid>
                <Grid item xs={6} md={3}>
                  <TextField
                    fullWidth
                    type="time"
                    label="Morning End"
                    value={greetings.morning_end}
                    onChange={(e) => handleChange('morning_end', e.target.value)}
                    InputLabelProps={{ shrink: true }}
                  />
                </Grid>
                <Grid item xs={6} md={3}>
                  <TextField
                    fullWidth
                    type="time"
                    label="Afternoon Start"
                    value={greetings.afternoon_start}
                    onChange={(e) => handleChange('afternoon_start', e.target.value)}
                    InputLabelProps={{ shrink: true }}
                  />
                </Grid>
                <Grid item xs={6} md={3}>
                  <TextField
                    fullWidth
                    type="time"
                    label="Afternoon End"
                    value={greetings.afternoon_end}
                    onChange={(e) => handleChange('afternoon_end', e.target.value)}
                    InputLabelProps={{ shrink: true }}
                  />
                </Grid>
                <Grid item xs={6} md={3}>
                  <TextField
                    fullWidth
                    type="time"
                    label="Evening Start"
                    value={greetings.evening_start}
                    onChange={(e) => handleChange('evening_start', e.target.value)}
                    InputLabelProps={{ shrink: true }}
                  />
                </Grid>
                <Grid item xs={6} md={3}>
                  <TextField
                    fullWidth
                    type="time"
                    label="Evening End"
                    value={greetings.evening_end}
                    onChange={(e) => handleChange('evening_end', e.target.value)}
                    InputLabelProps={{ shrink: true }}
                  />
                </Grid>
              </Grid>
            </Grid>

            <Grid item xs={12}>
              <Divider sx={{ my: 2 }} />
            </Grid>

            {/* Default Style */}
            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel>Default Style</InputLabel>
                <Select
                  value={greetings.default_style}
                  label="Default Style"
                  onChange={(e) => handleChange('default_style', e.target.value)}
                >
                  <MenuItem value="formal">Formal (Good morning, Good afternoon)</MenuItem>
                  <MenuItem value="casual">Casual (Morning!, Hi, Evening!)</MenuItem>
                  <MenuItem value="mixed">Mixed (varies by time)</MenuItem>
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12}>
              <Divider sx={{ my: 2 }} />
            </Grid>

            {/* Greeting Messages */}
            <Grid item xs={12}>
              <Typography variant="h6" gutterBottom>
                Greeting Messages
              </Typography>
              <Grid container spacing={2}>
                {/* Morning */}
                <Grid item xs={12} md={6}>
                  <Typography variant="subtitle1" gutterBottom>Morning Greetings</Typography>
                  <Stack spacing={2}>
                    <TextField
                      fullWidth
                      label="Formal Morning"
                      value={greetings.morning_formal}
                      onChange={(e) => handleChange('morning_formal', e.target.value)}
                      placeholder="Good morning"
                    />
                    <TextField
                      fullWidth
                      label="Casual Morning"
                      value={greetings.morning_casual}
                      onChange={(e) => handleChange('morning_casual', e.target.value)}
                      placeholder="Morning!"
                    />
                  </Stack>
                </Grid>

                {/* Afternoon */}
                <Grid item xs={12} md={6}>
                  <Typography variant="subtitle1" gutterBottom>Afternoon Greetings</Typography>
                  <Stack spacing={2}>
                    <TextField
                      fullWidth
                      label="Formal Afternoon"
                      value={greetings.afternoon_formal}
                      onChange={(e) => handleChange('afternoon_formal', e.target.value)}
                      placeholder="Good afternoon"
                    />
                    <TextField
                      fullWidth
                      label="Casual Afternoon"
                      value={greetings.afternoon_casual}
                      onChange={(e) => handleChange('afternoon_casual', e.target.value)}
                      placeholder="Hi"
                    />
                  </Stack>
                </Grid>

                {/* Evening */}
                <Grid item xs={12} md={6}>
                  <Typography variant="subtitle1" gutterBottom>Evening Greetings</Typography>
                  <Stack spacing={2}>
                    <TextField
                      fullWidth
                      label="Formal Evening"
                      value={greetings.evening_formal}
                      onChange={(e) => handleChange('evening_formal', e.target.value)}
                      placeholder="Good evening"
                    />
                    <TextField
                      fullWidth
                      label="Casual Evening"
                      value={greetings.evening_casual}
                      onChange={(e) => handleChange('evening_casual', e.target.value)}
                      placeholder="Evening!"
                    />
                  </Stack>
                </Grid>

                {/* Night */}
                <Grid item xs={12} md={6}>
                  <Typography variant="subtitle1" gutterBottom>Night Greeting</Typography>
                  <TextField
                    fullWidth
                    label="Night Greeting"
                    value={greetings.night_greeting}
                    onChange={(e) => handleChange('night_greeting', e.target.value)}
                    placeholder="Hello"
                    helperText="Used after evening_end or before morning_start"
                  />
                </Grid>
              </Grid>
            </Grid>

            {/* Save Button */}
            <Grid item xs={12}>
              <Button
                variant="contained"
                onClick={saveGreetings}
                disabled={loading}
                startIcon={<SaveIcon />}
                size="large"
                sx={{ mt: 2 }}
              >
                {loading ? 'Saving...' : 'Save Greeting Settings'}
              </Button>
            </Grid>
          </Grid>
        </CardContent>
      </Card>
    </Box>
  );
};

export default TimeBasedGreetings;