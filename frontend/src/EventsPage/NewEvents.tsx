import React, { FC, useEffect, useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import { useTheme } from '@mui/material';
import { LeadDetail as LeadDetailType, LeadEvent } from './types';

import {
  Box,
  Typography,
  Button,
  Paper,
  Stack,
  Divider,
  CircularProgress,
  Chip,
} from '@mui/material';

interface Props {
  events: LeadEvent[];
  leadDetails: Record<string, Partial<LeadDetailType>>;
  onLoadMore: () => void;
  hasMore: boolean;
  loadingMore: boolean;
}

const NewEvents: FC<Props> = ({
  events,
  leadDetails,
  onLoadMore,
  hasMore,
  loadingMore,
}) => {
  const [viewedEvents, setViewedEvents] = useState<Set<string>>(new Set());
  const theme = useTheme();
  useEffect(() => {
    const stored = localStorage.getItem('viewedEvents');
    if (stored) {
      try {
        setViewedEvents(new Set(JSON.parse(stored)));
      } catch {}
    }
  }, []);
  if (!events.length) {
    return (
      <Typography variant="body1" sx={{ mt: 2 }}>
        No new messages.
      </Typography>
    );
  }

  return (
    <Box sx={{ mt: 1 }}>
      <Stack spacing={2}>
        {events.map((e) => {
          const detail = leadDetails[e.lead_id];
          const isNew = !viewedEvents.has(String(e.event_id));

          return (
            <Paper
              key={e.event_id}
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
                <Typography variant="h6">Event #{e.event_id}</Typography>
                <Typography variant="body2" color="text.secondary">
                  {new Date(e.created_at).toLocaleString()}
                </Typography>

                <Typography variant="body2">
                  <strong>Lead ID:</strong> {e.lead_id}
                </Typography>

                {detail?.user_display_name && (
                  <Typography variant="body2">
                    <strong>User:</strong> {detail.user_display_name}
                  </Typography>
                )}

                {detail?.project?.job_names &&
                  detail.project.job_names.length > 0 && (
                    <Typography variant="body2">
                      <strong>Job Names:</strong>{' '}
                      {detail.project.job_names.join(', ')}
                    </Typography>
                  )}

                {detail?.phone_opt_in && (
                  <Chip label="Phone Opt-In" color="success" size="small" />
                )}
                {detail?.phone_in_text && (
                  <Chip label="Phone in text" color="info" size="small" />
                )}

                {e.event_type && (
                  <Typography variant="body2">
                    <strong>Event Type:</strong> {e.event_type}
                  </Typography>
                )}

                {e.user_type && (
                  <Typography variant="body2">
                    <strong>User Type:</strong> {e.user_type}
                  </Typography>
                )}

                {e.user_id && (
                  <Typography variant="body2">
                    <strong>User ID:</strong> {e.user_id}
                  </Typography>
                )}

                {e.user_display_name && (
                  <Typography variant="body2">
                    <strong>User Display Name:</strong> {e.user_display_name}
                  </Typography>
                )}

                {e.text && (
                  <Typography variant="body2">
                    <strong>Text:</strong> {e.text}
                  </Typography>
                )}

                {e.cursor && (
                  <Typography variant="body2">
                    <strong>Cursor:</strong> {e.cursor}
                  </Typography>
                )}

                <Typography variant="body2">
                  <strong>Time Created:</strong>{' '}
                  {new Date(e.time_created).toLocaleString()}
                </Typography>

                <Typography variant="body2">
                  <strong>Created At:</strong>{' '}
                  {new Date(e.created_at).toLocaleString()}
                </Typography>

                <Typography variant="body2">
                  <strong>Updated At:</strong>{' '}
                  {new Date(e.updated_at).toLocaleString()}
                </Typography>


                <Divider />

                <Box>
                  <Button
                    component={RouterLink}
                    to={`/events/${e.event_id}`}
                    variant="outlined"
                    size="small"
                  >
                    View Full Details
                  </Button>
                </Box>
              </Stack>
            </Paper>
          );
        })}
      </Stack>

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

export default NewEvents;
