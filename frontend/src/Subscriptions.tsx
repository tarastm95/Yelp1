import React, { useEffect, useState } from 'react';
import axios from 'axios';
import {
  Container,
  Typography,
  Box,
  TextField,
  Button,
  Paper,
  CircularProgress,
} from '@mui/material';

interface Subscription {
  business_id: string;
  subscribed_at: string;
}

const Subscriptions: React.FC = () => {
  const [subs, setSubs] = useState<Subscription[]>([]);
  const [loading, setLoading] = useState(true);
  const [newBiz, setNewBiz] = useState('');

  const loadSubs = () => {
    setLoading(true);
    axios
      .get<{ subscriptions: Subscription[] }>('/businesses/subscriptions/?subscription_type=WEBHOOK')
      .then(res => setSubs(res.data.subscriptions || []))
      .catch(() => setSubs([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadSubs();
  }, []);

  const handleSubscribe = () => {
    if (!newBiz) return;
    axios
      .post('/businesses/subscriptions/', {
        subscription_types: ['WEBHOOK'],
        business_ids: [newBiz],
      })
      .then(loadSubs)
      .catch(() => {});
  };

  const handleUnsubscribe = (bid: string) => {
    axios
      .delete('/businesses/subscriptions/', {
        data: { subscription_types: ['WEBHOOK'], business_ids: [bid] },
      })
      .then(loadSubs)
      .catch(() => {});
  };

  return (
    <Container sx={{ mt: 4 }}>
      <Typography variant="h4" gutterBottom>
        Subscriptions
      </Typography>
      <Box sx={{ display: 'flex', mb: 2 }}>
        <TextField
          size="small"
          label="Business ID"
          value={newBiz}
          onChange={e => setNewBiz(e.target.value)}
          sx={{ mr: 1 }}
        />
        <Button variant="contained" onClick={handleSubscribe}>
          Subscribe
        </Button>
      </Box>
      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
          <CircularProgress />
        </Box>
      ) : (
        <>
          {subs.map(s => (
            <Paper key={s.business_id} sx={{ p: 2, mb: 1, display: 'flex', justifyContent: 'space-between' }}>
              <Box>
                <Typography variant="subtitle1">{s.business_id}</Typography>
                <Typography variant="body2">
                  {new Date(s.subscribed_at).toLocaleString()}
                </Typography>
              </Box>
              <Button color="error" onClick={() => handleUnsubscribe(s.business_id)}>
                Unsubscribe
              </Button>
            </Paper>
          ))}
          {subs.length === 0 && <Typography>No subscriptions</Typography>}
        </>
      )}
    </Container>
  );
};

export default Subscriptions;
