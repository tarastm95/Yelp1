import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Paper,
  LinearProgress,
  Chip,
  Button,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Alert,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Stack,
  Divider,
  TextField,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
  IconButton,
  Tooltip,
  CircularProgress,
  Badge,
  Avatar,
} from '@mui/material';
import {
  HealthAndSafety as HealthIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
  CheckCircle as SuccessIcon,
  Speed as MetricsIcon,
  Build as DiagnosticIcon,
  Refresh as RefreshIcon,
  ExpandMore as ExpandMoreIcon,
  PlayArrow as ActionIcon,
  Timeline as TimelineIcon,
  Storage as DatabaseIcon,
  Api as ApiIcon,
  Memory as RedisIcon,
  Schedule as TaskIcon,
  TrendingUp as TrendingUpIcon,
  BugReport as BugIcon,
  Security as SecurityIcon,
} from '@mui/icons-material';
import axios from 'axios';

interface SystemHealth {
  health_score: number;
  status: string;
  errors: {
    critical_last_hour: number;
    high_last_hour: number;
    total_unresolved: number;
  };
  tasks: {
    total_last_hour: number;
    failed_last_hour: number;
    success_rate: number;
  };
  metrics: Record<string, any>;
  last_updated: string;
}

interface SystemError {
  error_id: string;
  timestamp: string;
  error_type: string;
  severity: string;
  component: string;
  error_message: string;
  lead_id?: string;
  business_id?: string;
  resolved: boolean;
  traceback?: string;
}

interface LeadDiagnostic {
  lead_id: string;
  health_status: string;
  issues: string[];
  analysis: {
    total_tasks: number;
    completed_tasks: number;
    failed_tasks: number;
    total_errors: number;
  };
  success_rate: number;
  timing_issues: any[];
  recommendations: any[];
}

const SystemDiagnostics: React.FC = () => {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [errors, setErrors] = useState<SystemError[]>([]);
  const [leadDiagnostic, setLeadDiagnostic] = useState<LeadDiagnostic | null>(null);
  const [leadId, setLeadId] = useState('');
  const [loading, setLoading] = useState(false);
  const [errorLoading, setErrorLoading] = useState(false);
  const [diagnosticLoading, setDiagnosticLoading] = useState(false);
  
  // Filters
  const [errorSeverity, setErrorSeverity] = useState('ALL');
  const [errorType, setErrorType] = useState('ALL');
  const [showResolved, setShowResolved] = useState(false);

  const loadSystemHealth = async () => {
    setLoading(true);
    try {
      const response = await axios.get<{health: SystemHealth, critical_errors: SystemError[]}>('/system/health/');
      setHealth(response.data.health);
      
      // Set critical errors from health response
      if (response.data.critical_errors) {
        setErrors(response.data.critical_errors);
      }
    } catch (err) {
      console.error('Failed to load system health:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadErrors = async () => {
    setErrorLoading(true);
    try {
      const params = new URLSearchParams();
      if (errorSeverity !== 'ALL') params.append('severity', errorSeverity);
      if (errorType !== 'ALL') params.append('type', errorType);
      params.append('resolved', showResolved.toString());
      params.append('limit', '20');

      const response = await axios.get<{errors: SystemError[]}>(`/system/errors/?${params.toString()}`);
      setErrors(response.data.errors);
    } catch (err) {
      console.error('Failed to load errors:', err);
    } finally {
      setErrorLoading(false);
    }
  };

  const loadLeadDiagnostic = async () => {
    if (!leadId.trim()) return;
    
    setDiagnosticLoading(true);
    try {
      const response = await axios.get<LeadDiagnostic>(`/leads/${leadId.trim()}/diagnostics/`);
      setLeadDiagnostic(response.data);
    } catch (err) {
      console.error('Failed to load lead diagnostic:', err);
      setLeadDiagnostic(null);
    } finally {
      setDiagnosticLoading(false);
    }
  };

  const executeAction = async (action: string, parameters: Record<string, any> = {}) => {
    try {
      const response = await axios.post('/system/actions/', {
        action,
        parameters
      });
      
      alert(`Action completed: ${response.data.result}`);
      loadSystemHealth(); // Refresh data
    } catch (err: any) {
      alert(`Action failed: ${err.response?.data?.error || 'Unknown error'}`);
    }
  };

  const resolveError = async (errorId: string, notes: string = '') => {
    try {
      await axios.post(`/system/errors/${errorId}/resolve/`, { notes });
      loadErrors(); // Refresh errors
    } catch (err) {
      console.error('Failed to resolve error:', err);
    }
  };

  useEffect(() => {
    loadSystemHealth();
    loadErrors();
    
    // Auto-refresh every 30 seconds
    const interval = setInterval(() => {
      loadSystemHealth();
    }, 30000);
    
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    loadErrors();
  }, [errorSeverity, errorType, showResolved]);

  const getHealthColor = (score: number) => {
    if (score >= 80) return '#4caf50';
    if (score >= 60) return '#ff9800';
    return '#f44336';
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'CRITICAL': return '#f44336';
      case 'HIGH': return '#ff5722';
      case 'MEDIUM': return '#ff9800';
      case 'LOW': return '#4caf50';
      default: return '#9e9e9e';
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" sx={{ mb: 3, display: 'flex', alignItems: 'center' }}>
        <DiagnosticIcon sx={{ mr: 2, fontSize: '2rem' }} />
        System Diagnostics & Error Tracking
      </Typography>

      {/* System Health Overview */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} md={4}>
          <Card elevation={3} sx={{ height: '100%' }}>
            <CardContent sx={{ textAlign: 'center' }}>
              <Avatar sx={{ 
                width: 80, 
                height: 80, 
                mx: 'auto', 
                mb: 2,
                bgcolor: health ? getHealthColor(health.health_score) : '#ccc'
              }}>
                <HealthIcon sx={{ fontSize: '2rem' }} />
              </Avatar>
              
              {loading ? (
                <CircularProgress />
              ) : health ? (
                <>
                  <Typography variant="h3" sx={{ color: getHealthColor(health.health_score), fontWeight: 'bold' }}>
                    {health.health_score}
                  </Typography>
                  <Typography variant="h6" color="text.secondary" gutterBottom>
                    Health Score
                  </Typography>
                  <Chip 
                    label={health.status}
                    sx={{ 
                      bgcolor: getHealthColor(health.health_score),
                      color: 'white',
                      fontWeight: 'bold'
                    }}
                  />
                </>
              ) : (
                <Typography color="error">Failed to load</Typography>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card elevation={3} sx={{ height: '100%' }}>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2, display: 'flex', alignItems: 'center' }}>
                <ErrorIcon sx={{ mr: 1 }} />
                Error Statistics
              </Typography>
              
              {health && (
                <Stack spacing={2}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Typography variant="body2">Critical (Last Hour)</Typography>
                    <Badge badgeContent={health.errors.critical_last_hour} color="error">
                      <Chip size="small" label={health.errors.critical_last_hour} />
                    </Badge>
                  </Box>
                  
                  <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Typography variant="body2">High Priority</Typography>
                    <Badge badgeContent={health.errors.high_last_hour} color="warning">
                      <Chip size="small" label={health.errors.high_last_hour} />
                    </Badge>
                  </Box>
                  
                  <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Typography variant="body2">Unresolved Total</Typography>
                    <Badge badgeContent={health.errors.total_unresolved} color="secondary">
                      <Chip size="small" label={health.errors.total_unresolved} />
                    </Badge>
                  </Box>
                </Stack>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card elevation={3} sx={{ height: '100%' }}>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2, display: 'flex', alignItems: 'center' }}>
                <TaskIcon sx={{ mr: 1 }} />
                Task Performance
              </Typography>
              
              {health && (
                <Stack spacing={2}>
                  <Box>
                    <Typography variant="body2" gutterBottom>Success Rate</Typography>
                    <LinearProgress 
                      variant="determinate" 
                      value={health.tasks.success_rate} 
                      sx={{ 
                        height: 8, 
                        borderRadius: 1,
                        bgcolor: '#e0e0e0',
                        '& .MuiLinearProgress-bar': {
                          bgcolor: health.tasks.success_rate > 95 ? '#4caf50' : 
                                  health.tasks.success_rate > 80 ? '#ff9800' : '#f44336'
                        }
                      }}
                    />
                    <Typography variant="h6" sx={{ mt: 1, fontWeight: 'bold' }}>
                      {health.tasks.success_rate}%
                    </Typography>
                  </Box>
                  
                  <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Typography variant="body2">Total (Last Hour)</Typography>
                    <Typography variant="body1" fontWeight="bold">
                      {health.tasks.total_last_hour}
                    </Typography>
                  </Box>
                  
                  <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Typography variant="body2">Failed (Last Hour)</Typography>
                    <Typography variant="body1" fontWeight="bold" color="error">
                      {health.tasks.failed_last_hour}
                    </Typography>
                  </Box>
                </Stack>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Quick Actions */}
      <Card elevation={3} sx={{ mb: 4 }}>
        <CardContent>
          <Typography variant="h6" sx={{ mb: 2, display: 'flex', alignItems: 'center' }}>
            <ActionIcon sx={{ mr: 1 }} />
            Quick Diagnostic Actions
          </Typography>
          
          <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
            <Button
              variant="contained"
              startIcon={<RefreshIcon />}
              onClick={() => executeAction('retry_failed_tasks', { hours: 1 })}
              color="warning"
            >
              Retry Failed Tasks (1h)
            </Button>
            
            <Button
              variant="contained"
              startIcon={<ApiIcon />}
              onClick={() => executeAction('test_yelp_api', { business_id: 'S4VbIKUr_s7FecEH72n_cA' })}
              color="info"
            >
              Test Yelp API
            </Button>
            
            <Button
              variant="outlined"
              startIcon={<BugIcon />}
              onClick={() => executeAction('clear_old_errors', { days: 7 })}
            >
              Clear Old Errors
            </Button>
            
            <Button
              variant="outlined"
              startIcon={<RefreshIcon />}
              onClick={() => {
                loadSystemHealth();
                loadErrors();
              }}
            >
              Refresh Dashboard
            </Button>
          </Stack>
        </CardContent>
      </Card>

      {/* Lead-Specific Diagnostics */}
      <Card elevation={3} sx={{ mb: 4 }}>
        <CardContent>
          <Typography variant="h6" sx={{ mb: 2, display: 'flex', alignItems: 'center' }}>
            <TimelineIcon sx={{ mr: 1 }} />
            Lead-Specific Diagnostics
          </Typography>
          
          <Stack direction="row" spacing={2} sx={{ mb: 2 }}>
            <TextField
              label="Lead ID"
              value={leadId}
              onChange={(e) => setLeadId(e.target.value)}
              placeholder="e.g., L1TH_vjYAD3YG0Yh8-pPrQ"
              sx={{ flex: 1 }}
            />
            <Button
              variant="contained"
              onClick={loadLeadDiagnostic}
              disabled={!leadId.trim() || diagnosticLoading}
              startIcon={diagnosticLoading ? <CircularProgress size={20} /> : <DiagnosticIcon />}
            >
              Analyze Lead
            </Button>
          </Stack>
          
          {leadDiagnostic && (
            <Paper sx={{ p: 3, mt: 2 }}>
              <Stack spacing={2}>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <Typography variant="h6">
                    Lead: {leadDiagnostic.lead_id}
                  </Typography>
                  <Chip 
                    label={leadDiagnostic.health_status}
                    color={leadDiagnostic.health_status === 'HEALTHY' ? 'success' : 
                           leadDiagnostic.health_status === 'WARNING' ? 'warning' : 'error'}
                    icon={leadDiagnostic.health_status === 'HEALTHY' ? <SuccessIcon /> : 
                          leadDiagnostic.health_status === 'WARNING' ? <WarningIcon /> : <ErrorIcon />}
                  />
                </Box>
                
                <Grid container spacing={2}>
                  <Grid item xs={6} md={3}>
                    <Paper sx={{ p: 2, textAlign: 'center' }}>
                      <Typography variant="h4" color="primary">{leadDiagnostic.analysis.total_tasks}</Typography>
                      <Typography variant="body2">Total Tasks</Typography>
                    </Paper>
                  </Grid>
                  <Grid item xs={6} md={3}>
                    <Paper sx={{ p: 2, textAlign: 'center' }}>
                      <Typography variant="h4" color="success.main">{leadDiagnostic.analysis.completed_tasks}</Typography>
                      <Typography variant="body2">Completed</Typography>
                    </Paper>
                  </Grid>
                  <Grid item xs={6} md={3}>
                    <Paper sx={{ p: 2, textAlign: 'center' }}>
                      <Typography variant="h4" color="error.main">{leadDiagnostic.analysis.failed_tasks}</Typography>
                      <Typography variant="body2">Failed</Typography>
                    </Paper>
                  </Grid>
                  <Grid item xs={6} md={3}>
                    <Paper sx={{ p: 2, textAlign: 'center' }}>
                      <Typography variant="h4" color="info.main">{leadDiagnostic.success_rate}%</Typography>
                      <Typography variant="body2">Success Rate</Typography>
                    </Paper>
                  </Grid>
                </Grid>
                
                {leadDiagnostic.issues.length > 0 && (
                  <Alert severity="warning">
                    <Typography variant="subtitle2" gutterBottom>Issues Found:</Typography>
                    <ul style={{ margin: 0, paddingLeft: '20px' }}>
                      {leadDiagnostic.issues.map((issue, index) => (
                        <li key={index}>{issue}</li>
                      ))}
                    </ul>
                  </Alert>
                )}
                
                {leadDiagnostic.recommendations.length > 0 && (
                  <Accordion>
                    <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                      <Typography>Recommendations ({leadDiagnostic.recommendations.length})</Typography>
                    </AccordionSummary>
                    <AccordionDetails>
                      <Stack spacing={1}>
                        {leadDiagnostic.recommendations.map((rec, index) => (
                          <Alert 
                            key={index}
                            severity={rec.severity === 'CRITICAL' ? 'error' : 
                                     rec.severity === 'HIGH' ? 'warning' : 'info'}
                          >
                            <Typography variant="subtitle2">{rec.title}</Typography>
                            <Typography variant="body2">{rec.description}</Typography>
                            <Typography variant="caption" fontStyle="italic">{rec.action}</Typography>
                          </Alert>
                        ))}
                      </Stack>
                    </AccordionDetails>
                  </Accordion>
                )}
              </Stack>
            </Paper>
          )}
        </CardContent>
      </Card>

      {/* Error Logs */}
      <Card elevation={3}>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
            <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center' }}>
              <BugIcon sx={{ mr: 1 }} />
              Error Logs
            </Typography>
            
            <Stack direction="row" spacing={2}>
              <FormControl size="small" sx={{ minWidth: 120 }}>
                <InputLabel>Severity</InputLabel>
                <Select
                  value={errorSeverity}
                  onChange={(e) => setErrorSeverity(e.target.value)}
                  label="Severity"
                >
                  <MenuItem value="ALL">All</MenuItem>
                  <MenuItem value="CRITICAL">Critical</MenuItem>
                  <MenuItem value="HIGH">High</MenuItem>
                  <MenuItem value="MEDIUM">Medium</MenuItem>
                  <MenuItem value="LOW">Low</MenuItem>
                </Select>
              </FormControl>
              
              <FormControl size="small" sx={{ minWidth: 140 }}>
                <InputLabel>Error Type</InputLabel>
                <Select
                  value={errorType}
                  onChange={(e) => setErrorType(e.target.value)}
                  label="Error Type"
                >
                  <MenuItem value="ALL">All Types</MenuItem>
                  <MenuItem value="API_ERROR">API Error</MenuItem>
                  <MenuItem value="TASK_ERROR">Task Error</MenuItem>
                  <MenuItem value="TOKEN_ERROR">Token Error</MenuItem>
                  <MenuItem value="WEBHOOK_ERROR">Webhook Error</MenuItem>
                  <MenuItem value="DJANGO_ERROR">Django Error</MenuItem>
                </Select>
              </FormControl>
              
              <Button
                variant="outlined"
                size="small"
                onClick={() => setShowResolved(!showResolved)}
                color={showResolved ? 'primary' : 'inherit'}
              >
                {showResolved ? 'Hide' : 'Show'} Resolved
              </Button>
            </Stack>
          </Box>

          {errorLoading ? (
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <CircularProgress />
            </Box>
          ) : (
            <List>
              {errors.map((error, index) => (
                <React.Fragment key={error.error_id}>
                  <ListItem alignItems="flex-start">
                    <ListItemIcon>
                      <Avatar sx={{ bgcolor: getSeverityColor(error.severity), width: 40, height: 40 }}>
                        {error.severity === 'CRITICAL' ? <ErrorIcon /> : 
                         error.severity === 'HIGH' ? <WarningIcon /> : <BugIcon />}
                      </Avatar>
                    </ListItemIcon>
                    
                    <ListItemText
                      primary={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                          <Chip 
                            label={error.error_type} 
                            size="small"
                            sx={{ bgcolor: getSeverityColor(error.severity), color: 'white' }}
                          />
                          <Chip 
                            label={error.component} 
                            size="small" 
                            variant="outlined"
                          />
                          <Typography variant="body2" color="text.secondary">
                            {new Date(error.timestamp).toLocaleString('uk-UA')}
                          </Typography>
                          {error.resolved && (
                            <Chip label="Resolved" size="small" color="success" />
                          )}
                        </Box>
                      }
                      secondary={
                        <Box>
                          <Typography variant="body1" sx={{ mb: 1 }}>
                            {error.error_message}
                          </Typography>
                          
                          {error.lead_id && (
                            <Typography variant="caption" display="block">
                              Lead ID: {error.lead_id}
                            </Typography>
                          )}
                          
                          {error.traceback && (
                            <Accordion sx={{ mt: 1 }}>
                              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                                <Typography variant="body2">
                                  View Traceback
                                </Typography>
                              </AccordionSummary>
                              <AccordionDetails>
                                <Paper sx={{ p: 2, bgcolor: '#f5f5f5' }}>
                                  <pre style={{ 
                                    fontSize: '11px', 
                                    margin: 0, 
                                    whiteSpace: 'pre-wrap',
                                    wordBreak: 'break-word'
                                  }}>
                                    {error.traceback}
                                  </pre>
                                </Paper>
                              </AccordionDetails>
                            </Accordion>
                          )}
                          
                          {!error.resolved && (
                            <Button
                              size="small"
                              variant="outlined"
                              color="success"
                              sx={{ mt: 1 }}
                              onClick={() => resolveError(error.error_id, 'Manually resolved via dashboard')}
                            >
                              Mark as Resolved
                            </Button>
                          )}
                        </Box>
                      }
                    />
                  </ListItem>
                  
                  {index < errors.length - 1 && <Divider />}
                </React.Fragment>
              ))}
              
              {errors.length === 0 && (
                <Box sx={{ textAlign: 'center', py: 4 }}>
                  <SuccessIcon sx={{ fontSize: 64, color: 'success.main', mb: 2 }} />
                  <Typography variant="h6" color="success.main">
                    No errors found!
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    System is running smoothly
                  </Typography>
                </Box>
              )}
            </List>
          )}
        </CardContent>
      </Card>
    </Box>
  );
};

export default SystemDiagnostics;
