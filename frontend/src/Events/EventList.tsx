// src/components/EventList.tsx
import React, { FC } from 'react';
import { DetailedEvent } from './types';
import { Box, Paper, Typography, List, ListItem, Link, Avatar, Stack } from '@mui/material';

interface Props { events: DetailedEvent[]; }

const EventList: FC<Props> = ({ events }) => {
  // For demonstration, we'll assume the first user in the list is the "current user".
  // In a real application, you would get this from your authentication state.
  const currentUserId = events.length > 0 ? events[0].user_display_name : '';

  return (
    <Box sx={{
      display: 'flex',
      flexDirection: 'column',
      p: 2,
      bgcolor: 'grey.100', // Chat window background
      borderRadius: '8px',
      border: '1px solid',
      borderColor: 'grey.300',
    }}>
      {events.length === 0
        ? <Typography>No event details.</Typography>
        : (
          <Stack spacing={2}>
            {events.map(evt => {
              const isCurrentUser = evt.user_display_name === currentUserId;
              const atts = evt.event_content.attachments || [];
              
              return (
                <Box
                  key={evt.id}
                  sx={{
                    display: 'flex',
                    justifyContent: isCurrentUser ? 'flex-end' : 'flex-start',
                  }}
                >
                  <Stack direction="row" spacing={1} alignItems="flex-start" sx={{ maxWidth: '80%' }}>
                    {!isCurrentUser && (
                      <Avatar sx={{ width: 40, height: 40, mt: 1 }}>
                        {evt.user_display_name.substring(0, 1)}
                      </Avatar>
                    )}
                    <Paper
                      elevation={2}
                      sx={{
                        p: 1.5,
                        bgcolor: isCurrentUser ? '#dcf8c6' : 'white',
                        borderRadius: isCurrentUser ? '20px 20px 5px 20px' : '20px 20px 20px 5px',
                      }}
                    >
                      <Stack spacing={0.5}>
                        <Typography variant="caption" color="text.secondary">
                          {evt.user_display_name} ({evt.user_type})
                        </Typography>
                        
                        {evt.event_content.text && (
                          <Typography variant="body1" sx={{ wordBreak: 'break-word' }}>
                            {evt.event_content.text}
                          </Typography>
                        )}

                        {atts.length > 0 && (
                          <div>
                            <Typography variant="subtitle2" sx={{ mt: 1, mb: 0.5 }}>Attachments:</Typography>
                            <List dense disablePadding>
                              {atts.map(a => (
                                <ListItem key={a.id} disablePadding>
                                  <Link href={a.url} target="_blank" rel="noopener noreferrer" variant="body2">
                                    {a.resource_name || a.mime_type}
                                  </Link>
                                </ListItem>
                              ))}
                            </List>
                          </div>
                        )}
                        <Typography variant="caption" color="text.secondary" sx={{ alignSelf: 'flex-end', mt: 0.5 }}>
                          {new Date(evt.time_created).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </Typography>
                      </Stack>
                    </Paper>
                     {isCurrentUser && (
                      <Avatar sx={{ width: 40, height: 40, mt: 1, ml: 1 }}>
                        {evt.user_display_name.substring(0, 1)}
                      </Avatar>
                    )}
                  </Stack>
                </Box>
              );
            })}
          </Stack>
        )
      }
    </Box>
  );
};

export default EventList;
