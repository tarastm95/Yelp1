import React, { FC } from 'react';
import {
  Card,
  CardMedia,
  CardContent,
  Typography,
  Link,
  Rating,
  Box,
  Chip,
  Stack,
  Divider,
  Grid,
  Avatar,
} from '@mui/material';
import LocationOnIcon from '@mui/icons-material/LocationOn';
import PhoneIcon from '@mui/icons-material/Phone';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import BusinessIcon from '@mui/icons-material/Business';
import PublicIcon from '@mui/icons-material/Public';
import StarIcon from '@mui/icons-material/Star';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';

const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

function formatTime(value: string): string {
  if (!value || value.length !== 4) return value;
  return `${value.slice(0, 2)}:${value.slice(2)}`;
}

function isOpenNow(openHours: any[] | undefined, timeZone?: string): boolean | undefined {
  if (!openHours || !timeZone) return undefined;
  const now = new Date();
  const tzNow = new Date(now.toLocaleString('en-US', { timeZone }));
  const dayIndex = (tzNow.getDay() + 6) % 7; // convert Sunday=0 to Monday=0
  const current = tzNow.getHours() * 100 + tzNow.getMinutes();

  for (const o of openHours) {
    if (o.day !== dayIndex) continue;
    const start = parseInt(o.start, 10);
    const end = parseInt(o.end, 10);
    if (!o.is_overnight) {
      if (current >= start && current < end) return true;
    } else {
      if (current >= start || current < end) return true;
    }
  }
  return false;
}

interface Business {
  business_id: string;
  name: string;
  location?: string;
  time_zone?: string;
  details?: any;
}

const BusinessInfoCard: FC<{ business: Business }> = ({ business }) => {
  const d = business.details || {};
  const address: string | undefined = d.location?.display_address?.join(', ');
  const phone: string | undefined = d.display_phone;
  const rating: number | undefined = d.rating;
  const reviewCount: number | undefined = d.review_count;
  const categories: string | undefined = d.categories
    ?.map((c: any) => c.title)
    .join(', ');

  const hoursInfo = d.hours?.[0];
  const openHours = hoursInfo?.open as any[] | undefined;
  const timeZone: string | undefined = business.time_zone || hoursInfo?.time_zone;
  const isOpen = isOpenNow(openHours, timeZone);

  const isClosed: boolean | undefined = d.is_closed;
  const image: string | undefined = d.image_url;
  const url: string | undefined = d.url;

  const hoursLines = openHours
    ? openHours.map(o => `${days[o.day]}: ${formatTime(o.start)} - ${formatTime(o.end)}${o.is_overnight ? ' (+1)' : ''}`)
    : [];
  const openDays = openHours ? Array.from(new Set(openHours.map(o => days[o.day]))).join(', ') : undefined;

  return (
    <Card 
      elevation={2}
      sx={{ 
        borderRadius: 3,
        overflow: 'hidden',
        transition: 'all 0.3s ease-in-out',
        '&:hover': {
          elevation: 4,
          transform: 'translateY(-2px)'
        }
      }}
    >
      <Box sx={{ position: 'relative' }}>
        {/* Header with business name and status */}
        <Box 
          sx={{ 
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            color: 'white',
            p: 3,
            position: 'relative'
          }}
        >
          <Stack direction="row" spacing={2} alignItems="flex-start">
            {image ? (
              <Avatar
                src={image}
                alt={business.name}
                sx={{ 
                  width: 80, 
                  height: 80,
                  border: '3px solid rgba(255,255,255,0.2)',
                  boxShadow: 3
                }}
              />
            ) : (
              <Avatar
                sx={{ 
                  width: 80, 
                  height: 80,
                  bgcolor: 'rgba(255,255,255,0.2)',
                  fontSize: '2rem',
                  fontWeight: 600
                }}
              >
                {business.name.charAt(0)}
              </Avatar>
            )}
            
            <Box sx={{ flex: 1, minWidth: 0 }}>
              <Typography 
                variant="h5" 
                sx={{ 
                  fontWeight: 700,
                  mb: 1,
                  wordBreak: 'break-word'
                }}
              >
                {business.name}
              </Typography>
              
              {address && (
                <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
                  <LocationOnIcon sx={{ fontSize: 18, opacity: 0.9 }} />
                  <Typography variant="body2" sx={{ opacity: 0.9 }}>
                    {address}
                  </Typography>
                </Stack>
              )}
              
              {phone && (
                <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
                  <PhoneIcon sx={{ fontSize: 18, opacity: 0.9 }} />
                  <Typography variant="body2" sx={{ opacity: 0.9, fontWeight: 500 }}>
                    {phone}
                  </Typography>
                </Stack>
              )}
            </Box>
            
            {/* Status badge */}
            <Box>
              {(isOpen !== undefined || isClosed !== undefined) && (
                <Chip
                  label={isClosed ? 'Closed' : isOpen ? 'Open now' : 'Closed now'}
                  size="small"
                  sx={{
                    bgcolor: isClosed || isOpen === false ? 'error.main' : 'success.main',
                    color: 'white',
                    fontWeight: 600,
                    '& .MuiChip-label': {
                      px: 2
                    }
                  }}
                />
              )}
            </Box>
          </Stack>
        </Box>

        {/* Content section */}
        <CardContent sx={{ p: 3 }}>
          <Grid container spacing={3}>
            {/* Rating and Reviews */}
            {(rating !== undefined || reviewCount !== undefined) && (
              <Grid item xs={12} sm={6}>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <StarIcon sx={{ color: 'warning.main', mr: 1 }} />
                  <Typography variant="h6" sx={{ fontWeight: 600, mr: 1 }}>
                    {rating !== undefined ? rating.toFixed(1) : 'N/A'}
                  </Typography>
                  {rating !== undefined && (
                    <Rating 
                      value={rating} 
                      precision={0.1} 
                      readOnly 
                      size="small" 
                      sx={{ mr: 1 }}
                    />
                  )}
                  {reviewCount !== undefined && (
                    <Typography variant="body2" color="text.secondary">
                      ({reviewCount} reviews)
                    </Typography>
                  )}
                </Box>
              </Grid>
            )}

            {/* Categories */}
            {categories && (
              <Grid item xs={12} sm={6}>
                <Box sx={{ mb: 2 }}>
                  <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
                    <BusinessIcon sx={{ color: 'text.secondary', fontSize: 20 }} />
                    <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                      Categories
                    </Typography>
                  </Stack>
                  <Typography variant="body2" color="text.secondary">
                    {categories}
                  </Typography>
                </Box>
              </Grid>
            )}

            {/* Time Zone */}
            {timeZone && (
              <Grid item xs={12} sm={6}>
                <Box sx={{ mb: 2 }}>
                  <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
                    <PublicIcon sx={{ color: 'text.secondary', fontSize: 20 }} />
                    <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                      Time Zone
                    </Typography>
                  </Stack>
                  <Typography variant="body2" color="text.secondary">
                    {timeZone}
                  </Typography>
                </Box>
              </Grid>
            )}

            {/* Operating Days */}
            {openDays && (
              <Grid item xs={12} sm={6}>
                <Box sx={{ mb: 2 }}>
                  <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
                    <AccessTimeIcon sx={{ color: 'text.secondary', fontSize: 20 }} />
                    <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                      Operating Days
                    </Typography>
                  </Stack>
                  <Typography variant="body2" color="text.secondary">
                    {openDays}
                  </Typography>
                </Box>
              </Grid>
            )}

            {/* Operating Hours */}
            {hoursLines.length > 0 && (
              <Grid item xs={12}>
                <Divider sx={{ my: 1 }} />
                <Box sx={{ mt: 2 }}>
                  <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 2 }}>
                    Operating Hours
                  </Typography>
                  <Box 
                    sx={{ 
                      display: 'grid', 
                      gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                      gap: 1
                    }}
                  >
                    {hoursLines.map((line, index) => (
                      <Typography 
                        key={index}
                        variant="body2" 
                        color="text.secondary"
                        sx={{ 
                          fontFamily: 'monospace',
                          fontSize: '0.875rem'
                        }}
                      >
                        {line}
                      </Typography>
                    ))}
                  </Box>
                </Box>
              </Grid>
            )}

            {/* Yelp Link */}
            {url && (
              <Grid item xs={12}>
                <Divider sx={{ my: 1 }} />
                <Box sx={{ mt: 2, textAlign: 'center' }}>
                  <Link 
                    href={url} 
                    target="_blank" 
                    rel="noopener"
                    sx={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      textDecoration: 'none',
                      color: 'primary.main',
                      fontWeight: 600,
                      '&:hover': {
                        textDecoration: 'underline'
                      }
                    }}
                  >
                    View on Yelp
                    <OpenInNewIcon sx={{ ml: 0.5, fontSize: 16 }} />
                  </Link>
                </Box>
              </Grid>
            )}
          </Grid>
        </CardContent>
      </Box>
    </Card>
  );
};

export default BusinessInfoCard;
