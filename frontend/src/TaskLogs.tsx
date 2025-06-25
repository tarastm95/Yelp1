import React, { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import {
  Container,
  Box,
  Typography,
  Tabs,
  Tab,
  Table,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
  CircularProgress,
} from '@mui/material';

interface TaskLog {
  task_id: string;
  args: any[];
  eta: string | null;
  status: string;
  result?: string | null;
  business_id?: string | null;
}

interface Business {
  business_id: string;
  name: string;
  time_zone?: string;
}

const TaskLogs: React.FC = () => {
  const [completedTasks, setCompletedTasks] = useState<TaskLog[]>([]);
  const [scheduledTasks, setScheduledTasks] = useState<TaskLog[]>([]);
  const [businesses, setBusinesses] = useState<Business[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<'completed' | 'scheduled'>('completed');

  useEffect(() => {
    axios
      .get<TaskLog[]>('/tasks/?status=success,failure')
      .then(res => setCompletedTasks(res.data))
      .catch(() => setCompletedTasks([]))
      .finally(() => setLoading(false));

    axios
      .get<TaskLog[]>('/tasks/?status=scheduled')
      .then(res => setScheduledTasks(res.data))
      .catch(() => setScheduledTasks([]));

    axios
      .get<Business[]>('/businesses/')
      .then(res => setBusinesses(res.data))
      .catch(() => setBusinesses([]));
  }, []);

  const tzMap = useMemo(() => {
    const map: Record<string, string> = {};
    businesses.forEach(b => {
      if (b.time_zone) map[b.business_id] = b.time_zone;
    });
    return map;
  }, [businesses]);

  const formatEta = (eta: string | null, bizId?: string | null) => {
    if (!eta) return '—';
    const date = new Date(eta);
    const tz = bizId ? tzMap[bizId] : undefined;
    return tz
      ? date.toLocaleString(undefined, { timeZone: tz })
      : date.toLocaleString();
  };

  const getLeadId = (args: any[] | undefined) => {
    if (!Array.isArray(args) || args.length === 0) return '';
    return String(args[0]);
  };

  const getMessage = (args: any[] | undefined) => {
    if (!Array.isArray(args) || args.length < 2) return '';
    return String(args[1]);
  };

  return (
    <Container sx={{ mt: 4 }}>
      <Typography variant="h4" gutterBottom>
        Celery Tasks
      </Typography>
      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 2 }}>
        <Tab label="Completed" value="completed" />
        <Tab label="Scheduled" value="scheduled" />
      </Tabs>
      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
          <CircularProgress />
        </Box>
      ) : tab === 'completed' ? (
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Lead ID</TableCell>
              <TableCell>Run Time</TableCell>
              <TableCell>Message</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Error</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {completedTasks.map(t => (
              <TableRow key={t.task_id}>
                <TableCell>{getLeadId(t.args)}</TableCell>
                <TableCell>{formatEta(t.eta, t.business_id)}</TableCell>
                <TableCell>{getMessage(t.args)}</TableCell>
                <TableCell>{t.status}</TableCell>
                <TableCell>{t.status === 'FAILURE' ? t.result || '' : ''}</TableCell>
              </TableRow>
            ))}
            {completedTasks.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} align="center">
                  No completed or failed tasks
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      ) : (
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Lead ID</TableCell>
              <TableCell>Run Time</TableCell>
              <TableCell>Message</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {scheduledTasks.map(t => (
              <TableRow key={t.task_id}>
                <TableCell>{getLeadId(t.args)}</TableCell>
                <TableCell>{formatEta(t.eta, t.business_id)}</TableCell>
                <TableCell>{getMessage(t.args)}</TableCell>
              </TableRow>
            ))}
            {scheduledTasks.length === 0 && (
              <TableRow>
                <TableCell colSpan={3} align="center">
                  No scheduled tasks
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      )}
    </Container>
  );
};

export default TaskLogs;
