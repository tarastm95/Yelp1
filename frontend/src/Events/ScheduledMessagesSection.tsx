// src/Events/ScheduledMessagesSection.tsx
import React, { FC, useState, useEffect } from 'react';
import axios from 'axios';
import { ScheduledSectionProps, ScheduledMessage } from './types';

// Material-UI components
import {
  Typography,
  TextField,
  Button,
  Box,
  CircularProgress,
  Alert,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Tooltip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  ToggleButtonGroup,
  ToggleButton,
  Chip,
  Stack,  // added
} from '@mui/material';

// Icons
import AddCircleOutlineIcon from '@mui/icons-material/AddCircleOutline';
import CancelIcon from '@mui/icons-material/Cancel';
import SnoozeIcon from '@mui/icons-material/Snooze';
import CalendarTodayIcon from '@mui/icons-material/CalendarToday';
import PersonPinIcon from '@mui/icons-material/PersonPin';
import WorkOutlineIcon from '@mui/icons-material/WorkOutline';

const calculateTimeLeft = (nextRun: string) => {
  const diff = new Date(nextRun).getTime() - Date.now();
  const minutes = Math.floor(Math.max(0, diff) / 60000);
  const seconds = Math.floor((Math.max(0, diff) % 60000) / 1000);
  return { minutes, seconds, rawDiff: diff };
};

const ScheduledMessagesSection: FC<ScheduledSectionProps> = ({
  leadId,
  displayName,
  jobNames,
  scheduled,
  onUpdate,
}) => {
  const [newContent, setNewContent] = useState('');
  const [newInterval, setNewInterval] = useState(60);
  const [newCalendar, setNewCalendar] = useState('');
  const [scheduleType, setScheduleType] = useState<'interval' | 'calendar'>('interval');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [timeNow, setTimeNow] = useState(new Date());
  const [cancelDialogOpen, setCancelDialogOpen] = useState(false);
  const [selectedMessage, setSelectedMessage] = useState<ScheduledMessage | null>(null);
  const [feedback, setFeedback] = useState<{ message: string; severity: 'success' | 'error' } | null>(null);

  // update the clock
  useEffect(() => {
    const timer = setInterval(() => setTimeNow(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  // initial fetch
  useEffect(() => {
    if (leadId) onUpdate();
  }, [leadId, onUpdate]);

  const showFeedback = (message: string, severity: 'success' | 'error') => {
    setFeedback({ message, severity });
    setTimeout(() => setFeedback(null), 3000);
  };

  const handleAdd = async () => {
    if (!newContent.trim()) return;
    let minutesToSend = newInterval;
    if (scheduleType === 'calendar') {
      if (!newCalendar) { setError('Please select date & time.'); return; }
      const diff = new Date(newCalendar).getTime() - Date.now();
      if (diff <= 0) { setError('Date & time must be in the future.'); return; }
      minutesToSend = Math.ceil(diff / 60000);
    }

    setLoading(true);
    setError(null);
    try {
      await axios.post(
        `/yelp/leads/${leadId}/scheduled_messages/`,
        { content: newContent, interval_minutes: minutesToSend },
        {}
      );
      setNewContent('');
      setNewInterval(60);
      setNewCalendar('');
      onUpdate();
      showFeedback('Scheduled successfully', 'success');
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || err.message || 'Failed to create schedule.');
      showFeedback('Error scheduling message', 'error');
    } finally {
      setLoading(false);
    }
  };

  const openCancel = (msg: ScheduledMessage) => {
    setSelectedMessage(msg);
    setCancelDialogOpen(true);
  };
  const closeCancel = () => {
    setSelectedMessage(null);
    setCancelDialogOpen(false);
  };
  const handleCancel = async () => {
    if (!selectedMessage) return;
    try {
      await axios.patch(
        `/yelp/leads/${leadId}/scheduled_messages/${selectedMessage.id}/`,
        { active: false },
        {}
      );
      onUpdate();
      showFeedback('Cancelled', 'success');
    } catch {
      setError('Failed to cancel.');
      showFeedback('Error cancelling', 'error');
    } finally {
      closeCancel();
    }
  };

  return (
    <>
      <Paper sx={{ p: 2, mb: 3 }}>
        {/* Header */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
          <Typography variant="h6">Scheduled Messages</Typography>
          <Typography variant="body2" color="text.secondary">
            Now: {timeNow.toLocaleString()}
          </Typography>
        </Box>

        {/* Add form */}
        <Paper variant="outlined" sx={{ p: 2, mb: 3 }}>
          <Typography variant="subtitle1" gutterBottom>
            Add New Schedule
          </Typography>
          <ToggleButtonGroup
            size="small"
            value={scheduleType}
            exclusive
            onChange={(_, v) => v && setScheduleType(v)}
            sx={{ mb: 2 }}
          >
            <ToggleButton value="interval">
              <SnoozeIcon fontSize="small" /> Interval
            </ToggleButton>
            <ToggleButton value="calendar">
              <CalendarTodayIcon fontSize="small" /> Calendar
            </ToggleButton>
          </ToggleButtonGroup>

          <TextField
            fullWidth
            multiline
            rows={3}
            value={newContent}
            onChange={e => setNewContent(e.target.value)}
            placeholder="Message template..."
            sx={{ mb: 2 }}
          />

          {scheduleType === 'interval' ? (
            <TextField
              fullWidth
              type="number"
              label="Interval (minutes)"
              value={newInterval}
              onChange={e => setNewInterval(Number(e.target.value))}
              sx={{ mb: 2 }}
            />
          ) : (
            <TextField
              fullWidth
              type="datetime-local"
              label="Date & Time"
              value={newCalendar}
              onChange={e => setNewCalendar(e.target.value)}
              InputLabelProps={{ shrink: true }}
              sx={{ mb: 2 }}
            />
          )}

          {/* replace Grid with Stack */}
          <Stack direction="row" spacing={1} sx={{ mb: 2 }}>
            <Chip
              icon={<PersonPinIcon />}
              label="Insert Name"
              onClick={() => setNewContent(c => c + displayName)}
              variant="outlined"
              size="small"
            />
            {jobNames.length > 0 && (
              <Chip
                icon={<WorkOutlineIcon />}
                label="Insert Jobs"
                onClick={() => setNewContent(c => c + jobNames.join(', '))}
                variant="outlined"
                size="small"
              />
            )}
          </Stack>

          <Button
            fullWidth
            variant="contained"
            onClick={handleAdd}
            disabled={loading || !newContent.trim()}
            startIcon={loading ? <CircularProgress size={20} /> : <AddCircleOutlineIcon />}
          >
            {loading ? 'Adding...' : 'Add Schedule'}
          </Button>

          {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}
        </Paper>

        {/* Table */}
        <Typography variant="subtitle1" gutterBottom>
          Current Schedules
        </Typography>
        <TableContainer component={Paper} variant="outlined">
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Message</TableCell>
                <TableCell>Next Run</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {scheduled.map(m => {
                const { minutes, seconds, rawDiff } = calculateTimeLeft(m.next_run!);
                return (
                  <TableRow key={m.id}>
                    <TableCell>{m.content}</TableCell>
                    <TableCell>{m.active && rawDiff > 0 ? `${minutes}m ${seconds}s` : '—'}</TableCell>
                    <TableCell align="right">
                      {m.active && (
                        <Tooltip title="Cancel">
                          <IconButton onClick={() => openCancel(m)} color="error" size="small">
                            <CancelIcon />
                          </IconButton>
                        </Tooltip>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
              {scheduled.length === 0 && (
                <TableRow>
                  <TableCell colSpan={3} align="center">
                    No scheduled messages.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>

        {/* Cancel Dialog */}
        <Dialog open={cancelDialogOpen} onClose={closeCancel}>
          <DialogTitle>Cancel Scheduled Message</DialogTitle>
          <DialogContent>
            <DialogContentText>
              Are you sure you want to cancel this message?<br/>
              <strong>"{selectedMessage?.content}"</strong>
            </DialogContentText>
          </DialogContent>
          <DialogActions>
            <Button onClick={closeCancel}>Back</Button>
            <Button onClick={handleCancel} color="error" autoFocus>Confirm</Button>
          </DialogActions>
        </Dialog>
      </Paper>

      {/* positioned Alert instead of Snackbar */}
      {feedback && (
        <Box
          sx={{
            position: 'fixed',
            top: 16,
            left: '50%',
            transform: 'translateX(-50%)',
            zIndex: 1300,
          }}
        >
          <Alert severity={feedback.severity}>{feedback.message}</Alert>
        </Box>
      )}
    </>
  );
};

export default ScheduledMessagesSection;
