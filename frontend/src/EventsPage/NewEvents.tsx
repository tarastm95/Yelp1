import React, { FC, useEffect, useState } from 'react';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
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
  Card,
  CardContent,
  Grid,
  Avatar,
} from '@mui/material';

import EventNoteIcon from '@mui/icons-material/EventNote';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import InfoIcon from '@mui/icons-material/Info';
import VisibilityIcon from '@mui/icons-material/Visibility';

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
  const navigate = useNavigate();

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
      <Paper 
        sx={{ 
          p: 6, 
          textAlign: 'center', 
          backgroundColor: 'grey.50',
          borderRadius: 3,
          border: '2px dashed',
          borderColor: 'grey.300'
        }}
      >
        <EventNoteIcon sx={{ fontSize: 64, color: 'grey.400', mb: 2 }} />
        <Typography variant="h6" color="text.secondary" sx={{ mb: 1 }}>
          No new events yet
        </Typography>
        <Typography variant="body2" color="text.secondary">
          When new events occur, they will appear here
        </Typography>
      </Paper>
    );
  }

  return (
    <Box sx={{ mt: 2 }}>
      <Stack spacing={3}>
        {events.map((e) => {
          const detail = leadDetails[e.lead_id];
          const isNew = !viewedEvents.has(String(e.event_id));

          return (
            <Card
              key={e.event_id}
              elevation={isNew ? 4 : 2}
              sx={{
                borderRadius: 3,
                overflow: 'hidden',
                position: 'relative',
                transition: 'all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1)',
                border: isNew ? '2px solid' : '1px solid',
                borderColor: isNew ? 'secondary.main' : 'grey.200',
                background: isNew 
                  ? 'linear-gradient(135deg, rgba(240, 147, 251, 0.02) 0%, rgba(245, 87, 108, 0.02) 100%)' 
                  : 'white',
                
                '&:hover': {
                  transform: 'translateY(-4px)',
                  boxShadow: isNew 
                    ? '0 12px 40px rgba(240, 147, 251, 0.2)' 
                    : '0 8px 32px rgba(0, 0, 0, 0.12)',
                  borderColor: isNew ? 'secondary.main' : 'secondary.light',
                }
              }}
            >
              {/* New Badge */}
              {isNew && (
                <Box
                  sx={{
                    position: 'absolute',
                    top: 16,
                    right: 16,
                    zIndex: 2
                  }}
                >
                  <Chip
                    label="NEW"
                    size="small"
                    sx={{
                      background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
                      color: 'white',
                      fontWeight: 700,
                      fontSize: '0.7rem',
                      animation: 'pulse 2s infinite',
                      boxShadow: 2,
                      '@keyframes pulse': {
                        '0%': { transform: 'scale(1)' },
                        '50%': { transform: 'scale(1.05)' },
                        '100%': { transform: 'scale(1)' }
                      }
                    }}
                  />
                </Box>
              )}

              <CardContent sx={{ p: 3 }}>
                <Grid container spacing={3}>
                  {/* Left Column - Main Info */}
                  <Grid item xs={12} md={8}>
                    <Stack spacing={2}>
                      {/* Header */}
                      <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                        <Avatar
                          sx={{
                            background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
                            width: 48,
                            height: 48,
                            mr: 2
                          }}
                        >
                          <EventNoteIcon />
                        </Avatar>
                        
                        <Box sx={{ flex: 1 }}>
                          <Typography variant="h6" sx={{ fontWeight: 700, mb: 0.5 }}>
                            Event #{e.event_id}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            {new Date(e.created_at).toLocaleString()}
                          </Typography>
                        </Box>
                      </Box>

                      {/* Details Grid */}
                      <Grid container spacing={2}>
                        <Grid item xs={12} sm={6}>
                          <Box sx={{ 
                            p: 2, 
                            backgroundColor: 'grey.50', 
                            borderRadius: 2,
                            border: '1px solid',
                            borderColor: 'grey.200'
                          }}>
                            <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
                              LEAD ID
                            </Typography>
                            <Typography variant="body2" sx={{ fontWeight: 500, mt: 0.5 }}>
                              {e.lead_id}
                            </Typography>
                          </Box>
                        </Grid>
                        
                        {detail?.user_display_name && (
                          <Grid item xs={12} sm={6}>
                            <Box sx={{ 
                              p: 2, 
                              backgroundColor: 'grey.50', 
                              borderRadius: 2,
                              border: '1px solid',
                              borderColor: 'grey.200'
                            }}>
                              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
                                USER
                              </Typography>
                              <Typography variant="body2" sx={{ fontWeight: 500, mt: 0.5 }}>
                                {detail.user_display_name}
                              </Typography>
                            </Box>
                          </Grid>
                        )}

                        {e.event_type && (
                          <Grid item xs={12} sm={6}>
                            <Box sx={{ 
                              p: 2, 
                              backgroundColor: 'grey.50', 
                              borderRadius: 2,
                              border: '1px solid',
                              borderColor: 'grey.200'
                            }}>
                              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
                                EVENT TYPE
                              </Typography>
                              <Typography variant="body2" sx={{ fontWeight: 500, mt: 0.5 }}>
                                {e.event_type}
                              </Typography>
                            </Box>
                          </Grid>
                        )}

                        {e.user_type && (
                          <Grid item xs={12} sm={6}>
                            <Box sx={{ 
                              p: 2, 
                              backgroundColor: 'grey.50', 
                              borderRadius: 2,
                              border: '1px solid',
                              borderColor: 'grey.200'
                            }}>
                              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
                                USER TYPE
                              </Typography>
                              <Typography variant="body2" sx={{ fontWeight: 500, mt: 0.5 }}>
                                {e.user_type}
                              </Typography>
                            </Box>
                          </Grid>
                        )}
                      </Grid>

                      {/* Job Names */}
                      {detail?.project?.job_names && detail.project.job_names.length > 0 && (
                        <Box>
                          <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600, mb: 1, display: 'block' }}>
                            JOB CATEGORIES
                          </Typography>
                          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                            {detail.project.job_names.map((job: string, idx: number) => (
                              <Chip
                                key={idx}
                                label={job}
                                size="small"
                                sx={{
                                  background: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
                                  color: 'white',
                                  fontWeight: 500,
                                  fontSize: '0.75rem'
                                }}
                              />
                            ))}
                          </Stack>
                        </Box>
                      )}
                    </Stack>
                  </Grid>

                  {/* Right Column - Status & Actions */}
                  <Grid item xs={12} md={4}>
                    <Stack spacing={2} sx={{ height: '100%' }}>
                      {/* Status Chips */}
                      <Box>
                        <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600, mb: 1, display: 'block' }}>
                          STATUS
                        </Typography>
                        <Stack direction="column" spacing={1}>
                          {detail?.phone_opt_in && (
                            <Chip 
                              label="Phone Opt-In" 
                              color="success" 
                              size="small"
                              icon={<CheckCircleIcon />}
                              sx={{ justifyContent: 'flex-start' }}
                            />
                          )}
                          {detail?.phone_in_text && !detail?.phone_in_additional_info && (
                            <Chip 
                              label="Phone in Text" 
                              color="info" 
                              size="small"
                              icon={<InfoIcon />}
                              sx={{ justifyContent: 'flex-start' }}
                            />
                          )}
                          {detail?.phone_in_additional_info && (
                            <Chip
                              label="Phone in Additional Info"
                              color="info"
                              size="small"
                              icon={<InfoIcon />}
                              sx={{ justifyContent: 'flex-start' }}
                            />
                          )}
                        </Stack>
                      </Box>

                      {/* Action Button */}
                      <Box sx={{ mt: 'auto' }}>
                        <Button
                          variant="contained"
                          size="small"
                          onClick={() => navigate(`/events/${e.event_id}`)}
                          startIcon={<VisibilityIcon />}
                          fullWidth
                          sx={{
                            background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
                            borderRadius: 2,
                            fontWeight: 600,
                            '&:hover': {
                              background: 'linear-gradient(135deg, #e082ea 0%, #e4485b 100%)',
                              transform: 'translateY(-1px)',
                              boxShadow: 3
                            }
                          }}
                        >
                          View Event Details
                        </Button>
                      </Box>
                    </Stack>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          );
        })}
      </Stack>

      {hasMore && (
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
          <Button
            variant="contained"
            size="large"
            onClick={onLoadMore}
            disabled={loadingMore}
            startIcon={loadingMore ? <CircularProgress size={20} color="inherit" /> : <EventNoteIcon />}
            sx={{
              background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
              borderRadius: 3,
              px: 4,
              py: 1.5,
              fontWeight: 600,
              fontSize: '1rem',
              textTransform: 'none',
              boxShadow: '0 8px 24px rgba(240, 147, 251, 0.3)',
              transition: 'all 0.3s ease-in-out',
              
              '&:hover:not(:disabled)': {
                background: 'linear-gradient(135deg, #e082ea 0%, #e4485b 100%)',
                transform: 'translateY(-2px)',
                boxShadow: '0 12px 32px rgba(240, 147, 251, 0.4)',
              },
              
              '&:disabled': {
                background: 'linear-gradient(135deg, #bbb 0%, #999 100%)',
                color: 'white',
              }
            }}
          >
            {loadingMore ? 'Loading More Events...' : 'Load More Events'}
          </Button>
        </Box>
      )}
    </Box>
  );
};

export default NewEvents;
