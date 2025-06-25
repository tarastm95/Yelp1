import React, { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import {
  Container,
  Box,
  Typography,
  Table,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
  CircularProgress,
  Tabs,
  Tab,
  Paper,
} from '@mui/material';

type MessageTask = {
  executed_at: string;
  text: string;
  business_name: string | null;
  task_type: string;
};

type CeleryTask = {
  task_id: string;
  name: string;
  args: any[];
  eta: string | null;
  business_id?: string | null;
};

type Business = {
  business_id: string;
  name: string;
  time_zone?: string;
};

const TaskLogs: React.FC = () => {
  const [scheduled, setScheduled] = useState<CeleryTask[]>([]);
  const [completed, setCompleted] = useState<MessageTask[]>([]);
  const [businesses, setBusinesses] = useState<Business[]>([]);
  const [loadingScheduled, setLoadingScheduled] = useState(true);
  const [loadingCompleted, setLoadingCompleted] = useState(true);
  const [tab, setTab] = useState(0);

  useEffect(() => {
    axios
      .get<CeleryTask[]>('/tasks/?status=SCHEDULED&status=STARTED')
      .then(res => setScheduled(res.data))
      .catch(() => setScheduled([]))
      .finally(() => setLoadingScheduled(false));

    axios
      .get<MessageTask[]>('/message_tasks/')
      .then(res => setCompleted(res.data))
      .catch(() => setCompleted([]))
      .finally(() => setLoadingCompleted(false));

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

  const extractMessage = (task: CeleryTask): string => {
    const args = task.args || [];
    if (args.length >= 2) return String(args[1]);
    return '';
  };

  return (
    <Container sx={{ mt: 4 }}>
      <Typography variant="h4" gutterBottom>
        Celery Tasks
      </Typography>
      <Paper sx={{ mb: 2 }}>
        <Tabs value={tab} onChange={(_, v) => setTab(v)} variant="fullWidth">
          <Tab label="In Progress" />
          <Tab label="Completed" />
        </Tabs>
      </Paper>

      {tab === 0 ? (
        loadingScheduled ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
            <CircularProgress />
          </Box>
        ) : (
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Run Time</TableCell>
                <TableCell>Message</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {scheduled.map(t => (
                <TableRow key={t.task_id}>
                  <TableCell>{formatEta(t.eta, t.business_id)}</TableCell>
                  <TableCell>{extractMessage(t)}</TableCell>
                </TableRow>
              ))}
              {scheduled.length === 0 && (
                <TableRow>
                  <TableCell colSpan={2} align="center">
                    No tasks.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        )
      ) : loadingCompleted ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
          <CircularProgress />
        </Box>
      ) : (
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Time</TableCell>
              <TableCell>Text</TableCell>
              <TableCell>Business</TableCell>
              <TableCell>Type</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {completed.map((r, idx) => (
              <TableRow key={idx}>
                <TableCell>{new Date(r.executed_at).toLocaleString()}</TableCell>
                <TableCell>{r.text}</TableCell>
                <TableCell>{r.business_name || ''}</TableCell>
                <TableCell>{r.task_type}</TableCell>
              </TableRow>
            ))}
            {completed.length === 0 && (
              <TableRow>
                <TableCell colSpan={4} align="center">
                  No tasks.
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
