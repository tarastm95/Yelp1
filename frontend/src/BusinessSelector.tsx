import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Container, Typography, Select, MenuItem, Box } from '@mui/material';
import BusinessInfoCard from './BusinessInfoCard';

interface Business {
  business_id: string;
  name: string;
  location?: string;
  time_zone?: string;
  details?: any;
}

const BusinessSelector: React.FC = () => {
  const [businesses, setBusinesses] = useState<Business[]>([]);
  const [selected, setSelected] = useState('');
  // Selected business details are already included in the list
  
  useEffect(() => {
    axios.get<Business[]>('/businesses/')
      .then(res => setBusinesses(res.data))
      .catch(() => setBusinesses([]));
  }, []);

  const handleSelect = (id: string) => {
    setSelected(id);
  };

  return (
    <Container sx={{ mt: 4 }}>
      <Typography variant="h5" gutterBottom>Select Business</Typography>
      <Select value={selected} onChange={e => handleSelect(e.target.value as string)} displayEmpty>
        <MenuItem value=""><em>Choose...</em></MenuItem>
        {businesses.map(b => (
          <MenuItem key={b.business_id} value={b.business_id}>
            {b.name}
            {b.location ? ` (${b.location})` : ''}
            {b.time_zone ? ` - ${b.time_zone}` : ''}
          </MenuItem>
        ))}
      </Select>
      {selected && (() => {
        const biz = businesses.find(b => b.business_id === selected);
        if (!biz) return null;
        return (
          <Box sx={{ mt: 2 }}>
            <BusinessInfoCard business={biz} />
          </Box>
        );
      })()}
    </Container>
  );
};

export default BusinessSelector;
