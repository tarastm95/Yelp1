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
  Card,
  CardContent,
  Stack,
  Chip,
  Avatar,
  Grid,
  alpha,
} from '@mui/material';

import { DetailedEvent, LeadDetail } from './types';
import { LeadEvent } from '../EventsPage/types';
import EventList from './EventList';
import InstantMessageSection from './InstantMessageSection';

// Icons
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import EventNoteIcon from '@mui/icons-material/EventNote';
import PersonIcon from '@mui/icons-material/Person';
import HistoryIcon from '@mui/icons-material/History';
import ChatIcon from '@mui/icons-material/Chat';
import WorkIcon from '@mui/icons-material/Work';

const EventDetail: FC = () => {
  const { id } = useParams<{ id: string }>();
  const [eventsDetail, setEventsDetail] = useState<DetailedEvent[]>([]);
  const [leadId, setLeadId] = useState<string | null>(null);
  const [leadDetail, setLeadDetail] = useState<LeadDetail | null>(null);
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
      } catch (e: any) {
        setError(e.message || 'Failed to load data');
      } finally {
        setLoading(false);
      }
    })();
  }, [id, fetchDetails, fetchLeadDetail]);

  // Early returns
  if (loading) {
    return (
      <Box sx={{ 
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)',
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center' 
      }}>
        <CircularProgress size={48} />
      </Box>
    );
  }
  
  if (error) {
    return (
      <Box sx={{ 
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)',
        p: 4
      }}>
        <Container maxWidth="md">
          <Alert severity="error" sx={{ borderRadius: 3, mb: 3 }}>{error}</Alert>
          <Button 
            component={RouterLink} 
            to="/events" 
            startIcon={<ArrowBackIcon />}
            sx={{
              background: 'rgba(255, 255, 255, 0.9)',
              backdropFilter: 'blur(10px)',
              borderRadius: 3,
              px: 3,
              py: 1.5,
              fontWeight: 600,
              color: 'text.primary',
              border: '1px solid',
              borderColor: alpha('#667eea', 0.2),
              
              '&:hover': {
                background: 'rgba(255, 255, 255, 1)',
                borderColor: '#667eea',
                transform: 'translateY(-2px)',
                boxShadow: '0 8px 24px rgba(102, 126, 234, 0.15)',
              }
            }}
          >
            Back to Events List
          </Button>
        </Container>
      </Box>
    );
  }
  
  if (!leadDetail || !leadId) {
    return (
      <Box sx={{ 
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)',
        p: 4
      }}>
        <Container maxWidth="md">
          <Alert severity="warning" sx={{ borderRadius: 3, mb: 3 }}>Failed to fetch client data</Alert>
          <Button 
            component={RouterLink} 
            to="/events" 
            startIcon={<ArrowBackIcon />}
            sx={{
              background: 'rgba(255, 255, 255, 0.9)',
              backdropFilter: 'blur(10px)',
              borderRadius: 3,
              px: 3,
              py: 1.5,
              fontWeight: 600,
              color: 'text.primary',
              border: '1px solid',
              borderColor: alpha('#667eea', 0.2),
              
              '&:hover': {
                background: 'rgba(255, 255, 255, 1)',
                borderColor: '#667eea',
                transform: 'translateY(-2px)',
                boxShadow: '0 8px 24px rgba(102, 126, 234, 0.15)',
              }
            }}
          >
            Back to Events List
          </Button>
        </Container>
      </Box>
    );
  }

  const displayName = leadDetail.user.display_name;
  const jobNames = leadDetail.project?.job_names || [];
  const lid = leadId;

  return (
    <Box sx={{ 
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)',
      pb: 6
    }}>
      <Container maxWidth="xl" sx={{ pt: 4 }}>
        {/* Back Button */}
        <Button
          component={RouterLink}
          to="/events"
          startIcon={<ArrowBackIcon />}
          sx={{
            mb: 3,
            background: 'rgba(255, 255, 255, 0.9)',
            backdropFilter: 'blur(10px)',
            borderRadius: 3,
            px: 3,
            py: 1.5,
            fontWeight: 600,
            color: 'text.primary',
            border: '1px solid',
            borderColor: alpha('#667eea', 0.2),
            
            '&:hover': {
              background: 'rgba(255, 255, 255, 1)',
              borderColor: '#667eea',
              transform: 'translateY(-2px)',
              boxShadow: '0 8px 24px rgba(102, 126, 234, 0.15)',
            }
          }}
        >
          Back to Events List
        </Button>

        {/* Hero Section */}
        <Card 
          elevation={4}
          sx={{ 
            borderRadius: 4,
            overflow: 'hidden',
            mb: 4,
            background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
            color: 'white',
            position: 'relative'
          }}
        >
          <Box
            sx={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              background: 'url("data:image/svg+xml,%3Csvg width="60" height="60" viewBox="0 0 60 60" xmlns="http://www.w3.org/2000/svg"%3E%3Cg fill="none" fill-rule="evenodd"%3E%3Cg fill="%23ffffff" fill-opacity="0.05"%3E%3Ccircle cx="30" cy="30" r="2"/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")',
              opacity: 0.3
            }}
          />
          
          <CardContent sx={{ p: 4, position: 'relative', zIndex: 1 }}>
            <Stack direction={{ xs: 'column', md: 'row' }} spacing={3} alignItems="center">
              {/* Avatar */}
              <Avatar
                sx={{
                  width: 100,
                  height: 100,
                  fontSize: '2.5rem',
                  fontWeight: 700,
                  background: 'rgba(255, 255, 255, 0.2)',
                  backdropFilter: 'blur(10px)',
                  border: '4px solid rgba(255, 255, 255, 0.3)',
                  boxShadow: '0 8px 32px rgba(0, 0, 0, 0.1)'
                }}
              >
                <EventNoteIcon sx={{ fontSize: '2.5rem' }} />
              </Avatar>
              
              {/* Info */}
              <Box sx={{ flex: 1, textAlign: { xs: 'center', md: 'left' } }}>
                <Typography variant="h3" sx={{ fontWeight: 800, mb: 1 }}>
                  Event Details #{id}
                </Typography>
                
                <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ mb: 2 }}>
                  <Chip
                    icon={<PersonIcon />}
                    label={displayName}
                    sx={{
                      background: 'rgba(255, 255, 255, 0.2)',
                      color: 'white',
                      fontWeight: 600,
                      '& .MuiChip-icon': { color: 'white' }
                    }}
                  />
                  
                  {jobNames.length > 0 && (
                    <Chip
                      icon={<WorkIcon />}
                      label={`${jobNames.length} Job${jobNames.length > 1 ? 's' : ''}`}
                      sx={{
                        background: 'rgba(255, 255, 255, 0.2)',
                        color: 'white',
                        fontWeight: 600,
                        '& .MuiChip-icon': { color: 'white' }
                      }}
                    />
                  )}
                </Stack>
                
                <Typography variant="h6" sx={{ opacity: 0.9 }}>
                  Event History & Instant Messaging
                </Typography>
              </Box>
            </Stack>
          </CardContent>
        </Card>

        <Grid container spacing={4}>
          {/* Event History Section */}
          <Grid item xs={12} lg={6}>
            <Card elevation={2} sx={{ borderRadius: 3, height: 'fit-content' }}>
              <Box sx={{ 
                background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
                p: 2,
                color: 'white'
              }}>
                <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', fontWeight: 600 }}>
                  <HistoryIcon sx={{ mr: 1 }} />
                  Event History
                </Typography>
              </Box>
              
              <CardContent sx={{ p: 3 }}>
                <EventList events={eventsDetail} />
              </CardContent>
            </Card>
          </Grid>

          {/* Instant Messages Section */}
          <Grid item xs={12} lg={6}>
            <Card elevation={2} sx={{ borderRadius: 3, height: 'fit-content' }}>
              <Box sx={{ 
                background: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
                p: 2,
                color: 'white'
              }}>
                <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', fontWeight: 600 }}>
                  <ChatIcon sx={{ mr: 1 }} />
                  Send Instant Message
                </Typography>
              </Box>
              
              <CardContent sx={{ p: 3 }}>
                <InstantMessageSection
                  leadId={lid}
                  displayName={displayName}
                  jobNames={jobNames}
                  onSent={() => {
                    fetchDetails(lid);
                  }}
                />
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Container>
    </Box>
  );
};

export default EventDetail;
