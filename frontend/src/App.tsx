import axios from 'axios';
import {
  BrowserRouter as Router,
  Routes,
  Route,
  Link as RouterLink,
} from 'react-router-dom';

// --- Material-UI Imports ---
import {
  AppBar,
  Toolbar,
  Typography,

  Button,
  CssBaseline,
  ThemeProvider,
  createTheme,
} from '@mui/material';

// --- Material-UI Icons ---
import HomeIcon from '@mui/icons-material/Home';
import EventIcon from '@mui/icons-material/Event';
import BusinessIcon from '@mui/icons-material/Business';
import VpnKeyIcon from '@mui/icons-material/VpnKey';
import ListAltIcon from '@mui/icons-material/ListAlt';
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

// Базовий URL для API
axios.defaults.baseURL = process.env.REACT_APP_API_BASE_URL
  ? `${process.env.REACT_APP_API_BASE_URL}/api`
  : 'http://localhost:8000/api';


// ---------------------------------------------
// Головний компонент з усіма маршрутами
// ---------------------------------------------
const App: React.FC = () => (
  <ThemeProvider theme={theme}>
    <CssBaseline />
    <Router>
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            Yelp Integration Dashboard
          </Typography>
          <Button color="inherit" component={RouterLink} to="/" startIcon={<HomeIcon />}>Home</Button>
          <Button color="inherit" component={RouterLink} to="/events" startIcon={<EventIcon />}>Events</Button>
          <Button color="inherit" component={RouterLink} to="/businesses" startIcon={<BusinessIcon />}>Businesses</Button>
          <Button color="inherit" component={RouterLink} to="/tokens" startIcon={<VpnKeyIcon />}>Tokens</Button>
          <Button color="inherit" component={RouterLink} to="/tasks" startIcon={<ListAltIcon />}>Tasks</Button>
        </Toolbar>
      </AppBar>
      <main>
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
          <Route path="/tasks" element={<TaskLogs />} />
        </Routes>
      </main>
    </Router>
  </ThemeProvider>
);

export default App;
