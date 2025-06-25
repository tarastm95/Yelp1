import React, { FC, useState, useEffect } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { ProcessedLead, LeadDetail as LeadDetailType, EventItem, LeadEvent } from './types';
import {
  Box,
  Typography,
  Button,
  Paper,
  Stack,
  Chip,
  useTheme,
  CircularProgress,
} from '@mui/material';

interface Props {
  leads: ProcessedLead[];
  leadDetails: Record<string, Partial<LeadDetailType>>;
  events: EventItem[];
  visibleCount: number;
  onLoadMore: () => void;
  hasMore: boolean;
  loadingMore: boolean;
}

const NewLeads: FC<Props> = ({
  leads,
  leadDetails,
  events,
  visibleCount,
  onLoadMore,
  hasMore,
  loadingMore,
}) => {
  const theme = useTheme();
  const navigate = useNavigate();

  const [viewedLeads, setViewedLeads] = useState<Set<string>>(new Set());
  const [fetchedEvents, setFetchedEvents] = useState<Record<string, string>>({});

  useEffect(() => {
    const stored = localStorage.getItem('viewedLeads');
    if (stored) {
      try {
        setViewedLeads(new Set(JSON.parse(stored)));
      } catch {}
    }
  }, []);

  useEffect(() => {
    (async () => {
      const toFetch = leads
        .map(l => l.lead_id)
        .filter(lid => {
          const inEvents = events.some(e =>
            e.payload?.data?.updates?.some(u => u.lead_id === lid && (u as any).id)
          );
          return !inEvents && fetchedEvents[lid] == null;
        });
      for (const lid of toFetch) {
        try {
          const { data } = await axios.get<LeadEvent>(
            `/lead-events/${encodeURIComponent(lid)}/latest/`
          );
          if (data.event_id) {
            setFetchedEvents(prev => ({ ...prev, [lid]: String(data.event_id) }));
          }
        } catch (err) {
          console.error('[lead events] failed for', lid, err);
        }
      }
    })();
  }, [leads, events]);

  const markAsViewed = (lead_id: string) => {
    if (!viewedLeads.has(lead_id)) {
      const updated = new Set(viewedLeads).add(lead_id);
      setViewedLeads(updated);
      localStorage.setItem('viewedLeads', JSON.stringify(Array.from(updated)));
    }
  };

  const handleViewClient = (lead_id: string) => {
    markAsViewed(lead_id);
    navigate(`/leads/${encodeURIComponent(lead_id)}`);
  };

  const handleViewEvent = (lead_id: string, eventId: string) => {
    markAsViewed(lead_id);
    navigate(`/events/${eventId}`);
  };

  if (leads.length === 0) {
    return (
      <Typography variant="body1" sx={{ mt: 2 }}>
        No processed leads.
      </Typography>
    );
  }

  return (
    <Box sx={{ mt: 1 }}>
      <Stack spacing={2}>
        {leads.slice(0, visibleCount).map(({ lead_id, business_id, processed_at }) => {
          const detail = leadDetails[lead_id] || {};
          const matchedEvent = events.find(e =>
            e.payload?.data?.updates?.some(u => u.lead_id === lead_id)
          );
          const update = matchedEvent?.payload?.data?.updates?.find(u => u.lead_id === lead_id) as any;
          const eventId = update?.id ? String(update.id) : fetchedEvents[lead_id];
          const isNew = !viewedLeads.has(lead_id);

          return (
            <Paper
              key={lead_id}
              elevation={2}
              sx={{
                p: 2,
                backgroundColor: isNew
                  ? theme.palette.action.hover
                  : theme.palette.background.paper,
                borderLeft: isNew
                  ? `4px solid ${theme.palette.primary.main}`
                  : 'none',
              }}
            >
              <Stack spacing={1}>
                {/* Lead ID */}
                <Typography variant="body2">
                  <strong>Lead ID:</strong> {lead_id}
                </Typography>

                {/* Business ID */}
                <Typography variant="body2">
                  <strong>Business ID:</strong> {business_id}
                </Typography>

                {/* Processed */}
                <Typography variant="body2">
                  <strong>Processed:</strong>{' '}
                  {new Date(processed_at).toLocaleString()}
                </Typography>

                {/* User */}
                {detail.user_display_name && (
                  <Typography variant="body2">
                    <strong>User:</strong> {detail.user_display_name}
                  </Typography>
                )}

                {/* Job Names */}
                {detail.project?.job_names && detail.project.job_names.length > 0 && (
                  <Typography variant="body2">
                    <strong>Job Names:</strong>{' '}
                    {detail.project.job_names.join(', ')}
                  </Typography>
                )}

                {/* Buttons */}
                <Box sx={{ display: 'flex', gap: 2, mt: 1 }}>
                  <Button
                    onClick={() => eventId && handleViewEvent(lead_id, eventId)}
                    variant="outlined"
                    size="small"
                    disabled={!eventId}
                    color={eventId ? 'primary' : 'inherit'}
                  >
                    View Event Details
                  </Button>
                  <Button
                    onClick={() => handleViewClient(lead_id)}
                    variant="outlined"
                    size="small"
                  >
                    Client Details
                  </Button>
                </Box>
              </Stack>
            </Paper>
          );
        })}
      </Stack>

      {/* Load more */}
      {hasMore && (
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 2 }}>
          <Button
            variant="contained"
            size="small"
            onClick={onLoadMore}
            disabled={loadingMore}
          >
            {loadingMore ? <CircularProgress size={20} /> : 'Load more'}
          </Button>
        </Box>
      )}
    </Box>
  );
};

export default NewLeads;
