import React, { FC, useEffect, useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import { useTheme } from '@mui/material';
import { EventItem, LeadDetail as LeadDetailType } from './types';

import {
  Box,
  Typography,
  Button,
  Paper,
  Stack,
  Divider,
  CircularProgress,
} from '@mui/material';

interface Props {
  events: EventItem[];
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
        Немає нових повідомлень.
      </Typography>
    );
  }

  return (
    <Box sx={{ mt: 1 }}>
      <Stack spacing={2}>
        {events.map((e) => {
          const upd = e.payload!.data!.updates![0];
          const detail = leadDetails[upd.lead_id];
          const isNew = !viewedEvents.has(String(e.id));

          return (
            <Paper
              key={e.id}
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
                <Typography variant="h6">Event #{e.id}</Typography>
                <Typography variant="body2" color="text.secondary">
                  {new Date(e.created_at).toLocaleString()}
                </Typography>

                <Typography variant="body2">
                  <strong>Lead ID:</strong> {upd.lead_id}
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

                {upd.event_type && (
                  <Typography variant="body2">
                    <strong>Event Type:</strong> {upd.event_type}
                  </Typography>
                )}

                {(upd.event_content?.text || upd.event_content?.fallback_text) && (
                  <Typography variant="body2">
                    <strong>Message:</strong>{' '}
                    {upd.event_content?.text || upd.event_content?.fallback_text}
                  </Typography>
                )}

                <Divider />

                <Box>
                  <Button
                    component={RouterLink}
                    to={`/events/${e.id}`}
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
