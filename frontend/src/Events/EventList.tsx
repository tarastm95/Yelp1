// src/components/EventList.tsx
import React, { FC } from 'react';
import { DetailedEvent } from './types';
import { 
  Box, 
  Paper, 
  Typography, 
  List, 
  ListItem, 
  Link, 
  Avatar, 
  Stack,
  Chip,
  Card,
  CardContent,
  Grid,
  alpha
} from '@mui/material';
import AttachFileIcon from '@mui/icons-material/AttachFile';
import PersonIcon from '@mui/icons-material/Person';
import AccessTimeIcon from '@mui/icons-material/AccessTime';

interface Props { 
  events: DetailedEvent[]; 
}

const EventList: FC<Props> = ({ events }) => {
  // For demonstration, we'll assume the first user in the list is the "current user".
  // In a real application, you would get this from your authentication state.
  const currentUserId = events.length > 0 ? events[0].user_display_name : '';

  if (events.length === 0) {
    return (
      <Paper 
        sx={{ 
          p: 4, 
          textAlign: 'center', 
          backgroundColor: 'grey.50',
          borderRadius: 3,
          border: '2px dashed',
          borderColor: 'grey.300'
        }}
      >
        <AccessTimeIcon sx={{ fontSize: 48, color: 'grey.400', mb: 2 }} />
        <Typography variant="h6" color="text.secondary" sx={{ mb: 1 }}>
          No event history yet
        </Typography>
        <Typography variant="body2" color="text.secondary">
          When events occur, they will appear here
        </Typography>
      </Paper>
    );
  }

  return (
    <Box sx={{
      display: 'flex',
      flexDirection: 'column',
      maxHeight: '600px',
      overflowY: 'auto',
      p: 1,
      bgcolor: 'grey.50',
      borderRadius: 3,
      border: '1px solid',
      borderColor: 'grey.200',
    }}>
      <Stack spacing={2}>
        {events.map((evt, index) => {
          const isCurrentUser = evt.user_display_name === currentUserId;
          const atts = evt.event_content.attachments || [];

          return (
            <Box
              key={evt.id}
              sx={{
                display: 'flex',
                flexDirection: isCurrentUser ? 'row-reverse' : 'row',
                alignItems: 'flex-start',
                gap: 2,
              }}
            >
              {/* Avatar */}
              <Avatar
                sx={{
                  width: 40,
                  height: 40,
                  bgcolor: isCurrentUser 
                    ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' 
                    : 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
                  fontSize: '1rem',
                  fontWeight: 600,
                  flexShrink: 0
                }}
              >
                {evt.user_display_name.charAt(0).toUpperCase()}
              </Avatar>

              {/* Message Content */}
              <Card
                elevation={1}
                sx={{
                  maxWidth: '70%',
                  minWidth: '200px',
                  backgroundColor: isCurrentUser ? 'primary.main' : 'white',
                  color: isCurrentUser ? 'white' : 'text.primary',
                  borderRadius: 3,
                  position: 'relative',
                  transition: 'all 0.2s ease-in-out',
                  
                  '&:hover': {
                    transform: 'translateY(-1px)',
                    boxShadow: 2
                  },
                  
                  // Chat bubble arrow
                  '&::before': {
                    content: '""',
                    position: 'absolute',
                    top: 12,
                    [isCurrentUser ? 'right' : 'left']: -8,
                    width: 0,
                    height: 0,
                    borderTop: '8px solid transparent',
                    borderBottom: '8px solid transparent',
                    [isCurrentUser ? 'borderLeft' : 'borderRight']: `8px solid ${isCurrentUser ? '#667eea' : 'white'}`,
                  }
                }}
              >
                <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                  <Stack spacing={1}>
                    {/* User Info */}
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Chip
                        icon={<PersonIcon />}
                        label={evt.user_type}
                        size="small"
                        sx={{
                          background: isCurrentUser 
                            ? alpha('#ffffff', 0.2) 
                            : alpha('#667eea', 0.1),
                          color: isCurrentUser ? 'white' : 'primary.main',
                          fontWeight: 500,
                          fontSize: '0.75rem',
                          '& .MuiChip-icon': {
                            color: 'inherit'
                          }
                        }}
                      />
                      
                      <Typography 
                        variant="caption" 
                        sx={{ 
                          opacity: 0.8,
                          fontWeight: 500
                        }}
                      >
                        {evt.user_display_name}
                      </Typography>
                    </Box>
                    
                    {/* Message Text */}
                    {evt.event_content.text && (
                      <Typography 
                        variant="body1" 
                        sx={{ 
                          wordBreak: 'break-word',
                          lineHeight: 1.5,
                          fontSize: '0.95rem'
                        }}
                      >
                        {evt.event_content.text}
                      </Typography>
                    )}

                    {/* Attachments */}
                    {atts.length > 0 && (
                      <Box>
                        <Typography 
                          variant="subtitle2" 
                          sx={{ 
                            mb: 1, 
                            fontWeight: 600,
                            display: 'flex',
                            alignItems: 'center',
                            gap: 0.5
                          }}
                        >
                          <AttachFileIcon sx={{ fontSize: 16 }} />
                          Attachments ({atts.length})
                        </Typography>
                        
                        <Stack spacing={1}>
                          {atts.map(a => (
                            <Paper
                              key={a.id}
                              elevation={0}
                              sx={{
                                p: 1.5,
                                borderRadius: 2,
                                backgroundColor: isCurrentUser 
                                  ? alpha('#ffffff', 0.15) 
                                  : alpha('#667eea', 0.05),
                                border: '1px solid',
                                borderColor: isCurrentUser 
                                  ? alpha('#ffffff', 0.2) 
                                  : alpha('#667eea', 0.1),
                              }}
                            >
                              <Link 
                                href={a.url} 
                                target="_blank" 
                                rel="noopener noreferrer" 
                                sx={{
                                  color: isCurrentUser ? 'white' : 'primary.main',
                                  textDecoration: 'none',
                                  fontSize: '0.875rem',
                                  fontWeight: 500,
                                  display: 'flex',
                                  alignItems: 'center',
                                  gap: 1,
                                  
                                  '&:hover': {
                                    textDecoration: 'underline'
                                  }
                                }}
                              >
                                <AttachFileIcon sx={{ fontSize: 16 }} />
                                {a.resource_name || a.mime_type}
                              </Link>
                            </Paper>
                          ))}
                        </Stack>
                      </Box>
                    )}
                    
                    {/* Timestamp */}
                    <Typography 
                      variant="caption" 
                      sx={{ 
                        alignSelf: isCurrentUser ? 'flex-start' : 'flex-end',
                        opacity: 0.7,
                        fontSize: '0.7rem',
                        fontWeight: 500,
                        display: 'flex',
                        alignItems: 'center',
                        gap: 0.5
                      }}
                    >
                      <AccessTimeIcon sx={{ fontSize: 12 }} />
                      {new Date(evt.time_created).toLocaleTimeString([], { 
                        hour: '2-digit', 
                        minute: '2-digit',
                        day: '2-digit',
                        month: 'short'
                      })}
                    </Typography>
                  </Stack>
                </CardContent>
              </Card>
            </Box>
          );
        })}
      </Stack>
    </Box>
  );
};

export default EventList;
