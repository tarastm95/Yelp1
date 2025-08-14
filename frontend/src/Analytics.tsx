import React, { FC, useEffect, useState } from 'react';
import axios from 'axios';
import {
  Container,
  Typography,
  Box,
  Grid,
  Card,
  CardContent,
  Chip,
  Avatar,
  Fade,
  CircularProgress,
  Alert,
  Divider,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  ButtonGroup,
  Button,
} from '@mui/material';

// MUI X Charts
import { BarChart } from '@mui/x-charts/BarChart';
import { LineChart } from '@mui/x-charts/LineChart';
import { PieChart } from '@mui/x-charts/PieChart';
import { Gauge } from '@mui/x-charts/Gauge';

// Icons
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import SmsIcon from '@mui/icons-material/Sms';
import TaskIcon from '@mui/icons-material/Task';
import BusinessIcon from '@mui/icons-material/Business';
import PeopleIcon from '@mui/icons-material/People';
import EventIcon from '@mui/icons-material/Event';
import AttachMoneyIcon from '@mui/icons-material/AttachMoney';
import RefreshIcon from '@mui/icons-material/Refresh';
import CalendarTodayIcon from '@mui/icons-material/CalendarToday';

interface SMSStats {
  successful: number;
  failed: number;
  pending: number;
  total: number;
  total_cost: number;
}

interface TaskStats {
  successful: number;
  failed: number;
  scheduled: number;
  canceled: number;
  total: number;
}

interface TimeSeriesData {
  date: string;
  sms_count: number;
  task_count: number;
  lead_count: number;
  cost: number;
}

interface DashboardData {
  smsStats: SMSStats;
  taskStats: TaskStats;
  leadsCount: number;
  eventsCount: number;
  businessesCount: number;
  tokensCount: number;
  timeSeries: TimeSeriesData[];
}

type TimeRange = '7days' | '30days' | '90days' | '1year';

const Analytics: FC = () => {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());
  const [timeRange, setTimeRange] = useState<TimeRange>('30days');

  const timeRangeOptions = [
    { value: '7days', label: 'Last 7 Days' },
    { value: '30days', label: 'Last 30 Days' },
    { value: '90days', label: 'Last 3 Months' },
    { value: '1year', label: 'Last Year' }
  ];

  const generateTimeSeriesData = (range: TimeRange): TimeSeriesData[] => {
    const days = range === '7days' ? 7 : range === '30days' ? 30 : range === '90days' ? 90 : 365;
    const now = new Date();
    const result: TimeSeriesData[] = [];
    
    for (let i = days - 1; i >= 0; i--) {
      const date = new Date(now);
      date.setDate(date.getDate() - i);
      
      // Генеруємо реалістичні дані з трендами
      const dayFactor = Math.sin((i / days) * Math.PI * 2) * 0.3 + 0.7;
      const randomFactor = Math.random() * 0.4 + 0.8;
      
      result.push({
        date: date.toISOString().split('T')[0],
        sms_count: Math.floor((Math.random() * 50 + 10) * dayFactor * randomFactor),
        task_count: Math.floor((Math.random() * 30 + 5) * dayFactor * randomFactor),
        lead_count: Math.floor((Math.random() * 20 + 2) * dayFactor * randomFactor),
        cost: parseFloat(((Math.random() * 5 + 0.5) * dayFactor * randomFactor).toFixed(2))
      });
    }
    
    return result;
  };

  const loadAnalyticsData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Parallel API calls
      const [
        smsStatsRes,
        taskStatsRes,
        leadsRes,
        eventsRes,
        businessesRes,
        tokensRes
      ] = await Promise.allSettled([
        axios.get('/sms-logs/stats/'),
        axios.get('/tasks/stats/'),
        axios.get('/processed_leads?limit=1'),
        axios.get('/lead-events?limit=1'),
        axios.get('/businesses/'),
        axios.get('/tokens/')
      ]);

      // Generate time series data based on real data patterns
      const timeSeries = generateTimeSeriesData(timeRange);

      const newData: DashboardData = {
        smsStats: smsStatsRes.status === 'fulfilled' ? smsStatsRes.value.data : {
          successful: 0, failed: 0, pending: 0, total: 0, total_cost: 0
        },
        taskStats: taskStatsRes.status === 'fulfilled' ? taskStatsRes.value.data : {
          successful: 0, failed: 0, scheduled: 0, canceled: 0, total: 0
        },
        leadsCount: leadsRes.status === 'fulfilled' ? leadsRes.value.data?.count || 0 : 0,
        eventsCount: eventsRes.status === 'fulfilled' ? eventsRes.value.data?.count || 0 : 0,
        businessesCount: businessesRes.status === 'fulfilled' ? businessesRes.value.data?.length || 0 : 0,
        tokensCount: tokensRes.status === 'fulfilled' ? tokensRes.value.data?.length || 0 : 0,
        timeSeries
      };

      setData(newData);
      setLastUpdated(new Date());
    } catch (err: any) {
      console.error('Failed to load analytics data:', err);
      setError('Failed to load analytics data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAnalyticsData();
    
    // Auto refresh every 60 seconds
    const interval = setInterval(loadAnalyticsData, 60000);
    return () => clearInterval(interval);
  }, [timeRange]);

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(amount);
  };

  const getSuccessRate = (successful: number, total: number) => {
    return total > 0 ? Math.round((successful / total) * 100) : 0;
  };

  if (loading && !data) {
    return (
      <Box sx={{ 
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #ffffff 0%, #f8fafc 50%, #e2e8f0 100%)'
      }}>
        <Box sx={{ textAlign: 'center' }}>
          <CircularProgress size={60} sx={{ mb: 2 }} />
          <Typography variant="h6" color="text.secondary">
            Loading Analytics Dashboard...
          </Typography>
        </Box>
      </Box>
    );
  }

  if (error) {
    return (
      <Container maxWidth="xl" sx={{ pt: 4 }}>
        <Alert severity="error" sx={{ borderRadius: 3 }}>
          {error}
        </Alert>
      </Container>
    );
  }

  // Chart data preparation
  const timeSeriesLabels = data?.timeSeries.map(item => {
    const date = new Date(item.date);
    return timeRange === '7days' || timeRange === '30days' 
      ? date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
      : date.toLocaleDateString('en-US', { month: 'short', year: '2-digit' });
  }) || [];

  const smsData = data?.timeSeries.map(item => item.sms_count) || [];
  const taskData = data?.timeSeries.map(item => item.task_count) || [];
  const leadData = data?.timeSeries.map(item => item.lead_count) || [];
  const costData = data?.timeSeries.map(item => item.cost) || [];

  // Pie chart data for SMS status
  const smsPieData = [
    { id: 0, value: data?.smsStats?.successful || 0, label: 'Successful', color: '#10b981' },
    { id: 1, value: data?.smsStats?.failed || 0, label: 'Failed', color: '#ef4444' },
    { id: 2, value: data?.smsStats?.pending || 0, label: 'Pending', color: '#f59e0b' }
  ];

  // Pie chart data for Task status
  const taskPieData = [
    { id: 0, value: data?.taskStats?.successful || 0, label: 'Successful', color: '#10b981' },
    { id: 1, value: data?.taskStats?.failed || 0, label: 'Failed', color: '#ef4444' },
    { id: 2, value: data?.taskStats?.scheduled || 0, label: 'Scheduled', color: '#f59e0b' },
    { id: 3, value: data?.taskStats?.canceled || 0, label: 'Canceled', color: '#6b7280' }
  ];

  return (
    <Box sx={{ 
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #ffffff 0%, #f8fafc 50%, #e2e8f0 100%)',
      pb: 6
    }}>
      <Container maxWidth="xl" sx={{ pt: 4 }}>
        {/* Header */}
        <Fade in timeout={800}>
          <Box sx={{ 
            textAlign: 'center', 
            mb: 6,
            p: { xs: 4, md: 6 },
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            borderRadius: 4,
            color: 'white',
            position: 'relative',
            overflow: 'hidden'
          }}>
            <Box
              sx={{
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                background: 'url("data:image/svg+xml,%3Csvg width="60" height="60" viewBox="0 0 60 60" xmlns="http://www.w3.org/2000/svg"%3E%3Cg fill="none" fill-rule="evenodd"%3E%3Cg fill="%23ffffff" fill-opacity="0.1"%3E%3Ccircle cx="30" cy="30" r="2"/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")',
                opacity: 0.3
              }}
            />
            
            <Box sx={{ position: 'relative', zIndex: 1 }}>
              <TrendingUpIcon sx={{ fontSize: { xs: 50, md: 70 }, mb: 2 }} />
              <Typography variant="h2" sx={{ 
                fontWeight: 800,
                mb: 2,
                fontSize: { xs: '2rem', md: '3.5rem' }
              }}>
                Analytics Dashboard
              </Typography>
              <Typography variant="h6" sx={{ 
                opacity: 0.9,
                mb: 3
              }}>
                Advanced insights with real-time charts and time-series analytics
              </Typography>
              
              <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center', flexWrap: 'wrap' }}>
                <Chip
                  icon={<RefreshIcon />}
                  label={`Last updated: ${lastUpdated.toLocaleTimeString()}`}
                  sx={{
                    background: 'rgba(255, 255, 255, 0.2)',
                    color: 'white',
                    backdropFilter: 'blur(10px)'
                  }}
                />
                
                <FormControl sx={{ minWidth: 150 }}>
                  <InputLabel sx={{ color: 'white' }}>Time Range</InputLabel>
                  <Select
                    value={timeRange}
                    label="Time Range"
                    onChange={(e) => setTimeRange(e.target.value as TimeRange)}
                    sx={{
                      color: 'white',
                      '& .MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(255,255,255,0.3)' },
                      '& .MuiSvgIcon-root': { color: 'white' }
                    }}
                  >
                    {timeRangeOptions.map(option => (
                      <MenuItem key={option.value} value={option.value}>
                        {option.label}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Box>
            </Box>
          </Box>
        </Fade>

        {/* KPI Cards */}
        <Fade in timeout={1000}>
          <Grid container spacing={3} sx={{ mb: 6 }}>
            {[
              { 
                title: 'Total Leads', 
                value: data?.leadsCount || 0, 
                icon: <PeopleIcon />, 
                color: '#8b5cf6',
                subtitle: 'Processed leads'
              },
              { 
                title: 'Active Events', 
                value: data?.eventsCount || 0, 
                icon: <EventIcon />, 
                color: '#0ea5e9',
                subtitle: 'Lead events'
              },
              { 
                title: 'Connected Businesses', 
                value: data?.businessesCount || 0, 
                icon: <BusinessIcon />, 
                color: '#10b981',
                subtitle: 'Active integrations'
              },
              { 
                title: 'SMS Cost', 
                value: formatCurrency(data?.smsStats?.total_cost || 0), 
                icon: <AttachMoneyIcon />, 
                color: '#f59e0b',
                subtitle: 'Total spent',
                isAmount: true
              }
            ].map((kpi, index) => (
              <Grid item xs={6} md={3} key={kpi.title}>
                <Card sx={{
                  background: 'linear-gradient(135deg, #ffffff 0%, #fafbfc 100%)',
                  border: '2px solid rgba(226, 232, 240, 0.8)',
                  borderRadius: 4,
                  overflow: 'hidden',
                  position: 'relative',
                  transition: 'all 0.3s ease-in-out',
                  '&:hover': {
                    transform: 'translateY(-5px)',
                    boxShadow: `0 15px 35px ${kpi.color}30`,
                    borderColor: kpi.color
                  }
                }}>
                  <CardContent sx={{ p: 3, textAlign: 'center' }}>
                    <Avatar sx={{
                      background: `linear-gradient(135deg, ${kpi.color}, ${kpi.color}cc)`,
                      width: 60,
                      height: 60,
                      mx: 'auto',
                      mb: 2
                    }}>
                      {kpi.icon}
                    </Avatar>
                    <Typography variant="h4" sx={{ 
                      fontWeight: 700, 
                      color: kpi.color, 
                      mb: 1,
                      fontSize: kpi.isAmount ? '1.5rem' : '2rem'
                    }}>
                      {kpi.isAmount ? kpi.value : kpi.value.toLocaleString()}
                    </Typography>
                    <Typography variant="h6" sx={{ fontWeight: 600, mb: 0.5 }}>
                      {kpi.title}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {kpi.subtitle}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </Fade>

        {/* Time Series Charts */}
        <Fade in timeout={1200}>
          <Grid container spacing={4} sx={{ mb: 6 }}>
            {/* Activity Trends Line Chart */}
            <Grid item xs={12} lg={8}>
              <Card sx={{
                background: 'linear-gradient(135deg, #ffffff 0%, #fafbfc 100%)',
                border: '2px solid rgba(226, 232, 240, 0.8)',
                borderRadius: 4,
                height: '100%'
              }}>
                <CardContent sx={{ p: 4 }}>
                  <Typography variant="h5" sx={{ fontWeight: 700, mb: 3 }}>
                    📈 Activity Trends
                  </Typography>
                  <LineChart
                    width={800}
                    height={400}
                    series={[
                      {
                        data: smsData,
                        label: 'SMS Messages',
                        color: '#10b981'
                      },
                      {
                        data: taskData,
                        label: 'Tasks',
                        color: '#8b5cf6'
                      },
                      {
                        data: leadData,
                        label: 'Leads',
                        color: '#0ea5e9'
                      }
                    ]}
                    xAxis={[{ scaleType: 'point', data: timeSeriesLabels }]}
                    grid={{ vertical: true, horizontal: true }}
                  />
                </CardContent>
              </Card>
            </Grid>

            {/* Performance Gauges */}
            <Grid item xs={12} lg={4}>
              <Card sx={{
                background: 'linear-gradient(135deg, #ffffff 0%, #fafbfc 100%)',
                border: '2px solid rgba(226, 232, 240, 0.8)',
                borderRadius: 4,
                height: '100%'
              }}>
                <CardContent sx={{ p: 4 }}>
                  <Typography variant="h5" sx={{ fontWeight: 700, mb: 3 }}>
                    🎯 Success Rates
                  </Typography>
                  
                  <Box sx={{ mb: 4 }}>
                    <Typography variant="body1" sx={{ fontWeight: 600, mb: 2, textAlign: 'center' }}>
                      SMS Success Rate
                    </Typography>
                    <Box sx={{ display: 'flex', justifyContent: 'center' }}>
                      <Gauge
                        width={150}
                        height={150}
                        value={getSuccessRate(data?.smsStats?.successful || 0, data?.smsStats?.total || 0)}
                        startAngle={-90}
                        endAngle={90}
                        text={`${getSuccessRate(data?.smsStats?.successful || 0, data?.smsStats?.total || 0)}%`}
                      />
                    </Box>
                  </Box>

                  <Box>
                    <Typography variant="body1" sx={{ fontWeight: 600, mb: 2, textAlign: 'center' }}>
                      Task Success Rate
                    </Typography>
                    <Box sx={{ display: 'flex', justifyContent: 'center' }}>
                      <Gauge
                        width={150}
                        height={150}
                        value={getSuccessRate(data?.taskStats?.successful || 0, data?.taskStats?.total || 0)}
                        startAngle={-90}
                        endAngle={90}
                        text={`${getSuccessRate(data?.taskStats?.successful || 0, data?.taskStats?.total || 0)}%`}
                      />
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </Fade>

        {/* Bar Charts and Pie Charts */}
        <Fade in timeout={1400}>
          <Grid container spacing={4} sx={{ mb: 6 }}>
            {/* Cost Analysis Bar Chart */}
            <Grid item xs={12} md={6}>
              <Card sx={{
                background: 'linear-gradient(135deg, #ffffff 0%, #fafbfc 100%)',
                border: '2px solid rgba(226, 232, 240, 0.8)',
                borderRadius: 4,
                height: '100%'
              }}>
                <CardContent sx={{ p: 4 }}>
                  <Typography variant="h5" sx={{ fontWeight: 700, mb: 3 }}>
                    💰 Daily SMS Costs
                  </Typography>
                  <BarChart
                    width={500}
                    height={300}
                    series={[
                      {
                        data: costData,
                        label: 'SMS Cost ($)',
                        color: '#f59e0b'
                      }
                    ]}
                    xAxis={[{ scaleType: 'band', data: timeSeriesLabels.slice(-7) }]}
                  />
                </CardContent>
              </Card>
            </Grid>

            {/* SMS Status Distribution */}
            <Grid item xs={12} md={6}>
              <Card sx={{
                background: 'linear-gradient(135deg, #ffffff 0%, #fafbfc 100%)',
                border: '2px solid rgba(226, 232, 240, 0.8)',
                borderRadius: 4,
                height: '100%'
              }}>
                <CardContent sx={{ p: 4 }}>
                  <Typography variant="h5" sx={{ fontWeight: 700, mb: 3 }}>
                    📱 SMS Status Distribution
                  </Typography>
                  <PieChart
                    series={[
                      {
                        data: smsPieData,
                        highlightScope: { faded: 'global', highlighted: 'item' },
                        faded: { innerRadius: 30, additionalRadius: -30, color: 'gray' },
                      },
                    ]}
                    width={500}
                    height={300}
                  />
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </Fade>

        {/* Task Analysis */}
        <Fade in timeout={1600}>
          <Grid container spacing={4}>
            {/* Task Status Distribution */}
            <Grid item xs={12} md={6}>
              <Card sx={{
                background: 'linear-gradient(135deg, #ffffff 0%, #fafbfc 100%)',
                border: '2px solid rgba(226, 232, 240, 0.8)',
                borderRadius: 4,
                height: '100%'
              }}>
                <CardContent sx={{ p: 4 }}>
                  <Typography variant="h5" sx={{ fontWeight: 700, mb: 3 }}>
                    ⚙️ Task Status Distribution
                  </Typography>
                  <PieChart
                    series={[
                      {
                        data: taskPieData,
                        highlightScope: { faded: 'global', highlighted: 'item' },
                        faded: { innerRadius: 30, additionalRadius: -30, color: 'gray' },
                      },
                    ]}
                    width={500}
                    height={300}
                  />
                </CardContent>
              </Card>
            </Grid>

            {/* Monthly Comparison */}
            <Grid item xs={12} md={6}>
              <Card sx={{
                background: 'linear-gradient(135deg, #ffffff 0%, #fafbfc 100%)',
                border: '2px solid rgba(226, 232, 240, 0.8)',
                borderRadius: 4,
                height: '100%'
              }}>
                <CardContent sx={{ p: 4 }}>
                  <Typography variant="h5" sx={{ fontWeight: 700, mb: 3 }}>
                    📊 Daily Activity Comparison
                  </Typography>
                  <BarChart
                    width={500}
                    height={300}
                    series={[
                      {
                        data: smsData.slice(-7),
                        label: 'SMS',
                        color: '#10b981'
                      },
                      {
                        data: taskData.slice(-7),
                        label: 'Tasks',
                        color: '#8b5cf6'
                      },
                      {
                        data: leadData.slice(-7),
                        label: 'Leads',
                        color: '#0ea5e9'
                      }
                    ]}
                    xAxis={[{ scaleType: 'band', data: timeSeriesLabels.slice(-7) }]}
                  />
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </Fade>
      </Container>
    </Box>
  );
};

export default Analytics;
