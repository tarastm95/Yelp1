import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  Stack,
  Chip,
  Paper,
  Divider,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  CircularProgress,
  Alert,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Grid,
  Avatar,
  List,
  ListItem,
  ListItemAvatar,
  ListItemText,
} from '@mui/material';
import {
  Search as SearchIcon,
  Timeline as TimelineIcon,
  ExpandMore as ExpandMoreIcon,
  Webhook as WebhookIcon,
  Schedule as PlanningIcon,
  Send as ExecutionIcon,
  Analytics as AnalysisIcon,
  Error as ErrorIcon,
  Computer as BackendIcon,
  Storage as WorkerIcon,
  Timer as SchedulerIcon,
  Api as ApiIcon,
} from '@mui/icons-material';
import axios from 'axios';

interface LeadActivityLog {
  id: number;
  timestamp: string;
  activity_type: string;
  component: string;
  event_name: string;
  message: string;
  metadata: Record<string, any>;
  business_id?: string;
  task_id?: string;
}

interface LeadInfo {
  name?: string;
  jobs?: string;
  created_at?: string;
  phone_number?: string;
}

interface LogsResponse {
  lead_id: string;
  lead_info?: LeadInfo;
  total_returned: number;
  summary: {
    total_logs: number;
    by_type: Record<string, number>;
  };
  logs: LeadActivityLog[];
}

const LeadLogs: React.FC = () => {
  const [leadId, setLeadId] = useState('');
  const [logs, setLogs] = useState<LeadActivityLog[]>([]);
  const [leadInfo, setLeadInfo] = useState<LeadInfo | null>(null);
  const [summary, setSummary] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Filters
  const [filterType, setFilterType] = useState('ALL');
  const [filterComponent, setFilterComponent] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  
  const activityTypeColors = {
    WEBHOOK: '#1976d2',
    PLANNING: '#388e3c', 
    EXECUTION: '#f57c00',
    ANALYSIS: '#7b1fa2',
    ERROR: '#d32f2f',
  };
  
  const componentIcons = {
    BACKEND: <BackendIcon />,
    WORKER: <WorkerIcon />,
    SCHEDULER: <SchedulerIcon />,
    API: <ApiIcon />,
  };

  const fetchLogs = async () => {
    if (!leadId.trim()) {
      setError('Please enter a Lead ID');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams();
      if (filterType !== 'ALL') params.append('type', filterType);
      if (filterComponent !== 'ALL') params.append('component', filterComponent);
      if (searchQuery) params.append('search', searchQuery);
      params.append('limit', '200');

      const response = await axios.get<LogsResponse>(
        `/leads/${leadId.trim()}/logs/?${params.toString()}`
      );

      setLogs(response.data.logs);
      setLeadInfo(response.data.lead_info || null);
      setSummary(response.data.summary);
      
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch logs');
      setLogs([]);
      setLeadInfo(null);
      setSummary(null);
    } finally {
      setLoading(false);
    }
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString('uk-UA', {
      day: '2-digit',
      month: '2-digit', 
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  const getActivityIcon = (type: string) => {
    switch (type) {
      case 'WEBHOOK': return <WebhookIcon />;
      case 'PLANNING': return <PlanningIcon />;
      case 'EXECUTION': return <ExecutionIcon />;
      case 'ANALYSIS': return <AnalysisIcon />;
      case 'ERROR': return <ErrorIcon />;
      default: return <TimelineIcon />;
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" sx={{ mb: 3, display: 'flex', alignItems: 'center' }}>
        <TimelineIcon sx={{ mr: 2, fontSize: '2rem' }} />
        Lead Activity Logs
      </Typography>

      {/* Search Section */}
      <Card elevation={2} sx={{ mb: 3 }}>
        <CardContent>
          <Stack spacing={3}>
            <TextField
              label="Lead ID"
              value={leadId}
              onChange={(e) => setLeadId(e.target.value)}
              placeholder="e.g., Z5Nl7jsRPJFQPSl8K9JDnQ"
              fullWidth
              variant="outlined"
            />
            
            <Grid container spacing={2}>
              <Grid item xs={12} md={4}>
                <FormControl fullWidth>
                  <InputLabel>Activity Type</InputLabel>
                  <Select
                    value={filterType}
                    onChange={(e) => setFilterType(e.target.value)}
                    label="Activity Type"
                  >
                    <MenuItem value="ALL">All Types</MenuItem>
                    <MenuItem value="WEBHOOK">Webhook Processing</MenuItem>
                    <MenuItem value="PLANNING">Follow-up Planning</MenuItem>
                    <MenuItem value="EXECUTION">Message Execution</MenuItem>
                    <MenuItem value="ANALYSIS">Event Analysis</MenuItem>
                    <MenuItem value="ERROR">Errors</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              
              <Grid item xs={12} md={4}>
                <FormControl fullWidth>
                  <InputLabel>Component</InputLabel>
                  <Select
                    value={filterComponent}
                    onChange={(e) => setFilterComponent(e.target.value)}
                    label="Component"
                  >
                    <MenuItem value="ALL">All Components</MenuItem>
                    <MenuItem value="BACKEND">Django Backend</MenuItem>
                    <MenuItem value="WORKER">RQ Worker</MenuItem>
                    <MenuItem value="SCHEDULER">RQ Scheduler</MenuItem>
                    <MenuItem value="API">API Requests</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              
              <Grid item xs={12} md={4}>
                <TextField
                  label="Search in messages"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search text..."
                  fullWidth
                />
              </Grid>
            </Grid>
            
            <Button
              variant="contained"
              onClick={fetchLogs}
              disabled={loading || !leadId.trim()}
              startIcon={loading ? <CircularProgress size={20} /> : <SearchIcon />}
              size="large"
            >
              {loading ? 'Searching...' : 'Search Logs'}
            </Button>
          </Stack>
        </CardContent>
      </Card>

      {/* Lead Info Section */}
      {leadInfo && (
        <Card elevation={2} sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 2 }}>Lead Information</Typography>
            <Grid container spacing={2}>
              <Grid item xs={12} md={3}>
                <Typography variant="body2" color="text.secondary">Name</Typography>
                <Typography variant="body1">{leadInfo.name || 'N/A'}</Typography>
              </Grid>
              <Grid item xs={12} md={3}>
                <Typography variant="body2" color="text.secondary">Project</Typography>
                <Typography variant="body1">{leadInfo.jobs || 'N/A'}</Typography>
              </Grid>
              <Grid item xs={12} md={3}>
                <Typography variant="body2" color="text.secondary">Phone</Typography>
                <Typography variant="body1">{leadInfo.phone_number || 'No phone'}</Typography>
              </Grid>
              <Grid item xs={12} md={3}>
                <Typography variant="body2" color="text.secondary">Created</Typography>
                <Typography variant="body1">
                  {leadInfo.created_at ? formatTimestamp(leadInfo.created_at) : 'N/A'}
                </Typography>
              </Grid>
            </Grid>
          </CardContent>
        </Card>
      )}

      {/* Summary Section */}
      {summary && (
        <Card elevation={2} sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 2 }}>Activity Summary</Typography>
            <Grid container spacing={2}>
              <Grid item xs={12} md={2}>
                <Paper sx={{ p: 2, textAlign: 'center' }}>
                  <Typography variant="h4" color="primary">{summary.total_logs}</Typography>
                  <Typography variant="body2">Total Logs</Typography>
                </Paper>
              </Grid>
              {Object.entries(summary.by_type || {}).map(([type, count]) => (
                <Grid item xs={12} md={2} key={type}>
                  <Paper sx={{ p: 2, textAlign: 'center' }}>
                    <Typography variant="h4" sx={{ color: activityTypeColors[type as keyof typeof activityTypeColors] }}>
                      {count as number}
                    </Typography>
                    <Typography variant="body2">{type}</Typography>
                  </Paper>
                </Grid>
              ))}
            </Grid>
          </CardContent>
        </Card>
      )}

      {/* Error Display */}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {/* Logs Display */}
      {logs.length > 0 && (
        <Card elevation={2}>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 2 }}>
              Activity Timeline ({logs.length} entries)
            </Typography>
            
            <List>
              {logs.map((log, index) => (
                <React.Fragment key={log.id}>
                  <ListItem alignItems="flex-start" sx={{ py: 2 }}>
                    <ListItemAvatar>
                      <Avatar sx={{ 
                        bgcolor: activityTypeColors[log.activity_type as keyof typeof activityTypeColors],
                        width: 48,
                        height: 48 
                      }}>
                        {getActivityIcon(log.activity_type)}
                      </Avatar>
                    </ListItemAvatar>
                    
                    <ListItemText
                      primary={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                          <Chip 
                            label={log.activity_type} 
                            size="small" 
                            sx={{ 
                              bgcolor: activityTypeColors[log.activity_type as keyof typeof activityTypeColors],
                              color: 'white'
                            }}
                          />
                          <Chip 
                            label={log.component} 
                            size="small" 
                            variant="outlined"
                            icon={componentIcons[log.component as keyof typeof componentIcons]}
                          />
                          <Typography variant="body2" color="text.secondary">
                            {formatTimestamp(log.timestamp)}
                          </Typography>
                        </Box>
                      }
                      secondary={
                        <Box>
                          <Typography variant="body1" sx={{ mb: 1 }}>
                            <strong>{log.event_name}:</strong> {log.message}
                          </Typography>
                          
                          {Object.keys(log.metadata || {}).length > 0 && (
                            <Accordion>
                              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                                <Typography variant="body2">
                                  View Details ({Object.keys(log.metadata).length} fields)
                                </Typography>
                              </AccordionSummary>
                              <AccordionDetails>
                                <Paper sx={{ p: 2, bgcolor: '#f5f5f5' }}>
                                  <pre style={{ 
                                    fontSize: '12px', 
                                    margin: 0, 
                                    wordWrap: 'break-word',
                                    whiteSpace: 'pre-wrap'
                                  }}>
                                    {JSON.stringify(log.metadata, null, 2)}
                                  </pre>
                                </Paper>
                              </AccordionDetails>
                            </Accordion>
                          )}
                          
                          {log.task_id && (
                            <Typography variant="caption" display="block" sx={{ mt: 1 }}>
                              Task ID: {log.task_id}
                            </Typography>
                          )}
                        </Box>
                      }
                    />
                  </ListItem>
                  
                  {index < logs.length - 1 && <Divider />}
                </React.Fragment>
              ))}
            </List>
          </CardContent>
        </Card>
      )}

      {/* Empty State */}
      {!loading && logs.length === 0 && leadId && !error && (
        <Card elevation={2}>
          <CardContent sx={{ textAlign: 'center', py: 6 }}>
            <TimelineIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
            <Typography variant="h6" color="text.secondary">
              No logs found for this Lead ID
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Try adjusting your filters or check if the Lead ID is correct
            </Typography>
          </CardContent>
        </Card>
      )}
    </Box>
  );
};

export default LeadLogs;
