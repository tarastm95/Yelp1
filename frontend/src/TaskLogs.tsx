import React, { useEffect, useState } from 'react';
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
} from '@mui/material';

type MessageTask = {
  executed_at: string;
  text: string;
  business_name: string | null;
  task_type: string;
};

const TaskLogs: React.FC = () => {
  const [rows, setRows] = useState<MessageTask[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    axios
      .get<MessageTask[]>('/message_tasks/')
      .then(res => setRows(res.data))
      .catch(() => setRows([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <Container sx={{ mt: 4 }}>
      <Typography variant="h4" gutterBottom>
        Message Tasks
      </Typography>
      {loading ? (
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
            {rows.map((r, idx) => (
              <TableRow key={idx}>
                <TableCell>{new Date(r.executed_at).toLocaleString()}</TableCell>
                <TableCell>{r.text}</TableCell>
                <TableCell>{r.business_name || ''}</TableCell>
                <TableCell>{r.task_type}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </Container>
  );
};

export default TaskLogs;
