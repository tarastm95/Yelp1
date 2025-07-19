// src/components/InstantMessageSection.tsx
import React, { FC, useState } from 'react';
import axios from 'axios';
import { InstantSectionProps } from './types';

// --- Material-UI Imports ---
import {
  Typography,
  TextField,
  Button,
  Box,
  CircularProgress,
  Alert,
  Chip,
  Paper,
} from '@mui/material';

// --- Material-UI Icons ---
import SendIcon from '@mui/icons-material/Send';
import PersonPinIcon from '@mui/icons-material/PersonPin';
import WorkOutlineIcon from '@mui/icons-material/WorkOutline';

const InstantMessageSection: FC<InstantSectionProps> = ({
  leadId,
  displayName,
  jobNames,
  onSent
}) => {
  const [msg, setMsg] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // Insert DisplayName placeholder
  const insertName = () => {
    setMsg(c => c + displayName);
  };

  // Insert JobNames placeholder
  const insertJobs = () => {
    const list = jobNames.join(', ');
    setMsg(c => c + list);
  };

  const send = async () => {
    setError(null);
    setSuccess(false);
    setSending(true);
    try {
      await axios.post(
        `/yelp/leads/${encodeURIComponent(leadId)}/events/`,
        { request_content: msg, request_type: 'TEXT' }
      );
      setSuccess(true);
      setMsg('');
      onSent();
      setTimeout(() => setSuccess(false), 4000);
    } catch (e: any) {
      setError(e.response?.data?.error?.description || 'Failed to send message');
    } finally {
      setSending(false);
    }
  };

  return (
    <Paper elevation={0} sx={{ p: 0 }}>
      <Typography variant="h6" component="h3" gutterBottom>
        Send an Instant Message
      </Typography>
      
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
        <Chip
          icon={<PersonPinIcon />}
          label="Insert Name"
          onClick={insertName}
          variant="outlined"
          size="small"
        />
        {jobNames.length > 0 && (
          <Chip
            icon={<WorkOutlineIcon />}
            label="Insert Jobs"
            onClick={insertJobs}
            variant="outlined"
            size="small"
          />
        )}
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      {success && <Alert severity="success" sx={{ mb: 2 }}>Message sent successfully!</Alert>}

      <TextField
        fullWidth
        multiline
        rows={4}
        value={msg}
        onChange={e => setMsg(e.target.value)}
        placeholder="Type your message here..."
        variant="outlined"
        sx={{ mb: 2 }}
        disabled={sending}
      />

      <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
        <Button
          variant="contained"
          onClick={send}
          disabled={sending || !msg.trim()}
          startIcon={sending ? <CircularProgress size={20} color="inherit" /> : <SendIcon />}
        >
          {sending ? 'Sending...' : 'Send Message'}
        </Button>
      </Box>
    </Paper>
  );
};

export default InstantMessageSection;
