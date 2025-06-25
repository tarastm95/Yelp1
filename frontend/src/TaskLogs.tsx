import React, { useEffect, useState } from 'react';
import axios from 'axios';
import {
  Container,
  Box,
  Tabs,
  Tab,
  Typography,
  Table,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
  CircularProgress,
} from '@mui/material';

type TaskLog = {
  task_id: string;
  name: string;
  args: any;
  kwargs: any;
  eta: string | null;
  started_at: string | null;
  finished_at: string | null;
  status: string;
  result: string | null;
  business_id: string | null;
};

const TaskLogs: React.FC = () => {
  const [tab, setTab] = useState(0);
  const [scheduled, setScheduled] = useState<TaskLog[]>([]);
  const [executed, setExecuted] = useState<TaskLog[]>([]);
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    axios
      .get<TaskLog[]>('/tasks/?status=SCHEDULED')
      .then(res => setScheduled(res.data))
      .catch(() => setScheduled([]));
    axios
      .get<TaskLog[]>('/tasks/?status=SUCCESS&status=FAILURE&status=STARTED')
      .then(res => setExecuted(res.data))
      .catch(() => setExecuted([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  const renderTable = (rows: TaskLog[]) => (
    <Table size="small">
      <TableHead>
        <TableRow>
          <TableCell>ID</TableCell>
          <TableCell>Name</TableCell>
          <TableCell>ETA</TableCell>
          <TableCell>Started</TableCell>
          <TableCell>Finished</TableCell>
          <TableCell>Status</TableCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {rows.map(r => (
          <TableRow key={r.task_id}>
            <TableCell>{r.task_id}</TableCell>
            <TableCell>{r.name}</TableCell>
            <TableCell>{r.eta ? new Date(r.eta).toLocaleString() : ''}</TableCell>
            <TableCell>
              {r.started_at ? new Date(r.started_at).toLocaleString() : ''}
            </TableCell>
            <TableCell>
              {r.finished_at ? new Date(r.finished_at).toLocaleString() : ''}
            </TableCell>
            <TableCell>{r.status}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );

  return (
    <Container sx={{ mt: 4 }}>
      <Typography variant="h4" gutterBottom>
        Celery Tasks
      </Typography>
      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
          <CircularProgress />
        </Box>
      ) : (
        <>
          <Tabs value={tab} onChange={(_, v) => setTab(v)}>
            <Tab label="Заплановані" />
            <Tab label="Виконані" />
          </Tabs>
          <Box hidden={tab !== 0}>{renderTable(scheduled)}</Box>
          <Box hidden={tab !== 1}>{renderTable(executed)}</Box>
        </>
      )}
    </Container>
  );
};

export default TaskLogs;
