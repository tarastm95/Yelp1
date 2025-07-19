import React, { FC } from 'react';
import {
  Card,
  CardMedia,
  CardContent,
  Typography,
  Link,
  Rating,
  Box,
} from '@mui/material';

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
    <Card sx={{ display: 'flex', p: 1 }}>
      {image && (
        <CardMedia
          component="img"
          image={image}
          alt={business.name}
          sx={{ width: 150, height: 150, objectFit: 'cover', mr: 2, borderRadius: 1 }}
        />
      )}
      <CardContent sx={{ p: 1, '&:last-child': { pb: 1 } }}>
        <Typography variant="h6">{business.name}</Typography>
        {address && (
          <Typography variant="body2" color="text.secondary">
            {address}
          </Typography>
        )}
        {phone && (
          <Typography variant="body2" sx={{ mt: 0.5 }}>
            {phone}
          </Typography>
        )}
        {(rating !== undefined || reviewCount !== undefined) && (
          <Box sx={{ display: 'flex', alignItems: 'center', mt: 0.5 }}>
            {rating !== undefined && (
              <Rating value={rating} precision={0.5} readOnly size="small" />
            )}
            <Typography variant="body2" sx={{ ml: 0.5 }}>
              {rating !== undefined ? rating : 'N/A'}
              {reviewCount !== undefined ? ` (${reviewCount} reviews)` : ''}
            </Typography>
          </Box>
        )}
        {categories && (
          <Typography variant="body2" sx={{ mt: 0.5 }}>
            Categories: {categories}
          </Typography>
        )}
        {timeZone && (
          <Typography variant="body2" sx={{ mt: 0.5 }}>
            Time zone: {timeZone}
          </Typography>
        )}
        {(isOpen !== undefined || isClosed !== undefined) && (
          <Typography
            variant="body2"
            sx={{ mt: 0.5 }}
            color={isClosed || isOpen === false ? 'error.main' : 'success.main'}
          >
            {isClosed ? 'Closed' : isOpen ? 'Open now' : 'Closed now'}
          </Typography>
        )}
        {openDays && (
          <Typography variant="body2" sx={{ mt: 0.5 }}>
            Days: {openDays}
          </Typography>
        )}
        {hoursLines.length > 0 && (
          <Typography variant="body2" sx={{ mt: 0.5 }}>
            Hours: {hoursLines.join('; ')}
          </Typography>
        )}
        {url && (
          <Typography variant="body2" sx={{ mt: 0.5 }}>
            <Link href={url} target="_blank" rel="noopener">
              View on Yelp
            </Link>
          </Typography>
        )}
      </CardContent>
    </Card>
  );
};

export default BusinessInfoCard;
