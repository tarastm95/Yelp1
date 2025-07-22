import React, { FC, useState, useEffect } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { ProcessedLead, LeadDetail as LeadDetailType, LeadEvent } from './types';
import {
  Box,
  Typography,
  Button,
  Paper,
  Stack,
  Chip,
  useTheme,
  CircularProgress,
  Card,
  CardContent,
  Grid,
  Avatar,
} from '@mui/material';
import PersonAddIcon from '@mui/icons-material/PersonAdd';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import InfoIcon from '@mui/icons-material/Info';
import VisibilityIcon from '@mui/icons-material/Visibility';
import EventIcon from '@mui/icons-material/Event';

// Base URL for API requests
const API_BASE = import.meta.env.VITE_API_URL || 'http://46.62.139.177:8000';

interface Props {
  leads: ProcessedLead[];
  leadDetails: Record<string, Partial<LeadDetailType>>;
  events: LeadEvent[];
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
  // Debug logging for received props
  console.log('[NewLeads] Received props:', {
    leadsLength: leads.length,
    leadDetailsCount: Object.keys(leadDetails).length,
    eventsCount: events.length,
    visibleCount,
    hasMore,
    loadingMore,
    leads: leads.slice(0, 3) // Show first 3 leads for debugging
  });

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
          const inEvents = events.some(e => e.lead_id === lid);
          return !inEvents && fetchedEvents[lid] == null;
        });
      for (const lid of toFetch) {
        try {
          const { data } = await axios.get<LeadEvent>(
            `${API_BASE}/api/lead-events/${encodeURIComponent(lid)}/latest/`
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
    console.log('[NewLeads] No leads to display, showing empty state');
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
        <PersonAddIcon sx={{ fontSize: 64, color: 'grey.400', mb: 2 }} />
        <Typography variant="h6" color="text.secondary" sx={{ mb: 1 }}>
          No processed leads yet
        </Typography>
        <Typography variant="body2" color="text.secondary">
          When you receive new leads from Yelp, they will appear here
        </Typography>
      </Paper>
    );
  }

  // Deduplicate leads before rendering to ensure no duplicates are shown
  const uniqueLeads = leads.filter((lead, index, arr) => 
    arr.findIndex(l => l.lead_id === lead.lead_id) === index
  );
  
  if (uniqueLeads.length !== leads.length) {
    console.log(`[NewLeads] Filtered ${leads.length - uniqueLeads.length} duplicate leads before rendering`);
  }

  if (uniqueLeads.length === 0) {
    console.log('[NewLeads] All leads were filtered out during deduplication');
    return (
      <Paper 
        sx={{ 
          p: 6, 
          textAlign: 'center', 
          backgroundColor: 'warning.50',
          borderRadius: 3,
          border: '2px dashed',
          borderColor: 'warning.main'
        }}
      >
        <PersonAddIcon sx={{ fontSize: 64, color: 'warning.main', mb: 2 }} />
        <Typography variant="h6" color="warning.main" sx={{ mb: 1 }}>
          All leads filtered out
        </Typography>
        <Typography variant="body2" color="text.secondary">
          All leads were removed during deduplication. This might be a bug.
        </Typography>
      </Paper>
    );
  }
  
  console.log('[NewLeads] After deduplication:', {
    originalLength: leads.length,
    uniqueLength: uniqueLeads.length,
    visibleCount,
    sliceLength: uniqueLeads.slice(0, visibleCount).length,
    renderingLeads: uniqueLeads.slice(0, 3) // Show what will be rendered
  });

  return (
    <Box sx={{ mt: 2 }}>
      <Stack spacing={3}>
        {uniqueLeads.slice(0, visibleCount).map(({ lead_id, business_id, processed_at }) => {
          const detail = leadDetails[lead_id] || {};
          const matchedEvent = events.find(e => e.lead_id === lead_id);
          const eventId = matchedEvent ? String(matchedEvent.event_id) : fetchedEvents[lead_id];
          const isNew = !viewedLeads.has(lead_id);

          return (
            <Card
              key={lead_id}
              elevation={isNew ? 4 : 2}
              sx={{
                borderRadius: 3,
                overflow: 'hidden',
                position: 'relative',
                transition: 'all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1)',
                border: isNew ? '2px solid' : '1px solid',
                borderColor: isNew ? 'primary.main' : 'grey.200',
                background: isNew 
                  ? 'linear-gradient(135deg, rgba(102, 126, 234, 0.02) 0%, rgba(118, 75, 162, 0.02) 100%)' 
                  : 'white',
                
                '&:hover': {
                  transform: 'translateY(-4px)',
                  boxShadow: isNew 
                    ? '0 12px 40px rgba(102, 126, 234, 0.2)' 
                    : '0 8px 32px rgba(0, 0, 0, 0.12)',
                  borderColor: isNew ? 'primary.main' : 'primary.light',
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
                            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                            width: 48,
                            height: 48,
                            mr: 2
                          }}
                        >
                          <PersonAddIcon />
                        </Avatar>
                        
                        <Box sx={{ flex: 1 }}>
                          <Typography variant="h6" sx={{ fontWeight: 700, mb: 0.5 }}>
                            {detail.user_display_name || 'Unknown User'}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            Lead ID: {lead_id}
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
                              BUSINESS ID
                            </Typography>
                            <Typography variant="body2" sx={{ fontWeight: 500, mt: 0.5 }}>
                              {business_id}
                            </Typography>
                          </Box>
                        </Grid>
                        
                        <Grid item xs={12} sm={6}>
                          <Box sx={{ 
                            p: 2, 
                            backgroundColor: 'grey.50', 
                            borderRadius: 2,
                            border: '1px solid',
                            borderColor: 'grey.200'
                          }}>
                            <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
                              PROCESSED
                            </Typography>
                            <Typography variant="body2" sx={{ fontWeight: 500, mt: 0.5 }}>
                              {new Date(processed_at).toLocaleString()}
                            </Typography>
                          </Box>
                        </Grid>
                      </Grid>

                      {/* Job Names */}
                      {detail.project?.job_names && detail.project.job_names.length > 0 && (
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
                          {detail.phone_opt_in && (
                            <Chip 
                              label="Phone Opt-In" 
                              color="success" 
                              size="small"
                              icon={<CheckCircleIcon />}
                              sx={{ justifyContent: 'flex-start' }}
                            />
                          )}
                          {detail.phone_in_text && !detail.phone_in_additional_info && (
                            <Chip 
                              label="Phone in Text" 
                              color="info" 
                              size="small"
                              icon={<InfoIcon />}
                              sx={{ justifyContent: 'flex-start' }}
                            />
                          )}
                          {detail.phone_in_additional_info && (
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

                      {/* Action Buttons */}
                      <Box sx={{ mt: 'auto' }}>
                        <Stack direction="column" spacing={1}>
                          <Button
                            variant="contained"
                            size="small"
                            onClick={() => handleViewClient(lead_id)}
                            startIcon={<VisibilityIcon />}
                            sx={{
                              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                              borderRadius: 2,
                              fontWeight: 600,
                              '&:hover': {
                                background: 'linear-gradient(135deg, #5a6fd8 0%, #6b4190 100%)',
                                transform: 'translateY(-1px)',
                                boxShadow: 3
                              }
                            }}
                          >
                            View Details
                          </Button>

                          {eventId && (
                            <Button
                              variant="outlined"
                              size="small"
                              onClick={() => handleViewEvent(lead_id, eventId)}
                              startIcon={<EventIcon />}
                              sx={{
                                borderRadius: 2,
                                fontWeight: 600,
                                borderColor: 'primary.main',
                                '&:hover': {
                                  borderColor: 'primary.dark',
                                  backgroundColor: 'primary.50',
                                  transform: 'translateY(-1px)'
                                }
                              }}
                            >
                              View Event
                            </Button>
                          )}
                        </Stack>
                      </Box>
                    </Stack>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          );
        })}
      </Stack>

      {/* Load more */}
      {hasMore && (
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
          <Button
            variant="contained"
            size="large"
            onClick={onLoadMore}
            disabled={loadingMore}
            startIcon={loadingMore ? <CircularProgress size={20} color="inherit" /> : <PersonAddIcon />}
            sx={{
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              borderRadius: 3,
              px: 4,
              py: 1.5,
              fontWeight: 600,
              fontSize: '1rem',
              textTransform: 'none',
              boxShadow: '0 8px 24px rgba(102, 126, 234, 0.3)',
              transition: 'all 0.3s ease-in-out',
              
              '&:hover:not(:disabled)': {
                background: 'linear-gradient(135deg, #5a6fd8 0%, #6b4190 100%)',
                transform: 'translateY(-2px)',
                boxShadow: '0 12px 32px rgba(102, 126, 234, 0.4)',
              },
              
              '&:disabled': {
                background: 'linear-gradient(135deg, #bbb 0%, #999 100%)',
                color: 'white',
              }
            }}
          >
            {loadingMore ? 'Loading More Leads...' : 'Load More Leads'}
          </Button>
        </Box>
      )}
    </Box>
  );
};

export default NewLeads;
