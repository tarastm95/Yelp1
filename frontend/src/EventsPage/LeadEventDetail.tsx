import React, { FC, useEffect, useState } from 'react';
import { useParams, Link as RouterLink } from 'react-router-dom';
import axios from 'axios';
import {
  Container,
  Typography,
  Box,
  Paper,
  CircularProgress,
  Alert,
  Button,
} from '@mui/material';
import { LeadEvent } from './types';

const LeadEventDetail: FC = () => {
  const { eventId } = useParams<{ eventId: string }>();
  const [event, setEvent] = useState<LeadEvent | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!eventId) return;
    (async () => {
      try {
        const { data } = await axios.get<LeadEvent>(
          `/lead-events/${encodeURIComponent(eventId)}/`
        );
        setEvent(data);
      } catch (e: any) {
        setError(e.message || 'Failed to load event');
      } finally {
        setLoading(false);
      }
    })();
  }, [eventId]);

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error || !event) {
    return (
      <Container sx={{ mt: 4 }}>
        <Alert severity="error">{error || 'Event not found'}</Alert>
        <Box sx={{ mt: 2 }}>
          <Button component={RouterLink} to="/events" variant="text">
            ← Back to Events List
          </Button>
        </Box>
      </Container>
    );
  }

  return (
    <Container sx={{ mt: 4 }}>
      <Typography variant="h4" gutterBottom>
        Lead Event Details
      </Typography>
      <Paper sx={{ p: 2 }}>
        <Typography variant="body2">
          <strong>Event ID:</strong> {event.event_id}
        </Typography>
        <Typography variant="body2">
          <strong>Lead ID:</strong> {event.lead_id}
        </Typography>
        <Typography variant="body2">
          <strong>Type:</strong> {event.event_type}
        </Typography>
        {event.text && (
          <Typography variant="body2">
            <strong>Text:</strong> {event.text}
          </Typography>
        )}
        <Typography variant="body2">
          <strong>Created:</strong>{' '}
          {new Date(event.time_created).toLocaleString()}
        </Typography>
      </Paper>
      <Box sx={{ mt: 2 }}>
        <Button component={RouterLink} to="/events" variant="text">
          ← Back to Events List
        </Button>
      </Box>
    </Container>
  );
};

export default LeadEventDetail;
