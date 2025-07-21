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
  Stack,
  Divider,
  Fade,
  alpha,
} from '@mui/material';

// --- Material-UI Icons ---
import SendIcon from '@mui/icons-material/Send';
import PersonIcon from '@mui/icons-material/Person';
import WorkIcon from '@mui/icons-material/Work';
import MessageIcon from '@mui/icons-material/Message';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';

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
        `/yelp/leads/${encodeURIComponent(leadId)}/messages/`,
        { text: msg }
      );
      setMsg('');
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
      if (onSent) onSent();
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed to send message');
    } finally {
      setSending(false);
    }
  };

  return (
    <Stack spacing={3}>
      {/* Quick Insert Section */}
      <Box>
        <Typography variant="subtitle2" sx={{ mb: 2, fontWeight: 600, color: 'text.secondary' }}>
          Quick Insert
        </Typography>
        
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
          <Chip
            icon={<PersonIcon />}
            label={`Name: ${displayName}`}
            clickable
            onClick={insertName}
            variant="outlined"
            sx={{
              borderColor: 'primary.main',
              color: 'primary.main',
              fontWeight: 500,
              '&:hover': {
                backgroundColor: alpha('#667eea', 0.08),
                borderColor: 'primary.dark',
              }
            }}
          />
          
          {jobNames.length > 0 && (
            <Chip
              icon={<WorkIcon />}
              label={`Jobs: ${jobNames.join(', ')}`}
              clickable
              onClick={insertJobs}
              variant="outlined"
              sx={{
                borderColor: 'success.main',
                color: 'success.main',
                fontWeight: 500,
                '&:hover': {
                  backgroundColor: alpha('#43e97b', 0.08),
                  borderColor: 'success.dark',
                }
              }}
            />
          )}
        </Stack>
      </Box>

      <Divider />

      {/* Message Input */}
      <Box>
        <Typography variant="subtitle2" sx={{ mb: 2, fontWeight: 600, color: 'text.secondary' }}>
          Compose Message
        </Typography>
        
        <TextField
          multiline
          minRows={4}
          maxRows={8}
          fullWidth
          value={msg}
          onChange={e => setMsg(e.target.value)}
          placeholder="Type your message here..."
          variant="outlined"
          sx={{
            mb: 2,
            '& .MuiOutlinedInput-root': {
              backgroundColor: 'white',
              borderRadius: 2,
              '&:hover .MuiOutlinedInput-notchedOutline': {
                borderColor: 'primary.main',
              },
              '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
                borderColor: 'primary.main',
                borderWidth: 2,
              }
            }
          }}
        />
        
        {/* Character Count */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="caption" color="text.secondary">
            {msg.length} characters
          </Typography>
          
          {msg.length > 1000 && (
            <Typography variant="caption" color="warning.main">
              Message is quite long
            </Typography>
          )}
        </Box>
        
        {/* Send Button */}
        <Button
          onClick={send}
          disabled={!msg.trim() || sending}
          variant="contained"
          size="large"
          fullWidth
          startIcon={sending ? <CircularProgress size={20} color="inherit" /> : <SendIcon />}
          sx={{
            background: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
            borderRadius: 2,
            py: 1.5,
            fontWeight: 600,
            fontSize: '1rem',
            textTransform: 'none',
            boxShadow: '0 4px 16px rgba(67, 233, 123, 0.3)',
            
            '&:hover:not(:disabled)': {
              background: 'linear-gradient(135deg, #3bd96b 0%, #32e7c5 100%)',
              transform: 'translateY(-2px)',
              boxShadow: '0 6px 20px rgba(67, 233, 123, 0.4)',
            },
            
            '&:disabled': {
              background: 'linear-gradient(135deg, #bbb 0%, #999 100%)',
              color: 'white',
            }
          }}
        >
          {sending ? 'Sending Message...' : 'Send Message'}
        </Button>
      </Box>

      {/* Status Messages */}
      {error && (
        <Fade in={!!error}>
          <Alert 
            severity="error" 
            sx={{ 
              borderRadius: 2,
              boxShadow: 1
            }}
            onClose={() => setError(null)}
          >
            {error}
          </Alert>
        </Fade>
      )}
      
      {success && (
        <Fade in={success}>
          <Alert 
            severity="success" 
            sx={{ 
              borderRadius: 2,
              boxShadow: 1
            }}
            icon={<CheckCircleIcon />}
          >
            Message sent successfully!
          </Alert>
        </Fade>
      )}
    </Stack>
  );
};

export default InstantMessageSection;
