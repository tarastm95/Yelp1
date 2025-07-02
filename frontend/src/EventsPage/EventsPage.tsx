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
} from '@mui/material';
import BusinessInfoCard from '../BusinessInfoCard';
import PersonAddIcon from '@mui/icons-material/PersonAdd';
import EventNoteIcon from '@mui/icons-material/EventNote';

const POLL_INTERVAL = 30000;

const API_BASE = process.env.REACT_APP_API_BASE_URL || 'http://46.62.139.177:8000';

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

  // Number of unread leads among the loaded ones
  const loadedLeadIds = new Set(leads.map(l => l.lead_id));
  const viewedLoadedIdsCount = Array.from(viewedLeads).filter(id =>
    loadedLeadIds.has(id)
  ).length;
  const unreadLeadsCount = Math.max(0, totalLeadsCount - viewedLoadedIdsCount);

  const filteredLeads = leads;


  // Load a page of leads and their details
  const loadLeads = async (url?: string) => {
    const reqUrl =
      url ||
      `${API_BASE}/api/processed_leads/${
        selectedBusiness ? `?business_id=${encodeURIComponent(selectedBusiness)}` : ''
      }`;
    try {
      console.log('[loadLeads] request', reqUrl);
      const { data } = await axios.get<PaginatedResponse<ProcessedLead>>(reqUrl);
      console.log('[loadLeads] received', data.results.length, 'leads');
      setTotalLeadsCount(data.count);
      setLeads(prev => [...prev, ...data.results]);
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
      setError(`Failed to load leads: ${err.message}`);
    }
  };

  // Load a page of events
  const loadEvents = async (url?: string) => {
    const reqUrl =
      url ||
      `${API_BASE}/api/lead-events/${
        selectedBusiness ? `?business_id=${encodeURIComponent(selectedBusiness)}` : ''
      }`;
    try {
      console.log('[loadEvents] request', reqUrl);
      const { data } = await axios.get<PaginatedResponse<LeadEvent>>(reqUrl);
      console.log('[loadEvents] received', data.results.length, 'events');
      setTotalEventsCount(data.count);
      setEvents(prev => [...prev, ...data.results]);
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
      const url = `${API_BASE}/api/lead-events?after_id=${lastEventIdRef.current}$
{selectedBusiness ? `&business_id=${encodeURIComponent(selectedBusiness)}` : ''}`;
      console.log('[pollEvents] request', url);
      const { data } = await axios.get<LeadEvent[]>(url);
      console.log('[pollEvents] received', data.length, 'events');
      if (data.length) {
        const sorted = [...data].sort((a, b) => a.id - b.id);
        const maxId = sorted[sorted.length - 1].id;
        setEvents(prev => [...sorted, ...prev]);
        setTotalEventsCount(prev => prev + data.length);
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

    Promise.all([loadLeads(), loadEvents()]).finally(() => setLoading(false));
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
    <Container sx={{ mt: 4, mb: 4 }}>
      <Typography variant="h4" sx={{ fontWeight: 500, mb: 2 }}>
        List of Events and Leads
      </Typography>
      <Box sx={{ mb: 2 }}>
        <Select
          value={selectedBusiness}
          onChange={e => setSelectedBusiness(e.target.value as string)}
          displayEmpty
          size="small"
        >
          <MenuItem value="">
            <em>All Businesses</em>
          </MenuItem>
          {businesses.map(b => (
            <MenuItem key={b.business_id} value={b.business_id}>
              {b.name}
              {b.location ? ` (${b.location})` : ''}
              {b.time_zone ? ` - ${b.time_zone}` : ''}
            </MenuItem>
          ))}
        </Select>
      </Box>

      {selectedBusiness && (() => {
        const biz = businesses.find(b => b.business_id === selectedBusiness);
        if (!biz) return null;
        return (
          <Box sx={{ mb: 2 }}>
            <BusinessInfoCard business={biz} />
          </Box>
        );
      })()}

      <Paper elevation={2} sx={{ borderRadius: 2, mb: 2 }}>
        <Tabs
          value={tabValue}
          onChange={(_, v) => setTabValue(v)}
          aria-label="Events & Leads Tabs"
          variant="fullWidth"
          textColor="primary"
          indicatorColor="primary"
        >
          <Tab
            icon={
              <Badge badgeContent={unreadLeadsCount} color="secondary" invisible={unreadLeadsCount === 0}>
                <PersonAddIcon />
              </Badge>
            }
            label={`Processed Leads (${totalLeadsCount}${unreadLeadsCount ? `, ${unreadLeadsCount} new` : ''})`}
            {...a11yProps(0)}
          />
          <Tab
            icon={
              <Badge badgeContent={unreadEventsCount} color="secondary" invisible={unreadEventsCount === 0}>
                <EventNoteIcon />
              </Badge>
            }
            label={`New Events (${totalEventsCount}${unreadEventsCount ? `, ${unreadEventsCount} new` : ''})`}
            {...a11yProps(1)}
          />
        </Tabs>
      </Paper>

      <TabPanel value={tabValue} index={0}>
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
  );
};

export default EventsPage;
