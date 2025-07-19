// src/components/LeadDetail.tsx
import React, { FC, useState, useEffect } from 'react';
import { useParams, Link as RouterLink } from 'react-router-dom';
import axios from 'axios';
import {
  Box,
  Card,
  CardHeader,
  CardContent,
  Typography,
  List,
  ListItem,
  ListItemText,
  Divider,
  Avatar,
  Chip,
  Button,
  CircularProgress,
  Alert,
  Card as MuiCard,
} from '@mui/material';
import { LeadDetail as LeadDetailType } from './types';

const LeadDetail: FC = () => {
  const { id: leadId } = useParams<{ id: string }>();
  const [detail, setDetail] = useState<LeadDetailType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!leadId) {
      setError('Unknown Lead ID');
      setLoading(false);
      return;
    }
    (async () => {
      try {
        const { data } = await axios.get<LeadDetailType>(
          `/lead-details/${encodeURIComponent(leadId)}/`
        );
        setDetail(data);
      } catch (e) {
        console.error(e);
        setError('Failed to load client details');
      } finally {
        setLoading(false);
      }
    })();
  }, [leadId]);

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" mt={4}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box mt={4} px={2}>
        <Alert severity="error">{error}</Alert>
      </Box>
    );
  }

  if (!detail) {
    return (
      <Box mt={4} px={2}>
        <Typography variant="body1">No data available</Typography>
      </Box>
    );
  }

  const {
    business_id,
    conversation_id,
    temporary_email_address,
    temporary_email_address_expiry,
    time_created,
    last_event_time,
    user_display_name,
    project,
  } = detail;

  const survey = project?.survey_answers ?? [];
  const jobs = project?.job_names ?? [];
  const atts = project?.attachments ?? [];

  return (
    <Box maxWidth={900} mx="auto" py={4} px={2}>
      <Button
        component={RouterLink}
        to="/events"
        variant="outlined"
        sx={{ mb: 3 }}
      >
        ← Back to the list of events
      </Button>

      <MuiCard>
        <CardHeader
          avatar={<Avatar>{user_display_name?.charAt(0) ?? ''}</Avatar>}
          title={`Lead ID: ${leadId}`}
          subheader={
            last_event_time
              ? `Last Event: ${new Date(last_event_time).toLocaleString()}`
              : undefined
          }
        />
        <CardContent>
          {/* General information */}
          <Box mb={4}>
            <Typography variant="h6" gutterBottom>
              General information
            </Typography>
            <List disablePadding>
              <ListItem>
                <ListItemText primary="Business ID" secondary={business_id} />
              </ListItem>
              <Divider />
              <ListItem>
                <ListItemText primary="Conversation ID" secondary={conversation_id} />
              </ListItem>
              {temporary_email_address && (
                <>
                  <Divider />
                  <ListItem>
                    <ListItemText
                      primary="Temporary Email"
                      secondary={temporary_email_address}
                    />
                  </ListItem>
                </>
              )}
              {temporary_email_address_expiry && (
                <>
                  <Divider />
                  <ListItem>
                    <ListItemText
                      primary="Email Expiry"
                      secondary={new Date(temporary_email_address_expiry).toLocaleString()}
                    />
                  </ListItem>
                </>
              )}
              <Divider />
              <ListItem>
                <ListItemText
                  primary="Time Created"
                  secondary={new Date(time_created).toLocaleString()}
                />
              </ListItem>
            </List>
          </Box>

          {/* User information */}
          <Box mb={4}>
            <Typography variant="h6" gutterBottom>
              User
            </Typography>
            <Typography>
              <strong>Display Name:</strong> {user_display_name}
            </Typography>
          </Box>

          {/* Project information */}
          {project && (
            <Box>
              <Typography variant="h6" gutterBottom>
                Project
              </Typography>

              {/* Survey Answers */}
              {survey.length > 0 && (
                <Box mb={2}>
                  <Typography variant="subtitle1">Survey Answers</Typography>
                  {survey.map((sa: any, i: number) => (
                    <Box key={i} my={1}>
                      <Typography fontWeight={600}>{sa.question_text}</Typography>
                      {sa.answer_text?.map((ans: string, j: number) => (
                        <Chip key={j} label={ans} size="small" sx={{ mr: 1, mb: 1 }} />
                      ))}
                    </Box>
                  ))}
                </Box>
              )}

              {/* Grid for location, info, availability, jobs */}
              <Box
                sx={{
                  display: 'grid',
                  gridTemplateColumns: { xs: '1fr', md: 'repeat(3,1fr)' },
                  gap: 2,
                }}
              >
                {project.location && (
                  <Box>
                    <Typography fontWeight={600}>Location</Typography>
                    <Typography variant="body2">
                      {Object.entries(project.location)
                        .map(([k, v]) => `${k}: ${v}`)
                        .join(', ')}
                    </Typography>
                  </Box>
                )}
                {project.additional_info && (
                  <Box>
                    <Typography fontWeight={600}>Additional Info</Typography>
                    <Typography variant="body2">{project.additional_info}</Typography>
                  </Box>
                )}
                {project.availability && (
                  <Box>
                    <Typography fontWeight={600}>Availability</Typography>
                    <Typography variant="body2">
                      {project.availability.status}
                      {project.availability.dates?.length
                        ? ` — ${project.availability.dates.join(', ')}`
                        : ''}
                    </Typography>
                  </Box>
                )}
                {jobs.length > 0 && (
                  <Box sx={{ gridColumn: { md: 'span 2' } }}>
                    <Typography fontWeight={600}>Job Names</Typography>
                    {jobs.map((job: string, idx: number) => (
                      <Chip key={idx} label={job} size="small" sx={{ mr: 1, mb: 1 }} />
                    ))}
                  </Box>
                )}
              </Box>

              {/* Attachments */}
              {atts.length > 0 && (
                <Box mt={3}>
                  <Typography variant="subtitle1" gutterBottom>
                    Attachments
                  </Typography>
                  <Box
                    sx={{
                      display: 'grid',
                      gridTemplateColumns: {
                        xs: '1fr',
                        sm: 'repeat(2,1fr)',
                        md: 'repeat(3,1fr)',
                      },
                      gap: 2,
                    }}
                  >
                    {atts.map((att: any) => {
                      const proxyUrl = `/yelp/leads/${leadId}/attachments/${encodeURIComponent(att.id)}/`;
                      return (
                        <MuiCard variant="outlined" key={att.id}>
                          <a href={att.url} target="_blank" rel="noreferrer">
                            <img
                              src={proxyUrl}
                              alt={att.resource_name}
                              style={{ width: '100%', borderRadius: 4 }}
                            />
                          </a>
                          <CardContent>
                            <Typography variant="body2" align="center">
                              {att.resource_name}
                            </Typography>
                          </CardContent>
                        </MuiCard>
                      );
                    })}
                  </Box>
                </Box>
              )}
            </Box>
          )}
        </CardContent>
      </MuiCard>
    </Box>
  );
};

export default LeadDetail;
