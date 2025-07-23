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
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';

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
  const [editing, setEditing] = useState<NotificationSetting | null>(null);
  const [editPhone, setEditPhone] = useState('');
  const [editTemplate, setEditTemplate] = useState('');

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

  const handleEditOpen = (item: NotificationSetting) => {
    setEditing(item);
    setEditPhone(item.phone_number);
    setEditTemplate(item.message_template);
  };

  const handleUpdate = async () => {
    if (!editing) return;
    try {
      await axios.put(`/notifications/${editing.id}/`, {
        phone_number: editPhone,
        message_template: editTemplate,
      });
      setEditing(null);
      setSaved(true);
      load();
    } catch {
      setError('Failed to update settings');
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await axios.delete(`/notifications/${id}/`);
      load();
    } catch {
      setError('Failed to delete');
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
                <Box key={it.id} sx={{ mb: 1, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Box>
                    <Typography variant="subtitle2">{it.phone_number}</Typography>
                    <Typography variant="body2" color="text.secondary">
                      {it.message_template}
                    </Typography>
                  </Box>
                  <Box>
                    <IconButton size="small" onClick={() => handleEditOpen(it)}>
                      <EditIcon fontSize="small" />
                    </IconButton>
                    <IconButton size="small" onClick={() => handleDelete(it.id)}>
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </Box>
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
      <Dialog open={Boolean(editing)} onClose={() => setEditing(null)}>
        <DialogTitle>Edit Notification</DialogTitle>
        <DialogContent sx={{ pt: 1 }}>
          <TextField
            fullWidth
            label="Phone Number"
            value={editPhone}
            onChange={e => setEditPhone(e.target.value)}
            margin="normal"
          />
          <TextField
            fullWidth
            multiline
            minRows={3}
            label="Message Template"
            value={editTemplate}
            onChange={e => setEditTemplate(e.target.value)}
            margin="normal"
          />
          <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
            {PLACEHOLDERS.map(ph => (
              <Chip key={ph} label={ph} size="small" />
            ))}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditing(null)}>Cancel</Button>
          <Button variant="contained" onClick={handleUpdate}>Save</Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default Notifications;
