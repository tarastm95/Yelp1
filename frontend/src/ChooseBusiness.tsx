import React, { FC, useState, useEffect } from 'react';
import axios from 'axios';
import { Container, Select, MenuItem, Box } from '@mui/material';

interface Business {
  business_id: string;
  name: string;
  location?: string;
  time_zone?: string;
}

const ChooseBusiness: FC = () => {
  const [businesses, setBusinesses] = useState<Business[]>([]);
  const [selectedBusiness, setSelectedBusiness] = useState('');

  useEffect(() => {
    axios.get<Business[]>('/businesses/')
      .then(res => setBusinesses(res.data))
      .catch(() => setBusinesses([]));
  }, []);

  return (
    <Container maxWidth={false} sx={{ mt: 4, mb: 4, maxWidth: 1000, mx: 'auto' }}>
      <Box sx={{ mb: 2 }}>
        <Select
          value={selectedBusiness}
          onChange={e => setSelectedBusiness(e.target.value as string)}
          displayEmpty
          size="small"
          sx={{ mt: 2 }}
        >
          <MenuItem value="" disabled>
            <em>Choose business</em>
          </MenuItem>
          {businesses.map(b => (
            <MenuItem key={b.business_id} value={b.business_id}>
              {b.name}
              {b.location ? ` (${b.location})` : ''}
              {b.time_zone ? ` - ${b.time_zone}` : ''}
            </MenuItem>
          ))}
        </Select>
      </Box>
    </Container>
  );
};

export default ChooseBusiness;
