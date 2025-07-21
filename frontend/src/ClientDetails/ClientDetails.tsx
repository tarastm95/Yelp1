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
  Container,
  Grid,
  Stack,
  Paper,
  IconButton,
  alpha,
} from '@mui/material';
import { LeadDetail as LeadDetailType } from './types';

// Icons
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import PersonIcon from '@mui/icons-material/Person';
import BusinessIcon from '@mui/icons-material/Business';
import EmailIcon from '@mui/icons-material/Email';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import PhoneIcon from '@mui/icons-material/Phone';
import LocationOnIcon from '@mui/icons-material/LocationOn';
import WorkIcon from '@mui/icons-material/Work';
import CalendarTodayIcon from '@mui/icons-material/CalendarToday';
import AttachFileIcon from '@mui/icons-material/AttachFile';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import InfoIcon from '@mui/icons-material/Info';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import EventIcon from '@mui/icons-material/Event';

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
      <Box sx={{ 
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)',
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center' 
      }}>
        <CircularProgress size={48} />
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ 
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)',
        p: 4
      }}>
        <Container maxWidth="md">
          <Alert severity="error" sx={{ borderRadius: 3 }}>{error}</Alert>
        </Container>
      </Box>
    );
  }

  if (!detail) {
    return (
      <Box sx={{ 
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)',
        p: 4
      }}>
        <Container maxWidth="md">
          <Alert severity="warning" sx={{ borderRadius: 3 }}>No data available</Alert>
        </Container>
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
    <Box sx={{ 
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)',
      pb: 6
    }}>
      <Container maxWidth="xl" sx={{ pt: 4 }}>
        {/* Back Button */}
        <Button
          component={RouterLink}
          to="/events"
          startIcon={<ArrowBackIcon />}
          sx={{
            mb: 3,
            background: 'rgba(255, 255, 255, 0.9)',
            backdropFilter: 'blur(10px)',
            borderRadius: 3,
            px: 3,
            py: 1.5,
            fontWeight: 600,
            color: 'text.primary',
            border: '1px solid',
            borderColor: alpha('#667eea', 0.2),
            
            '&:hover': {
              background: 'rgba(255, 255, 255, 1)',
              borderColor: '#667eea',
              transform: 'translateY(-2px)',
              boxShadow: '0 8px 24px rgba(102, 126, 234, 0.15)',
            }
          }}
        >
          Back to Events List
        </Button>

        {/* Hero Section */}
        <Card 
          elevation={4}
          sx={{ 
            borderRadius: 4,
            overflow: 'hidden',
            mb: 4,
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            color: 'white',
            position: 'relative'
          }}
        >
          <Box
            sx={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              background: 'url("data:image/svg+xml,%3Csvg width="60" height="60" viewBox="0 0 60 60" xmlns="http://www.w3.org/2000/svg"%3E%3Cg fill="none" fill-rule="evenodd"%3E%3Cg fill="%23ffffff" fill-opacity="0.05"%3E%3Ccircle cx="30" cy="30" r="2"/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")',
              opacity: 0.3
            }}
          />
          
          <CardContent sx={{ p: 4, position: 'relative', zIndex: 1 }}>
            <Stack direction={{ xs: 'column', md: 'row' }} spacing={3} alignItems="center">
              {/* Avatar */}
              <Avatar
                sx={{
                  width: 120,
                  height: 120,
                  fontSize: '3rem',
                  fontWeight: 700,
                  background: 'rgba(255, 255, 255, 0.2)',
                  backdropFilter: 'blur(10px)',
                  border: '4px solid rgba(255, 255, 255, 0.3)',
                  boxShadow: '0 8px 32px rgba(0, 0, 0, 0.1)'
                }}
              >
                {user_display_name?.charAt(0)?.toUpperCase() || 'U'}
              </Avatar>
              
              {/* Info */}
              <Box sx={{ flex: 1, textAlign: { xs: 'center', md: 'left' } }}>
                <Typography variant="h3" sx={{ fontWeight: 800, mb: 1 }}>
                  {user_display_name || 'Unknown User'}
                </Typography>
                
                <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ mb: 2 }}>
                  <Chip
                    icon={<PersonIcon />}
                    label={`Lead ID: ${leadId}`}
                    sx={{
                      background: 'rgba(255, 255, 255, 0.2)',
                      color: 'white',
                      fontWeight: 600,
                      '& .MuiChip-icon': { color: 'white' }
                    }}
                  />
                  
                  {last_event_time && (
                    <Chip
                      icon={<EventIcon />}
                      label={`Last Event: ${new Date(last_event_time).toLocaleDateString()}`}
                      sx={{
                        background: 'rgba(255, 255, 255, 0.2)',
                        color: 'white',
                        fontWeight: 600,
                        '& .MuiChip-icon': { color: 'white' }
                      }}
                    />
                  )}
                </Stack>
                
                <Typography variant="h6" sx={{ opacity: 0.9 }}>
                  Lead Details & Project Information
                </Typography>
              </Box>
            </Stack>
          </CardContent>
        </Card>

        <Grid container spacing={4}>
          {/* Left Column - General Info */}
          <Grid item xs={12} lg={6}>
            <Stack spacing={3}>
              {/* General Information */}
              <Card elevation={2} sx={{ borderRadius: 3 }}>
                <Box sx={{ 
                  background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
                  p: 2,
                  color: 'white'
                }}>
                  <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', fontWeight: 600 }}>
                    <InfoIcon sx={{ mr: 1 }} />
                    General Information
                  </Typography>
                </Box>
                
                <CardContent sx={{ p: 0 }}>
                  <List>
                    <ListItem sx={{ py: 2, px: 3 }}>
                      <BusinessIcon sx={{ mr: 2, color: 'primary.main' }} />
                      <ListItemText 
                        primary="Business ID" 
                        secondary={business_id}
                        primaryTypographyProps={{ fontWeight: 600 }}
                      />
                    </ListItem>
                    
                    <Divider />
                    
                    <ListItem sx={{ py: 2, px: 3 }}>
                      <PhoneIcon sx={{ mr: 2, color: 'primary.main' }} />
                      <ListItemText 
                        primary="Conversation ID" 
                        secondary={conversation_id}
                        primaryTypographyProps={{ fontWeight: 600 }}
                      />
                    </ListItem>
                    
                    {temporary_email_address && (
                      <>
                        <Divider />
                        <ListItem sx={{ py: 2, px: 3 }}>
                          <EmailIcon sx={{ mr: 2, color: 'primary.main' }} />
                          <ListItemText
                            primary="Temporary Email"
                            secondary={temporary_email_address}
                            primaryTypographyProps={{ fontWeight: 600 }}
                          />
                        </ListItem>
                      </>
                    )}
                    
                    {temporary_email_address_expiry && (
                      <>
                        <Divider />
                        <ListItem sx={{ py: 2, px: 3 }}>
                          <AccessTimeIcon sx={{ mr: 2, color: 'warning.main' }} />
                          <ListItemText
                            primary="Email Expiry"
                            secondary={new Date(temporary_email_address_expiry).toLocaleString()}
                            primaryTypographyProps={{ fontWeight: 600 }}
                          />
                        </ListItem>
                      </>
                    )}
                    
                    <Divider />
                    
                    <ListItem sx={{ py: 2, px: 3 }}>
                      <CalendarTodayIcon sx={{ mr: 2, color: 'primary.main' }} />
                      <ListItemText
                        primary="Time Created"
                        secondary={new Date(time_created).toLocaleString()}
                        primaryTypographyProps={{ fontWeight: 600 }}
                      />
                    </ListItem>
                  </List>
                </CardContent>
              </Card>

              {/* Job Categories */}
              {jobs.length > 0 && (
                <Card elevation={2} sx={{ borderRadius: 3 }}>
                  <Box sx={{ 
                    background: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
                    p: 2,
                    color: 'white'
                  }}>
                    <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', fontWeight: 600 }}>
                      <WorkIcon sx={{ mr: 1 }} />
                      Job Categories
                    </Typography>
                  </Box>
                  
                  <CardContent sx={{ p: 3 }}>
                    <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                      {jobs.map((job: string, idx: number) => (
                        <Chip
                          key={idx}
                          label={job}
                          sx={{
                            background: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
                            color: 'white',
                            fontWeight: 600,
                            fontSize: '0.9rem',
                            py: 1
                          }}
                        />
                      ))}
                    </Stack>
                  </CardContent>
                </Card>
              )}
            </Stack>
          </Grid>

          {/* Right Column - Project Info */}
          <Grid item xs={12} lg={6}>
            <Stack spacing={3}>
              {/* Project Details */}
              {project && (
                <>
                  {/* Project Location & Info */}
                  <Card elevation={2} sx={{ borderRadius: 3 }}>
                    <Box sx={{ 
                      background: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
                      p: 2,
                      color: 'white'
                    }}>
                      <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', fontWeight: 600 }}>
                        <LocationOnIcon sx={{ mr: 1 }} />
                        Project Details
                      </Typography>
                    </Box>
                    
                    <CardContent sx={{ p: 3 }}>
                      <Grid container spacing={3}>
                        {project.location && (
                          <Grid item xs={12}>
                            <Box sx={{ 
                              p: 2, 
                              backgroundColor: 'grey.50', 
                              borderRadius: 2,
                              border: '1px solid',
                              borderColor: 'grey.200'
                            }}>
                              <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1, color: 'primary.main' }}>
                                Location
                              </Typography>
                              <Typography variant="body2">
                                {Object.entries(project.location)
                                  .map(([k, v]) => `${k}: ${v}`)
                                  .join(', ')}
                              </Typography>
                            </Box>
                          </Grid>
                        )}
                        
                        {project.additional_info && (
                          <Grid item xs={12}>
                            <Box sx={{ 
                              p: 2, 
                              backgroundColor: 'grey.50', 
                              borderRadius: 2,
                              border: '1px solid',
                              borderColor: 'grey.200'
                            }}>
                              <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1, color: 'primary.main' }}>
                                Additional Information
                              </Typography>
                              <Typography variant="body2">{project.additional_info}</Typography>
                            </Box>
                          </Grid>
                        )}
                        
                        {project.availability && (
                          <Grid item xs={12}>
                            <Box sx={{ 
                              p: 2, 
                              backgroundColor: 'grey.50', 
                              borderRadius: 2,
                              border: '1px solid',
                              borderColor: 'grey.200'
                            }}>
                              <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1, color: 'primary.main' }}>
                                Availability
                              </Typography>
                              <Stack direction="row" spacing={1} alignItems="center">
                                <Chip 
                                  label={project.availability.status}
                                  color="success"
                                  size="small"
                                  icon={<CheckCircleIcon />}
                                />
                                {project.availability.dates?.length && (
                                  <Typography variant="body2">
                                    {project.availability.dates.join(', ')}
                                  </Typography>
                                )}
                              </Stack>
                            </Box>
                          </Grid>
                        )}
                      </Grid>
                    </CardContent>
                  </Card>

                  {/* Survey Answers */}
                  {survey.length > 0 && (
                    <Card elevation={2} sx={{ borderRadius: 3 }}>
                      <Box sx={{ 
                        background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
                        p: 2,
                        color: 'white'
                      }}>
                        <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', fontWeight: 600 }}>
                          <HelpOutlineIcon sx={{ mr: 1 }} />
                          Survey Answers
                        </Typography>
                      </Box>
                      
                      <CardContent sx={{ p: 3 }}>
                        <Stack spacing={3}>
                          {survey.map((sa: any, i: number) => (
                            <Box key={i}>
                              <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 2, color: 'primary.main' }}>
                                {sa.question_text}
                              </Typography>
                              <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                                {sa.answer_text?.map((ans: string, j: number) => (
                                  <Chip 
                                    key={j} 
                                    label={ans} 
                                    variant="outlined"
                                    sx={{ 
                                      borderColor: 'primary.main',
                                      color: 'primary.main',
                                      fontWeight: 500
                                    }}
                                  />
                                ))}
                              </Stack>
                            </Box>
                          ))}
                        </Stack>
                      </CardContent>
                    </Card>
                  )}
                </>
              )}
            </Stack>
          </Grid>
        </Grid>

        {/* Attachments Section */}
        {atts.length > 0 && (
          <Card elevation={2} sx={{ borderRadius: 3, mt: 4 }}>
            <Box sx={{ 
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              p: 2,
              color: 'white'
            }}>
              <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', fontWeight: 600 }}>
                <AttachFileIcon sx={{ mr: 1 }} />
                Attachments ({atts.length})
              </Typography>
            </Box>
            
            <CardContent sx={{ p: 3 }}>
              <Grid container spacing={3}>
                {atts.map((att: any) => {
                  const proxyUrl = `/yelp/leads/${leadId}/attachments/${encodeURIComponent(att.id)}/`;
                  return (
                    <Grid item xs={12} sm={6} md={4} key={att.id}>
                      <Card 
                        variant="outlined" 
                        sx={{ 
                          borderRadius: 3,
                          overflow: 'hidden',
                          transition: 'all 0.3s ease-in-out',
                          '&:hover': {
                            transform: 'translateY(-4px)',
                            boxShadow: 3
                          }
                        }}
                      >
                        <Box
                          component="a"
                          href={att.url}
                          target="_blank"
                          rel="noreferrer"
                          sx={{ display: 'block', textDecoration: 'none' }}
                        >
                          <Box
                            component="img"
                            src={proxyUrl}
                            alt={att.resource_name}
                            sx={{ 
                              width: '100%', 
                              height: 200,
                              objectFit: 'cover',
                              backgroundColor: 'grey.100'
                            }}
                          />
                        </Box>
                        <CardContent sx={{ p: 2 }}>
                          <Typography 
                            variant="body2" 
                            align="center"
                            sx={{ 
                              fontWeight: 500,
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap'
                            }}
                          >
                            {att.resource_name}
                          </Typography>
                        </CardContent>
                      </Card>
                    </Grid>
                  );
                })}
              </Grid>
            </CardContent>
          </Card>
        )}
      </Container>
    </Box>
  );
};

export default LeadDetail;
