// src/components/HistorySection.tsx
import React, { FC } from 'react';
import { MessageHistory } from './types';

// --- Material-UI Imports ---
import {
  Typography,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Paper,
  Divider,
  Box,
} from '@mui/material';

// --- Material-UI Icons ---
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';

const HistorySection: FC<{ history: MessageHistory[] }> = ({ history }) => (
  <Paper elevation={0} sx={{ p: 0 }}>
    <Typography variant="h6" component="h3" gutterBottom>
      Execution History
    </Typography>
    {history.length > 0 ? (
      <Paper variant="outlined">
        <List disablePadding>
          {history.map((h, index) => (
            <React.Fragment key={h.id}>
              <ListItem>
                <ListItemIcon>
                  {h.status === 'SUCCESS' ? (
                    <CheckCircleOutlineIcon color="success" />
                  ) : (
                    <ErrorOutlineIcon color="error" />
                  )}
                </ListItemIcon>
                <ListItemText
                  primary={
                    <Typography component="span" variant="body1">
                      Status: <strong>{h.status}</strong>
                    </Typography>
                  }
                  secondary={
                    <>
                      <Typography component="span" variant="body2" color="text.secondary">
                        {new Date(h.executed_at).toLocaleString()}
                      </Typography>
                      {h.error && (
                        <Typography component="div" variant="caption" color="error" sx={{ mt: 0.5 }}>
                          Error: {h.error}
                        </Typography>
                      )}
                    </>
                  }
                />
              </ListItem>
              {index < history.length - 1 && <Divider component="li" />}
            </React.Fragment>
          ))}
        </List>
      </Paper>
    ) : (
      <Typography color="text.secondary">
        No execution history available.
      </Typography>
    )}
  </Paper>
);

export default HistorySection;
