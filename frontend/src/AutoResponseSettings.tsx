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

const TIME_UNITS = [
  { value: 'sec', label: 'sec', factor: 1 },
  { value: 'hour', label: 'hr', factor: 3600 },
  { value: 'day', label: 'day', factor: 86400 },
] as const;
type TimeUnit = typeof TIME_UNITS[number]['value'];

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
  const [followDelayValue, setFollowDelayValue] = useState(1);
  const [followDelayUnit, setFollowDelayUnit] = useState<TimeUnit>('hour');
  const [exportToSheets, setExportToSheets] = useState(false);

  // follow-up templates
  const [templates, setTemplates] = useState<FollowUpTemplate[]>([]);
  const [newText, setNewText] = useState('');
  const [newDelayValue, setNewDelayValue] = useState(1);
  const [newDelayUnit, setNewDelayUnit] = useState<TimeUnit>('hour');
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
    if (secs % 86400 === 0) return `${secs / 86400} day${secs / 86400 !== 1 ? 's' : ''}`;
    if (secs % 3600 === 0) return `${secs / 3600} hr${secs / 3600 !== 1 ? 's' : ''}`;
    if (secs % 60 === 0) return `${secs / 60} min`;
    return `${secs} sec`;
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
        const secs = d.follow_up_delay;
        if (secs % 86400 === 0) {
          setFollowDelayValue(secs / 86400);
          setFollowDelayUnit('day');
        } else if (secs % 3600 === 0) {
          setFollowDelayValue(secs / 3600);
          setFollowDelayUnit('hour');
        } else {
          setFollowDelayValue(secs);
          setFollowDelayUnit('sec');
        }
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
    const delaySecs = followDelayValue * TIME_UNITS.find(u => u.value === followDelayUnit)!.factor;
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
    const delaySecs = newDelayValue * TIME_UNITS.find(u => u.value === newDelayUnit)!.factor;
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
        setNewDelayValue(1);
        setNewDelayUnit('hour');
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
    <Container maxWidth="sm" sx={{ mt:4, mb:4 }}>
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
                  label="Delay"
                  type="number"
                  inputProps={{ min:0 }}
                  sx={{ width:120 }}
                  value={followDelayValue}
                  onChange={e => setFollowDelayValue(Number(e.target.value))}
                />
                <Select
                  value={followDelayUnit}
                  onChange={e => setFollowDelayUnit(e.target.value as TimeUnit)}
                  size="small"
                >
                  {TIME_UNITS.map(u => (
                    <MenuItem key={u.value} value={u.value}>{u.label}</MenuItem>
                  ))}
                </Select>
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
                      const ms = Date.now() + t.delay * 1000;
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
                    label="Delay"
                    type="number"
                    inputProps={{ min:1 }}
                    sx={{ width:120 }}
                    value={newDelayValue}
                    onChange={e => setNewDelayValue(Number(e.target.value))}
                  />
                  <Select
                    value={newDelayUnit}
                    onChange={e => setNewDelayUnit(e.target.value as TimeUnit)}
                    size="small"
                  >
                    {TIME_UNITS.map(u => (
                      <MenuItem key={u.value} value={u.value}>{u.label}</MenuItem>
                    ))}
                  </Select>
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
                    const secs = newDelayValue * TIME_UNITS.find(u => u.value === newDelayUnit)!.factor;
                    const ms = Date.now() + secs * 1000;
                    const fmt = new Intl.DateTimeFormat([], { hour: '2-digit', minute: '2-digit', timeZone: tz });
                    const local = fmt.format(ms);
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
