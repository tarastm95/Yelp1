import React, { useEffect, useState } from 'react';
import axios from 'axios';
import {
  Container,
  Typography,
  Box,
  Paper,
  CircularProgress,
  Alert,
  Card,
  CardContent,
  Grid,
  Stack,
  Chip,
  Avatar,
  LinearProgress,
  Divider,
  Button,
  alpha,
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import BusinessInfoCard from './BusinessInfoCard';

// Icons
import VpnKeyIcon from '@mui/icons-material/VpnKey';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import WarningIcon from '@mui/icons-material/Warning';
import RefreshIcon from '@mui/icons-material/Refresh';
import SecurityIcon from '@mui/icons-material/Security';
import BusinessIcon from '@mui/icons-material/Business';
import LoginIcon from '@mui/icons-material/Login';

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
  const navigate = useNavigate();

  useEffect(() => {
    axios.get<TokenInfo[]>('/tokens/')
      .then(res => setTokens(res.data))
      .catch(() => setTokens([]))
      .finally(() => setLoading(false));
  }, []);

  const refreshData = () => {
    setLoading(true);
    axios.get<TokenInfo[]>('/tokens/')
      .then(res => setTokens(res.data))
      .catch(() => setTokens([]))
      .finally(() => setLoading(false));
  };

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

  // Calculate overall status
  const now = new Date();
  const activeTokens = tokens.filter(t => {
    const exp = t.expires_at ? new Date(t.expires_at) : null;
    const refreshExpires = new Date(t.updated_at).getTime() + 365 * 86400 * 1000;
    return !((exp && exp.getTime() <= now.getTime()) || (now.getTime() >= refreshExpires));
  });

  const expiredTokens = tokens.filter(t => {
    const exp = t.expires_at ? new Date(t.expires_at) : null;
    return exp && exp.getTime() <= now.getTime();
  });

  const refreshExpiredTokens = tokens.filter(t => {
    const refreshExpires = new Date(t.updated_at).getTime() + 365 * 86400 * 1000;
    return now.getTime() >= refreshExpires;
  });

  return (
    <Box sx={{ 
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)',
      pb: 6
    }}>
      <Container maxWidth="xl" sx={{ pt: 4 }}>
        {/* Hero Section */}
        <Card 
          elevation={4}
          sx={{ 
            borderRadius: 4,
            overflow: 'hidden',
            mb: 4,
            background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
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
              {/* Icon */}
              <Avatar
                sx={{
                  width: 100,
                  height: 100,
                  background: 'rgba(255, 255, 255, 0.2)',
                  backdropFilter: 'blur(10px)',
                  border: '4px solid rgba(255, 255, 255, 0.3)',
                  boxShadow: '0 8px 32px rgba(0, 0, 0, 0.1)'
                }}
              >
                <SecurityIcon sx={{ fontSize: '2.5rem', color: 'white' }} />
              </Avatar>
              
              {/* Info */}
              <Box sx={{ flex: 1, textAlign: { xs: 'center', md: 'left' } }}>
                <Typography variant="h3" sx={{ fontWeight: 800, mb: 1 }}>
                  Token & Business Status
                </Typography>
                
                <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ mb: 2 }}>
                  <Chip
                    icon={<BusinessIcon />}
                    label={`${tokens.length} Business${tokens.length !== 1 ? 'es' : ''}`}
                    sx={{
                      background: 'rgba(255, 255, 255, 0.2)',
                      color: 'white',
                      fontWeight: 600,
                      '& .MuiChip-icon': { color: 'white' }
                    }}
                  />
                  
                  <Chip
                    icon={activeTokens.length === tokens.length ? <CheckCircleIcon /> : <WarningIcon />}
                    label={`${activeTokens.length}/${tokens.length} Active`}
                    sx={{
                      background: activeTokens.length === tokens.length 
                        ? 'rgba(76, 175, 80, 0.8)' 
                        : 'rgba(255, 152, 0, 0.8)',
                      color: 'white',
                      fontWeight: 600,
                      '& .MuiChip-icon': { color: 'white' }
                    }}
                  />
                </Stack>
                
                <Typography variant="h6" sx={{ opacity: 0.9 }}>
                  Monitor your Yelp authorization status and business connections
                </Typography>
              </Box>
              
              {/* Refresh Button */}
              <Button
                onClick={refreshData}
                startIcon={<RefreshIcon />}
                sx={{
                  background: 'rgba(255, 255, 255, 0.2)',
                  backdropFilter: 'blur(10px)',
                  borderRadius: 3,
                  px: 3,
                  py: 1.5,
                  fontWeight: 600,
                  color: 'white',
                  border: '1px solid rgba(255, 255, 255, 0.3)',
                  
                  '&:hover': {
                    background: 'rgba(255, 255, 255, 0.3)',
                    transform: 'translateY(-2px)',
                    boxShadow: '0 8px 24px rgba(255, 255, 255, 0.2)',
                  }
                }}
              >
                Refresh Status
              </Button>
            </Stack>
          </CardContent>
        </Card>

        {/* Status Overview Cards */}
        <Grid container spacing={3} sx={{ mb: 4 }}>
          <Grid item xs={12} md={4}>
            <Card elevation={2} sx={{ borderRadius: 3, height: '100%' }}>
              <CardContent sx={{ p: 3, textAlign: 'center' }}>
                <Avatar
                  sx={{
                    width: 64,
                    height: 64,
                    mx: 'auto',
                    mb: 2,
                    background: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)'
                  }}
                >
                  <CheckCircleIcon sx={{ fontSize: '2rem', color: 'white' }} />
                </Avatar>
                
                <Typography variant="h4" sx={{ fontWeight: 700, mb: 1, color: 'success.main' }}>
                  {activeTokens.length}
                </Typography>
                
                <Typography variant="h6" sx={{ fontWeight: 600, mb: 1 }}>
                  Active Tokens
                </Typography>
                
                <Typography variant="body2" color="text.secondary">
                  Working properly and ready to use
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={4}>
            <Card elevation={2} sx={{ borderRadius: 3, height: '100%' }}>
              <CardContent sx={{ p: 3, textAlign: 'center' }}>
                <Avatar
                  sx={{
                    width: 64,
                    height: 64,
                    mx: 'auto',
                    mb: 2,
                    background: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)'
                  }}
                >
                  <WarningIcon sx={{ fontSize: '2rem', color: 'white' }} />
                </Avatar>
                
                <Typography variant="h4" sx={{ fontWeight: 700, mb: 1, color: 'warning.main' }}>
                  {expiredTokens.length}
                </Typography>
                
                <Typography variant="h6" sx={{ fontWeight: 600, mb: 1 }}>
                  Expired Tokens
                </Typography>
                
                <Typography variant="body2" color="text.secondary">
                  Need to be refreshed automatically
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={4}>
            <Card elevation={2} sx={{ borderRadius: 3, height: '100%' }}>
              <CardContent sx={{ p: 3, textAlign: 'center' }}>
                <Avatar
                  sx={{
                    width: 64,
                    height: 64,
                    mx: 'auto',
                    mb: 2,
                    background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)'
                  }}
                >
                  <ErrorIcon sx={{ fontSize: '2rem', color: 'white' }} />
                </Avatar>
                
                <Typography variant="h4" sx={{ fontWeight: 700, mb: 1, color: 'error.main' }}>
                  {refreshExpiredTokens.length}
                </Typography>
                
                <Typography variant="h6" sx={{ fontWeight: 600, mb: 1 }}>
                  Need Reauth
                </Typography>
                
                <Typography variant="body2" color="text.secondary">
                  Require manual reauthorization
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        {/* Empty State */}
        {tokens.length === 0 && (
          <Paper 
            sx={{ 
              p: 6, 
              textAlign: 'center', 
              backgroundColor: 'grey.50',
              borderRadius: 3,
              border: '2px dashed',
              borderColor: 'grey.300'
            }}
          >
            <VpnKeyIcon sx={{ fontSize: 64, color: 'grey.400', mb: 2 }} />
            <Typography variant="h6" color="text.secondary" sx={{ mb: 1 }}>
              No tokens found
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              You need to authorize with Yelp to start using the integration
            </Typography>
            <Button
              variant="contained"
              startIcon={<LoginIcon />}
              onClick={() => navigate('/auth')}
              sx={{
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                borderRadius: 2,
                px: 4,
                py: 1.5,
                fontWeight: 600,
                '&:hover': {
                  background: 'linear-gradient(135deg, #5a6fd8 0%, #6b4190 100%)',
                  transform: 'translateY(-2px)',
                  boxShadow: 3
                }
              }}
            >
              Authorize with Yelp
            </Button>
          </Paper>
        )}

        {/* Token Details */}
        <Grid container spacing={3}>
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

            const refreshExpires = new Date(t.updated_at).getTime() + 365 * 86400 * 1000;
            const refreshExpired = now.getTime() >= refreshExpires;

            // Calculate progress percentage for access token
            const totalDuration = exp ? 3600 : 0; // Typically 1 hour for access tokens
            const progressPercentage = exp && !expired 
              ? Math.max(0, Math.min(100, (remainingSec! / totalDuration) * 100))
              : expired ? 0 : 100;

            return (
              <Grid item xs={12} lg={6} key={t.business_id}>
                <Card
                  elevation={2}
                  sx={{
                    borderRadius: 3,
                    overflow: 'hidden',
                    position: 'relative',
                    transition: 'all 0.3s ease-in-out',
                    border: '2px solid',
                    borderColor: expired || refreshExpired ? 'error.main' : activeTokens.find(at => at.business_id === t.business_id) ? 'success.main' : 'grey.200',
                    
                    '&:hover': {
                      transform: 'translateY(-4px)',
                      boxShadow: expired || refreshExpired 
                        ? '0 12px 40px rgba(244, 67, 54, 0.2)' 
                        : '0 8px 32px rgba(0, 0, 0, 0.12)',
                    }
                  }}
                >
                  {/* Status Header */}
                  <Box sx={{ 
                    background: expired || refreshExpired 
                      ? 'linear-gradient(135deg, #f87171 0%, #ef4444 100%)'
                      : activeTokens.find(at => at.business_id === t.business_id)
                        ? 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)'
                        : 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
                    p: 2,
                    color: 'white'
                  }}>
                    <Stack direction="row" alignItems="center" spacing={2}>
                      <Avatar
                        sx={{
                          background: 'rgba(255, 255, 255, 0.2)',
                          backdropFilter: 'blur(10px)',
                          width: 40,
                          height: 40
                        }}
                      >
                        {expired || refreshExpired ? <ErrorIcon /> : <VpnKeyIcon />}
                      </Avatar>
                      
                      <Box sx={{ flex: 1 }}>
                        <Typography variant="h6" sx={{ fontWeight: 700 }}>
                          {t.business?.name || 'Unknown Business'}
                        </Typography>
                        <Typography variant="caption" sx={{ opacity: 0.9 }}>
                          Business ID: {t.business_id}
                        </Typography>
                      </Box>
                      
                      <Chip
                        label={
                          refreshExpired ? 'Reauth Required' :
                          expired ? 'Token Expired' : 
                          'Active'
                        }
                        size="small"
                        sx={{
                          background: 'rgba(255, 255, 255, 0.2)',
                          color: 'white',
                          fontWeight: 600
                        }}
                      />
                    </Stack>
                  </Box>

                  <CardContent sx={{ p: 3 }}>
                    {/* Business Info */}
                    {t.business && (
                      <Box sx={{ mb: 3 }}>
                        <BusinessInfoCard business={t.business} />
                      </Box>
                    )}

                    <Divider sx={{ my: 2 }} />

                    {/* Token Information */}
                    <Stack spacing={2}>
                      {/* Access Token Status */}
                      <Box>
                        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
                          <Typography variant="subtitle2" sx={{ fontWeight: 600, display: 'flex', alignItems: 'center' }}>
                            <AccessTimeIcon sx={{ mr: 1, fontSize: 16 }} />
                            Access Token
                          </Typography>
                          
                          {exp && !expired && (
                            <Typography variant="caption" color="text.secondary">
                              {days > 0 && `${days}d `}
                              {hours > 0 && `${hours}h `}
                              {minutes}m remaining
                            </Typography>
                          )}
                        </Stack>
                        
                        {exp && (
                          <LinearProgress
                            variant="determinate"
                            value={progressPercentage}
                            sx={{
                              height: 8,
                              borderRadius: 4,
                              backgroundColor: 'grey.200',
                              '& .MuiLinearProgress-bar': {
                                background: expired 
                                  ? 'linear-gradient(135deg, #f87171 0%, #ef4444 100%)'
                                  : progressPercentage > 30
                                    ? 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)'
                                    : 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
                                borderRadius: 4
                              }
                            }}
                          />
                        )}
                        
                        {!exp && (
                          <Typography variant="body2" color="text.secondary">
                            No expiration time available
                          </Typography>
                        )}
                      </Box>

                      {/* Updated Info */}
                      <Box sx={{ 
                        p: 2, 
                        backgroundColor: 'grey.50', 
                        borderRadius: 2,
                        border: '1px solid',
                        borderColor: 'grey.200'
                      }}>
                        <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
                          LAST UPDATED
                        </Typography>
                        <Typography variant="body2" sx={{ fontWeight: 500, mt: 0.5 }}>
                          {new Date(t.updated_at).toLocaleString()}
                        </Typography>
                      </Box>

                      {/* Status Alerts */}
                      {expired && (
                        <Alert 
                          severity="warning" 
                          sx={{ borderRadius: 2 }}
                          icon={<WarningIcon />}
                        >
                          Access token has expired but will be refreshed automatically
                        </Alert>
                      )}
                      
                      {refreshExpired && (
                        <Alert 
                          severity="error" 
                          sx={{ borderRadius: 2 }}
                          icon={<ErrorIcon />}
                          action={
                            <Button 
                              color="inherit" 
                              size="small"
                              onClick={() => navigate('/auth')}
                              sx={{ fontWeight: 600 }}
                            >
                              Reauthorize
                            </Button>
                          }
                        >
                          Refresh token expired - manual reauthorization required
                        </Alert>
                      )}
                    </Stack>
                  </CardContent>
                </Card>
              </Grid>
            );
          })}
        </Grid>

        {/* Quick Actions */}
        {tokens.length > 0 && (refreshExpiredTokens.length > 0 || expiredTokens.length > 0) && (
          <Card elevation={2} sx={{ borderRadius: 3, mt: 4 }}>
            <Box sx={{ 
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              p: 2,
              color: 'white'
            }}>
              <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', fontWeight: 600 }}>
                <LoginIcon sx={{ mr: 1 }} />
                Quick Actions
              </Typography>
            </Box>
            
            <CardContent sx={{ p: 3 }}>
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
                {refreshExpiredTokens.length > 0 && (
                  <Button
                    variant="contained"
                    startIcon={<LoginIcon />}
                    onClick={() => navigate('/auth')}
                    sx={{
                      background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
                      borderRadius: 2,
                      px: 3,
                      py: 1.5,
                      fontWeight: 600,
                      '&:hover': {
                        background: 'linear-gradient(135deg, #e082ea 0%, #e4485b 100%)',
                        transform: 'translateY(-2px)',
                        boxShadow: 3
                      }
                    }}
                  >
                    Reauthorize ({refreshExpiredTokens.length})
                  </Button>
                )}
                
                <Button
                  variant="outlined"
                  startIcon={<RefreshIcon />}
                  onClick={refreshData}
                  sx={{
                    borderColor: 'primary.main',
                    color: 'primary.main',
                    borderRadius: 2,
                    px: 3,
                    py: 1.5,
                    fontWeight: 600,
                    '&:hover': {
                      borderColor: 'primary.dark',
                      backgroundColor: 'primary.50',
                      transform: 'translateY(-1px)'
                    }
                  }}
                >
                  Refresh All Status
                </Button>
              </Stack>
            </CardContent>
          </Card>
        )}
      </Container>
    </Box>
  );
};

export default TokenStatus;
