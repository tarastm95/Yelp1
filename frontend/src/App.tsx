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
import YelpAuth from "./YelpAuth";
import ClientDetails from "./ClientDetails/ClientDetails";
import BusinessSelector from "./BusinessSelector";
import TokenStatus from "./TokenStatus";
import TaskLogs from "./TaskLogs";
import SettingsTemplates from "./SettingsTemplates";
import Subscriptions from "./Subscriptions";
import LoginPage from "./LoginPage";
import TopMenu from "./TopMenu";

// A default theme for the application
const theme = createTheme({
  palette: {
    primary: {
      main: '#3f51b5',
    },
    secondary: {
      main: '#f50057',
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
        <TopMenu />
        <Box component="main" sx={{ p: 3 }}>
          <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/events" element={<EventsPage />} />
              <Route path="/events/:id" element={<EventDetail />} />
              <Route path="/leads/:id" element={<ClientDetails />} />
              <Route path="/auth" element={<YelpAuth />} />
              <Route path="/callback" element={<YelpCallback />} />
              <Route path="/businesses" element={<BusinessSelector />} />
              <Route path="/settings" element={<AutoResponseSettings />} />
              <Route path="/tokens" element={<TokenStatus />} />
              <Route path="/subscriptions" element={<Subscriptions />} />
              <Route path="/tasks" element={<TaskLogs />} />
              <Route path="/templates" element={<SettingsTemplates />} />
            </Routes>
        </Box>
      </Router>
    </ThemeProvider>
  );
};

export default App;
