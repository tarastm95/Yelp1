import React, { FC, useState, useEffect, useRef } from 'react';
import axios from 'axios';
import {
  LeadDetail as LeadDetailType,
  ProcessedLead,
  LeadEvent,
} from './types';
import NewLeads from './NewLeads';
import NewEvents from './NewEvents';

import {
  Container,
  Box,
  Tabs,
  Tab,
  Typography,
  CircularProgress,
  Alert,
  Paper,
  Badge,
  useTheme,
  Fade,
  Select,
  MenuItem,
  Card,
  CardContent,
} from '@mui/material';
import BusinessInfoCard from '../BusinessInfoCard';
import PersonAddIcon from '@mui/icons-material/PersonAdd';
import EventNoteIcon from '@mui/icons-material/EventNote';
import BusinessIcon from '@mui/icons-material/Business';

const POLL_INTERVAL = 30000;

const API_BASE = import.meta.env.VITE_API_URL || 'http://46.62.139.177:8000';

interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

interface Business {
  business_id: string;
  name: string;
  location?: string;
  time_zone?: string;
  details?: any;
}

const TabPanel: FC<{ children?: React.ReactNode; value: number; index: number }> = ({
  children,
  value,
  index,
}) => {
  const theme = useTheme();
  console.log(`[TabPanel] index=${index}, value=${value}, shouldShow=${value === index}`);
  
  return (
    <div role="tabpanel" hidden={value !== index} id={`events-tabpanel-${index}`} aria-labelledby={`events-tab-${index}`}>
      {value === index && (
        <Fade in timeout={300}>
          <Box sx={{ mt: 2 }}>
            <Paper elevation={1} sx={{ p: 2, backgroundColor: theme.palette.background.paper }}>
              {children}
            </Paper>
          </Box>
        </Fade>
      )}
    </div>
  );
};

function a11yProps(index: number) {
  return {
    id: `events-tab-${index}`,
    'aria-controls': `events-tabpanel-${index}`,
  };
}

const EventsPage: FC = () => {
  const theme = useTheme();

  // Businesses list and selected business
  const [businesses, setBusinesses] = useState<Business[]>([]);
  const [selectedBusiness, setSelectedBusiness] = useState('');

  // IDs of viewed leads (for the "new" badge)
  const [viewedLeads, setViewedLeads] = useState<Set<string>>(new Set());
  const [viewedEvents, setViewedEvents] = useState<Set<string>>(new Set());
  
  // Helper functions for deduplication
  const deduplicateLeads = (existingLeads: ProcessedLead[], newLeads: ProcessedLead[]): ProcessedLead[] => {
    const existingIds = new Set(existingLeads.map(l => l.lead_id));
    const uniqueNewLeads = newLeads.filter(l => !existingIds.has(l.lead_id));
    
    if (newLeads.length !== uniqueNewLeads.length) {
      console.log(`[DEDUP LEADS] Filtered ${newLeads.length - uniqueNewLeads.length} duplicate leads`);
    }
    
    return [...existingLeads, ...uniqueNewLeads];
  };

  const deduplicateEvents = (existingEvents: LeadEvent[], newEvents: LeadEvent[]): LeadEvent[] => {
    const existingIds = new Set(existingEvents.map(e => e.event_id));
    const uniqueNewEvents = newEvents.filter(e => !existingIds.has(e.event_id));
    
    if (newEvents.length !== uniqueNewEvents.length) {
      console.log(`[DEDUP EVENTS] Filtered ${newEvents.length - uniqueNewEvents.length} duplicate events`);
    }
    
    return [...existingEvents, ...uniqueNewEvents];
  };

  const deduplicateEventsAtStart = (existingEvents: LeadEvent[], newEvents: LeadEvent[]): LeadEvent[] => {
    const existingIds = new Set(existingEvents.map(e => e.event_id));
    const uniqueNewEvents = newEvents.filter(e => !existingIds.has(e.event_id));
    
    if (newEvents.length !== uniqueNewEvents.length) {
      console.log(`[DEDUP EVENTS START] Filtered ${newEvents.length - uniqueNewEvents.length} duplicate events`);
    }
    
    return [...uniqueNewEvents, ...existingEvents];
  };

  // Function to clean up any existing duplicates in state
  const cleanupExistingDuplicates = React.useCallback(() => {
    setLeads(prev => {
      const uniqueLeads = prev.filter((lead, index, arr) => 
        arr.findIndex(l => l.lead_id === lead.lead_id) === index
      );
      if (prev.length !== uniqueLeads.length) {
        console.log(`[CLEANUP] Removed ${prev.length - uniqueLeads.length} duplicate leads from state`);
      }
      return uniqueLeads;
    });

    setEvents(prev => {
      const uniqueEvents = prev.filter((event, index, arr) => 
        arr.findIndex(e => e.event_id === event.event_id) === index
      );
      if (prev.length !== uniqueEvents.length) {
        console.log(`[CLEANUP] Removed ${prev.length - uniqueEvents.length} duplicate events from state`);
      }
      return uniqueEvents;
    });
  }, []);

  useEffect(() => {
    const storedLeads = localStorage.getItem('viewedLeads');
    if (storedLeads) {
      try {
        setViewedLeads(new Set(JSON.parse(storedLeads)));
      } catch {}
    }
    const storedEvents = localStorage.getItem('viewedEvents');
    if (storedEvents) {
      try {
        setViewedEvents(new Set(JSON.parse(storedEvents)));
      } catch {}
    }
  }, []);

  // Load businesses list
  useEffect(() => {
    axios
      .get<Business[]>('/businesses/')
      .then(res => {
        const sorted = [...res.data].sort((a, b) =>
          a.name.localeCompare(b.name)
        );
        setBusinesses(sorted);
      })
      .catch(() => setBusinesses([]));
  }, []);

  // Total number of leads/events (for badges)
  const [totalLeadsCount, setTotalLeadsCount] = useState(0);
  const [totalEventsCount, setTotalEventsCount] = useState(0);

  // States for leads and their details
  const [leads, setLeads] = useState<ProcessedLead[]>([]);
  const [leadDetails, setLeadDetails] = useState<Record<string, Partial<LeadDetailType>>>({});
  const [leadsNextUrl, setLeadsNextUrl] = useState<string | null>(null);

  // Events
  const [events, setEvents] = useState<LeadEvent[]>([]);
  const [eventsNextUrl, setEventsNextUrl] = useState<string | null>(null);
  const lastEventIdRef = useRef<number | null>(null);

  // UI states
  const [loading, setLoading] = useState(true);
  const [loadingMoreLeads, setLoadingMoreLeads] = useState(false);
  const [loadingMoreEvents, setLoadingMoreEvents] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tabValue, setTabValue] = useState(0);
  
  // Track last request to avoid race conditions
  const lastLeadsRequestRef = useRef<string>('');
  const lastEventsRequestRef = useRef<string>('');

  // Number of unread leads among the loaded ones
  const loadedLeadIds = new Set(leads.map(l => l.lead_id));
  const viewedLoadedIdsCount = Array.from(viewedLeads).filter(id =>
    loadedLeadIds.has(id)
  ).length;
  const unreadLeadsCount = Math.max(0, totalLeadsCount - viewedLoadedIdsCount);

  const filteredLeads = leads;
  
  // Debug logging for leads state
  console.log('[EventsPage] Current state:', {
    leadsLength: leads.length,
    filteredLeadsLength: filteredLeads.length,
    totalLeadsCount,
    loading,
    selectedBusiness,
    tabValue,
    leads: leads.slice(0, 3) // Show first 3 leads for debugging
  });


  // Load a page of leads and their details
  const loadLeads = async (url?: string) => {
    const reqUrl =
      url ||
      `${API_BASE}/api/processed_leads${
        selectedBusiness ? `?business_id=${encodeURIComponent(selectedBusiness)}` : ''
      }`;
    
    const requestId = `leads-${Date.now()}-${Math.random()}`;
    lastLeadsRequestRef.current = requestId;
    
    try {
      console.log('[loadLeads] request', reqUrl);
      console.log('[loadLeads] selectedBusiness:', selectedBusiness);
      console.log('[loadLeads] API_BASE:', API_BASE);
      
      const { data } = await axios.get<PaginatedResponse<ProcessedLead>>(reqUrl);
      
      // Check if this is still the latest request
      if (lastLeadsRequestRef.current !== requestId) {
        console.log('[loadLeads] Ignoring stale request - current:', lastLeadsRequestRef.current, 'received:', requestId);
        return;
      }
      
      console.log('[loadLeads] received', data.results.length, 'leads');
      console.log('[loadLeads] total count:', data.count);
      console.log('[loadLeads] next url:', data.next);
      console.log('[loadLeads] data:', data);
      
      setTotalLeadsCount(data.count);
      console.log('[loadLeads] Set totalLeadsCount to:', data.count);
      
      setLeads(prev => {
        const newLeads = deduplicateLeads(prev, data.results);
        console.log('[loadLeads] Setting leads state:', {
          previousCount: prev.length,
          newDataCount: data.results.length,
          resultingCount: newLeads.length,
          deduplicationWorked: prev.length + data.results.length >= newLeads.length,
          newLeads: newLeads.slice(0, 3) // Show first 3 for debugging
        });
        console.log('[loadLeads] About to return newLeads with length:', newLeads.length);
        return newLeads;
      });
      setLeadsNextUrl(data.next);

      const detailsArr = await Promise.all(
        data.results.map(l =>
          axios
            .get<Partial<LeadDetailType>>(
              `${API_BASE}/api/lead-details/${encodeURIComponent(l.lead_id)}/`
            )
            .then(res => ({ ...res.data, lead_id: l.lead_id }))
            .catch(() => ({ lead_id: l.lead_id, user_display_name: '—' }))
        )
      );

      setLeadDetails(prev => {
        const map = { ...prev } as Record<string, Partial<LeadDetailType>>;
        detailsArr.forEach(d => {
          if (d.lead_id) map[d.lead_id] = d;
        });
        return map;
      });
    } catch (err: any) {
      console.error('[loadLeads] error', err);
      console.error('[loadLeads] error details:', {
        message: err.message,
        status: err.response?.status,
        statusText: err.response?.statusText,
        data: err.response?.data,
        url: reqUrl
      });
      setError(`Failed to load leads: ${err.message} (Status: ${err.response?.status || 'Unknown'})`);
    }
  };

  // Load a page of events
  const loadEvents = async (url?: string) => {
    const reqUrl =
      url ||
      `${API_BASE}/api/lead-events${
        selectedBusiness ? `?business_id=${encodeURIComponent(selectedBusiness)}` : ''
      }`;
    
    const requestId = `events-${Date.now()}-${Math.random()}`;
    lastEventsRequestRef.current = requestId;
    
    try {
      console.log('[loadEvents] request', reqUrl);
      const { data } = await axios.get<PaginatedResponse<LeadEvent>>(reqUrl);
      
      // Check if this is still the latest request
      if (lastEventsRequestRef.current !== requestId) {
        console.log('[loadEvents] Ignoring stale request - current:', lastEventsRequestRef.current, 'received:', requestId);
        return;
      }
      
      console.log('[loadEvents] received', data.results.length, 'events');
      setTotalEventsCount(data.count);
      setEvents(prev => deduplicateEvents(prev, data.results));
      setEventsNextUrl(data.next);
      if (data.results.length) {
        const maxId = Math.max(...data.results.map(e => e.id));
        lastEventIdRef.current = Math.max(lastEventIdRef.current || 0, maxId);
      }
    } catch {
      console.error('[loadEvents] failed');
      setError('Failed to load events');
    }
  };

  // Pull new events after the last one
  const pollEvents = async () => {
    if (lastEventIdRef.current == null) return;
    try {
      const url = `${API_BASE}/api/lead-events?after_id=${lastEventIdRef.current}${
        selectedBusiness ? `&business_id=${encodeURIComponent(selectedBusiness)}` : ''
      }`;
      console.log('[pollEvents] request', url);
      const { data } = await axios.get<LeadEvent[]>(url);
      console.log('[pollEvents] received', data.length, 'events');
      if (data.length) {
        const sorted = [...data].sort((a, b) => a.id - b.id);
        const maxId = sorted[sorted.length - 1].id;
        
        // Count only unique events that will actually be added
        const existingIds = new Set(events.map(e => e.event_id));
        const uniqueNewEvents = sorted.filter(e => !existingIds.has(e.event_id));
        
        setEvents(prev => deduplicateEventsAtStart(prev, sorted));
        setTotalEventsCount(prev => prev + uniqueNewEvents.length);
        lastEventIdRef.current = Math.max(lastEventIdRef.current || 0, maxId);
      }
    } catch {
      console.error('[pollEvents] failed');
    }
  };

  // Load the first pages and whenever business selection changes
  useEffect(() => {
    setLoading(true);
    setLeads([]);
    setLeadDetails({});
    setEvents([]);
    setLeadsNextUrl(null);
    setEventsNextUrl(null);
    lastEventIdRef.current = null;
    lastLeadsRequestRef.current = '';
    lastEventsRequestRef.current = '';

    console.log('[useEffect] Starting to load leads and events for selectedBusiness:', selectedBusiness);
    Promise.all([loadLeads(), loadEvents()])
      .then(() => {
        console.log('[useEffect] Promise.all completed successfully');
        // Clean up any duplicates that might have occurred
        setTimeout(cleanupExistingDuplicates, 100);
      })
      .catch((error) => {
        console.error('[useEffect] Promise.all failed:', error);
      })
      .finally(() => {
        console.log('[useEffect] Setting loading to false');
        setLoading(false);
      });
  }, [selectedBusiness]);

  // Poll for new events
  useEffect(() => {
    const timer = setInterval(() => {
      pollEvents();
    }, POLL_INTERVAL);
    return () => clearInterval(timer);
  }, [selectedBusiness]);

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 6 }}>
        <CircularProgress />
      </Box>
    );
  }
  if (error) {
    return (
      <Container sx={{ mt: 4 }}>
        <Alert severity="error">{error}</Alert>
      </Container>
    );
  }

  const filteredEvents = events;
  const newEvents = [...filteredEvents].sort((a, b) => b.id - a.id);
  const unreadEventsCount = Math.max(0, totalEventsCount - viewedEvents.size);

  return (
    <Box sx={{ 
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)',
      pb: 6
    }}>
      <Container maxWidth="xl" sx={{ pt: 4 }}>
        {/* Page Header */}
        <Box 
          sx={{ 
            textAlign: 'center',
            mb: 4,
            p: 3,
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            borderRadius: 3,
            color: 'white',
            position: 'relative',
            overflow: 'hidden'
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
          
          <Box sx={{ position: 'relative', zIndex: 1 }}>
            <EventNoteIcon sx={{ fontSize: 48, mb: 1, opacity: 0.9 }} />
            <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>
              Events & Leads Dashboard
            </Typography>
            <Typography variant="body1" sx={{ opacity: 0.9 }}>
              Monitor and manage your Yelp events and customer leads
            </Typography>
          </Box>
        </Box>

        {/* Business Selector */}
        <Card elevation={2} sx={{ mb: 3, borderRadius: 3, overflow: 'hidden' }}>
          <Box sx={{ 
            background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
            p: 2,
            color: 'white'
          }}>
            <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', fontWeight: 600 }}>
              <BusinessIcon sx={{ mr: 1 }} />
              Business Filter
            </Typography>
          </Box>
          
          <CardContent sx={{ p: 3 }}>
            <Box sx={{ mb: 2 }}>
              <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                Select Business
              </Typography>
              <Select
                value={selectedBusiness}
                onChange={e => setSelectedBusiness(e.target.value as string)}
                displayEmpty
                fullWidth
                sx={{ 
                  '& .MuiOutlinedInput-root': {
                    borderRadius: 2,
                    backgroundColor: 'grey.50'
                  }
                }}
              >
                <MenuItem value="">
                  <Box sx={{ display: 'flex', alignItems: 'center', color: 'text.secondary' }}>
                    <BusinessIcon sx={{ mr: 1, fontSize: 20 }} />
                    <em>All Businesses</em>
                  </Box>
                </MenuItem>
                {businesses.map(b => (
                  <MenuItem key={b.business_id} value={b.business_id}>
                    <Box sx={{ display: 'flex', alignItems: 'center', width: '100%' }}>
                      <BusinessIcon sx={{ mr: 2, color: 'primary.main', fontSize: 20 }} />
                      <Box sx={{ flex: 1 }}>
                        <Typography variant="body1" sx={{ fontWeight: 500 }}>
                          {b.name}
                        </Typography>
                        {(b.location || b.time_zone) && (
                          <Typography variant="caption" color="text.secondary">
                            {b.location ? `${b.location}` : ''}
                            {b.location && b.time_zone ? ' • ' : ''}
                            {b.time_zone ? b.time_zone : ''}
                          </Typography>
                        )}
                      </Box>
                    </Box>
                  </MenuItem>
                ))}
              </Select>
            </Box>
          </CardContent>
        </Card>

        {/* Selected Business Info */}
        {selectedBusiness && (() => {
          const biz = businesses.find(b => b.business_id === selectedBusiness);
          if (!biz) return null;
          return (
            <Box sx={{ mb: 3 }}>
              <BusinessInfoCard business={biz} />
            </Box>
          );
        })()}

        {/* Tabs Section */}
        <Card elevation={2} sx={{ borderRadius: 3, overflow: 'hidden', mb: 3 }}>
          <Tabs
            value={tabValue}
            onChange={(_, v) => setTabValue(v)}
            aria-label="Events & Leads Tabs"
            variant="fullWidth"
            sx={{
              background: 'linear-gradient(135deg, #f8f9ff 0%, #e3e7fc 100%)',
              '& .MuiTab-root': {
                py: 3,
                fontWeight: 600,
                fontSize: '1rem',
                textTransform: 'none',
                minHeight: 'auto',
                transition: 'all 0.3s ease-in-out',
                
                '&.Mui-selected': {
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  color: 'white',
                  borderRadius: '12px 12px 0 0',
                  transform: 'translateY(-2px)',
                  boxShadow: '0 4px 12px rgba(102, 126, 234, 0.3)',
                  
                  '& .MuiSvgIcon-root': {
                    color: 'white',
                  }
                },
                
                '&:hover:not(.Mui-selected)': {
                  backgroundColor: 'rgba(102, 126, 234, 0.08)',
                  transform: 'translateY(-1px)',
                }
              },
              '& .MuiTabs-indicator': {
                display: 'none'
              }
            }}
          >
            <Tab
              icon={
                <Badge 
                  badgeContent={unreadLeadsCount} 
                  color="secondary" 
                  invisible={unreadLeadsCount === 0}
                  sx={{
                    '& .MuiBadge-badge': {
                      fontSize: '0.75rem',
                      fontWeight: 600,
                      minWidth: 20,
                      height: 20
                    }
                  }}
                >
                  <PersonAddIcon sx={{ fontSize: 24 }} />
                </Badge>
              }
              label={
                <Box sx={{ textAlign: 'center' }}>
                  <Typography variant="body1" sx={{ fontWeight: 'inherit', mb: 0.5 }}>
                    Processed Leads
                  </Typography>
                  <Typography variant="caption" sx={{ opacity: 0.8 }}>
                    {totalLeadsCount} total{unreadLeadsCount ? `, ${unreadLeadsCount} new` : ''}
                  </Typography>
                </Box>
              }
              {...a11yProps(0)}
            />
            <Tab
              icon={
                <Badge 
                  badgeContent={unreadEventsCount} 
                  color="secondary" 
                  invisible={unreadEventsCount === 0}
                  sx={{
                    '& .MuiBadge-badge': {
                      fontSize: '0.75rem',
                      fontWeight: 600,
                      minWidth: 20,
                      height: 20
                    }
                  }}
                >
                  <EventNoteIcon sx={{ fontSize: 24 }} />
                </Badge>
              }
              label={
                <Box sx={{ textAlign: 'center' }}>
                  <Typography variant="body1" sx={{ fontWeight: 'inherit', mb: 0.5 }}>
                    New Events
                  </Typography>
                  <Typography variant="caption" sx={{ opacity: 0.8 }}>
                    {totalEventsCount} total{unreadEventsCount ? `, ${unreadEventsCount} new` : ''}
                  </Typography>
                </Box>
              }
              {...a11yProps(1)}
            />
          </Tabs>
        </Card>

        <TabPanel value={tabValue} index={0}>
          {(() => {
            console.log('[EventsPage] Rendering NewLeads with:', {
              leads: filteredLeads.length,
              leadDetails: Object.keys(leadDetails).length,
              events: filteredEvents.length,
              visibleCount: filteredLeads.length,
              tabValue,
              isTabActive: tabValue === 0
            });
            return null;
          })()}
          <NewLeads
            leads={filteredLeads}
            leadDetails={leadDetails}
            events={filteredEvents}
            visibleCount={filteredLeads.length}
            onLoadMore={() => {
              if (leadsNextUrl) {
                setLoadingMoreLeads(true);
                loadLeads(leadsNextUrl).finally(() => setLoadingMoreLeads(false));
              }
            }}
            hasMore={Boolean(leadsNextUrl)}
            loadingMore={loadingMoreLeads}
          />
        </TabPanel>

        <TabPanel value={tabValue} index={1}>
          <NewEvents
            events={newEvents}
            leadDetails={leadDetails}
            onLoadMore={() => {
              if (eventsNextUrl) {
                setLoadingMoreEvents(true);
                loadEvents(eventsNextUrl).finally(() => setLoadingMoreEvents(false));
              }
            }}
            hasMore={Boolean(eventsNextUrl)}
            loadingMore={loadingMoreEvents}
          />
        </TabPanel>
      </Container>
    </Box>
  );
};

export default EventsPage;
