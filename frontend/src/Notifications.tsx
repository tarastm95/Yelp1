import React, { useEffect, useState } from 'react';
import axios from 'axios';
import {
  Container,
  Paper,
  Typography,
  TextField,
  Button,
  Snackbar,
  Alert,
  Box,
  Stack,
  Chip,
} from '@mui/material';

const PLACEHOLDERS = ['{business_id}', '{lead_id}', '{business_name}', '{timestamp}'] as const;

const Notifications: React.FC = () => {
  const [phone, setPhone] = useState('');
  const [template, setTemplate] = useState('');
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    axios.get('/notifications/')
      .then(res => {
        setPhone(res.data.phone_number || '');
        setTemplate(res.data.message_template || '');
      })
      .catch(() => setError('Failed to load settings'));
  }, []);

  const handleSave = async () => {
    try {
      await axios.put('/notifications/', {
        phone_number: phone,
        message_template: template,
      });
      setSaved(true);
    } catch {
      setError('Failed to save settings');
    }
  };

  return (
    <Container maxWidth="sm" sx={{ mt: 4 }}>
      <Paper elevation={3} sx={{ p: 3 }}>
        <Typography variant="h5" gutterBottom>
          Notification Settings
        </Typography>
        <Box sx={{ mt: 2 }}>
          <TextField
            fullWidth
            label="Phone Number"
            value={phone}
            onChange={e => setPhone(e.target.value)}
            margin="normal"
          />
          <TextField
            fullWidth
            multiline
            minRows={3}
            label="Message Template"
            value={template}
            onChange={e => setTemplate(e.target.value)}
            margin="normal"
          />
          <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
            {PLACEHOLDERS.map(ph => (
              <Chip key={ph} label={ph} size="small" />
            ))}
          </Stack>
          <Button variant="contained" sx={{ mt: 2 }} onClick={handleSave}>
            Save
          </Button>
        </Box>
      </Paper>
      <Snackbar
        open={saved}
        autoHideDuration={3000}
        onClose={() => setSaved(false)}
      >
        <Alert onClose={() => setSaved(false)} severity="success" sx={{ width: '100%' }}>
          Saved
        </Alert>
      </Snackbar>
      <Snackbar
        open={!!error}
        autoHideDuration={3000}
        onClose={() => setError('')}
      >
        <Alert onClose={() => setError('')} severity="error" sx={{ width: '100%' }}>
          {error}
        </Alert>
      </Snackbar>
    </Container>
  );
};

export default Notifications;
