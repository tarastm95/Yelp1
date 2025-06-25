// src/components/AutoResponseSettings.tsx
import React, { FC, useState, useEffect, useRef } from 'react';
import axios from 'axios';

// MUI imports
import {
  Container,
  Paper,
  Typography,
  TextField,
  Switch,
  FormControlLabel,
  Button,
  Stack,
  Box,
  Select,
  MenuItem,
  Snackbar,
  Alert,
  CircularProgress,
  List,
  ListItem,
  ListItemText,
  IconButton,
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import BusinessInfoCard from './BusinessInfoCard';

// Helper placeholders used in message templates

const PLACEHOLDERS = ['{name}', '{jobs}', '{sep}'] as const;
type Placeholder = typeof PLACEHOLDERS[number];

interface Business {
  business_id: string;
  name: string;
  location?: string;
  time_zone?: string;
  details?: any;
}

interface AutoResponse {
  id: number;
  enabled: boolean;
  greeting_template: string;
  include_name: boolean;
  include_jobs: boolean;
  follow_up_template: string;
  follow_up_delay: number;
  export_to_sheets: boolean;
}

interface FollowUpTemplate {
  id: number;
  name: string;
  template: string;
  delay: number; // seconds
  open_from: string;
  open_to: string;
  active: boolean;
}

const AutoResponseSettings: FC = () => {
  // businesses
  const [businesses, setBusinesses] = useState<Business[]>([]);
  const [selectedBusiness, setSelectedBusiness] = useState('');

  // auto-response state
  const [settingsId, setSettingsId] = useState<number | null>(null);
  const [enabled, setEnabled] = useState(false);
  const [greetingTemplate, setGreetingTemplate] = useState('');
  const [includeName, setIncludeName] = useState(true);
  const [includeJobs, setIncludeJobs] = useState(true);
  const [followUpTemplate, setFollowUpTemplate] = useState('');
  const [followDelayDays, setFollowDelayDays] = useState(0);
  const [followDelayHours, setFollowDelayHours] = useState(1);
  const [followDelayMinutes, setFollowDelayMinutes] = useState(0);
  const [followDelaySeconds, setFollowDelaySeconds] = useState(0);
  const [exportToSheets, setExportToSheets] = useState(false);

  // follow-up templates
  const [templates, setTemplates] = useState<FollowUpTemplate[]>([]);
  const [newText, setNewText] = useState('');
  const [newDelayDays, setNewDelayDays] = useState(0);
  const [newDelayHours, setNewDelayHours] = useState(1);
  const [newDelayMinutes, setNewDelayMinutes] = useState(0);
  const [newDelaySeconds, setNewDelaySeconds] = useState(0);
  const [newOpenFrom, setNewOpenFrom] = useState('08:00');
  const [newOpenTo, setNewOpenTo] = useState('20:00');

  // UI state
  const [loading, setLoading] = useState(true);
  const [tplLoading, setTplLoading] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState('');

  // refs for placeholder insertion
  const greetingRef = useRef<HTMLTextAreaElement | null>(null);
  const followRef = useRef<HTMLTextAreaElement | null>(null);
  const tplRef = useRef<HTMLTextAreaElement | null>(null);

  // helper to insert placeholder
  const insertPlaceholder = (
    ph: Placeholder,
    target: 'greeting' | 'follow' | 'template'
  ) => {
    let ref: HTMLTextAreaElement | null = null;
    let base = '';
    let setter: (v: string) => void = () => {};
    if (target === 'greeting') {
      ref = greetingRef.current;
      base = greetingTemplate;
      setter = setGreetingTemplate;
    } else if (target === 'follow') {
      ref = followRef.current;
      base = followUpTemplate;
      setter = setFollowUpTemplate;
    } else {
      ref = tplRef.current;
      base = newText;
      setter = setNewText;
    }
    if (!ref) return;
    const start = ref.selectionStart ?? 0;
    const end = ref.selectionEnd ?? 0;
    const updated = base.slice(0, start) + ph + base.slice(end);
    setter(updated);
    setTimeout(() => {
      ref!.focus();
      ref!.setSelectionRange(start + ph.length, start + ph.length);
    }, 0);
  };

  const formatDelay = (secs: number) => {
    const d = Math.floor(secs / 86400);
    secs %= 86400;
    const h = Math.floor(secs / 3600);
    secs %= 3600;
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    const parts = [] as string[];
    if (d) parts.push(`${d}d`);
    if (h) parts.push(`${h}h`);
    if (m) parts.push(`${m}m`);
    if (s) parts.push(`${s}s`);
    return parts.join(' ') || '0s';
  };

  // load settings
  const loadSettings = (biz?: string) => {
    setLoading(true);
    const url = biz ? `/settings/auto-response/?business_id=${biz}` : '/settings/auto-response/';
    axios.get<AutoResponse>(url)
      .then(res => {
        const d = res.data;
        setSettingsId(d.id);
        setEnabled(d.enabled);
        setGreetingTemplate(d.greeting_template);
        setIncludeName(d.include_name);
        setIncludeJobs(d.include_jobs);
        setFollowUpTemplate(d.follow_up_template);
        let secs = d.follow_up_delay;
        setFollowDelayDays(Math.floor(secs / 86400));
        secs %= 86400;
        setFollowDelayHours(Math.floor(secs / 3600));
        secs %= 3600;
        setFollowDelayMinutes(Math.floor(secs / 60));
        setFollowDelaySeconds(secs % 60);
        setExportToSheets(d.export_to_sheets);
      })
      .catch(() => setError('Не вдалося завантажити налаштування.'))
      .finally(() => setLoading(false));
  };

  const loadTemplates = (biz?: string) => {
    setTplLoading(true);
    const url = biz ? `/follow-up-templates/?business_id=${biz}` : '/follow-up-templates/';
    axios.get<FollowUpTemplate[]>(url)
      .then(res => setTemplates(res.data))
      .catch(() => setError('Не вдалося завантажити шаблони follow-up.'))
      .finally(() => setTplLoading(false));
  };

  useEffect(() => {
    axios.get<Business[]>('/businesses/')
      .then(res => setBusinesses(res.data))
      .catch(() => setBusinesses([]));

    loadTemplates();
    loadSettings();
  }, []);

  useEffect(() => {
    loadSettings(selectedBusiness || undefined);
    loadTemplates(selectedBusiness || undefined);
  }, [selectedBusiness]);

  // save settings
  const handleSaveSettings = () => {
    if (settingsId === null) return;
    setLoading(true);
    const url = selectedBusiness ? `/settings/auto-response/?business_id=${selectedBusiness}` : '/settings/auto-response/';
    const delaySecs =
      followDelayDays * 86400 +
      followDelayHours * 3600 +
      followDelayMinutes * 60 +
      followDelaySeconds;
    axios.put<AutoResponse>(url, {
      enabled,
      greeting_template: greetingTemplate,
      include_name: includeName,
      include_jobs: includeJobs,
      follow_up_template: followUpTemplate,
      follow_up_delay: delaySecs,
      export_to_sheets: exportToSheets,
    })
      .then(res => {
        setSettingsId(res.data.id);
        setSaved(true);
        setError('');
      })
      .catch(() => setError('Помилка збереження налаштувань.'))
      .finally(() => setLoading(false));
  };

  // add new template
  const handleAddTemplate = () => {
    setTplLoading(true);
    const url = selectedBusiness ? `/follow-up-templates/?business_id=${selectedBusiness}` : '/follow-up-templates/';
    const delaySecs =
      newDelayDays * 86400 +
      newDelayHours * 3600 +
      newDelayMinutes * 60 +
      newDelaySeconds;
    axios.post<FollowUpTemplate>(url, {
      name: `Custom ${templates.length + 1}`,
      template: newText,
      delay: delaySecs,
      open_from: newOpenFrom,
      open_to: newOpenTo,
      active: true,
    })
      .then(res => {
        setTemplates(prev => [...prev, res.data]);
        setNewText('');
        setNewDelayDays(0);
        setNewDelayHours(1);
        setNewDelayMinutes(0);
        setNewDelaySeconds(0);
        setNewOpenFrom('08:00');
        setNewOpenTo('20:00');
      })
      .catch(() => setError('Не вдалося додати шаблон.'))
      .finally(() => setTplLoading(false));
  };

  // delete a template
  const handleDeleteTemplate = (tplId: number) => {
    const url = selectedBusiness ? `/follow-up-templates/${tplId}/?business_id=${selectedBusiness}` : `/follow-up-templates/${tplId}/`;
    axios.delete(url)
      .then(() => {
        setTemplates(prev => prev.filter(t => t.id !== tplId));
      })
      .catch(() => setError('Не вдалося видалити шаблон.'));
  };

  const handleCloseSnackbar = () => {
    setSaved(false);
    setError('');
  };

  return (
    <Container maxWidth={false} sx={{ mt:4, mb:4, maxWidth: 900, mx: 'auto' }}>
      <Box sx={{ mb: 2 }}>
        <Select
          value={selectedBusiness}
          onChange={e => setSelectedBusiness(e.target.value as string)}
          displayEmpty
          size="small"
        >
          <MenuItem value="">
            <em>Default Settings</em>
          </MenuItem>
          {businesses.map(b => (
            <MenuItem key={b.business_id} value={b.business_id}>
              {b.name}
              {b.location ? ` (${b.location})` : ''}
              {b.time_zone ? ` - ${b.time_zone}` : ''}
            </MenuItem>
          ))}
        </Select>
      </Box>

      {selectedBusiness && (() => {
        const biz = businesses.find(b => b.business_id === selectedBusiness);
        if (!biz) return null;
        return (
          <Box sx={{ mb: 2 }}>
            <BusinessInfoCard business={biz} />
          </Box>
        );
      })()}

      <Paper sx={{ p:3 }} elevation={3}>
        <Typography variant="h5" gutterBottom>
          Auto-response Settings
        </Typography>

        {loading ? (
          <Box display="flex" justifyContent="center" mt={4}>
            <CircularProgress />
          </Box>
        ) : (
          <Stack spacing={4}>

            {/* Greeting */}
            <Box>
              <Typography variant="h6">Greeting Message</Typography>
              <Stack direction="row" spacing={1} mb={1}>
                {PLACEHOLDERS.map(ph => (
                  <Button key={ph} size="small" variant="outlined"
                    onClick={() => insertPlaceholder(ph, 'greeting')}>
                    {ph}
                  </Button>
                ))}
              </Stack>
              <TextField
                inputRef={greetingRef}
                multiline
                minRows={4}
                fullWidth
                value={greetingTemplate}
                onChange={e => setGreetingTemplate(e.target.value)}
              />
              <Stack direction="row" spacing={2} mt={2}>
                <FormControlLabel
                  control={<Switch checked={includeName} onChange={e => setIncludeName(e.target.checked)} />}
                  label="Include Name"
                />
                <FormControlLabel
                  control={<Switch checked={includeJobs} onChange={e => setIncludeJobs(e.target.checked)} />}
                  label="Include Jobs"
                />
              </Stack>
            </Box>

            {/* Built-in Follow-up */}
            <Box>
              <Typography variant="h6">Built-in Follow-up</Typography>
              <Stack direction="row" spacing={1} mb={1}>
                {PLACEHOLDERS.map(ph => (
                  <Button key={ph} size="small" variant="outlined"
                    onClick={() => insertPlaceholder(ph, 'follow')}>
                    {ph}
                  </Button>
                ))}
              </Stack>
              <TextField
                inputRef={followRef}
                multiline
                minRows={3}
                fullWidth
                value={followUpTemplate}
                onChange={e => setFollowUpTemplate(e.target.value)}
              />
              <Stack direction="row" spacing={1} alignItems="center" sx={{ mt:2 }}>
                <TextField
                  label="Days"
                  type="number"
                  inputProps={{ min:0 }}
                  sx={{ width:80 }}
                  value={followDelayDays}
                  onChange={e => setFollowDelayDays(Number(e.target.value))}
                />
                <TextField
                  label="Hours"
                  type="number"
                  inputProps={{ min:0 }}
                  sx={{ width:80 }}
                  value={followDelayHours}
                  onChange={e => setFollowDelayHours(Number(e.target.value))}
                />
                <TextField
                  label="Min"
                  type="number"
                  inputProps={{ min:0 }}
                  sx={{ width:80 }}
                  value={followDelayMinutes}
                  onChange={e => setFollowDelayMinutes(Number(e.target.value))}
                />
                <TextField
                  label="Sec"
                  type="number"
                  inputProps={{ min:0 }}
                  sx={{ width:80 }}
                  value={followDelaySeconds}
                  onChange={e => setFollowDelaySeconds(Number(e.target.value))}
                />
              </Stack>
            </Box>

            {/* Global Follow-up Templates */}
            <Box>
              <Typography variant="h6">Additional Follow-up Templates</Typography>
              {tplLoading ? (
                <CircularProgress size={24} />
              ) : (
                <List dense>
                  {templates.map(t => {
                    const biz = businesses.find(b => b.business_id === selectedBusiness);
                    const tz = biz?.time_zone;
                    let localTime = '';
                    if (tz) {
                      const ms = Date.now();
                      const fmt = new Intl.DateTimeFormat([], { hour: '2-digit', minute: '2-digit', timeZone: tz });
                      localTime = fmt.format(ms);
                    }
                    return (
                      <ListItem
                        key={t.id}
                        secondaryAction={
                          <IconButton edge="end" onClick={() => handleDeleteTemplate(t.id)}>
                            <DeleteIcon />
                          </IconButton>
                        }
                      >
                        <ListItemText
                          primary={t.template}
                          secondary={`Every ${formatDelay(t.delay)}${localTime ? ` - ${localTime}` : ''}`}
                        />
                      </ListItem>
                    );
                  })}
                </List>
              )}

              <Stack direction="row" spacing={2} alignItems="flex-start" mt={2}>
                <Box flexGrow={1}>
                  <Stack direction="row" spacing={1} mb={1}>
                    {PLACEHOLDERS.map(ph => (
                      <Button key={ph} size="small" variant="outlined"
                        onClick={() => insertPlaceholder(ph, 'template')}>
                        {ph}
                      </Button>
                    ))}
                  </Stack>
                  <TextField
                    inputRef={tplRef}
                    multiline
                    minRows={2}
                    fullWidth
                    value={newText}
                    onChange={e => setNewText(e.target.value)}
                    placeholder="New follow-up template..."
                  />
                </Box>
                <Stack direction="row" spacing={1} alignItems="center">
                  <TextField
                    label="Days"
                    type="number"
                    inputProps={{ min:0 }}
                    sx={{ width:70 }}
                    value={newDelayDays}
                    onChange={e => setNewDelayDays(Number(e.target.value))}
                  />
                  <TextField
                    label="Hours"
                    type="number"
                    inputProps={{ min:0 }}
                    sx={{ width:70 }}
                    value={newDelayHours}
                    onChange={e => setNewDelayHours(Number(e.target.value))}
                  />
                  <TextField
                    label="Min"
                    type="number"
                    inputProps={{ min:0 }}
                    sx={{ width:70 }}
                    value={newDelayMinutes}
                    onChange={e => setNewDelayMinutes(Number(e.target.value))}
                  />
                  <TextField
                    label="Sec"
                    type="number"
                    inputProps={{ min:0 }}
                    sx={{ width:70 }}
                    value={newDelaySeconds}
                    onChange={e => setNewDelaySeconds(Number(e.target.value))}
                  />
                  <TextField
                    label="From"
                    type="time"
                    value={newOpenFrom}
                    onChange={e => setNewOpenFrom(e.target.value)}
                    size="small"
                  />
                  <TextField
                    label="To"
                    type="time"
                    value={newOpenTo}
                    onChange={e => setNewOpenTo(e.target.value)}
                    size="small"
                  />
                  {selectedBusiness && (() => {
                    const biz = businesses.find(b => b.business_id === selectedBusiness);
                    const tz = biz?.time_zone;
                    if (!tz) return null;
                    const fmt = new Intl.DateTimeFormat([], { hour: '2-digit', minute: '2-digit', timeZone: tz });
                    const local = fmt.format(Date.now());
                    return (
                      <Typography variant="body2" sx={{ ml:1 }}>
                        {local}
                      </Typography>
                    );
                  })()}
                </Stack>
                <Button onClick={handleAddTemplate} disabled={tplLoading}>
                  Add
                </Button>
              </Stack>
            </Box>

            {/* Controls */}
            <Stack direction="row" spacing={2} alignItems="center">
              <FormControlLabel
                control={<Switch checked={enabled} onChange={e => setEnabled(e.target.checked)} />}
                label="Enable Auto-response"
              />
              <FormControlLabel
                control={<Switch checked={exportToSheets} onChange={e => setExportToSheets(e.target.checked)} />}
                label="Export to Sheets"
              />
              <Box flexGrow={1}/>
              <Button variant="contained" onClick={handleSaveSettings}>
                Save Settings
              </Button>
            </Stack>
          </Stack>
        )}
      </Paper>

      <Snackbar
        open={saved || Boolean(error)}
        autoHideDuration={4000}
        onClose={handleCloseSnackbar}
        anchorOrigin={{ vertical:'bottom', horizontal:'center' }}
      >
        {saved ? (
          <Alert onClose={handleCloseSnackbar} severity="success" sx={{ width:'100%' }}>
            Settings saved!
          </Alert>
        ) : error ? (
          <Alert onClose={handleCloseSnackbar} severity="error" sx={{ width:'100%' }}>
            {error}
          </Alert>
        ) : undefined}
      </Snackbar>
    </Container>
  );
};

export default AutoResponseSettings;
