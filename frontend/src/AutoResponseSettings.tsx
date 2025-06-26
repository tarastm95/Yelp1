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
  Card,
  CardActionArea,
  CardContent,
  Snackbar,
  Alert,
  CircularProgress,
  List,
  ListItem,
  ListItemText,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
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
  greeting_delay: number;
  greeting_open_from: string;
  greeting_open_to: string;
  include_name: boolean;
  include_jobs: boolean;
  follow_up_template: string;
  follow_up_delay: number;
  follow_up_open_from: string;
  follow_up_open_to: string;
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

interface FollowUpTplData {
  template: string;
  delay: number;
  open_from: string;
  open_to: string;
}

interface AutoResponseSettingsData {
  enabled: boolean;
  greeting_template: string;
  greeting_delay: number;
  greeting_open_from: string;
  greeting_open_to: string;
  include_name: boolean;
  include_jobs: boolean;
  follow_up_template: string;
  follow_up_delay: number;
  follow_up_open_from: string;
  follow_up_open_to: string;
  export_to_sheets: boolean;
  follow_up_templates: FollowUpTplData[];
}

interface SettingsTemplate {
  id: number;
  name: string;
  description: string;
  data: AutoResponseSettingsData;
}

const AutoResponseSettings: FC = () => {
  // businesses
  const [businesses, setBusinesses] = useState<Business[]>([]);
  const [selectedBusiness, setSelectedBusiness] = useState('');

  // auto-response state
  const [settingsId, setSettingsId] = useState<number | null>(null);
  const [enabled, setEnabled] = useState(false);
  const [greetingTemplate, setGreetingTemplate] = useState('');
  const [greetingDelayHours, setGreetingDelayHours] = useState(0);
  const [greetingDelayMinutes, setGreetingDelayMinutes] = useState(0);
  const [greetingDelaySeconds, setGreetingDelaySeconds] = useState(0);
  const [includeName, setIncludeName] = useState(true);
  const [includeJobs, setIncludeJobs] = useState(true);
  const [followUpTemplate, setFollowUpTemplate] = useState('');
  const [followDelayDays, setFollowDelayDays] = useState(0);
  const [followDelayHours, setFollowDelayHours] = useState(1);
  const [followDelayMinutes, setFollowDelayMinutes] = useState(0);
  const [followDelaySeconds, setFollowDelaySeconds] = useState(0);
  const [greetingOpenFrom, setGreetingOpenFrom] = useState('08:00:00');
  const [greetingOpenTo, setGreetingOpenTo] = useState('20:00:00');
  const [followOpenFrom, setFollowOpenFrom] = useState('08:00:00');
  const [followOpenTo, setFollowOpenTo] = useState('20:00:00');
  const [exportToSheets, setExportToSheets] = useState(false);

  // follow-up templates
  const [templates, setTemplates] = useState<FollowUpTemplate[]>([]);
  const [newText, setNewText] = useState('');
  const [newDelayDays, setNewDelayDays] = useState(0);
  const [newDelayHours, setNewDelayHours] = useState(1);
  const [newDelayMinutes, setNewDelayMinutes] = useState(0);
  const [newDelaySeconds, setNewDelaySeconds] = useState(0);
  const [newOpenFrom, setNewOpenFrom] = useState('08:00:00');
  const [newOpenTo, setNewOpenTo] = useState('20:00:00');

  // edit follow-up template
  const [editingTpl, setEditingTpl] = useState<FollowUpTemplate | null>(null);
  const [editOpen, setEditOpen] = useState(false);
  const [editText, setEditText] = useState('');
  const [editDelayDays, setEditDelayDays] = useState(0);
  const [editDelayHours, setEditDelayHours] = useState(0);
  const [editDelayMinutes, setEditDelayMinutes] = useState(0);
  const [editDelaySeconds, setEditDelaySeconds] = useState(0);
  const [editOpenFrom, setEditOpenFrom] = useState('08:00:00');
  const [editOpenTo, setEditOpenTo] = useState('20:00:00');

  // saved settings templates
  const [settingsTemplates, setSettingsTemplates] = useState<SettingsTemplate[]>([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState<number | 'current' | ''>('');

  // track initial settings and applied template
  const initialSettings = useRef<AutoResponseSettingsData | null>(null);
  const [appliedTemplateId, setAppliedTemplateId] = useState<number | null>(null);

  // local time of selected business
  const [localTime, setLocalTime] = useState('');

  // UI state
  const [loading, setLoading] = useState(true);
  const [tplLoading, setTplLoading] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState('');

  // track ids of templates originally loaded from backend
  const loadedTemplateIds = useRef<number[]>([]);


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
        let gsecs = d.greeting_delay || 0;
        setGreetingDelayHours(Math.floor(gsecs / 3600));
        gsecs %= 3600;
        setGreetingDelayMinutes(Math.floor(gsecs / 60));
        setGreetingDelaySeconds(gsecs % 60);
        setGreetingOpenFrom(d.greeting_open_from || '08:00:00');
        setGreetingOpenTo(d.greeting_open_to || '20:00:00');
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
        setFollowOpenFrom(d.follow_up_open_from || '08:00:00');
        setFollowOpenTo(d.follow_up_open_to || '20:00:00');
        setExportToSheets(d.export_to_sheets);
        initialSettings.current = {
          enabled: d.enabled,
          greeting_template: d.greeting_template,
          greeting_delay: d.greeting_delay,
          greeting_open_from: d.greeting_open_from || '08:00:00',
          greeting_open_to: d.greeting_open_to || '20:00:00',
          include_name: d.include_name,
          include_jobs: d.include_jobs,
          follow_up_template: d.follow_up_template,
          follow_up_delay: d.follow_up_delay,
          follow_up_open_from: d.follow_up_open_from || '08:00:00',
          follow_up_open_to: d.follow_up_open_to || '20:00:00',
          export_to_sheets: d.export_to_sheets,
          follow_up_templates: initialSettings.current?.follow_up_templates || [],
        };
        setAppliedTemplateId(null);
      })
      .catch(() => setError('Failed to load settings.'))
      .finally(() => setLoading(false));
  };

  const loadTemplates = (biz?: string) => {
    setTplLoading(true);
    const url = biz ? `/follow-up-templates/?business_id=${biz}` : '/follow-up-templates/';
    axios.get<FollowUpTemplate[]>(url)
      .then(res => {
        setTemplates(res.data);
        loadedTemplateIds.current = res.data.map(t => t.id);
        if (res.data.length) {
          setNewOpenFrom(res.data[0].open_from);
          setNewOpenTo(res.data[0].open_to);
        } else {
          setNewOpenFrom('08:00:00');
          setNewOpenTo('20:00:00');
        }
        const mapped = res.data.map(t => ({
          template: t.template,
          delay: t.delay,
          open_from: t.open_from,
          open_to: t.open_to,
        }));
        if (!initialSettings.current) {
          initialSettings.current = {
            enabled: false,
            greeting_template: '',
            greeting_delay: 0,
            greeting_open_from: '08:00:00',
            greeting_open_to: '20:00:00',
            include_name: true,
            include_jobs: true,
            follow_up_template: '',
            follow_up_delay: 0,
            follow_up_open_from: '08:00:00',
            follow_up_open_to: '20:00:00',
            export_to_sheets: false,
            follow_up_templates: mapped,
          };
        } else {
          initialSettings.current = {
            ...initialSettings.current,
            follow_up_templates: mapped,
          };
        }
      })
      .catch(() => setError('Failed to load follow-up templates.'))
      .finally(() => setTplLoading(false));
  };

  const applySettingsData = (d: AutoResponseSettingsData) => {
    setEnabled(d.enabled);
    setGreetingTemplate(d.greeting_template);
    let gsecs = d.greeting_delay || 0;
    setGreetingDelayHours(Math.floor(gsecs / 3600));
    gsecs %= 3600;
    setGreetingDelayMinutes(Math.floor(gsecs / 60));
    setGreetingDelaySeconds(gsecs % 60);
    setGreetingOpenFrom(d.greeting_open_from || '08:00:00');
    setGreetingOpenTo(d.greeting_open_to || '20:00:00');
    setIncludeName(d.include_name);
    setIncludeJobs(d.include_jobs);
    setFollowUpTemplate(d.follow_up_template);
    let secs = d.follow_up_delay || 0;
    setFollowDelayDays(Math.floor(secs / 86400));
    secs %= 86400;
    setFollowDelayHours(Math.floor(secs / 3600));
    secs %= 3600;
    setFollowDelayMinutes(Math.floor(secs / 60));
    setFollowDelaySeconds(secs % 60);
    setFollowOpenFrom(d.follow_up_open_from || '08:00:00');
    setFollowOpenTo(d.follow_up_open_to || '20:00:00');
    setExportToSheets(d.export_to_sheets);

    if (Array.isArray(d.follow_up_templates)) {
      const mapped = d.follow_up_templates.map((t: any, idx: number) => ({
        id: -(idx + 1),
        name: `Template ${idx + 1}`,
        template: t.template,
        delay: t.delay,
        open_from: t.open_from,
        open_to: t.open_to,
        active: true,
      }));
      setTemplates(mapped);
      if (mapped.length) {
        setNewOpenFrom(mapped[0].open_from);
        setNewOpenTo(mapped[0].open_to);
      } else {
        setNewOpenFrom('08:00:00');
        setNewOpenTo('20:00:00');
      }
    } else {
      setTemplates([]);
      setNewOpenFrom('08:00:00');
      setNewOpenTo('20:00:00');
    }
  };

  const applyTemplate = (tpl: SettingsTemplate) => {
    if (tpl.id === -1) {
      if (initialSettings.current) {
        applySettingsData(initialSettings.current);
      }
      setAppliedTemplateId(null);
    } else if (appliedTemplateId === tpl.id) {
      if (initialSettings.current) {
        applySettingsData(initialSettings.current);
      }
      setAppliedTemplateId(null);
    } else {
      applySettingsData(tpl.data);
      setAppliedTemplateId(tpl.id);
    }
  };

  const loadSettingsTemplates = () => {
    axios.get<SettingsTemplate[]>('/settings-templates/')
      .then(res => setSettingsTemplates(res.data))
      .catch(() => setSettingsTemplates([]));
  };

  useEffect(() => {
    axios.get<Business[]>('/businesses/')
      .then(res => setBusinesses(res.data))
      .catch(() => setBusinesses([]));

    loadTemplates();
    loadSettings();
    loadSettingsTemplates();
  }, []);


  useEffect(() => {
    loadSettings(selectedBusiness || undefined);
    loadTemplates(selectedBusiness || undefined);
  }, [selectedBusiness]);

  // reload templates when other tabs modify them
  useEffect(() => {
    const handler = (e: StorageEvent) => {
      if (e.key === 'followTemplateUpdated') {
        loadTemplates(selectedBusiness || undefined);
      }
    };
    window.addEventListener('storage', handler);
    return () => window.removeEventListener('storage', handler);
  }, [selectedBusiness]);

  // update local time for selected business
  useEffect(() => {
    let timer: ReturnType<typeof setInterval> | undefined;
    const biz = businesses.find(b => b.business_id === selectedBusiness);
    const tz = biz?.time_zone;
    if (tz) {
      const fmt = new Intl.DateTimeFormat([], {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        timeZone: tz,
      });
      const update = () => setLocalTime(fmt.format(Date.now()));
      update();
      timer = setInterval(update, 1000);
    } else {
      setLocalTime('');
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [selectedBusiness, businesses]);

  // save settings
  const handleSaveSettings = async () => {
    setLoading(true);
    const url = selectedBusiness ? `/settings/auto-response/?business_id=${selectedBusiness}` : '/settings/auto-response/';
    const delaySecs =
      followDelayDays * 86400 +
      followDelayHours * 3600 +
      followDelayMinutes * 60 +
      followDelaySeconds;
    const greetDelaySecs =
      greetingDelayHours * 3600 +
      greetingDelayMinutes * 60 +
      greetingDelaySeconds;
    try {
      const res = await axios.put<AutoResponse>(url, {
        enabled,
        greeting_template: greetingTemplate,
        greeting_delay: greetDelaySecs,
        greeting_open_from: greetingOpenFrom,
        greeting_open_to: greetingOpenTo,
        include_name: includeName,
        include_jobs: includeJobs,
        follow_up_template: followUpTemplate,
        follow_up_delay: delaySecs,
        follow_up_open_from: followOpenFrom,
        follow_up_open_to: followOpenTo,
        export_to_sheets: exportToSheets,
      });

      setSettingsId(res.data.id);
      initialSettings.current = {
        enabled,
        greeting_template: greetingTemplate,
        greeting_delay: greetDelaySecs,
        greeting_open_from: greetingOpenFrom,
        greeting_open_to: greetingOpenTo,
        include_name: includeName,
        include_jobs: includeJobs,
        follow_up_template: followUpTemplate,
        follow_up_delay: delaySecs,
        follow_up_open_from: followOpenFrom,
        follow_up_open_to: followOpenTo,
        export_to_sheets: exportToSheets,
        follow_up_templates: initialSettings.current?.follow_up_templates || [],
      };

      const bizParam = selectedBusiness ? `?business_id=${selectedBusiness}` : '';

      // remove templates that were loaded initially but no longer present
      const toDelete = loadedTemplateIds.current.filter(
        id => !templates.some(t => t.id === id)
      );
      await Promise.all(
        toDelete.map(id =>
          axios.delete(`/follow-up-templates/${id}/${bizParam}`)
        )
      );

      // create or update current templates
      for (const tpl of templates) {
        const data = {
          name: tpl.name,
          template: tpl.template,
          delay: tpl.delay,
          open_from: tpl.open_from,
          open_to: tpl.open_to,
          active: tpl.active,
        };
        if (tpl.id < 0) {
          const resp = await axios.post<FollowUpTemplate>(
            `/follow-up-templates/${bizParam}`,
            data
          );
          tpl.id = resp.data.id;
        } else {
          await axios.put<FollowUpTemplate>(
            `/follow-up-templates/${tpl.id}/${bizParam}`,
            data
          );
        }
      }

      loadedTemplateIds.current = templates.map(t => t.id);

      setSaved(true);
      setError('');
    } catch {
      setError('Failed to save settings.');
    } finally {
      setLoading(false);
    }
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
        loadedTemplateIds.current.push(res.data.id);
        setNewText('');
        setNewDelayDays(0);
        setNewDelayHours(1);
        setNewDelayMinutes(0);
        setNewDelaySeconds(0);
        setNewOpenFrom('08:00');
        setNewOpenTo('20:00');
      })
      .catch(() => setError('Failed to add template.'))
      .finally(() => setTplLoading(false));
  };

  const handleEditTemplate = (tpl: FollowUpTemplate) => {
    setEditingTpl(tpl);
    setEditText(tpl.template);
    let secs = tpl.delay;
    setEditDelayDays(Math.floor(secs / 86400));
    secs %= 86400;
    setEditDelayHours(Math.floor(secs / 3600));
    secs %= 3600;
    setEditDelayMinutes(Math.floor(secs / 60));
    setEditDelaySeconds(secs % 60);
    setEditOpenFrom(tpl.open_from);
    setEditOpenTo(tpl.open_to);
    setEditOpen(true);
  };

  const handleUpdateTemplate = () => {
    if (!editingTpl) return;
    setTplLoading(true);
    const url = selectedBusiness
      ? `/follow-up-templates/${editingTpl.id}/?business_id=${selectedBusiness}`
      : `/follow-up-templates/${editingTpl.id}/`;
    const delaySecs =
      editDelayDays * 86400 +
      editDelayHours * 3600 +
      editDelayMinutes * 60 +
      editDelaySeconds;
    axios
      .put<FollowUpTemplate>(url, {
        name: editingTpl.name,
        template: editText,
        delay: delaySecs,
        open_from: editOpenFrom,
        open_to: editOpenTo,
        active: editingTpl.active,
      })
      .then(res => {
        setTemplates(prev => prev.map(t => (t.id === res.data.id ? res.data : t)));
        setSaved(true);
        setEditOpen(false);
      })
      .catch(() => setError('Failed to update template.'))
      .finally(() => setTplLoading(false));
  };

  // delete a template
  const handleDeleteTemplate = (tplId: number) => {
    const url = selectedBusiness ? `/follow-up-templates/${tplId}/?business_id=${selectedBusiness}` : `/follow-up-templates/${tplId}/`;
    axios.delete(url)
      .then(() => {
        setTemplates(prev => prev.filter(t => t.id !== tplId));
        loadedTemplateIds.current = loadedTemplateIds.current.filter(id => id !== tplId);
      })
      .catch(() => setError('Failed to delete template.'));
  };

  const handleCloseSnackbar = () => {
    setSaved(false);
    setError('');
  };

  return (
    <Container maxWidth={false} sx={{ mt:4, mb:4, maxWidth: 1000, mx: 'auto' }}>
      <Box sx={{ mb: 2 }}>
        <Box>
          <Select
            value={selectedTemplateId}
            onChange={e => {
              const val = e.target.value as any;
              setSelectedTemplateId(val);

              if (initialSettings.current) {
                if (val === 'current' || val === '') {
                  applyTemplate({
                    id: -1,
                    name: 'Current',
                    description: '',
                    data: initialSettings.current,
                  });
                } else {
                  const id = val as number;
                  const tpl = settingsTemplates.find(t => t.id === id);
                  if (tpl) {
                    applyTemplate(tpl);
                  }
                }
              }
            }}
            displayEmpty
            size="small"
            sx={{ minWidth: 200 }}
          >
            <MenuItem value="">
              <em>Select Template</em>
            </MenuItem>
            <MenuItem value="current">Current</MenuItem>
            {settingsTemplates.map(t => (
              <MenuItem key={t.id} value={t.id}>{t.name}</MenuItem>
            ))}
          </Select>
        </Box>

        <Select
          value={selectedBusiness}
          onChange={e => setSelectedBusiness(e.target.value as string)}
          displayEmpty
          size="small"
          sx={{ mt: 2 }}
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
              <Stack direction="row" spacing={1} alignItems="center" sx={{ mt:2 }}>
                <TextField
                  label="Hours"
                  type="number"
                  inputProps={{ min:0 }}
                  sx={{ width:80 }}
                  value={greetingDelayHours}
                  onChange={e => setGreetingDelayHours(Number(e.target.value))}
                />
                <TextField
                  label="Min"
                  type="number"
                  inputProps={{ min:0 }}
                  sx={{ width:80 }}
                  value={greetingDelayMinutes}
                  onChange={e => setGreetingDelayMinutes(Number(e.target.value))}
                />
                <TextField
                  label="Sec"
                  type="number"
                  inputProps={{ min:0 }}
                  sx={{ width:80 }}
                  value={greetingDelaySeconds}
                  onChange={e => setGreetingDelaySeconds(Number(e.target.value))}
                />
              </Stack>
              <Box sx={{ mt: 1 }}>
                <Typography variant="body2" gutterBottom>Business Hours</Typography>
                <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
                  <TextField
                    label="From"
                    type="time"
                    inputProps={{ step: 1 }}
                    value={greetingOpenFrom}
                    onChange={e => setGreetingOpenFrom(e.target.value)}
                    size="small"
                  />
                  <TextField
                    label="To"
                    type="time"
                    inputProps={{ step: 1 }}
                    value={greetingOpenTo}
                    onChange={e => setGreetingOpenTo(e.target.value)}
                    size="small"
                  />
                </Stack>
              </Box>
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
              <Box sx={{ mt: 1 }}>
                <Typography variant="body2" gutterBottom>Business Hours</Typography>
                <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
                  <TextField
                    label="From"
                    type="time"
                    inputProps={{ step: 1 }}
                    value={followOpenFrom}
                    onChange={e => setFollowOpenFrom(e.target.value)}
                    size="small"
                  />
                  <TextField
                    label="To"
                    type="time"
                    inputProps={{ step: 1 }}
                    value={followOpenTo}
                    onChange={e => setFollowOpenTo(e.target.value)}
                    size="small"
                  />
                </Stack>
              </Box>
            </Box>

            {/* Global Follow-up Templates */}
            <Box>
              <Typography variant="h6">Additional Follow-up Templates</Typography>
              {localTime && (
                <Typography variant="body2" sx={{ mt: 0.5 }}>
                  Current time: {localTime}
                </Typography>
              )}
              {tplLoading ? (
                <CircularProgress size={24} />
              ) : (
                <List dense>
                  {templates.map(t => (
                      <ListItem
                        key={t.id}
                        secondaryAction={
                          <>
                            <IconButton edge="end" onClick={() => handleEditTemplate(t)}>
                              <EditIcon />
                            </IconButton>
                            <IconButton edge="end" onClick={() => handleDeleteTemplate(t.id)}>
                              <DeleteIcon />
                            </IconButton>
                          </>
                        }
                      >
                        <ListItemText
                          primary={t.template}
                          secondary={`In ${formatDelay(t.delay)} | Dispatch working hours: ${t.open_from} - ${t.open_to}`}
                        />
                      </ListItem>
                  ))}
                </List>
              )}

              <Stack
                direction="row"
                spacing={2}
                alignItems="flex-start"
                mt={2}
                flexWrap="wrap"
              >
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
                <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
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
                </Stack>
                <Box sx={{ mt: 1 }}>
                  <Typography variant="body2" gutterBottom>Business Hours</Typography>
                  <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
                    <TextField
                      label="From"
                      type="time"
                      inputProps={{ step: 1 }}
                      value={newOpenFrom}
                      onChange={e => setNewOpenFrom(e.target.value)}
                      size="small"
                    />
                    <TextField
                      label="To"
                      type="time"
                      inputProps={{ step: 1 }}
                      value={newOpenTo}
                      onChange={e => setNewOpenTo(e.target.value)}
                      size="small"
                    />
                  </Stack>
                </Box>
                <Button onClick={handleAddTemplate} disabled={tplLoading} sx={{ mt: 1 }}>
                  Add
                </Button>
              </Stack>
              <Dialog open={editOpen} onClose={() => setEditOpen(false)} maxWidth="sm" fullWidth>
                <DialogTitle>Edit Follow-up Template</DialogTitle>
                <DialogContent dividers>
                  <Stack spacing={2} sx={{ mt:1 }}>
                    <Stack direction="row" spacing={1} mb={1}>
                      {PLACEHOLDERS.map(ph => (
                        <Button key={ph} size="small" variant="outlined" onClick={() => setEditText(v => v + ph)}>
                          {ph}
                        </Button>
                      ))}
                    </Stack>
                    <TextField
                      multiline
                      minRows={2}
                      fullWidth
                      value={editText}
                      onChange={e => setEditText(e.target.value)}
                      placeholder="Follow-up template..."
                    />
                    <Stack direction="row" spacing={1} alignItems="center">
                      <TextField label="Days" type="number" inputProps={{min:0}} sx={{width:70}}
                        value={editDelayDays} onChange={e=>setEditDelayDays(Number(e.target.value))}/>
                      <TextField label="Hours" type="number" inputProps={{min:0}} sx={{width:70}}
                        value={editDelayHours} onChange={e=>setEditDelayHours(Number(e.target.value))}/>
                      <TextField label="Min" type="number" inputProps={{min:0}} sx={{width:70}}
                        value={editDelayMinutes} onChange={e=>setEditDelayMinutes(Number(e.target.value))}/>
                      <TextField label="Sec" type="number" inputProps={{min:0}} sx={{width:70}}
                        value={editDelaySeconds} onChange={e=>setEditDelaySeconds(Number(e.target.value))}/>
                    </Stack>
                    <Box>
                      <Typography variant="body2" gutterBottom>Business Hours</Typography>
                      <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
                        <TextField label="From" type="time" inputProps={{ step: 1 }} value={editOpenFrom}
                          onChange={e=>setEditOpenFrom(e.target.value)} size="small"/>
                        <TextField label="To" type="time" inputProps={{ step: 1 }} value={editOpenTo}
                          onChange={e=>setEditOpenTo(e.target.value)} size="small"/>
                      </Stack>
                    </Box>
                  </Stack>
                </DialogContent>
                <DialogActions>
                  <Button onClick={() => setEditOpen(false)}>Cancel</Button>
                  <Button variant="contained" onClick={handleUpdateTemplate} disabled={tplLoading}>Save</Button>
                </DialogActions>
              </Dialog>
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
