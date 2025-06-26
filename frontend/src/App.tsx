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
  Drawer,
  IconButton,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Box,
  useMediaQuery,
  useTheme,
} from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';

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
import SettingsTemplates from "./SettingsTemplates";

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
axios.defaults.baseURL = process.env.REACT_APP_API_BASE_URL
  ? `${process.env.REACT_APP_API_BASE_URL}/api`
  : 'http://localhost:8000/api';


// ---------------------------------------------
// Main component with all routes and responsive drawer
// ---------------------------------------------
const drawerWidth = 240;

const App: React.FC = () => {
  const [mobileOpen, setMobileOpen] = React.useState(false);
  const themeHook = useTheme();
  const isMobile = useMediaQuery(themeHook.breakpoints.down('sm'));

  const handleDrawerToggle = () => {
    setMobileOpen(prev => !prev);
  };

  const drawer = (
    <div>
      <Toolbar />
      <List>
        <ListItem disablePadding>
          <ListItemButton component={RouterLink} to="/" onClick={() => setMobileOpen(false)}>
            <ListItemIcon>
              <HomeIcon />
            </ListItemIcon>
            <ListItemText primary="Home" />
          </ListItemButton>
        </ListItem>
        <ListItem disablePadding>
          <ListItemButton component={RouterLink} to="/events" onClick={() => setMobileOpen(false)}>
            <ListItemIcon>
              <EventIcon />
            </ListItemIcon>
            <ListItemText primary="Events" />
          </ListItemButton>
        </ListItem>
        <ListItem disablePadding>
          <ListItemButton component={RouterLink} to="/businesses" onClick={() => setMobileOpen(false)}>
            <ListItemIcon>
              <BusinessIcon />
            </ListItemIcon>
            <ListItemText primary="Businesses" />
          </ListItemButton>
        </ListItem>
        <ListItem disablePadding>
          <ListItemButton component={RouterLink} to="/tokens" onClick={() => setMobileOpen(false)}>
            <ListItemIcon>
              <VpnKeyIcon />
            </ListItemIcon>
            <ListItemText primary="Tokens" />
          </ListItemButton>
        </ListItem>
        <ListItem disablePadding>
          <ListItemButton component={RouterLink} to="/tasks" onClick={() => setMobileOpen(false)}>
            <ListItemIcon>
              <ListAltIcon />
            </ListItemIcon>
            <ListItemText primary="Tasks" />
          </ListItemButton>
        </ListItem>
        <ListItem disablePadding>
          <ListItemButton component={RouterLink} to="/templates" onClick={() => setMobileOpen(false)}>
            <ListItemIcon>
              <ListAltIcon />
            </ListItemIcon>
            <ListItemText primary="Templates" />
          </ListItemButton>
        </ListItem>
      </List>
    </div>
  );

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Router>
        <Box sx={{ display: 'flex' }}>
          <AppBar position="fixed" sx={{ zIndex: themeHook.zIndex.drawer + 1 }}>
            <Toolbar>
              {isMobile && (
                <IconButton
                  color="inherit"
                  edge="start"
                  onClick={handleDrawerToggle}
                  sx={{ mr: 2, display: { sm: 'none' } }}
                >
                  <MenuIcon />
                </IconButton>
              )}
              <Typography variant="h6" noWrap component="div">
                Yelp Integration Dashboard
              </Typography>
            </Toolbar>
          </AppBar>

          <Box component="nav" sx={{ width: { sm: drawerWidth }, flexShrink: { sm: 0 } }} aria-label="mailbox folders">
            <Drawer
              variant={isMobile ? 'temporary' : 'permanent'}
              open={isMobile ? mobileOpen : true}
              onClose={handleDrawerToggle}
              ModalProps={{ keepMounted: true }}
              sx={{
                '& .MuiDrawer-paper': { width: drawerWidth, boxSizing: 'border-box' },
              }}
            >
              {drawer}
            </Drawer>
          </Box>

          <Box component="main" sx={{ flexGrow: 1, p: 3, width: { sm: `calc(100% - ${drawerWidth}px)` } }}>
            <Toolbar />
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
              <Route path="/templates" element={<SettingsTemplates />} />
            </Routes>
          </Box>
        </Box>
      </Router>
    </ThemeProvider>
  );
};

export default App;
