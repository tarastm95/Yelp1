// src/components/EventDetail.tsx
import React, { FC, useState, useEffect, useCallback } from 'react';
import { useParams, Link as RouterLink } from 'react-router-dom';
import axios from 'axios';
import {
  Container,
  Typography,
  Box,
  Paper,
  Divider,
  CircularProgress,
  Alert,
  Button,
} from '@mui/material';

import { DetailedEvent, LeadDetail, ScheduledMessage, MessageHistory } from './types';
import { LeadEvent } from '../EventsPage/types';
import EventList from './EventList';
import InstantMessageSection from './InstantMessageSection';
import ScheduledMessagesSection from './ScheduledMessagesSection';
import HistorySection from './HistorySection';

const EventDetail: FC = () => {
  const { id } = useParams<{ id: string }>();
  const [eventsDetail, setEventsDetail] = useState<DetailedEvent[]>([]);
  const [leadId, setLeadId] = useState<string | null>(null);
  const [leadDetail, setLeadDetail] = useState<LeadDetail | null>(null);
  const [scheduled, setScheduled] = useState<ScheduledMessage[]>([]);
  const [history, setHistory] = useState<MessageHistory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDetails = useCallback(async (lead: string) => {
    const { data } = await axios.get<{ events: DetailedEvent[] }>(
      `/yelp/leads/${encodeURIComponent(lead)}/events/`,
      { params: { limit: 20 } }
    );
    setEventsDetail(data.events);
  }, []);

  const fetchLeadDetail = useCallback(async (lead: string) => {
    try {
      const { data } = await axios.get<LeadDetail>(
        `/yelp/leads/${encodeURIComponent(lead)}/`
      );
      setLeadDetail(data);
    } catch {
      setLeadDetail(null);
    }
  }, []);

  const fetchScheduled = useCallback(async () => {
    if (!leadId) return;
    const { data } = await axios.get<ScheduledMessage[]>(
      `/yelp/leads/${leadId}/scheduled_messages/`
    );
    setScheduled(data);
  }, [leadId]);

  const fetchHistory = useCallback(async () => {
    if (!leadId) return;
    const { data } = await axios.get<MessageHistory[]>(
      `/yelp/leads/${leadId}/scheduled_messages/history/`
    );
    setHistory(data);
  }, [leadId]);

  useEffect(() => {
    if (!loading && !error && id) {
      const stored = localStorage.getItem('viewedEvents');
      let set: Set<string>;
      try {
        set = new Set(stored ? JSON.parse(stored) : []);
      } catch {
        set = new Set();
      }
      if (!set.has(id)) {
        set.add(id);
        localStorage.setItem('viewedEvents', JSON.stringify(Array.from(set)));
      }
    }
  }, [loading, error, id]);

  useEffect(() => {
    if (!id) {
      setError('Event ID is missing');
      setLoading(false);
      return;
    }
    (async () => {
      try {
        let found: string | undefined;
        if (/^\d+$/.test(id)) {
          // Numeric ID → get local event
          const { data: evt } = await axios.get<{ id: number; payload?: any }>(
            `/events/${id}/`
          );
          found = evt.payload?.data?.updates?.[0]?.lead_id;
        } else {
          // Otherwise try to fetch LeadEvent by event_id
          const { data: le } = await axios.get<LeadEvent>(
            `/lead-events/${encodeURIComponent(id)}/`
          );
          found = le.lead_id;
        }
        if (!found) throw new Error('No update data');

        setLeadId(found);
        await fetchDetails(found);
        await fetchLeadDetail(found);
        await fetchScheduled();
        await fetchHistory();
      } catch (e: any) {
        setError(e.message || 'Failed to load data');
      } finally {
        setLoading(false);
      }
    })();
  }, [id, fetchDetails, fetchLeadDetail, fetchScheduled, fetchHistory]);

  // Early returns
  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
        <CircularProgress />
      </Box>
    );
  }
  if (error) {
    return (
      <Container sx={{ mt: 4 }}>
        <Alert severity="error">{error}</Alert>
        <Box sx={{ mt: 2 }}>
          <Button component={RouterLink} to="/events" variant="text">
            ← Back to Events List
          </Button>
        </Box>
      </Container>
    );
  }
  if (!leadDetail || !leadId) {
    return (
      <Container sx={{ mt: 4 }}>
        <Alert severity="warning">Failed to fetch client data</Alert>
        <Box sx={{ mt: 2 }}>
          <Button component={RouterLink} to="/events" variant="text">
            ← Back to Events List
          </Button>
        </Box>
      </Container>
    );
  }

  const displayName = leadDetail.user.display_name;
  const jobNames = leadDetail.project?.job_names || [];
  const lid = leadId;

  return (
    <Container sx={{ mt: 4, mb: 4 }}>
      {/* Page title */}
      <Typography variant="h4" gutterBottom>
        Event Details
 #{id}
      </Typography>

      {/* Event history section */}
      <Paper elevation={2} sx={{ p: 2, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Event History
        </Typography>
        <EventList events={eventsDetail} />
      </Paper>

      {/* Instant messages section */}
      <Paper elevation={2} sx={{ p: 2, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Instant Messages
        </Typography>
        <InstantMessageSection
          leadId={lid}
          displayName={displayName}
          jobNames={jobNames}
          onSent={() => {
            fetchDetails(lid);
            fetchHistory();
          }}
        />
      </Paper>

      {/* Scheduled messages section */}
      <Paper elevation={2} sx={{ p: 2, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Scheduled Messages
        </Typography>
        <ScheduledMessagesSection
          leadId={lid}
          displayName={displayName}
          jobNames={jobNames}
          scheduled={scheduled}
          onUpdate={fetchScheduled}
        />
      </Paper>

      {/* Scheduled history section */}
      <Paper elevation={2} sx={{ p: 2, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          History of Scheduled Messages
        </Typography>
        <HistorySection history={history} />
      </Paper>

      {/* Back button */}
      <Box sx={{ mt: 2 }}>
        <Button component={RouterLink} to="/events" variant="text">
          ← Back to Events List
        </Button>
      </Box>
    </Container>
  );
};

export default EventDetail;
