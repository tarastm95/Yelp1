import React, { useEffect, useState } from 'react';
import axios from 'axios';
import {
  Container,
  Typography,
  Box,
  Paper,
  CircularProgress,
  Alert,
} from '@mui/material';
import BusinessInfoCard from './BusinessInfoCard';

interface TokenInfo {
  business_id: string;
  expires_at: string | null;
  updated_at: string;
  business: {
    business_id: string;
    name: string;
    location?: string;
    details?: any;
  } | null;
}

const TokenStatus: React.FC = () => {
  const [tokens, setTokens] = useState<TokenInfo[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    axios.get<TokenInfo[]>('/tokens/')
      .then(res => setTokens(res.data))
      .catch(() => setTokens([]))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Container sx={{ mt: 4 }}>
      <Typography variant="h4" gutterBottom>
        Token Status
      </Typography>
      {tokens.map(t => {
        const exp = t.expires_at ? new Date(t.expires_at) : null;
        const now = new Date();
        const remainingSec = exp
          ? Math.floor((exp.getTime() - now.getTime()) / 1000)
          : null;
        const expired = remainingSec !== null && remainingSec <= 0;

        const absSec = remainingSec !== null ? Math.max(0, remainingSec) : 0;
        const days = Math.floor(absSec / 86400);
        const hours = Math.floor((absSec % 86400) / 3600);
        const minutes = Math.floor((absSec % 3600) / 60);
        const seconds = absSec % 60;

        const refreshExpires = new Date(t.updated_at).getTime() + 365 * 86400 * 1000;
        const refreshExpired = now.getTime() >= refreshExpires;

        return (
          <Paper
            key={t.business_id}
            sx={{
              p: 2,
              mb: 2,
              border: 1,
              borderColor: expired || refreshExpired ? 'error.main' : 'divider',
            }}
          >
            {t.business && <BusinessInfoCard business={t.business} />}
            <Typography variant="body2" sx={{ mt: 1 }}>
              Updated at: {new Date(t.updated_at).toLocaleString()}
            </Typography>
            {exp && !expired && (
              <Typography variant="body2">
                Expires in: {days}d {hours}h {minutes}m {seconds}s
              </Typography>
            )}
            {exp && expired && (
              <Alert severity="error" sx={{ mt: 1 }}>
                Access token expired
              </Alert>
            )}
            {!exp && <Typography variant="body2">Expires at: —</Typography>}
            {refreshExpired && (
              <Alert severity="error" sx={{ mt: 1 }}>
                Refresh token expired - reauthorize required
              </Alert>
            )}
          </Paper>
        );
      })}
    </Container>
  );
};

export default TokenStatus;
