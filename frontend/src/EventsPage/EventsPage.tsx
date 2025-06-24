import React, { FC, useState, useEffect, useRef } from 'react';
import axios from 'axios';
import {
  EventItem,
  LeadDetail as LeadDetailType,
  ProcessedLead,
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

  // IDs of viewed leads (для бейджа "new")
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

  // Загальна кількість лідів/івентів (для бейджів)
  const [totalLeadsCount, setTotalLeadsCount] = useState(0);
  const [totalEventsCount, setTotalEventsCount] = useState(0);

  // Стани для лідів та їхніх деталей
  const [leads, setLeads] = useState<ProcessedLead[]>([]);
  const [leadDetails, setLeadDetails] = useState<Record<string, Partial<LeadDetailType>>>({});
  const [leadsNextUrl, setLeadsNextUrl] = useState<string | null>(null);

  // Події
  const [events, setEvents] = useState<EventItem[]>([]);
  const [eventsNextUrl, setEventsNextUrl] = useState<string | null>(null);
  const lastEventIdRef = useRef<number | null>(null);

  // UI стани
  const [loading, setLoading] = useState(true);
  const [loadingMoreLeads, setLoadingMoreLeads] = useState(false);
  const [loadingMoreEvents, setLoadingMoreEvents] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tabValue, setTabValue] = useState(0);

  // Кількість непрочитаних лідів серед відфільтрованих
  const filteredLeads = selectedBusiness
    ? leads.filter(l => l.business_id === selectedBusiness)
    : leads;
  const loadedLeadIds = new Set(leads.map(l => l.lead_id));
  const viewedLoadedIdsCount = Array.from(viewedLeads).filter(id =>
    loadedLeadIds.has(id)
  ).length;
  const unreadLeadsCount = Math.max(0, totalLeadsCount - viewedLoadedIdsCount);


  // Завантажити сторінку лідів та їх деталі
  const loadLeads = async (url = 'http://localhost:8000/api/processed_leads/') => {
    try {
      const { data } = await axios.get<PaginatedResponse<ProcessedLead>>(url);
      setTotalLeadsCount(data.count);
      setLeads(prev => [...prev, ...data.results]);
      setLeadsNextUrl(data.next);

      const detailsArr = await Promise.all(
        data.results.map(l =>
          axios
            .get<Partial<LeadDetailType>>(
              `http://localhost:8000/api/lead-details/${encodeURIComponent(l.lead_id)}/`
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
      setError(`Не вдалося завантажити ліди: ${err.message}`);
    }
  };

  // Завантажити сторінку подій
  const loadEvents = async (url = 'http://localhost:8000/api/events/') => {
    try {
      const { data } = await axios.get<PaginatedResponse<EventItem>>(url);
      setTotalEventsCount(data.count);
      setEvents(prev => [...prev, ...data.results]);
      setEventsNextUrl(data.next);
      if (data.results.length) {
        const maxId = Math.max(...data.results.map(e => e.id));
        lastEventIdRef.current = Math.max(lastEventIdRef.current || 0, maxId);
      }
    } catch {
      setError('Помилка завантаження подій');
    }
  };

  // Підтягнути нові події після останньої
  const pollEvents = async () => {
    if (lastEventIdRef.current == null) return;
    try {
      const { data } = await axios.get<EventItem[]>(
        `http://localhost:8000/api/events?after_id=${lastEventIdRef.current}`
      );
      if (data.length) {
        const sorted = [...data].sort((a, b) => a.id - b.id);
        const maxId = sorted[sorted.length - 1].id;
        setEvents(prev => [...sorted, ...prev]);
        setTotalEventsCount(prev => prev + data.length);
        lastEventIdRef.current = Math.max(lastEventIdRef.current || 0, maxId);
      }
    } catch {
      /* ignore */
    }
  };

  // На старті підвантажуємо перші сторінки
  const initializedRef = useRef(false);
  useEffect(() => {
    if (initializedRef.current) {
      return;
    }
    initializedRef.current = true;

    Promise.all([loadLeads(), loadEvents()]).finally(() => setLoading(false));
    const timer = setInterval(() => {
      pollEvents();
    }, POLL_INTERVAL);
    return () => clearInterval(timer);
  }, []);

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

  const filteredEvents = selectedBusiness
    ? events.filter(e => {
        const leadId = e.payload?.data?.updates?.[0]?.lead_id;
        const biz = leadDetails[leadId]?.business_id;
        return biz === selectedBusiness;
      })
    : events;

  const newEvents = filteredEvents
    .filter(e => e.payload?.data?.updates?.[0]?.event_type === 'NEW_EVENT')
    .sort((a, b) => b.id - a.id);
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
