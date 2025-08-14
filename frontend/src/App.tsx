import axios from 'axios';
import { useState, FC } from 'react';
import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
} from 'react-router-dom';

// --- Material-UI Imports ---
import {
  CssBaseline,
  ThemeProvider,
  createTheme,
  Box,
} from '@mui/material';

// --- Material-UI Icons ---

import EventDetail from "./Events/EventDetail";
import EventsPage from "./EventsPage/EventsPage";
import Home from "./Home";
import YelpCallback from "./YelpCallback";
import AutoResponseSettings from "./AutoResponseSettings";
import AIGlobalSettings from "./AIGlobalSettings";
import YelpAuth from "./YelpAuth";
import ClientDetails from "./ClientDetails/ClientDetails";
import TokenStatus from "./TokenStatus";
import TaskLogs from "./TaskLogs";
import SMSLogs from "./SMSLogs";
import Subscriptions from "./Subscriptions";
import LoginPage from "./LoginPage";
import TopMenu from "./TopMenu";
import TimeBasedGreetings from "./TimeBasedGreetings";
import JobMappings from "./JobMappings";
import Analytics from "./Analytics";

// A enhanced theme for the application with modern design
const theme = createTheme({
  palette: {
    primary: {
      main: '#667eea',
      light: '#98a8f7',
      dark: '#4a5bb8',
      contrastText: '#ffffff',
    },
    secondary: {
      main: '#f093fb',
      light: '#f5b6fc',
      dark: '#d066e8',
      contrastText: '#ffffff',
    },
    background: {
      default: '#f5f7fa',
      paper: '#ffffff',
    },
    text: {
      primary: '#1a1a1a',
      secondary: '#6b7280',
    },
    success: {
      main: '#43e97b',
      light: '#72f099',
      dark: '#2eb85c',
    },
    warning: {
      main: '#fbbf24',
      light: '#fcd34d',
      dark: '#f59e0b',
    },
    error: {
      main: '#f87171',
      light: '#fca5a5',
      dark: '#ef4444',
    },
    info: {
      main: '#60a5fa',
      light: '#93c5fd',
      dark: '#3b82f6',
    },
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    h1: {
      fontWeight: 800,
      fontSize: '2.5rem',
      lineHeight: 1.2,
    },
    h2: {
      fontWeight: 700,
      fontSize: '2rem',
      lineHeight: 1.3,
    },
    h3: {
      fontWeight: 600,
      fontSize: '1.75rem',
      lineHeight: 1.4,
    },
    h4: {
      fontWeight: 600,
      fontSize: '1.5rem',
      lineHeight: 1.4,
    },
    h5: {
      fontWeight: 600,
      fontSize: '1.25rem',
      lineHeight: 1.5,
    },
    h6: {
      fontWeight: 600,
      fontSize: '1.125rem',
      lineHeight: 1.5,
    },
    body1: {
      fontSize: '1rem',
      lineHeight: 1.6,
    },
    body2: {
      fontSize: '0.875rem',
      lineHeight: 1.5,
    },
    button: {
      fontWeight: 600,
      textTransform: 'none',
    },
  },
  shape: {
    borderRadius: 12,
  },
  shadows: [
    'none',
    '0px 2px 4px rgba(0, 0, 0, 0.05)',
    '0px 4px 8px rgba(0, 0, 0, 0.08)',
    '0px 8px 16px rgba(0, 0, 0, 0.1)',
    '0px 12px 24px rgba(0, 0, 0, 0.12)',
    '0px 16px 32px rgba(0, 0, 0, 0.15)',
    '0px 20px 40px rgba(0, 0, 0, 0.18)',
    '0px 24px 48px rgba(0, 0, 0, 0.2)',
    '0px 28px 56px rgba(0, 0, 0, 0.22)',
    '0px 32px 64px rgba(0, 0, 0, 0.24)',
    '0px 36px 72px rgba(0, 0, 0, 0.26)',
    '0px 40px 80px rgba(0, 0, 0, 0.28)',
    '0px 44px 88px rgba(0, 0, 0, 0.3)',
    '0px 48px 96px rgba(0, 0, 0, 0.32)',
    '0px 52px 104px rgba(0, 0, 0, 0.34)',
    '0px 56px 112px rgba(0, 0, 0, 0.36)',
    '0px 60px 120px rgba(0, 0, 0, 0.38)',
    '0px 64px 128px rgba(0, 0, 0, 0.4)',
    '0px 68px 136px rgba(0, 0, 0, 0.42)',
    '0px 72px 144px rgba(0, 0, 0, 0.44)',
    '0px 76px 152px rgba(0, 0, 0, 0.46)',
    '0px 80px 160px rgba(0, 0, 0, 0.48)',
    '0px 84px 168px rgba(0, 0, 0, 0.5)',
    '0px 88px 176px rgba(0, 0, 0, 0.52)',
    '0px 92px 184px rgba(0, 0, 0, 0.54)',
  ],
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          fontWeight: 600,
          padding: '8px 24px',
          boxShadow: 'none',
          '&:hover': {
            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
            transform: 'translateY(-2px)',
          },
        },
        contained: {
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          '&:hover': {
            background: 'linear-gradient(135deg, #5a6fd8 0%, #6b4190 100%)',
          },
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 16,
          border: '1px solid rgba(0, 0, 0, 0.08)',
          boxShadow: '0 4px 12px rgba(0, 0, 0, 0.05)',
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          borderRadius: 16,
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            borderRadius: 12,
            '&:hover .MuiOutlinedInput-notchedOutline': {
              borderColor: '#667eea',
            },
          },
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          fontWeight: 500,
        },
      },
    },
  },
});

// Base URL for the API
axios.defaults.baseURL = import.meta.env.VITE_API_BASE_URL
  ? `${import.meta.env.VITE_API_BASE_URL}/api`
  : 'http://46.62.139.177:8000/api';


// ---------------------------------------------
// Main component with top navigation menu
// ---------------------------------------------

const App: FC = () => {
  const [authenticated, setAuthenticated] = useState(
    localStorage.getItem('isAuthenticated') === 'true'
  );

  const handleLogout = () => {
    localStorage.removeItem('isAuthenticated');
    setAuthenticated(false);
  };

  if (!authenticated) {
    return (
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <Router>
          <Routes>
            <Route
              path="/login"
              element={<LoginPage onLogin={() => setAuthenticated(true)} />}
            />
            <Route path="*" element={<Navigate to="/login" replace />} />
          </Routes>
        </Router>
      </ThemeProvider>
    );
  }


  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Router>
        <TopMenu onLogout={handleLogout} />
        <Box component="main" sx={{ p: 3 }}>
                      <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/events" element={<EventsPage />} />
              <Route path="/events/:id" element={<EventDetail />} />
              <Route path="/leads/:id" element={<ClientDetails />} />
              <Route path="/auth" element={<YelpAuth />} />
              <Route path="/callback" element={<YelpCallback />} />
              <Route path="/settings" element={<AutoResponseSettings />} />
              <Route path="/ai-settings" element={<AIGlobalSettings />} />
              <Route path="/time-greetings" element={<TimeBasedGreetings />} />
              <Route path="/job-mappings" element={<JobMappings />} />
              <Route path="/tokens" element={<TokenStatus />} />
              <Route path="/subscriptions" element={<Subscriptions />} />
              <Route path="/tasks" element={<TaskLogs />} />
              <Route path="/sms-logs" element={<SMSLogs />} />
              <Route path="/analytics" element={<Analytics />} />
            </Routes>
        </Box>
      </Router>
    </ThemeProvider>
  );
};

export default App;
