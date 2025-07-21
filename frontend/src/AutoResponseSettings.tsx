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
  Tabs,
  Tab,
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
  Chip,
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import MessageIcon from '@mui/icons-material/Message';
import ScheduleIcon from '@mui/icons-material/Schedule';
import AddIcon from '@mui/icons-material/Add';
import SettingsIcon from '@mui/icons-material/Settings';
import PersonIcon from '@mui/icons-material/Person';
import WorkIcon from '@mui/icons-material/Work';
import TimerIcon from '@mui/icons-material/Timer';
import BusinessCenterIcon from '@mui/icons-material/BusinessCenter';
import TuneIcon from '@mui/icons-material/Tune';
import PhoneIcon from '@mui/icons-material/Phone';
import PhoneDisabledIcon from '@mui/icons-material/PhoneDisabled';
import ContactPhoneIcon from '@mui/icons-material/ContactPhone';
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
  greeting_off_hours_template: string;
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
  greeting_off_hours_template: string;
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


const AutoResponseSettings: FC = () => {
  // businesses
  const [businesses, setBusinesses] = useState<Business[]>([]);
  const [selectedBusiness, setSelectedBusiness] = useState('');
  const [phoneOptIn, setPhoneOptIn] = useState(false);
  const [phoneAvailable, setPhoneAvailable] = useState(false);

  // auto-response state
  const [settingsId, setSettingsId] = useState<number | null>(null);
  const [enabled, setEnabled] = useState(false);
  const [greetingTemplate, setGreetingTemplate] = useState('');
  const [greetingAfterTemplate, setGreetingAfterTemplate] = useState('');
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

  // track initial settings
  const initialSettings = useRef<AutoResponseSettingsData | null>(null);

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
  const greetingAfterRef = useRef<HTMLTextAreaElement | null>(null);
  const followRef = useRef<HTMLTextAreaElement | null>(null);
  const tplRef = useRef<HTMLTextAreaElement | null>(null);

  // helper to insert placeholder
  const insertPlaceholder = (
    ph: Placeholder,
    target: 'greeting' | 'follow' | 'template' | 'after'
  ) => {
    let ref: HTMLTextAreaElement | null = null;
    let base = '';
    let setter: (v: string) => void = () => {};
    if (target === 'greeting') {
      ref = greetingRef.current;
      base = greetingTemplate;
      setter = setGreetingTemplate;
    } else if (target === 'after') {
      ref = greetingAfterRef.current;
      base = greetingAfterTemplate;
      setter = setGreetingAfterTemplate;
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

  const emptySettings: AutoResponseSettingsData = {
    enabled: false,
    greeting_template: '',
    greeting_off_hours_template: '',
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
    follow_up_templates: [],
  };

  const resetSettings = () => {
    applySettingsData(emptySettings);
    setSettingsId(null);
    initialSettings.current = null;
    loadedTemplateIds.current = [];
  };

  // load settings
  const loadSettings = (biz?: string, attempts = 2) => {
    setLoading(true);
    setError('');
    const params = new URLSearchParams();
    params.append('phone_opt_in', phoneOptIn ? 'true' : 'false');
    params.append('phone_available', phoneAvailable ? 'true' : 'false');
    if (biz) params.append('business_id', biz);
    const url = `/settings/auto-response/?${params.toString()}`;

    const fetch = (remain: number) => {
      axios.get<AutoResponse>(url)
        .then(res => {
          setError('');
          const d = res.data;
          setSettingsId(d.id);
          setEnabled(d.enabled);
          setGreetingTemplate(d.greeting_template);
          setGreetingAfterTemplate(d.greeting_off_hours_template || '');
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
            greeting_off_hours_template: d.greeting_off_hours_template || '',
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
          setLoading(false);
        })
        .catch(err => {
          console.error('Failed to load settings:', err);
          if (remain > 0) {
            setTimeout(() => fetch(remain - 1), 1000);
          } else {
            const detail = err.response?.status
              ? `${err.response.status} ${err.response.statusText}`
              : '';
            setError(`Failed to load settings.${detail ? ` (${detail})` : ''}`);
            setLoading(false);
          }
        });
    };

    fetch(attempts);
  };

  const loadTemplates = (biz?: string) => {
    setTplLoading(true);
    setError('');
    const params = new URLSearchParams();
    params.append('phone_opt_in', phoneOptIn ? 'true' : 'false');
    params.append('phone_available', phoneAvailable ? 'true' : 'false');
    if (biz) params.append('business_id', biz);
    const url = `/follow-up-templates/?${params.toString()}`;
    axios.get<FollowUpTemplate[]>(url)
      .then(res => {
        setError('');
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
            greeting_off_hours_template: '',
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
            greeting_off_hours_template:
              initialSettings.current?.greeting_off_hours_template || '',
            follow_up_templates: mapped,
          };
        }
      })
      .catch(err => {
        console.error('Failed to load follow-up templates:', err);
        const detail = err.response?.status
          ? `${err.response.status} ${err.response.statusText}`
          : '';
        setError(
          `Failed to load follow-up templates.${detail ? ` (${detail})` : ''}`
        );
      })
      .finally(() => setTplLoading(false));
  };

  const applySettingsData = (d: AutoResponseSettingsData) => {
    setEnabled(d.enabled);
    setGreetingTemplate(d.greeting_template);
    setGreetingAfterTemplate(d.greeting_off_hours_template || '');
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


  useEffect(() => {
    axios.get<Business[]>('/businesses/')
      .then(res => setBusinesses(res.data))
      .catch(() => setBusinesses([]));

  }, []);


  useEffect(() => {
    if (selectedBusiness) {
      loadSettings(selectedBusiness);
      loadTemplates(selectedBusiness);
    } else {
      resetSettings();
      setLoading(false);
      setTplLoading(false);
    }
  }, [selectedBusiness, phoneOptIn, phoneAvailable]);


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
    const params = new URLSearchParams();
    params.append('phone_opt_in', phoneOptIn ? 'true' : 'false');
    params.append('phone_available', phoneAvailable ? 'true' : 'false');
    if (selectedBusiness) params.append('business_id', selectedBusiness);
    const url = `/settings/auto-response/?${params.toString()}`;
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
        greeting_off_hours_template: greetingAfterTemplate,
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
        greeting_off_hours_template: greetingAfterTemplate,
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

      const params = new URLSearchParams();
      params.append('phone_opt_in', phoneOptIn ? 'true' : 'false');
      params.append('phone_available', phoneAvailable ? 'true' : 'false');
      if (selectedBusiness) params.append('business_id', selectedBusiness);
      const bizParam = `?${params.toString()}`;

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
    const params = new URLSearchParams();
    params.append('phone_opt_in', phoneOptIn ? 'true' : 'false');
    params.append('phone_available', phoneAvailable ? 'true' : 'false');
    if (selectedBusiness) params.append('business_id', selectedBusiness);
    const url = `/follow-up-templates/?${params.toString()}`;
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
    const params = new URLSearchParams();
    params.append('phone_opt_in', phoneOptIn ? 'true' : 'false');
    params.append('phone_available', phoneAvailable ? 'true' : 'false');
    if (selectedBusiness) params.append('business_id', selectedBusiness);
    const url = `/follow-up-templates/${editingTpl.id}/?${params.toString()}`;
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
    const params = new URLSearchParams();
    params.append('phone_opt_in', phoneOptIn ? 'true' : 'false');
    params.append('phone_available', phoneAvailable ? 'true' : 'false');
    if (selectedBusiness) params.append('business_id', selectedBusiness);
    const url = `/follow-up-templates/${tplId}/?${params.toString()}`;
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

  if (!selectedBusiness) {
    return (
      <Container maxWidth={false} sx={{ mt: 4, mb: 4, maxWidth: 1000, mx: 'auto' }}>
        {/* Page Header */}
        <Box 
          sx={{ 
            textAlign: 'center',
            mb: 4,
            p: 4,
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            borderRadius: 3,
            color: 'white'
          }}
        >
          <SettingsIcon sx={{ fontSize: 64, mb: 2, opacity: 0.9 }} />
          <Typography variant="h3" sx={{ fontWeight: 700, mb: 1 }}>
            Auto-Response Settings
          </Typography>
          <Typography variant="h6" sx={{ opacity: 0.9 }}>
            Configure automated messaging for your business
          </Typography>
        </Box>

        {/* Business Selection Card */}
        <Card 
          elevation={4}
          sx={{ 
            borderRadius: 3,
            overflow: 'hidden',
            maxWidth: 600,
            mx: 'auto'
          }}
        >
          <Box sx={{ 
            backgroundColor: 'primary.50', 
            p: 3, 
            textAlign: 'center',
            borderBottom: '1px solid',
            borderColor: 'divider'
          }}>
            <BusinessCenterIcon sx={{ fontSize: 48, color: 'primary.main', mb: 1 }} />
            <Typography variant="h5" sx={{ fontWeight: 600, mb: 1 }}>
              Select Your Business
            </Typography>
            <Typography variant="body1" color="text.secondary">
              Choose a business to configure auto-response settings
            </Typography>
          </Box>
          
          <CardContent sx={{ p: 4 }}>
            <Box sx={{ mb: 3 }}>
              <Typography variant="subtitle2" sx={{ mb: 2, fontWeight: 600 }}>
                Available Businesses
              </Typography>
              <Select
                value={selectedBusiness}
                onChange={e => setSelectedBusiness(e.target.value as string)}
                displayEmpty
                fullWidth
                size="large"
                sx={{ 
                  '& .MuiOutlinedInput-root': {
                    borderRadius: 2,
                    backgroundColor: 'grey.50'
                  }
                }}
              >
                <MenuItem value="" disabled>
                  <Box sx={{ display: 'flex', alignItems: 'center', color: 'text.secondary' }}>
                    <BusinessCenterIcon sx={{ mr: 1, fontSize: 20 }} />
                    <em>Choose your business...</em>
                  </Box>
                </MenuItem>
                {businesses.map(b => (
                  <MenuItem key={b.business_id} value={b.business_id}>
                    <Box sx={{ display: 'flex', alignItems: 'center', width: '100%' }}>
                      <BusinessCenterIcon sx={{ mr: 2, color: 'primary.main', fontSize: 20 }} />
                      <Box sx={{ flex: 1 }}>
                        <Typography variant="body1" sx={{ fontWeight: 500 }}>
                          {b.name}
                        </Typography>
                        {(b.location || b.time_zone) && (
                          <Typography variant="caption" color="text.secondary">
                            {b.location ? `${b.location}` : ''}
                            {b.location && b.time_zone ? ' • ' : ''}
                            {b.time_zone ? b.time_zone : ''}
                          </Typography>
                        )}
                      </Box>
                    </Box>
                  </MenuItem>
                ))}
              </Select>
            </Box>

            {businesses.length === 0 && (
              <Alert severity="info" sx={{ borderRadius: 2 }}>
                <Typography variant="body2">
                  No businesses found. Please make sure you have businesses configured in your account.
                </Typography>
              </Alert>
            )}
          </CardContent>
        </Card>
      </Container>
    );
  }

  return (
    <Container maxWidth={false} sx={{ mt: 4, mb: 4, maxWidth: 1000, mx: 'auto' }}>
      {/* Page Header */}
      <Box 
        sx={{ 
          textAlign: 'center',
          mb: 4,
          p: 3,
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          borderRadius: 3,
          color: 'white'
        }}
      >
        <SettingsIcon sx={{ fontSize: 48, mb: 1, opacity: 0.9 }} />
        <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>
          Auto-Response Settings
        </Typography>
        <Typography variant="body1" sx={{ opacity: 0.9 }}>
          Configure automated messaging for your business
        </Typography>
      </Box>

      {/* Business Selector */}
      <Card elevation={2} sx={{ mb: 3, borderRadius: 2, overflow: 'hidden' }}>
        <Box sx={{ 
          backgroundColor: 'primary.50', 
          p: 2, 
          borderBottom: '1px solid',
          borderColor: 'divider'
        }}>
          <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center' }}>
            <BusinessCenterIcon sx={{ mr: 1, color: 'primary.main' }} />
            Business Selection
          </Typography>
        </Box>
        
        <CardContent sx={{ p: 3 }}>
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
              Current Business
            </Typography>
            <Select
              value={selectedBusiness}
              onChange={e => setSelectedBusiness(e.target.value as string)}
              displayEmpty
              fullWidth
              sx={{ 
                '& .MuiOutlinedInput-root': {
                  borderRadius: 2,
                  backgroundColor: 'grey.50'
                }
              }}
            >
              <MenuItem value="" disabled>
                <Box sx={{ display: 'flex', alignItems: 'center', color: 'text.secondary' }}>
                  <BusinessCenterIcon sx={{ mr: 1, fontSize: 20 }} />
                  <em>Choose business...</em>
                </Box>
              </MenuItem>
              {businesses.map(b => (
                <MenuItem key={b.business_id} value={b.business_id}>
                  <Box sx={{ display: 'flex', alignItems: 'center', width: '100%' }}>
                    <BusinessCenterIcon sx={{ mr: 2, color: 'primary.main', fontSize: 20 }} />
                    <Box sx={{ flex: 1 }}>
                      <Typography variant="body1" sx={{ fontWeight: 500 }}>
                        {b.name}
                      </Typography>
                      {(b.location || b.time_zone) && (
                        <Typography variant="caption" color="text.secondary">
                          {b.location ? `${b.location}` : ''}
                          {b.location && b.time_zone ? ' • ' : ''}
                          {b.time_zone ? b.time_zone : ''}
                        </Typography>
                      )}
                    </Box>
                  </Box>
                </MenuItem>
              ))}
            </Select>
          </Box>

          {/* Phone Type Tabs */}
          <Box sx={{ mt: 3 }}>
            <Typography variant="subtitle2" sx={{ mb: 2, fontWeight: 600 }}>
              Phone Configuration Type
            </Typography>
            <Paper 
              elevation={0} 
              sx={{ 
                backgroundColor: 'grey.100', 
                borderRadius: 2, 
                p: 0.5,
                display: 'inline-flex',
                width: 'fit-content'
              }}
            >
              <Tabs
                value={phoneOptIn ? 'opt' : phoneAvailable ? 'text' : 'no'}
                onChange={(_, v) => {
                  if (v === 'opt') {
                    setPhoneOptIn(true);
                    setPhoneAvailable(false);
                  } else if (v === 'text') {
                    setPhoneOptIn(false);
                    setPhoneAvailable(true);
                  } else {
                    setPhoneOptIn(false);
                    setPhoneAvailable(false);
                  }
                }}
                TabIndicatorProps={{
                  style: { display: 'none' }
                }}
                sx={{
                  minHeight: 'auto',
                  '& .MuiTab-root': {
                    minHeight: 'auto',
                    borderRadius: 1.5,
                    margin: 0.5,
                    minWidth: 'auto',
                    px: 2,
                    py: 1,
                    fontSize: '0.875rem',
                    fontWeight: 500,
                    color: 'text.secondary',
                    transition: 'all 0.2s ease-in-out',
                    '&.Mui-selected': {
                      backgroundColor: 'white',
                      color: 'primary.main',
                      boxShadow: 1
                    }
                  }
                }}
              >
                <Tab 
                  icon={<PhoneDisabledIcon sx={{ fontSize: 18 }} />}
                  iconPosition="start"
                  label="No Phone" 
                  value="no" 
                />
                <Tab 
                  icon={<ContactPhoneIcon sx={{ fontSize: 18 }} />}
                  iconPosition="start"
                  label="Opt-In Phone" 
                  value="opt" 
                />
                <Tab 
                  icon={<PhoneIcon sx={{ fontSize: 18 }} />}
                  iconPosition="start"
                  label="Real Phone" 
                  value="text" 
                />
              </Tabs>
            </Paper>
          </Box>
        </CardContent>
      </Card>

      {selectedBusiness && (() => {
        const biz = businesses.find(b => b.business_id === selectedBusiness);
        if (!biz) return null;
        return (
          <Box sx={{ mb: 2 }}>
            <BusinessInfoCard business={biz} />
          </Box>
        );
      })()}

      <Paper 
        elevation={3}
        sx={{ 
          borderRadius: 3,
          overflow: 'hidden',
          background: 'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)'
        }}
      >
        {/* Header Section */}
        <Box 
          sx={{ 
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            color: 'white',
            p: 3
          }}
        >
          <Stack direction="row" spacing={2} alignItems="center">
            <SettingsIcon sx={{ fontSize: 32 }} />
            <Box>
              <Typography variant="h5" sx={{ fontWeight: 700 }}>
                Auto-response Settings
              </Typography>
              {localTime && (
                <Typography variant="body2" sx={{ opacity: 0.9, mt: 0.5 }}>
                  <TimerIcon sx={{ fontSize: 16, mr: 0.5, verticalAlign: 'middle' }} />
                  Current time: {localTime}
                </Typography>
              )}
            </Box>
          </Stack>
        </Box>

        {/* Content Section */}
        <Box sx={{ p: 3 }}>
          {loading ? (
            <Box display="flex" justifyContent="center" py={8}>
              <CircularProgress size={48} />
            </Box>
          ) : (
            <Stack spacing={4}>
              {/* Greeting Message Section */}
              <Card elevation={2} sx={{ borderRadius: 2, overflow: 'hidden' }}>
                <Box sx={{ 
                  backgroundColor: 'primary.50', 
                  p: 2, 
                  borderBottom: '1px solid',
                  borderColor: 'divider'
                }}>
                  <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center' }}>
                    <MessageIcon sx={{ mr: 1, color: 'primary.main' }} />
                    {phoneAvailable ? 'Greeting Message (Business Hours)' : 'Greeting Message'}
                  </Typography>
                </Box>
                
                <CardContent sx={{ p: 3 }}>
                  <Stack spacing={3}>
                    {/* Placeholder buttons */}
                    <Box>
                      <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                        Insert Variables
                      </Typography>
                      <Stack direction="row" spacing={1} flexWrap="wrap" gap={1}>
                        {PLACEHOLDERS.map(ph => (
                          <Chip
                            key={ph}
                            label={ph}
                            size="small"
                            variant="outlined"
                            clickable
                            onClick={() => insertPlaceholder(ph, 'greeting')}
                            sx={{ 
                              '&:hover': { backgroundColor: 'primary.50' }
                            }}
                          />
                        ))}
                      </Stack>
                    </Box>

                    {/* Message template */}
                    <TextField
                      inputRef={greetingRef}
                      multiline
                      minRows={4}
                      fullWidth
                      value={greetingTemplate}
                      onChange={e => setGreetingTemplate(e.target.value)}
                      placeholder="Enter your greeting message template..."
                      variant="outlined"
                      sx={{
                        '& .MuiOutlinedInput-root': {
                          backgroundColor: 'white'
                        }
                      }}
                    />

                    {/* Options */}
                    <Box>
                      <Typography variant="subtitle2" sx={{ mb: 2, fontWeight: 600 }}>
                        Message Options
                      </Typography>
                      <Stack direction="row" spacing={3} flexWrap="wrap">
                        <FormControlLabel
                          control={
                            <Switch 
                              checked={includeName} 
                              onChange={e => setIncludeName(e.target.checked)}
                              color="primary"
                            />
                          }
                          label={
                            <Box sx={{ display: 'flex', alignItems: 'center' }}>
                              <PersonIcon sx={{ mr: 0.5, fontSize: 18 }} />
                              Include Name
                            </Box>
                          }
                        />
                        <FormControlLabel
                          control={
                            <Switch 
                              checked={includeJobs} 
                              onChange={e => setIncludeJobs(e.target.checked)}
                              color="primary"
                            />
                          }
                          label={
                            <Box sx={{ display: 'flex', alignItems: 'center' }}>
                              <WorkIcon sx={{ mr: 0.5, fontSize: 18 }} />
                              Include Jobs
                            </Box>
                          }
                        />
                      </Stack>
                    </Box>

                    {/* Timing and Business Hours */}
                    <Stack direction={{ xs: 'column', md: 'row' }} spacing={3}>
                      {/* Send Delay */}
                      <Box sx={{ flex: 1 }}>
                        <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                          Send After
                        </Typography>
                        <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
                          <TextField
                            label="Hours"
                            type="number"
                            inputProps={{ min: 0, max: 23 }}
                            sx={{ width: 80 }}
                            value={greetingDelayHours}
                            onChange={e => setGreetingDelayHours(Number(e.target.value))}
                            size="small"
                          />
                          <TextField
                            label="Minutes"
                            type="number"
                            inputProps={{ min: 0, max: 59 }}
                            sx={{ width: 90 }}
                            value={greetingDelayMinutes}
                            onChange={e => setGreetingDelayMinutes(Number(e.target.value))}
                            size="small"
                          />
                          <TextField
                            label="Seconds"
                            type="number"
                            inputProps={{ min: 0, max: 59 }}
                            sx={{ width: 90 }}
                            value={greetingDelaySeconds}
                            onChange={e => setGreetingDelaySeconds(Number(e.target.value))}
                            size="small"
                          />
                        </Stack>
                      </Box>

                      {/* Business Hours */}
                      <Box sx={{ flex: 1 }}>
                        <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                          Business Hours
                        </Typography>
                        <Stack direction="row" spacing={1} alignItems="center">
                          <TextField
                            label="From"
                            type="time"
                            inputProps={{ step: 1 }}
                            value={greetingOpenFrom}
                            onChange={e => setGreetingOpenFrom(e.target.value)}
                            size="small"
                            sx={{ flex: 1 }}
                          />
                          <Typography variant="body2" color="text.secondary">
                            to
                          </Typography>
                          <TextField
                            label="To"
                            type="time"
                            inputProps={{ step: 1 }}
                            value={greetingOpenTo}
                            onChange={e => setGreetingOpenTo(e.target.value)}
                            size="small"
                            sx={{ flex: 1 }}
                          />
                        </Stack>
                      </Box>
                    </Stack>
                  </Stack>
                </CardContent>
              </Card>

              {/* Off Hours Greeting Message */}
              {phoneAvailable && (
                <Card elevation={2} sx={{ borderRadius: 2, overflow: 'hidden' }}>
                  <Box sx={{ 
                    backgroundColor: 'warning.50', 
                    p: 2, 
                    borderBottom: '1px solid',
                    borderColor: 'divider'
                  }}>
                    <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center' }}>
                      <AccessTimeIcon sx={{ mr: 1, color: 'warning.main' }} />
                      Greeting Message (Off Hours)
                    </Typography>
                  </Box>
                  
                  <CardContent sx={{ p: 3 }}>
                    <Stack spacing={3}>
                      {/* Placeholder buttons */}
                      <Box>
                        <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                          Insert Variables
                        </Typography>
                        <Stack direction="row" spacing={1} flexWrap="wrap" gap={1}>
                          {PLACEHOLDERS.map(ph => (
                            <Chip
                              key={ph}
                              label={ph}
                              size="small"
                              variant="outlined"
                              clickable
                              onClick={() => insertPlaceholder(ph, 'after')}
                              sx={{ 
                                '&:hover': { backgroundColor: 'warning.50' }
                              }}
                            />
                          ))}
                        </Stack>
                      </Box>

                      {/* Message template */}
                      <TextField
                        inputRef={greetingAfterRef}
                        multiline
                        minRows={4}
                        fullWidth
                        value={greetingAfterTemplate}
                        onChange={e => setGreetingAfterTemplate(e.target.value)}
                        placeholder="Enter your off-hours greeting message template..."
                        variant="outlined"
                        sx={{
                          '& .MuiOutlinedInput-root': {
                            backgroundColor: 'white'
                          }
                        }}
                      />
                    </Stack>
                  </CardContent>
                </Card>
              )}

              {/* Built-in Follow-up Section */}
              {!phoneAvailable && (
                <Card elevation={2} sx={{ borderRadius: 2, overflow: 'hidden' }}>
                  <Box sx={{ 
                    backgroundColor: 'success.50', 
                    p: 2, 
                    borderBottom: '1px solid',
                    borderColor: 'divider'
                  }}>
                    <Stack direction="row" spacing={2} alignItems="center" justifyContent="space-between">
                      <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center' }}>
                        <MessageIcon sx={{ mr: 1, color: 'success.main' }} />
                        Built-in Follow-up
                      </Typography>
                      {!followUpTemplate.trim() && (
                        <Chip
                          label="Inactive"
                          color="error"
                          size="small"
                          variant="outlined"
                        />
                      )}
                    </Stack>
                  </Box>
                  
                  <CardContent sx={{ p: 3 }}>
                    <Stack spacing={3}>
                      {/* Placeholder buttons */}
                      <Box>
                        <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                          Insert Variables
                        </Typography>
                        <Stack direction="row" spacing={1} flexWrap="wrap" gap={1}>
                          {PLACEHOLDERS.map(ph => (
                            <Chip
                              key={ph}
                              label={ph}
                              size="small"
                              variant="outlined"
                              clickable
                              onClick={() => insertPlaceholder(ph, 'follow')}
                              sx={{ 
                                '&:hover': { backgroundColor: 'success.50' }
                              }}
                            />
                          ))}
                        </Stack>
                      </Box>

                      {/* Message template */}
                      <TextField
                        inputRef={followRef}
                        multiline
                        minRows={3}
                        fullWidth
                        value={followUpTemplate}
                        onChange={e => setFollowUpTemplate(e.target.value)}
                        placeholder="Enter your follow-up message template..."
                        variant="outlined"
                        sx={{
                          '& .MuiOutlinedInput-root': {
                            backgroundColor: 'white'
                          }
                        }}
                      />

                      {/* Timing and Business Hours */}
                      <Stack direction={{ xs: 'column', md: 'row' }} spacing={3}>
                        {/* Send Delay */}
                        <Box sx={{ flex: 1 }}>
                          <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                            Send After
                          </Typography>
                          <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
                            <TextField
                              label="Days"
                              type="number"
                              inputProps={{ min: 0, max: 365 }}
                              sx={{ width: 80 }}
                              value={followDelayDays}
                              onChange={e => setFollowDelayDays(Number(e.target.value))}
                              size="small"
                            />
                            <TextField
                              label="Hours"
                              type="number"
                              inputProps={{ min: 0, max: 23 }}
                              sx={{ width: 80 }}
                              value={followDelayHours}
                              onChange={e => setFollowDelayHours(Number(e.target.value))}
                              size="small"
                            />
                            <TextField
                              label="Minutes"
                              type="number"
                              inputProps={{ min: 0, max: 59 }}
                              sx={{ width: 90 }}
                              value={followDelayMinutes}
                              onChange={e => setFollowDelayMinutes(Number(e.target.value))}
                              size="small"
                            />
                            <TextField
                              label="Seconds"
                              type="number"
                              inputProps={{ min: 0, max: 59 }}
                              sx={{ width: 90 }}
                              value={followDelaySeconds}
                              onChange={e => setFollowDelaySeconds(Number(e.target.value))}
                              size="small"
                            />
                          </Stack>
                        </Box>

                        {/* Business Hours */}
                        <Box sx={{ flex: 1 }}>
                          <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                            Business Hours
                          </Typography>
                          <Stack direction="row" spacing={1} alignItems="center">
                            <TextField
                              label="From"
                              type="time"
                              inputProps={{ step: 1 }}
                              value={followOpenFrom}
                              onChange={e => setFollowOpenFrom(e.target.value)}
                              size="small"
                              sx={{ flex: 1 }}
                            />
                            <Typography variant="body2" color="text.secondary">
                              to
                            </Typography>
                            <TextField
                              label="To"
                              type="time"
                              inputProps={{ step: 1 }}
                              value={followOpenTo}
                              onChange={e => setFollowOpenTo(e.target.value)}
                              size="small"
                              sx={{ flex: 1 }}
                            />
                          </Stack>
                        </Box>
                      </Stack>
                    </Stack>
                  </CardContent>
                </Card>
              )}

            {/* Global Follow-up Templates */}
            {!phoneAvailable && (
            <Box>
              <Typography variant="h6" sx={{ mb: 2, display: 'flex', alignItems: 'center' }}>
                <MessageIcon sx={{ mr: 1, color: 'primary.main' }} />
                Additional Follow-up Templates
              </Typography>
              {tplLoading ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
                  <CircularProgress size={24} />
                </Box>
              ) : (
                <Box sx={{ mb: 3 }}>
                  {templates.length === 0 ? (
                    <Paper 
                      sx={{ 
                        p: 3, 
                        textAlign: 'center', 
                        backgroundColor: 'grey.50',
                        border: '2px dashed',
                        borderColor: 'grey.300'
                      }}
                    >
                      <MessageIcon sx={{ fontSize: 48, color: 'grey.400', mb: 1 }} />
                      <Typography variant="body1" color="text.secondary">
                        No follow-up templates yet
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Create your first template below to get started
                      </Typography>
                    </Paper>
                  ) : (
                    <Stack spacing={2}>
                      {templates.map((t, index) => (
                        <Card 
                          key={t.id}
                          elevation={1}
                          sx={{ 
                            border: '1px solid',
                            borderColor: 'grey.200',
                            transition: 'all 0.2s ease-in-out',
                            '&:hover': {
                              borderColor: 'primary.main',
                              boxShadow: 2
                            }
                          }}
                        >
                          <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                              <Box sx={{ flex: 1, mr: 2 }}>
                                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                                  <Chip 
                                    label={`Template ${index + 1}`}
                                    size="small"
                                    color="primary"
                                    variant="outlined"
                                    sx={{ mr: 1, fontSize: '0.75rem' }}
                                  />
                                  <Box sx={{ display: 'flex', alignItems: 'center', color: 'text.secondary' }}>
                                    <ScheduleIcon sx={{ fontSize: 16, mr: 0.5 }} />
                                    <Typography variant="caption">
                                      {formatDelay(t.delay)}
                                    </Typography>
                                  </Box>
                                </Box>
                                
                                <Typography 
                                  variant="body1" 
                                  sx={{ 
                                    mb: 1,
                                    lineHeight: 1.4,
                                    fontWeight: 500
                                  }}
                                >
                                  {t.template}
                                </Typography>
                                
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                                  <Box sx={{ display: 'flex', alignItems: 'center', color: 'text.secondary' }}>
                                    <AccessTimeIcon sx={{ fontSize: 16, mr: 0.5 }} />
                                    <Typography variant="caption">
                                      Working hours: {t.open_from} - {t.open_to}
                                    </Typography>
                                  </Box>
                                  {t.active && (
                                    <Chip 
                                      label="Active" 
                                      size="small" 
                                      color="success" 
                                      sx={{ height: 20, fontSize: '0.7rem' }}
                                    />
                                  )}
                                </Box>
                              </Box>
                              
                              <Box sx={{ display: 'flex', gap: 0.5 }}>
                                <IconButton 
                                  size="small" 
                                  onClick={() => handleEditTemplate(t)}
                                  sx={{ 
                                    color: 'primary.main',
                                    '&:hover': { backgroundColor: 'primary.50' }
                                  }}
                                >
                                  <EditIcon fontSize="small" />
                                </IconButton>
                                <IconButton 
                                  size="small" 
                                  onClick={() => handleDeleteTemplate(t.id)}
                                  sx={{ 
                                    color: 'error.main',
                                    '&:hover': { backgroundColor: 'error.50' }
                                  }}
                                >
                                  <DeleteIcon fontSize="small" />
                                </IconButton>
                              </Box>
                            </Box>
                          </CardContent>
                        </Card>
                      ))}
                    </Stack>
                  )}
                </Box>
              )}

              <Paper 
                elevation={0}
                sx={{ 
                  p: 3, 
                  mt: 3,
                  border: '1px solid',
                  borderColor: 'grey.200',
                  borderRadius: 2,
                  backgroundColor: 'grey.50'
                }}
              >
                <Typography variant="h6" sx={{ mb: 2, display: 'flex', alignItems: 'center' }}>
                  <AddIcon sx={{ mr: 1, color: 'primary.main' }} />
                  Create New Follow-up Template
                </Typography>
                
                <Stack spacing={3}>
                  {/* Template Message */}
                  <Box>
                    <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                      Message Template
                    </Typography>
                    <Stack direction="row" spacing={1} mb={1} flexWrap="wrap">
                      {PLACEHOLDERS.map(ph => (
                        <Chip
                          key={ph}
                          label={ph}
                          size="small"
                          variant="outlined"
                          clickable
                          onClick={() => insertPlaceholder(ph, 'template')}
                          sx={{ 
                            '&:hover': { backgroundColor: 'primary.50' }
                          }}
                        />
                      ))}
                    </Stack>
                    <TextField
                      inputRef={tplRef}
                      multiline
                      minRows={3}
                      fullWidth
                      value={newText}
                      onChange={e => setNewText(e.target.value)}
                      placeholder="Enter your follow-up message template..."
                      variant="outlined"
                      sx={{
                        '& .MuiOutlinedInput-root': {
                          backgroundColor: 'white'
                        }
                      }}
                    />
                  </Box>

                  <Stack direction={{ xs: 'column', md: 'row' }} spacing={3}>
                    {/* Timing Settings */}
                    <Box sx={{ flex: 1 }}>
                      <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                        Send After
                      </Typography>
                      <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
                        <TextField
                          label="Days"
                          type="number"
                          inputProps={{ min: 0, max: 365 }}
                          sx={{ width: 80 }}
                          value={newDelayDays}
                          onChange={e => setNewDelayDays(Number(e.target.value))}
                          size="small"
                        />
                        <TextField
                          label="Hours"
                          type="number"
                          inputProps={{ min: 0, max: 23 }}
                          sx={{ width: 80 }}
                          value={newDelayHours}
                          onChange={e => setNewDelayHours(Number(e.target.value))}
                          size="small"
                        />
                        <TextField
                          label="Minutes"
                          type="number"
                          inputProps={{ min: 0, max: 59 }}
                          sx={{ width: 90 }}
                          value={newDelayMinutes}
                          onChange={e => setNewDelayMinutes(Number(e.target.value))}
                          size="small"
                        />
                        <TextField
                          label="Seconds"
                          type="number"
                          inputProps={{ min: 0, max: 59 }}
                          sx={{ width: 90 }}
                          value={newDelaySeconds}
                          onChange={e => setNewDelaySeconds(Number(e.target.value))}
                          size="small"
                        />
                      </Stack>
                    </Box>

                    {/* Business Hours */}
                    <Box sx={{ flex: 1 }}>
                      <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                        Working Hours
                      </Typography>
                      <Stack direction="row" spacing={1} alignItems="center">
                        <TextField
                          label="From"
                          type="time"
                          inputProps={{ step: 1 }}
                          value={newOpenFrom}
                          onChange={e => setNewOpenFrom(e.target.value)}
                          size="small"
                          sx={{ flex: 1 }}
                        />
                        <Typography variant="body2" color="text.secondary">
                          to
                        </Typography>
                        <TextField
                          label="To"
                          type="time"
                          inputProps={{ step: 1 }}
                          value={newOpenTo}
                          onChange={e => setNewOpenTo(e.target.value)}
                          size="small"
                          sx={{ flex: 1 }}
                        />
                      </Stack>
                    </Box>
                  </Stack>

                  {/* Action Button */}
                  <Box sx={{ pt: 1 }}>
                    <Button 
                      variant="contained"
                      onClick={handleAddTemplate} 
                      disabled={tplLoading || !newText.trim()}
                      startIcon={tplLoading ? <CircularProgress size={16} /> : <AddIcon />}
                      sx={{ 
                        px: 3,
                        py: 1,
                        borderRadius: 2
                      }}
                    >
                      {tplLoading ? 'Adding Template...' : 'Add Template'}
                    </Button>
                  </Box>
                </Stack>
              </Paper>
              <Dialog open={editOpen} onClose={() => setEditOpen(false)} maxWidth="md" fullWidth>
                <DialogTitle sx={{ 
                  pb: 2, 
                  display: 'flex', 
                  alignItems: 'center',
                  borderBottom: '1px solid',
                  borderColor: 'grey.200'
                }}>
                  <EditIcon sx={{ mr: 1, color: 'primary.main' }} />
                  Edit Follow-up Template
                </DialogTitle>
                <DialogContent sx={{ p: 3 }}>
                  <Stack spacing={3} sx={{ mt: 1 }}>
                    {/* Template Message */}
                    <Box>
                      <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                        Message Template
                      </Typography>
                      <Stack direction="row" spacing={1} mb={1} flexWrap="wrap">
                        {PLACEHOLDERS.map(ph => (
                          <Chip
                            key={ph}
                            label={ph}
                            size="small"
                            variant="outlined"
                            clickable
                            onClick={() => setEditText(v => v + ph)}
                            sx={{ 
                              '&:hover': { backgroundColor: 'primary.50' }
                            }}
                          />
                        ))}
                      </Stack>
                      <TextField
                        multiline
                        minRows={3}
                        fullWidth
                        value={editText}
                        onChange={e => setEditText(e.target.value)}
                        placeholder="Enter your follow-up message template..."
                        variant="outlined"
                      />
                    </Box>

                    <Stack direction={{ xs: 'column', md: 'row' }} spacing={3}>
                      {/* Timing Settings */}
                      <Box sx={{ flex: 1 }}>
                        <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                          Send After
                        </Typography>
                        <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
                          <TextField 
                            label="Days" 
                            type="number" 
                            inputProps={{ min: 0, max: 365 }} 
                            sx={{ width: 80 }}
                            value={editDelayDays} 
                            onChange={e => setEditDelayDays(Number(e.target.value))}
                            size="small"
                          />
                          <TextField 
                            label="Hours" 
                            type="number" 
                            inputProps={{ min: 0, max: 23 }} 
                            sx={{ width: 80 }}
                            value={editDelayHours} 
                            onChange={e => setEditDelayHours(Number(e.target.value))}
                            size="small"
                          />
                          <TextField 
                            label="Minutes" 
                            type="number" 
                            inputProps={{ min: 0, max: 59 }} 
                            sx={{ width: 90 }}
                            value={editDelayMinutes} 
                            onChange={e => setEditDelayMinutes(Number(e.target.value))}
                            size="small"
                          />
                          <TextField 
                            label="Seconds" 
                            type="number" 
                            inputProps={{ min: 0, max: 59 }} 
                            sx={{ width: 90 }}
                            value={editDelaySeconds} 
                            onChange={e => setEditDelaySeconds(Number(e.target.value))}
                            size="small"
                          />
                        </Stack>
                      </Box>

                      {/* Business Hours */}
                      <Box sx={{ flex: 1 }}>
                        <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                          Working Hours
                        </Typography>
                        <Stack direction="row" spacing={1} alignItems="center">
                          <TextField 
                            label="From" 
                            type="time" 
                            inputProps={{ step: 1 }} 
                            value={editOpenFrom}
                            onChange={e => setEditOpenFrom(e.target.value)} 
                            size="small"
                            sx={{ flex: 1 }}
                          />
                          <Typography variant="body2" color="text.secondary">
                            to
                          </Typography>
                          <TextField 
                            label="To" 
                            type="time" 
                            inputProps={{ step: 1 }} 
                            value={editOpenTo}
                            onChange={e => setEditOpenTo(e.target.value)} 
                            size="small"
                            sx={{ flex: 1 }}
                          />
                        </Stack>
                      </Box>
                    </Stack>
                  </Stack>
                </DialogContent>
                <DialogActions sx={{ p: 3, pt: 2 }}>
                  <Button 
                    onClick={() => setEditOpen(false)}
                    variant="outlined"
                    sx={{ px: 3 }}
                  >
                    Cancel
                  </Button>
                  <Button 
                    variant="contained" 
                    onClick={handleUpdateTemplate} 
                    disabled={tplLoading || !editText.trim()}
                    startIcon={tplLoading ? <CircularProgress size={16} /> : <EditIcon />}
                    sx={{ px: 3 }}
                  >
                    {tplLoading ? 'Saving...' : 'Save Changes'}
                  </Button>
                </DialogActions>
              </Dialog>
            </Box>
            )}

            {/* Global Settings & Actions */}
            <Card elevation={2} sx={{ borderRadius: 2, overflow: 'hidden' }}>
              <Box sx={{ 
                backgroundColor: 'info.50', 
                p: 2, 
                borderBottom: '1px solid',
                borderColor: 'divider'
              }}>
                <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center' }}>
                  <SettingsIcon sx={{ mr: 1, color: 'info.main' }} />
                  Global Settings
                </Typography>
              </Box>
              
              <CardContent sx={{ p: 3 }}>
                <Stack spacing={3}>
                  {/* Settings Controls */}
                  <Box>
                    <Typography variant="subtitle2" sx={{ mb: 2, fontWeight: 600 }}>
                      System Configuration
                    </Typography>
                    <Stack direction="row" spacing={4} flexWrap="wrap">
                      <FormControlLabel
                        control={
                          <Switch 
                            checked={enabled} 
                            onChange={e => setEnabled(e.target.checked)}
                            color="primary"
                          />
                        }
                        label={
                          <Box sx={{ display: 'flex', alignItems: 'center' }}>
                            <MessageIcon sx={{ mr: 0.5, fontSize: 18 }} />
                            Enable Auto-response
                          </Box>
                        }
                      />
                      <FormControlLabel
                        control={
                          <Switch 
                            checked={exportToSheets} 
                            onChange={e => setExportToSheets(e.target.checked)}
                            color="primary"
                          />
                        }
                        label={
                          <Box sx={{ display: 'flex', alignItems: 'center' }}>
                            <BusinessCenterIcon sx={{ mr: 0.5, fontSize: 18 }} />
                            Export to Sheets
                          </Box>
                        }
                      />
                    </Stack>
                  </Box>

                  {/* Save Action */}
                  <Box sx={{ textAlign: 'right', pt: 2, borderTop: '1px solid', borderColor: 'divider' }}>
                    <Button 
                      variant="contained" 
                      onClick={handleSaveSettings}
                      disabled={loading}
                      size="large"
                      startIcon={loading ? <CircularProgress size={20} /> : <SettingsIcon />}
                      sx={{ 
                        px: 4,
                        py: 1.5,
                        borderRadius: 2,
                        fontWeight: 600,
                        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                        '&:hover': {
                          background: 'linear-gradient(135deg, #5a6fd8 0%, #6b4190 100%)',
                          transform: 'translateY(-1px)',
                          boxShadow: 3
                        },
                        transition: 'all 0.2s ease-in-out'
                      }}
                    >
                      {loading ? 'Saving Settings...' : 'Save All Settings'}
                    </Button>
                  </Box>
                </Stack>
              </CardContent>
            </Card>
          </Stack>
        )}
      </Box>
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
