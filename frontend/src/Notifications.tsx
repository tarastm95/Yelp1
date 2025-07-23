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

interface NotificationSetting {
  id: number;
  phone_number: string;
  message_template: string;
}

const Notifications: React.FC = () => {
  const [phone, setPhone] = useState('');
  const [template, setTemplate] = useState('');
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState('');
  const [items, setItems] = useState<NotificationSetting[]>([]);

  const load = () => {
    axios.get<NotificationSetting[]>('/notifications/')
      .then(res => setItems(res.data))
      .catch(() => setItems([]));
  };

  useEffect(() => {
    load();
  }, []);

  const handleSave = async () => {
    if (items.some(i => i.phone_number === phone)) {
      setError('Phone number already exists');
      return;
    }
    try {
      await axios.post('/notifications/', {
        phone_number: phone,
        message_template: template,
      });
      setSaved(true);
      setPhone('');
      setTemplate('');
      load();
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
          {items.length > 0 && (
            <Box sx={{ mb: 2 }}>
              {items.map(it => (
                <Box key={it.id} sx={{ mb: 1 }}>
                  <Typography variant="subtitle2">{it.phone_number}</Typography>
                  <Typography variant="body2" color="text.secondary">
                    {it.message_template}
                  </Typography>
                </Box>
              ))}
            </Box>
          )}
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
