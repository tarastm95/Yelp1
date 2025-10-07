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
  FormControl,
  InputLabel,
  FormHelperText,
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
  Checkbox,
  FormGroup,
  ListItemIcon,
  Grid,
  Divider,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import MessageIcon from '@mui/icons-material/Message';
import ScheduleIcon from '@mui/icons-material/Schedule';
import AddIcon from '@mui/icons-material/Add';
import SettingsIcon from '@mui/icons-material/Settings';
import PersonIcon from '@mui/icons-material/Person';
import { Psychology as VectorIcon } from '@mui/icons-material';
import WorkIcon from '@mui/icons-material/Work';
import TimerIcon from '@mui/icons-material/Timer';
import BusinessCenterIcon from '@mui/icons-material/BusinessCenter';
import InfoIcon from '@mui/icons-material/Info';
import TuneIcon from '@mui/icons-material/Tune';
import PhoneIcon from '@mui/icons-material/Phone';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import PhoneDisabledIcon from '@mui/icons-material/PhoneDisabled';
import ContactPhoneIcon from '@mui/icons-material/ContactPhone';
import BusinessInfoCard from './BusinessInfoCard';
import NotificationSettings from './NotificationSettings';
import SampleRepliesManager from './SampleRepliesManager';
import WarningIcon from '@mui/icons-material/Warning';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';

// Helper placeholders used in message templates

// For Template Configuration and Follow-up Templates - include greetings
const TEMPLATE_PLACEHOLDERS = ['{name}', '{jobs}', '{greetings}'] as const;

// For Notification Settings and other sections - full placeholders
const NOTIFICATION_PLACEHOLDERS = ['{name}', '{jobs}', '{sep}', '{reason}', '{greetings}'] as const;

// All placeholders for general use
const PLACEHOLDERS = TEMPLATE_PLACEHOLDERS;
type Placeholder = typeof TEMPLATE_PLACEHOLDERS[number];

const PLACEHOLDER_DESCRIPTIONS: Record<string, string> = {
  '{name}': 'Customer display name',
  '{jobs}': 'List of services requested',
  '{sep}': 'Separator between services',
  '{reason}': 'Reason for SMS (Phone Found, Customer Reply, Phone Opt-in)',
  '{greetings}': 'Time-based greeting (Good morning, Good afternoon, etc.)'
};

const DAY_NAMES = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const DAY_FULL_NAMES = {
  'Mon': 'Monday',
  'Tue': 'Tuesday', 
  'Wed': 'Wednesday',
  'Thu': 'Thursday',
  'Fri': 'Friday',
  'Sat': 'Saturday',
  'Sun': 'Sunday'
};

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
  greeting_open_days: string;
  export_to_sheets: boolean;
  // AI fields - maximally simplified
  use_ai_greeting: boolean;
  // All AI behavior (location, response time, business data, style) controlled via Custom Instructions
  ai_custom_prompt?: string;
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
  greeting_open_days: string;
  export_to_sheets: boolean;
  follow_up_templates: FollowUpTplData[];
  // AI fields - maximally simplified
  use_ai_greeting: boolean;
  // All AI behavior (location, response time, business data, style) controlled via Custom Instructions
  ai_custom_prompt?: string;
  // Sample Replies fields (MODE 2: AI Generated)
  use_sample_replies?: boolean;
  sample_replies_content?: string;
  sample_replies_filename?: string;
  sample_replies_priority?: boolean;
  // AI Business Data Settings removed - controlled via Custom Instructions
  ai_max_message_length: number;
  // Business-specific AI Model Settings
  ai_model?: string;
  ai_temperature?: number | null;
  // Vector Search Settings
  vector_similarity_threshold?: number;
  vector_search_limit?: number;
  vector_chunk_types?: string[];
}


const AutoResponseSettings: FC = () => {
  // businesses
  const [businesses, setBusinesses] = useState<Business[]>([]);
  const [businessesLoading, setBusinessesLoading] = useState(true);
  const [selectedBusiness, setSelectedBusiness] = useState('');
  // phoneOptIn removed - merged with No Phone scenario
  const [phoneAvailable, setPhoneAvailable] = useState(false);

  // auto-response state
  const [settingsId, setSettingsId] = useState<number | null>(null);
  const [enabled, setEnabled] = useState(false);
  const [greetingTemplate, setGreetingTemplate] = useState('');
  const [greetingAfterTemplate, setGreetingAfterTemplate] = useState('');
  const [greetingDelayHours, setGreetingDelayHours] = useState(0);
  const [greetingDelayMinutes, setGreetingDelayMinutes] = useState(0);
  const [greetingDelaySeconds, setGreetingDelaySeconds] = useState(0);
  const includeName = true;
  const includeJobs = true;
  const [greetingOpenFrom, setGreetingOpenFrom] = useState('08:00:00');
  const [greetingOpenTo, setGreetingOpenTo] = useState('20:00:00');
  const [greetingOpenDays, setGreetingOpenDays] = useState('Mon, Tue, Wed, Thu, Fri');
  const [exportToSheets, setExportToSheets] = useState(false);

  // AI settings state - simplified to just Custom Instructions
  const [useAiGreeting, setUseAiGreeting] = useState(false);
  // All AI behavior controlled via Custom Instructions (no individual checkboxes)
  const [aiCustomPrompt, setAiCustomPrompt] = useState('');
  const [aiPreview, setAiPreview] = useState('');
  const [aiPreviewLoading, setAiPreviewLoading] = useState(false);
  const [aiCustomPreviewText, setAiCustomPreviewText] = useState('');

  // Sample Replies state (MODE 2: AI Generated)
  const [useSampleReplies, setUseSampleReplies] = useState(false);
  const [sampleRepliesContent, setSampleRepliesContent] = useState('');
  const [sampleRepliesFilename, setSampleRepliesFilename] = useState('');
  const [sampleRepliesPriority, setSampleRepliesPriority] = useState(true);

  // AI Business Data Settings removed - now controlled via Custom Instructions
  const [aiMaxMessageLength, setAiMaxMessageLength] = useState(160);
  
  // 🤖 Business-specific AI Model Settings
  const [aiModel, setAiModel] = useState('gpt-4o');  // ✅ Default to gpt-4o
  const [aiTemperature, setAiTemperature] = useState<number | ''>(0.7);  // ✅ Default temperature
  
  // 🔍 Vector Search Settings  
  const [vectorSimilarityThreshold, setVectorSimilarityThreshold] = useState(0.4);
  const [vectorSearchLimit, setVectorSearchLimit] = useState(5);
  const [vectorChunkTypes, setVectorChunkTypes] = useState<string[]>([]);

  // 📱 SMS Notification Settings
  const [smsOnPhoneFound, setSmsOnPhoneFound] = useState(true);
  const [smsOnCustomerReply, setSmsOnCustomerReply] = useState(true);
  const [smsOnPhoneOptIn, setSmsOnPhoneOptIn] = useState(true);

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
  const tplRef = useRef<HTMLTextAreaElement | null>(null);

  // helper to insert placeholder
  const insertPlaceholder = (
    ph: Placeholder,
    target: 'greeting' | 'template' | 'after'
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

  const toggleDay = (day: string) => {
    const parts = greetingOpenDays
      .split(',')
      .map(p => p.trim())
      .filter(Boolean);
    const idx = parts.indexOf(day);
    if (idx >= 0) {
      parts.splice(idx, 1);
    } else {
      parts.push(day);
    }
    const ordered = DAY_NAMES.filter(d => parts.includes(d));
    setGreetingOpenDays(ordered.join(', '));
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
    greeting_open_days: 'Mon, Tue, Wed, Thu, Fri',
    export_to_sheets: false,
    follow_up_templates: [],
    // AI fields - maximally simplified 
    use_ai_greeting: false,
    // All AI behavior controlled via Custom Instructions (no individual checkboxes)
    ai_custom_prompt: undefined,
    // Business data controlled via Custom Instructions (individual settings removed)
    ai_max_message_length: 0,
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
    params.append('phone_opt_in', 'false');  // Always false - merged with No Phone
    params.append('phone_available', phoneAvailable ? 'true' : 'false');
    if (biz) params.append('business_id', biz);
    const url = `/settings/auto-response/?${params.toString()}`;

    const fetch = (remain: number) => {
      axios.get<AutoResponse>(url)
        .then(res => {
        console.log('✅ [FRONTEND] AI Preview response received:', res.data);
        console.log('📊 [FRONTEND] Response details:', {
          preview: res.data.preview?.substring(0, 100) + '...',
          vectorSearchEnabled: res.data.vector_search_enabled,
          vectorResultsCount: res.data.vector_results_count,
          status: res.status
        });
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
          setGreetingOpenDays(d.greeting_open_days || 'Mon, Tue, Wed, Thu, Fri');
          setExportToSheets(d.export_to_sheets);
          
          // Set AI settings - maximally simplified
          setUseAiGreeting(d.use_ai_greeting || false);
          // All AI behavior controlled via Custom Instructions (location, response time, business data, style)
          setAiCustomPrompt(d.ai_custom_prompt || '');
          
          // Set Sample Replies settings (MODE 2: AI Generated)
          setUseSampleReplies(d.use_sample_replies || false);
          setSampleRepliesContent(d.sample_replies_content || '');
          setSampleRepliesFilename(d.sample_replies_filename || '');
          setSampleRepliesPriority(d.sample_replies_priority ?? true);
          
          // Business data settings removed - controlled via Custom Instructions
          setAiMaxMessageLength(d.ai_max_message_length ?? 160);
          
          // Set Business-specific AI Model Settings
          setAiModel(d.ai_model ?? 'gpt-4o');  // ✅ Default to gpt-4o if not set
          setAiTemperature(d.ai_temperature ?? 0.7);  // ✅ Default temperature
          
          // Set Vector Search Settings
          setVectorSimilarityThreshold(d.vector_similarity_threshold ?? 0.6);
          setVectorSearchLimit(d.vector_search_limit ?? 5);
          setVectorChunkTypes(d.vector_chunk_types ?? []);
          
          // Set SMS Notification Settings
          setSmsOnPhoneFound(d.sms_on_phone_found ?? true);
          setSmsOnCustomerReply(d.sms_on_customer_reply ?? true);
          setSmsOnPhoneOptIn(d.sms_on_phone_opt_in ?? true);
          
          initialSettings.current = {
            enabled: d.enabled,
            greeting_template: d.greeting_template,
            greeting_off_hours_template: d.greeting_off_hours_template || '',
            greeting_delay: d.greeting_delay,
            greeting_open_from: d.greeting_open_from || '08:00:00',
            greeting_open_to: d.greeting_open_to || '20:00:00',
            greeting_open_days: d.greeting_open_days || 'Mon, Tue, Wed, Thu, Fri',
            export_to_sheets: d.export_to_sheets,
            follow_up_templates: initialSettings.current?.follow_up_templates || [],
                        // AI fields - maximally simplified
                        use_ai_greeting: d.use_ai_greeting,
                        // All AI behavior controlled via Custom Instructions
                        ai_custom_prompt: d.ai_custom_prompt,
            // AI Business Data Settings
            // Business data controlled via Custom Instructions
            ai_max_message_length: 0,
            // AI Model Settings
            ai_model: d.ai_model ?? '',
            ai_temperature: d.ai_temperature ?? null,
            // Vector Search Settings
            vector_similarity_threshold: d.vector_similarity_threshold ?? 0.6,
            vector_search_limit: d.vector_search_limit ?? 5,
            vector_chunk_types: d.vector_chunk_types ?? [],
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
    params.append('phone_opt_in', 'false');  // Always false - merged with No Phone
    params.append('phone_available', phoneAvailable ? 'true' : 'false');
    if (biz) params.append('business_id', biz);
    const url = `/follow-up-templates/?${params.toString()}`;
    axios.get<FollowUpTemplate[]>(url)
      .then(res => {
        console.log('✅ [FRONTEND] AI Preview response received:', res.data);
        console.log('📊 [FRONTEND] Response details:', {
          preview: res.data.preview?.substring(0, 100) + '...',
          vectorSearchEnabled: res.data.vector_search_enabled,
          vectorResultsCount: res.data.vector_results_count,
          status: res.status
        });
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
            greeting_open_days: 'Mon, Tue, Wed, Thu, Fri',
            export_to_sheets: false,
            follow_up_templates: mapped,
            // AI fields
            use_ai_greeting: false,
            ai_response_style: 'auto',
            ai_include_location: true,
            ai_mention_response_time: true,
            ai_custom_prompt: undefined,
            // AI Business Data Settings
            // Business data controlled via Custom Instructions
            ai_max_message_length: 0,
          };
        } else {
          initialSettings.current = {
            ...initialSettings.current,
            greeting_off_hours_template:
              initialSettings.current?.greeting_off_hours_template || '',
            greeting_open_days: initialSettings.current?.greeting_open_days || 'Mon, Tue, Wed, Thu, Fri',
            follow_up_templates: mapped,
            // AI fields - maximally simplified
            use_ai_greeting: initialSettings.current?.use_ai_greeting || false,
            // All AI behavior controlled via Custom Instructions  
            ai_custom_prompt: initialSettings.current?.ai_custom_prompt,
            // AI Business Data Settings
            // Business data controlled via Custom Instructions
            ai_max_message_length: 0,
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
    setGreetingOpenDays(d.greeting_open_days || 'Mon, Tue, Wed, Thu, Fri');
    setExportToSheets(d.export_to_sheets);

    // Apply AI settings - simplified to just Custom Instructions  
    setUseAiGreeting(d.use_ai_greeting || false);
    // All AI behavior controlled via Custom Instructions (location, response time, business data, etc)
    setAiCustomPrompt(d.ai_custom_prompt || '');

    // Business data settings removed - controlled via Custom Instructions  
    setAiMaxMessageLength(d.ai_max_message_length ?? 160);

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
    setBusinessesLoading(true);
    axios.get<Business[]>('/businesses/')
      .then(res => {
        console.log('✅ [FRONTEND] AI Preview response received:', res.data);
        console.log('📊 [FRONTEND] Response details:', {
          preview: res.data.preview?.substring(0, 100) + '...',
          vectorSearchEnabled: res.data.vector_search_enabled,
          vectorResultsCount: res.data.vector_results_count,
          status: res.status
        });
        setBusinesses(res.data);
        setBusinessesLoading(false);
      })
      .catch(() => {
        setBusinesses([]);
        setBusinessesLoading(false);
      });

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
  }, [selectedBusiness, phoneAvailable]);  // phoneOptIn removed


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

  useEffect(() => {
    if (!phoneAvailable) {
      setGreetingOpenDays('');
    }
  }, [phoneAvailable]);

  // save settings
  const handleSaveSettings = async () => {
    setLoading(true);
    
    // ✅ ВАЛІДАЦІЯ: Custom Instructions обов'язкові для AI режиму
    if (useAiGreeting && !aiCustomPrompt.trim()) {
      setError('Custom Instructions are required when AI Generation is enabled. Please provide fallback instructions to ensure quality responses.');
      setLoading(false);
      return;
    }
    
    const params = new URLSearchParams();
    params.append('phone_opt_in', 'false');  // Always false - merged with No Phone
    params.append('phone_available', phoneAvailable ? 'true' : 'false');
    if (selectedBusiness) params.append('business_id', selectedBusiness);
    const url = `/settings/auto-response/?${params.toString()}`;
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
        greeting_open_days: greetingOpenDays,
        export_to_sheets: exportToSheets,
        // AI fields
        use_ai_greeting: useAiGreeting,
        // ai_response_style removed - AI learns style from PDF examples
        // All AI behavior controlled via Custom Instructions
        ai_custom_prompt: aiCustomPrompt,
        // Sample Replies fields (MODE 2: AI Generated)
        use_sample_replies: useSampleReplies,
        sample_replies_content: sampleRepliesContent,
        sample_replies_filename: sampleRepliesFilename,
        sample_replies_priority: sampleRepliesPriority,
        // AI Business Data Settings
        // Business data settings removed - controlled via Custom Instructions
        ai_max_message_length: aiMaxMessageLength,
        // Business-specific AI Model Settings
        ai_model: aiModel,
        ai_temperature: aiTemperature === '' ? null : aiTemperature,
        // SMS Notification Settings
        sms_on_phone_found: smsOnPhoneFound,
        sms_on_customer_reply: smsOnCustomerReply,
        sms_on_phone_opt_in: smsOnPhoneOptIn,
      });

      setSettingsId(res.data.id);
      initialSettings.current = {
        enabled,
        greeting_template: greetingTemplate,
        greeting_off_hours_template: greetingAfterTemplate,
        greeting_delay: greetDelaySecs,
        greeting_open_from: greetingOpenFrom,
        greeting_open_to: greetingOpenTo,
        greeting_open_days: greetingOpenDays,
        export_to_sheets: exportToSheets,
        follow_up_templates: initialSettings.current?.follow_up_templates || [],
        // AI fields
        use_ai_greeting: useAiGreeting,
        // ai_response_style removed - AI learns style from PDF examples
        // All AI behavior controlled via Custom Instructions
        ai_custom_prompt: aiCustomPrompt,
        // AI Business Data Settings
        // Business data settings removed - controlled via Custom Instructions
        ai_max_message_length: aiMaxMessageLength,
        // SMS Notification Settings
        sms_on_phone_found: smsOnPhoneFound,
        sms_on_customer_reply: smsOnCustomerReply,
        sms_on_phone_opt_in: smsOnPhoneOptIn,
      };

      const params = new URLSearchParams();
      params.append('phone_opt_in', 'false'); // Phone opt-in merged with No Phone
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
    } catch (error: any) {
      console.error('Save settings error:', error);
      
      // Handle validation errors from backend
      if (error.response?.status === 400 && error.response?.data?.ai_custom_prompt) {
        setError(error.response.data.ai_custom_prompt[0]);
      } else if (error.response?.data?.message) {
        setError(error.response.data.message);
      } else {
        setError('Failed to save settings.');
      }
    } finally {
      setLoading(false);
    }
  };

  // auto-save AI model settings
  const handleSaveAiModelSettings = async (newAiModel?: string, newAiTemperature?: number | '') => {
    if (!selectedBusiness) return; // Only save if a business is selected
    
    const params = new URLSearchParams();
    params.append('phone_opt_in', 'false');  // Always false - merged with No Phone
    params.append('phone_available', phoneAvailable ? 'true' : 'false');
    params.append('business_id', selectedBusiness);
    const url = `/settings/auto-response/?${params.toString()}`;
    
    const greetDelaySecs =
      greetingDelayHours * 3600 +
      greetingDelayMinutes * 60 +
      greetingDelaySeconds;
    
    try {
      await axios.put<AutoResponse>(url, {
        enabled,
        greeting_template: greetingTemplate,
        greeting_off_hours_template: greetingAfterTemplate,
        greeting_delay: greetDelaySecs,
        greeting_open_from: greetingOpenFrom,
        greeting_open_to: greetingOpenTo,
        greeting_open_days: greetingOpenDays,
        export_to_sheets: exportToSheets,
        // AI fields
        use_ai_greeting: useAiGreeting,
        // ai_response_style removed - AI learns style from PDF examples
        // All AI behavior controlled via Custom Instructions
        ai_custom_prompt: aiCustomPrompt,
        // AI Business Data Settings
        // Business data settings removed - controlled via Custom Instructions
        ai_max_message_length: aiMaxMessageLength,
        // Business-specific AI Model Settings (use new values if provided, otherwise current state)
        ai_model: newAiModel !== undefined ? newAiModel : aiModel,
        ai_temperature: newAiTemperature !== undefined 
          ? (newAiTemperature === '' ? null : newAiTemperature)
          : (aiTemperature === '' ? null : aiTemperature),
        // Vector Search Settings
        vector_similarity_threshold: vectorSimilarityThreshold,
        vector_search_limit: vectorSearchLimit,
        vector_chunk_types: vectorChunkTypes,
        // SMS Notification Settings
        sms_on_phone_found: smsOnPhoneFound,
        sms_on_customer_reply: smsOnCustomerReply,
        sms_on_phone_opt_in: smsOnPhoneOptIn,
      });
      
      // Show brief success indicator (optional)
      console.log('AI model settings auto-saved');
    } catch (error) {
      console.error('Failed to auto-save AI model settings:', error);
      // Could show a brief error message here if desired
    }
  };

  // auto-save vector search settings
  const handleSaveVectorSettings = async () => {
    if (!selectedBusiness) return; // Only save if a business is selected
    
    const params = new URLSearchParams();
    params.append('phone_opt_in', 'false');  // Always false - merged with No Phone
    params.append('phone_available', phoneAvailable ? 'true' : 'false');
    params.append('business_id', selectedBusiness);
    const url = `/settings/auto-response/?${params.toString()}`;
    
    const greetDelaySecs =
      greetingDelayHours * 3600 +
      greetingDelayMinutes * 60 +
      greetingDelaySeconds;
    
    try {
      await axios.put<AutoResponse>(url, {
        enabled,
        greeting_template: greetingTemplate,
        greeting_off_hours_template: greetingAfterTemplate,
        greeting_delay: greetDelaySecs,
        greeting_open_from: greetingOpenFrom,
        greeting_open_to: greetingOpenTo,
        greeting_open_days: greetingOpenDays,
        export_to_sheets: exportToSheets,
        // AI fields
        use_ai_greeting: useAiGreeting,
        // ai_response_style removed - AI learns style from PDF examples
        // All AI behavior controlled via Custom Instructions
        ai_custom_prompt: aiCustomPrompt,
        // Sample Replies fields (MODE 2: AI Generated)
        use_sample_replies: useSampleReplies,
        sample_replies_content: sampleRepliesContent,
        sample_replies_filename: sampleRepliesFilename,
        sample_replies_priority: sampleRepliesPriority,
        // AI Business Data Settings
        // Business data settings removed - controlled via Custom Instructions
        ai_max_message_length: aiMaxMessageLength,
        // Business-specific AI Model Settings
        ai_model: aiModel,
        ai_temperature: aiTemperature === '' ? null : aiTemperature,
        // Vector Search Settings
        vector_similarity_threshold: vectorSimilarityThreshold,
        vector_search_limit: vectorSearchLimit,
        vector_chunk_types: vectorChunkTypes,
        // SMS Notification Settings
        sms_on_phone_found: smsOnPhoneFound,
        sms_on_customer_reply: smsOnCustomerReply,
        sms_on_phone_opt_in: smsOnPhoneOptIn,
      });
      
      console.log('Vector search settings auto-saved');
    } catch (error) {
      console.error('Failed to auto-save vector search settings:', error);
    }
  };

  // add new template
  const handleAddTemplate = () => {
    setTplLoading(true);
    const params = new URLSearchParams();
    params.append('phone_opt_in', 'false');  // Always false - merged with No Phone
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
        console.log('✅ [FRONTEND] AI Preview response received:', res.data);
        console.log('📊 [FRONTEND] Response details:', {
          preview: res.data.preview?.substring(0, 100) + '...',
          vectorSearchEnabled: res.data.vector_search_enabled,
          vectorResultsCount: res.data.vector_results_count,
          status: res.status
        });
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
    params.append('phone_opt_in', 'false');  // Always false - merged with No Phone
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
        console.log('✅ [FRONTEND] AI Preview response received:', res.data);
        console.log('📊 [FRONTEND] Response details:', {
          preview: res.data.preview?.substring(0, 100) + '...',
          vectorSearchEnabled: res.data.vector_search_enabled,
          vectorResultsCount: res.data.vector_results_count,
          status: res.status
        });
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
    params.append('phone_opt_in', 'false');  // Always false - merged with No Phone
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

  // Function to check if current time is within business hours
  const isWithinBusinessHours = () => {
    if (!selectedBusiness || !localTime) return true; // Default to business hours if no time info
    
    const currentTime = localTime.replace(/:/g, ''); // Convert "14:30:45" to "143045"
    const openTime = greetingOpenFrom.replace(/:/g, ''); // Convert "08:00:00" to "080000"  
    const closeTime = greetingOpenTo.replace(/:/g, ''); // Convert "20:00:00" to "200000"
    
    // Simple time comparison (works for same-day hours)
    return currentTime >= openTime && currentTime <= closeTime;
  };

  // Handle AI mode change with auto-fill Custom Instructions
  const handleAiModeChange = (enableAi: boolean) => {
    setUseAiGreeting(enableAi);
    
    // ✅ AUTO-FILL Custom Instructions when enabling AI mode
    if (enableAi && !aiCustomPrompt.trim()) {
      const defaultPrompt = `You are a professional business communication assistant.

BUSINESS INFORMATION USAGE:
- Always mention our business rating and review count when available  
- Include our phone number for direct contact
- Mention our specialization/service categories
- Include business location when relevant to customer request
- Mention estimated response time if needed (e.g., "within 24 hours")

COMMUNICATION STYLE:
- Be friendly, professional, and helpful
- Use conversational but business-appropriate tone
- Address customer's specific service request
- Offer next steps (estimate, consultation, etc)
- End with professional closing

EXAMPLE: "Hi [Name]! [Business] (4.0★, 12 reviews) in [Location] specializes in [category]. We'd love to help with [request]. Call [phone] - we typically respond within 2 hours!"

AVOID: Generic responses, overly formal language, sales pressure`;
      
      setAiCustomPrompt(defaultPrompt);
    }
  };

  // Generate AI preview
  const generateAiPreview = async () => {
    if (!selectedBusiness) {
      setAiPreview('Please select a business first.');
      return;
    }

    console.log('📡 [FRONTEND] Sending AI Preview request...', {
      apiEndpoint: '/ai-preview/',
      requestData: {
        business_id: selectedBusiness,
        phone_available: phoneAvailable,
        custom_preview_text: aiCustomPreviewText,
        vector_settings: {
          similarity_threshold: vectorSimilarityThreshold,
          search_limit: vectorSearchLimit,
          chunk_types: vectorChunkTypes
        }
      }
    });
    
    setAiPreviewLoading(true);
    try {
      const response = await axios.post('/ai/preview/', {
        business_id: selectedBusiness,  // Передаємо business_id для отримання реальних даних
        // ai_response_style removed - AI learns style from PDF examples
        // All AI behavior controlled via Custom Instructions
        ai_custom_prompt: aiCustomPrompt || undefined,  // Custom Instructions is now the primary prompt (no fallback needed)
        custom_preview_text: aiCustomPreviewText || undefined, // 🎯 Додаємо custom preview text
        // Business data controlled via Custom Instructions (individual checkboxes removed)
        // ai_max_message_length removed - AI auto-detects length from Sample Replies examples
        // Business-specific AI Model Settings
        ai_model: aiModel,
        ai_temperature: aiTemperature === '' ? null : aiTemperature,
        // Vector Search Settings (for preview)
        vector_similarity_threshold: vectorSimilarityThreshold,
        vector_search_limit: vectorSearchLimit,
        vector_chunk_types: vectorChunkTypes,
      });

      setAiPreview(response.data.preview);
    } catch (error) {
      console.error('Failed to generate AI preview:', error);
      setAiPreview('Error generating preview. Please check your AI settings.');
    } finally {
      setAiPreviewLoading(false);
    }
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
                disabled={businessesLoading}
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

            {!businessesLoading && businesses.length === 0 && (
              <Alert severity="info" sx={{ borderRadius: 2 }}>
                <Typography variant="body2">
                  No businesses found. Please make sure you have businesses configured in your account.
                </Typography>
              </Alert>
            )}
            
            {businessesLoading && (
              <Alert severity="info" sx={{ borderRadius: 2 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <CircularProgress size={16} />
                  <Typography variant="body2">
                    Loading businesses...
                  </Typography>
                </Box>
              </Alert>
            )}
          </CardContent>
        </Card>
      </Container>
    );
  }

  return (
    <Container maxWidth={false} sx={{ mt: 4, mb: 4, maxWidth: 1000, mx: 'auto' }}>
      
      {/* Top Status Indicator */}
      <Card 
        elevation={2} 
        sx={{ 
          mb: 3, 
          background: useAiGreeting !== initialSettings.current?.use_ai_greeting 
            ? 'linear-gradient(135deg, #fff3e0 0%, #ffcc02 100%)' 
            : 'linear-gradient(135deg, #e8f5e8 0%, #4caf50 100%)',
          border: '2px solid',
          borderColor: useAiGreeting !== initialSettings.current?.use_ai_greeting ? 'warning.main' : 'success.main'
        }}
      >
        <CardContent sx={{ py: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <Typography variant="h6" sx={{ fontWeight: 700, color: 'text.primary' }}>
                🎯 GREETING MESSAGE STATUS
              </Typography>
              
              {useAiGreeting !== initialSettings.current?.use_ai_greeting ? (
                <Chip
                  icon={<WarningIcon sx={{ fontSize: 16 }} />}
                  label="UNSAVED CHANGES"
                  color="warning"
                  variant="filled"
                  sx={{ fontWeight: 600, fontSize: '0.8rem' }}
                />
              ) : (
                <Chip
                  icon={<CheckCircleIcon sx={{ fontSize: 16 }} />}
                  label="SAVED"
                  color="success"
                  variant="filled"
                  sx={{ fontWeight: 600, fontSize: '0.8rem' }}
                />
              )}
            </Box>
            
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, flexWrap: 'wrap' }}>
              <Typography variant="body2" sx={{ fontWeight: 600, color: 'text.secondary' }}>
                Active Mode:
              </Typography>
              <Chip
                icon={initialSettings.current?.use_ai_greeting ? <PersonIcon sx={{ fontSize: 14 }} /> : <MessageIcon sx={{ fontSize: 14 }} />}
                label={initialSettings.current?.use_ai_greeting ? '🤖 AI GENERATED' : '📝 TEMPLATE MESSAGE'}
                color={initialSettings.current?.use_ai_greeting ? 'info' : 'primary'}
                variant="filled"
                sx={{ fontWeight: 700, fontSize: '0.8rem' }}
              />
              
              {useAiGreeting !== initialSettings.current?.use_ai_greeting && (
                <>
                  <Typography variant="body2" sx={{ color: 'warning.main', fontWeight: 600 }}>
                    →
                  </Typography>
                  <Chip
                    icon={useAiGreeting ? <PersonIcon sx={{ fontSize: 14 }} /> : <MessageIcon sx={{ fontSize: 14 }} />}
                    label={useAiGreeting ? '🤖 AI GENERATED' : '📝 TEMPLATE MESSAGE'}
                    color="warning"
                    variant="outlined"
                    sx={{ fontWeight: 600, fontSize: '0.8rem' }}
                  />
                </>
              )}
            </Box>
          </Box>
        </CardContent>
      </Card>

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

      {selectedBusiness && (() => {
        const biz = businesses.find(b => b.business_id === selectedBusiness);
        if (!biz) return null;
        return (
          <Box sx={{ mb: 2 }}>
            <BusinessInfoCard business={biz} />
          </Box>
        );
      })()}

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
                value={phoneAvailable ? 'text' : 'no'}
                onChange={(_, v) => {
                  if (v === 'text') {
                    setPhoneAvailable(true);
                  } else {
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
                  label="No Phone and Phone Opt-In"
                  value="no"
                />

                <Tab
                  icon={<PhoneIcon sx={{ fontSize: 18 }} />}
                  iconPosition="start"
                  label="Phone Number in Message"
                  value="text"
                />
              </Tabs>
            </Paper>
          </Box>
        </CardContent>
      </Card>

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
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center' }}>
                      <MessageIcon sx={{ mr: 1, color: 'primary.main' }} />
                      {phoneAvailable ? 'Greeting Message (Business Hours)' : 'Greeting Message'}
                    </Typography>

                    {/* Saved Mode Status Indicator */}
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                      {/* Saved Mode */}
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.75rem', fontWeight: 600 }}>
                          💾 SAVED MODE:
                        </Typography>
                        <Chip
                          icon={initialSettings.current?.use_ai_greeting ? <PersonIcon sx={{ fontSize: 14 }} /> : <MessageIcon sx={{ fontSize: 14 }} />}
                          label={initialSettings.current?.use_ai_greeting ? 'AI GENERATED' : 'TEMPLATE MESSAGE'}
                          size="small"
                          color={initialSettings.current?.use_ai_greeting ? 'info' : 'primary'}
                          variant="filled"
                          sx={{ 
                            fontSize: '0.75rem',
                            height: 24,
                            fontWeight: 700,
                            border: '2px solid',
                            borderColor: initialSettings.current?.use_ai_greeting ? 'info.dark' : 'primary.dark'
                          }}
                        />
                      </Box>

                      {/* Unsaved Changes Indicator */}
                      {useAiGreeting !== initialSettings.current?.use_ai_greeting && (
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Typography variant="caption" sx={{ color: 'warning.main', fontSize: '0.75rem', fontWeight: 600 }}>
                            ⚠️ UNSAVED:
                          </Typography>
                          <Chip
                            icon={useAiGreeting ? <PersonIcon sx={{ fontSize: 14 }} /> : <MessageIcon sx={{ fontSize: 14 }} />}
                            label={useAiGreeting ? 'AI GENERATED' : 'TEMPLATE MESSAGE'}
                            size="small"
                            color="warning"
                            variant="outlined"
                            sx={{ 
                              fontSize: '0.75rem',
                              height: 24,
                              fontWeight: 600,
                              animation: 'blink 1.5s infinite'
                            }}
                          />
                        </Box>
                      )}
                    </Box>
                  </Box>
                </Box>
                
                <CardContent sx={{ p: 3 }}>
                  <Stack spacing={3}>
                    {/* Message Type Selection */}
                    <Box sx={{ textAlign: 'center' }}>
                      <Typography variant="h6" sx={{ mb: 3, fontWeight: 700, color: 'primary.main' }}>
                        🎯 SELECT GREETING MESSAGE MODE
                      </Typography>
                      
                      {/* Mode Selection Buttons */}
                      <Box sx={{ display: 'flex', justifyContent: 'center', gap: 2, mb: 3 }}>
                        {/* Template Mode Button */}
                        <Card 
                          elevation={useAiGreeting === false ? 4 : 1}
                          sx={{
                            p: 3,
                            minWidth: 200,
                            cursor: 'pointer',
                            transition: 'all 0.3s ease',
                            backgroundColor: useAiGreeting === false ? 'primary.50' : 'white',
                            border: '3px solid',
                            borderColor: useAiGreeting === false ? 'primary.main' : 'grey.300',
                            transform: useAiGreeting === false ? 'scale(1.05)' : 'scale(1)',
                            '&:hover': {
                              elevation: 3,
                              transform: 'scale(1.02)'
                            },
                            '@keyframes blink': {
                              '0%, 50%': { opacity: 1 },
                              '25%, 75%': { opacity: 0.5 }
                            }
                          }}
                          onClick={() => handleAiModeChange(false)}
                        >
                          <Box sx={{ textAlign: 'center' }}>
                            <MessageIcon sx={{ fontSize: 40, color: useAiGreeting === false ? 'primary.main' : 'grey.500', mb: 1 }} />
                            <Typography variant="h6" sx={{ fontWeight: 700, color: useAiGreeting === false ? 'primary.main' : 'text.secondary' }}>
                              📝 TEMPLATE MESSAGE
                            </Typography>
                            <Typography variant="body2" sx={{ mt: 1, color: 'text.secondary' }}>
                              Use predefined message templates with customer data placeholders
                            </Typography>
                            {useAiGreeting === false && (
                              <Chip
                                label="✓ SELECTED"
                                size="small"
                                color="primary"
                                variant="filled"
                                sx={{ mt: 2, fontWeight: 600 }}
                              />
                            )}
                          </Box>
                        </Card>

                        {/* AI Mode Button */}
                        <Card 
                          elevation={useAiGreeting === true ? 4 : 1}
                          sx={{
                            p: 3,
                            minWidth: 200,
                            cursor: 'pointer',
                            transition: 'all 0.3s ease',
                            backgroundColor: useAiGreeting === true ? 'info.50' : 'white',
                            border: '3px solid',
                            borderColor: useAiGreeting === true ? 'info.main' : 'grey.300',
                            transform: useAiGreeting === true ? 'scale(1.05)' : 'scale(1)',
                            '&:hover': {
                              elevation: 3,
                              transform: 'scale(1.02)'
                            }
                          }}
                          onClick={() => handleAiModeChange(true)}
                        >
                          <Box sx={{ textAlign: 'center' }}>
                            <PersonIcon sx={{ fontSize: 40, color: useAiGreeting === true ? 'info.main' : 'grey.500', mb: 1 }} />
                            <Typography variant="h6" sx={{ fontWeight: 700, color: useAiGreeting === true ? 'info.main' : 'text.secondary' }}>
                              🤖 AI GENERATED
                            </Typography>
                            <Typography variant="body2" sx={{ mt: 1, color: 'text.secondary' }}>
                              Automatically generate personalized messages using AI
                            </Typography>
                            {useAiGreeting === true && (
                              <Chip
                                label="✓ SELECTED"
                                size="small"
                                color="info"
                                variant="filled"
                                sx={{ mt: 2, fontWeight: 600 }}
                              />
                            )}
                          </Box>
                        </Card>
                      </Box>

                      {/* Selected Mode Description */}
                      <Box sx={{ 
                        p: 2, 
                        backgroundColor: useAiGreeting ? 'info.50' : 'primary.50', 
                        borderRadius: 2,
                        border: '1px solid',
                        borderColor: useAiGreeting ? 'info.main' : 'primary.main'
                      }}>
                        <Typography variant="body2" sx={{ fontWeight: 600, color: useAiGreeting ? 'info.dark' : 'primary.dark' }}>
                          {useAiGreeting
                            ? '🤖 AI Mode Selected: Messages will be generated automatically using artificial intelligence based on customer information and business context.'
                            : '📝 Template Mode Selected: Use predefined message templates with placeholders like {name}, {jobs}, and {reason} that will be replaced with actual customer data.'
                          }
                        </Typography>
                      </Box>

                                             {/* Save Reminder */}
                       {useAiGreeting !== initialSettings.current?.use_ai_greeting && (
                        <Box sx={{ 
                          mt: 2,
                          p: 2, 
                          backgroundColor: 'warning.50', 
                          borderRadius: 2,
                          border: '2px solid',
                          borderColor: 'warning.main',
                          textAlign: 'center',
                          '@keyframes shake': {
                            '0%, 100%': { transform: 'translateX(0)' },
                            '25%': { transform: 'translateX(-5px)' },
                            '75%': { transform: 'translateX(5px)' }
                          },
                          animation: 'shake 0.5s ease-in-out infinite alternate'
                        }}>
                          <Typography variant="h6" sx={{ fontWeight: 700, color: 'warning.dark', mb: 1 }}>
                            ⚠️ MODE CHANGED - PLEASE SAVE!
                          </Typography>
                          <Typography variant="body2" sx={{ color: 'warning.dark' }}>
                            You have selected a different greeting message mode. 
                            <strong> Click "Save Settings" to apply the changes.</strong>
                          </Typography>
                          
                          {/* Mode Comparison */}
                          <Box sx={{ mt: 2, display: 'flex', justifyContent: 'center', gap: 2, flexWrap: 'wrap' }}>
                            <Box sx={{ textAlign: 'center' }}>
                              <Typography variant="caption" sx={{ display: 'block', fontWeight: 600, color: 'error.main' }}>
                                CURRENTLY ACTIVE:
                              </Typography>
                                                             <Chip
                                 icon={initialSettings.current?.use_ai_greeting ? <PersonIcon sx={{ fontSize: 14 }} /> : <MessageIcon sx={{ fontSize: 14 }} />}
                                 label={initialSettings.current?.use_ai_greeting ? 'AI Generated' : 'Template Message'}
                                 size="small"
                                 color="error"
                                 variant="filled"
                                 sx={{ fontWeight: 600 }}
                               />
                            </Box>
                            
                            <Typography variant="h6" sx={{ color: 'warning.dark', alignSelf: 'center' }}>
                              →
                            </Typography>
                            
                            <Box sx={{ textAlign: 'center' }}>
                              <Typography variant="caption" sx={{ display: 'block', fontWeight: 600, color: 'success.main' }}>
                                WILL BECOME:
                              </Typography>
                              <Chip
                                icon={useAiGreeting ? <PersonIcon sx={{ fontSize: 14 }} /> : <MessageIcon sx={{ fontSize: 14 }} />}
                                label={useAiGreeting ? 'AI Generated' : 'Template Message'}
                                size="small"
                                color="success"
                                variant="filled"
                                sx={{ fontWeight: 600 }}
                              />
                            </Box>
                          </Box>
                        </Box>
                      )}
                    </Box>

                    {/* AI Settings */}
                    {useAiGreeting && (
                      <>
                        {/* AI Configuration Header */}
                        <Box sx={{ 
                          textAlign: 'center', 
                          py: 3, 
                          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                          borderRadius: 2,
                          color: 'white',
                          mb: 3
                        }}>
                          <Typography variant="h5" sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, mb: 1 }}>
                            <PersonIcon sx={{ mr: 1, fontSize: 28 }} />
                            🤖 AI Configuration Active
                          </Typography>
                          <Typography variant="body2" sx={{ opacity: 0.9, mb: 2 }}>
                            Advanced AI-powered response generation is enabled for this business
                          </Typography>
                          
                          {/* Instructions */}
                          <Box sx={{ 
                            background: 'rgba(255,255,255,0.1)', 
                            p: 2, 
                            borderRadius: 1, 
                            textAlign: 'left',
                            fontSize: '0.85rem'
                          }}>
                            <Typography variant="body2" sx={{ fontWeight: 600, mb: 1, color: '#fff' }}>
                              🎯 How Simplified AI System Works:
                            </Typography>
                            
                            <Typography variant="caption" sx={{ display: 'block', mb: 1, color: 'rgba(255,255,255,0.95)' }}>
                              <strong>2-Step AI Generation:</strong> <strong>Vector Search</strong> → <strong>Custom Instructions</strong>
                            </Typography>
                            
                            <Box sx={{ mt: 1 }}>
                              <Typography variant="caption" sx={{ display: 'block', color: 'rgba(255,255,255,0.9)' }}>
                                <strong>🔍 Step 1 - Vector Search (Sample Replies):</strong><br/>
                                If Sample Replies PDF uploaded + custom preview text provided → AI searches for similar inquiry→response pairs and uses authentic style from your examples.<br/>
                                <em>→ Result: Natural responses matching your business voice</em>
                              </Typography>
                              
                              <Typography variant="caption" sx={{ display: 'block', mt: 1, color: 'rgba(255,255,255,0.9)' }}>
                                <strong>📝 Step 2 - Custom Instructions (Primary):</strong><br/>
                                AI sees ALL available business data (rating: 4.0★, phone: (213) 816-1560, specialization: General Contractors) + your Custom Instructions.<br/>
                                <em>→ Example: "Always mention our 4.0★ rating and phone. We specialize in contractors. Be friendly and offer free estimates."</em><br/>
                                <em>→ Result: "Hi! Priority Remodeling (4.0★, 12 reviews) specializes in General Contractors. Call (213) 816-1560 for a free estimate!"</em>
                              </Typography>
                            </Box>
                            
                            <Typography variant="caption" sx={{ display: 'block', mt: 1.5, fontWeight: 600, color: '#fff' }}>
                              💡 <strong>Best Practice:</strong> Write specific instructions about what business information to mention and how to communicate with customers.
                            </Typography>
                            
                            <Typography variant="caption" sx={{ display: 'block', mt: 1.5, fontWeight: 600, color: 'rgba(255,200,200,1)' }}>
                              ⚠️ <strong>If AI fails:</strong> System uses template fallback: "Hello [Customer Name]! Thank you for your inquiry about [services]. We'll get back to you soon!"
                            </Typography>
                          </Box>
                        </Box>

                        {/* AI Settings Grid */}
                        <Grid container spacing={3}>
                          {/* Additional Configuration - Compact Accordion Design */}
                          <Grid item xs={12}>
                            <Card elevation={2} sx={{ borderRadius: 3, overflow: 'hidden' }}>
                              {/* Compact Header */}
                              <Box sx={{ 
                                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                                p: 2,
                                color: 'white'
                              }}>
                                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                                    <TuneIcon sx={{ mr: 1.5, fontSize: 24 }} />
                                    <Box>
                                      <Typography variant="h6" sx={{ fontWeight: 600, lineHeight: 1.2 }}>
                                  Additional Configuration
                                </Typography>
                                      <Typography variant="caption" sx={{ opacity: 0.9, display: 'block' }}>
                                        Advanced settings and AI model configuration
                                      </Typography>
                              </Box>
                                  </Box>
                                  
                                  {/* Quick Status Indicators */}
                                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                    <Chip
                                      size="small"
                                      label={`${aiMaxMessageLength || 160} chars`}
                                      sx={{ 
                                        backgroundColor: 'rgba(255,255,255,0.2)',
                                        color: 'white',
                                        border: '1px solid rgba(255,255,255,0.3)',
                                        fontWeight: 600
                                      }}
                                    />
                                    <Chip
                                      size="small"
                                      label={aiModel || 'Global Model'}
                                      sx={{ 
                                        backgroundColor: 'rgba(255,255,255,0.2)',
                                        color: 'white',
                                        border: '1px solid rgba(255,255,255,0.3)',
                                        fontWeight: 600
                                      }}
                                    />
                                  </Box>
                                </Box>
                              </Box>

                              {/* Accordion Sections */}
                              <Box sx={{ backgroundColor: 'grey.50' }}>
                                {/* 1. Customer Data Info - Collapsed by default */}
                                <Accordion sx={{ 
                                  backgroundColor: 'transparent', 
                                  boxShadow: 'none',
                                  '&:before': { display: 'none' }
                                }}>
                                  <AccordionSummary
                                    expandIcon={<ExpandMoreIcon />}
                                    sx={{ 
                                      backgroundColor: 'white',
                                      borderBottom: '1px solid',
                                      borderBottomColor: 'divider',
                                      minHeight: 56,
                                      '&.Mui-expanded': { minHeight: 56 }
                                    }}
                                  >
                                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                                      <InfoIcon sx={{ color: 'info.main', fontSize: 20 }} />
                              <Box>
                                        <Typography variant="subtitle2" sx={{ fontWeight: 600, color: 'info.main' }}>
                                          Customer Data Information
                                </Typography>
                                        <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                                          What information is automatically included in AI responses
                                        </Typography>
                                      </Box>
                                    </Box>
                                  </AccordionSummary>
                                  <AccordionDetails sx={{ backgroundColor: 'info.50', p: 3 }}>
                                <Typography variant="caption" sx={{ mb: 2, display: 'block', color: 'text.secondary', fontStyle: 'italic' }}>
                                  The following customer information is automatically analyzed and included in every AI message (cannot be disabled):
                                </Typography>
                                
                                <Box sx={{ 
                                  p: 2, 
                                      backgroundColor: 'white', 
                                  borderRadius: 1, 
                                  border: '1px solid', 
                                  borderColor: 'info.200' 
                                }}>
                                      <Grid container spacing={2}>
                                    <Grid item xs={12} sm={6}>
                                          <Typography variant="caption" sx={{ fontWeight: 600, color: 'info.dark', mb: 1, display: 'block' }}>
                                        Customer Information:
                                      </Typography>
                                          <Box sx={{ pl: 1 }}>
                                            <Typography variant="caption" sx={{ display: 'flex', alignItems: 'center', mb: 0.5 }}>
                                              <PersonIcon sx={{ fontSize: 14, color: 'info.main', mr: 1 }} />
                                              Customer name (if available)
                                            </Typography>
                                            <Typography variant="caption" sx={{ display: 'flex', alignItems: 'center' }}>
                                              <WorkIcon sx={{ fontSize: 14, color: 'info.main', mr: 1 }} />
                                              Services of interest (job types)
                                            </Typography>
                                          </Box>
                                    </Grid>
                                    <Grid item xs={12} sm={6}>
                                          <Typography variant="caption" sx={{ fontWeight: 600, color: 'info.dark', mb: 1, display: 'block' }}>
                                        Context Information:
                                      </Typography>
                                          <Box sx={{ pl: 1 }}>
                                            <Typography variant="caption" sx={{ display: 'flex', alignItems: 'center', mb: 0.5 }}>
                                              <InfoIcon sx={{ fontSize: 14, color: 'info.main', mr: 1 }} />
                                              Additional info from customer
                                            </Typography>
                                            <Typography variant="caption" sx={{ display: 'flex', alignItems: 'center' }}>
                                              <AccessTimeIcon sx={{ fontSize: 14, color: 'info.main', mr: 1 }} />
                                              Inquiry timing (business hours)
                                            </Typography>
                                          </Box>
                                    </Grid>
                                  </Grid>
                                </Box>
                                  </AccordionDetails>
                                </Accordion>

                                {/* 2. Advanced AI Model Settings (Message Length AUTO-DETECTED from Sample Replies) */}
                                <Accordion sx={{ 
                                  backgroundColor: 'transparent', 
                                  boxShadow: 'none',
                                  '&:before': { display: 'none' }
                                }}>
                                  <AccordionSummary
                                    expandIcon={<ExpandMoreIcon />}
                                    sx={{ 
                                      backgroundColor: 'white',
                                      borderBottom: '1px solid',
                                      borderBottomColor: 'divider',
                                      minHeight: 56,
                                      '&.Mui-expanded': { minHeight: 56 }
                                    }}
                                  >
                                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                                      <SettingsIcon sx={{ color: 'secondary.main', fontSize: 20 }} />
                                      <Box>
                                        <Typography variant="subtitle2" sx={{ fontWeight: 600, color: 'secondary.main' }}>
                                          Advanced AI Model Settings
                                        </Typography>
                                        <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                                          Override global AI settings for this business
                                        </Typography>
                                      </Box>
                                      <Box sx={{ ml: 'auto', display: 'flex', gap: 1 }}>
                                        <Chip
                                          size="small"
                                          label={aiModel || 'Global'}
                                          color={aiModel ? 'secondary' : 'default'}
                                          variant="outlined"
                                        />
                                        {aiTemperature !== '' && (
                                          <Chip
                                            size="small"
                                            label={`T=${aiTemperature}`}
                                            color="secondary"
                                            variant="outlined"
                                          />
                                        )}
                                      </Box>
                                    </Box>
                                  </AccordionSummary>
                                  <AccordionDetails sx={{ backgroundColor: 'secondary.50', p: 3 }}>
                                    
                                <Box sx={{ 
                                  p: 2, 
                                      backgroundColor: 'white', 
                                  borderRadius: 1, 
                                  border: '1px solid', 
                                      borderColor: 'secondary.200' 
                                    }}>
                                  <Stack spacing={2}>
                                    {/* AI Model Selection */}
                                    <Box>
                                          <FormControl size="small" sx={{ width: 320, backgroundColor: 'grey.50' }}>
                                        <InputLabel>OpenAI Model (optional)</InputLabel>
                                        <Select
                                          value={aiModel}
                                          onChange={e => {
                                            const newValue = e.target.value;
                                            setAiModel(newValue);
                                            handleSaveAiModelSettings(newValue, undefined);
                                          }}
                                          label="OpenAI Model (optional)"
                                        >
                                          <MenuItem value="gpt-4o">
                                            <Box>
                                              <Typography variant="body2">gpt-4o <Chip label="Default" size="small" color="primary" sx={{ ml: 1 }} /></Typography>
                                              <Typography variant="caption" color="text.secondary">Recommended - Best quality and compliance with instructions</Typography>
                                            </Box>
                                          </MenuItem>

                                              <MenuItem value="gpt-4o-mini">
                                            <Box>
                                                  <Typography variant="body2">GPT-4o Mini <Chip label="Budget" size="small" color="success" sx={{ ml: 1 }} /></Typography>
                                                  <Typography variant="caption" color="text.secondary">⚡ Fastest & most cost-effective. May skip some instructions.</Typography>
                                            </Box>
                                          </MenuItem>
                                        </Select>
                                        <FormHelperText>
                                          {aiModel 
                                            ? `Currently using: ${aiModel}` 
                                            : "Using default: gpt-4o (recommended)"}
                                        </FormHelperText>
                                      </FormControl>
                                    </Box>
                                    
                                    {/* AI Temperature */}
                                    <Box>
                                          <FormControl size="small" sx={{ width: 280, backgroundColor: 'grey.50' }}>
                                        <InputLabel>AI Temperature (optional)</InputLabel>
                                        <Select
                                          value={aiTemperature === '' ? '' : aiTemperature.toString()}
                                          onChange={e => {
                                            const newValue = e.target.value === '' ? '' : Number(e.target.value);
                                            setAiTemperature(newValue);
                                            handleSaveAiModelSettings(undefined, newValue);
                                          }}
                                          label="AI Temperature (optional)"
                                        >
                                          <MenuItem value={0.7}>
                                            <Box>
                                              <Typography variant="body2">0.7 <Chip label="Default" size="small" color="primary" sx={{ ml: 1 }} /></Typography>
                                              <Typography variant="caption" color="text.secondary">Balanced creativity - Recommended for most use cases</Typography>
                                            </Box>
                                          </MenuItem>
                                          <MenuItem value="0.1">
                                            <Box>
                                              <Typography variant="body2">0.1 - Very Focused <Chip label="Consistent" size="small" color="info" sx={{ ml: 1 }} /></Typography>
                                              <Typography variant="caption" color="text.secondary">Very consistent, predictable responses. Best for formal business.</Typography>
                                            </Box>
                                          </MenuItem>
                                          <MenuItem value="0.3">
                                            <Box>
                                              <Typography variant="body2">0.3 - Focused <Chip label="Recommended" size="small" color="primary" sx={{ ml: 1 }} /></Typography>
                                              <Typography variant="caption" color="text.secondary">Reliable yet natural responses. Great for customer support.</Typography>
                                            </Box>
                                          </MenuItem>
                                          <MenuItem value="0.7">
                                            <Box>
                                              <Typography variant="body2">0.7 - Balanced</Typography>
                                              <Typography variant="caption" color="text.secondary">Good balance of consistency and creativity.</Typography>
                                            </Box>
                                          </MenuItem>
                                          <MenuItem value="1.0">
                                            <Box>
                                              <Typography variant="body2">1.0 - Creative</Typography>
                                              <Typography variant="caption" color="text.secondary">More varied, creative responses. Use with caution.</Typography>
                                            </Box>
                                          </MenuItem>
                                        </Select>
                                        <FormHelperText>
                                          {aiTemperature !== '' 
                                                    ? `Creativity level: ${aiTemperature <= 0.3 ? 'Very focused' : aiTemperature <= 0.7 ? 'Balanced' : 'Creative'}` 
                                                : "Using default: 0.7 (balanced)"}
                                        </FormHelperText>
                                      </FormControl>
                                    </Box>
                                  </Stack>
                                </Box>
                                  </AccordionDetails>
                                </Accordion>
                              </Box>
                            </Card>
                          </Grid>

                          {/* 🔍 Vector Search & MODE 2 Settings (for Sample Replies) */}
                          <Grid item xs={12}>
                              {useSampleReplies && (
                                <Box sx={{ 
                                  borderRadius: 2, 
                                  border: '1px solid', 
                                  borderColor: 'info.300',
                                  backgroundColor: 'info.50',
                                  overflow: 'hidden'
                                }}>
                                  {/* Header */}
                                  <Box sx={{ 
                                    p: 2.5, 
                                    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                                    color: 'white'
                                  }}>
                                    <Typography variant="h6" sx={{ 
                                      fontWeight: 600, 
                                      display: 'flex', 
                                      alignItems: 'center', 
                                      gap: 1
                                    }}>
                                      <VectorIcon sx={{ fontSize: 24 }} />
                                      🔍 MODE 2: Vector-Enhanced Sample Replies
                                    </Typography>
                                    <Typography variant="body2" sx={{ 
                                      opacity: 0.9, 
                                      display: 'block', 
                                      mt: 0.5,
                                      fontWeight: 500
                                    }}>
                                      Advanced semantic chunking with OpenAI embeddings for intelligent contextual replies
                                    </Typography>
                                  </Box>

                                  {/* Accordion: MODE 2 Vector-Enhanced Sample Replies */}
                                  <Accordion sx={{ 
                                    backgroundColor: 'transparent', 
                                    boxShadow: 'none',
                                    '&:before': { display: 'none' }
                                  }}>
                                    <AccordionSummary
                                      expandIcon={<ExpandMoreIcon />}
                                      sx={{ 
                                        backgroundColor: 'gradient.main',
                                        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                                        color: 'white',
                                        borderBottom: '1px solid',
                                        borderBottomColor: 'divider',
                                        '&.Mui-expanded': {
                                          minHeight: 48,
                                        },
                                        '& .MuiAccordionSummary-content.Mui-expanded': {
                                          margin: '12px 0',
                                        },
                                        '& .MuiSvgIcon-root': {
                                          color: 'white'
                                        }
                                      }}
                                    >
                                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                                        <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                                          🤖 Intelligent Processing Features
                                        </Typography>
                                        <Chip
                                          label="Advanced"
                                          size="small"
                                          sx={{ 
                                            backgroundColor: 'rgba(255,255,255,0.2)',
                                            color: 'white',
                                            border: '1px solid rgba(255,255,255,0.3)'
                                          }}
                                        />
                                      </Box>
                                    </AccordionSummary>
                                    <AccordionDetails sx={{ backgroundColor: 'gradient.light', p: 3 }}>
                                      <Stack spacing={3}>
                                        {/* Feature Description */}
                                        <Box sx={{ 
                                          p: 2.5, 
                                          backgroundColor: 'white', 
                                          borderRadius: 2,
                                          border: '1px solid',
                                          borderColor: 'primary.200'
                                        }}>
                                          <Typography variant="h6" sx={{ mb: 1.5, fontWeight: 600, color: 'primary.dark', display: 'flex', alignItems: 'center' }}>
                                            <VectorIcon sx={{ mr: 1, fontSize: 24 }} />
                                            Intelligent Sample Replies Processing
                                          </Typography>
                                          <Typography variant="body2" sx={{ mb: 2, color: 'text.secondary', lineHeight: 1.6 }}>
                                            MODE 2 uses advanced vector embeddings to intelligently match customer inquiries with your most relevant sample replies. 
                                            Instead of using all sample data, it finds the most contextually similar examples to generate highly targeted responses.
                                          </Typography>
                                          
                                          <Grid container spacing={2} sx={{ mt: 1 }}>
                                            <Grid item xs={12} md={6}>
                                              <Box sx={{ p: 1.5, backgroundColor: 'success.50', borderRadius: 1 }}>
                                                <Typography variant="caption" sx={{ fontWeight: 600, color: 'success.dark' }}>
                                                  ✅ Benefits:
                                                </Typography>
                                                <Box component="ul" sx={{ mt: 1, pl: 2, mb: 0 }}>
                                                  <Typography component="li" variant="caption" sx={{ color: 'success.dark' }}>
                                                    More accurate responses
                                                  </Typography>
                                                  <Typography component="li" variant="caption" sx={{ color: 'success.dark' }}>
                                                    Context-aware matching
                                                  </Typography>
                                                  <Typography component="li" variant="caption" sx={{ color: 'success.dark' }}>
                                                    Better style consistency
                                                  </Typography>
                                                </Box>
                                              </Box>
                                            </Grid>
                                            <Grid item xs={12} md={6}>
                                              <Box sx={{ p: 1.5, backgroundColor: 'info.50', borderRadius: 1 }}>
                                                <Typography variant="caption" sx={{ fontWeight: 600, color: 'info.dark' }}>
                                                  🔧 How it works:
                                                </Typography>
                                                <Box component="ol" sx={{ mt: 1, pl: 2, mb: 0 }}>
                                                  <Typography component="li" variant="caption" sx={{ color: 'info.dark' }}>
                                                    Analyzes customer inquiry
                                                  </Typography>
                                                  <Typography component="li" variant="caption" sx={{ color: 'info.dark' }}>
                                                    Searches vector database
                                                  </Typography>
                                                  <Typography component="li" variant="caption" sx={{ color: 'info.dark' }}>
                                                    Applies Custom Instructions
                                                  </Typography>
                                                </Box>
                                              </Box>
                                            </Grid>
                                          </Grid>
                                        </Box>

                                        {/* Vector Search Parameters */}
                                        <Box sx={{ 
                                          p: 2.5, 
                                          backgroundColor: 'white', 
                                          borderRadius: 2,
                                          border: '1px solid',
                                          borderColor: 'info.200'
                                        }}>
                                          <Typography variant="h6" sx={{ mb: 2, fontWeight: 600, color: 'info.dark', display: 'flex', alignItems: 'center' }}>
                                            ⚙️ Vector Search Parameters
                                            <Chip
                                              label={`${vectorSimilarityThreshold} threshold, ${vectorSearchLimit} results`}
                                              size="small"
                                              color="info"
                                              variant="outlined"
                                              sx={{ ml: 1 }}
                                            />
                                          </Typography>
                                          
                                          <Grid container spacing={3}>
                                        {/* Similarity Threshold */}
                                            <Grid item xs={12} md={6}>
                                              <FormControl size="small" fullWidth sx={{ backgroundColor: 'grey.50' }}>
                                            <InputLabel>Similarity Threshold</InputLabel>
                                            <Select
                                              value={vectorSimilarityThreshold.toString()}
                                              onChange={e => {
                                                const newValue = Number(e.target.value);
                                                setVectorSimilarityThreshold(newValue);
                                                handleSaveVectorSettings();
                                              }}
                                              label="Similarity Threshold"
                                            >
                                              <MenuItem value="0.4">
                                                <Box>
                                                  <Typography variant="body2">0.4 - Very Loose <Chip label="More Results" size="small" color="success" sx={{ ml: 1 }} /></Typography>
                                                  <Typography variant="caption" color="text.secondary">Finds many results, including loosely related content</Typography>
                                                </Box>
                                              </MenuItem>
                                              <MenuItem value="0.5">
                                                <Box>
                                                  <Typography variant="body2">0.5 - Loose</Typography>
                                                  <Typography variant="caption" color="text.secondary">Good balance for diverse content matching</Typography>
                                                </Box>
                                              </MenuItem>
                                              <MenuItem value="0.6">
                                                <Box>
                                                  <Typography variant="body2">0.6 - Balanced <Chip label="Recommended" size="small" color="primary" sx={{ ml: 1 }} /></Typography>
                                                  <Typography variant="caption" color="text.secondary">Good balance of quality and quantity of results</Typography>
                                                </Box>
                                              </MenuItem>
                                              <MenuItem value="0.7">
                                                <Box>
                                                  <Typography variant="body2">0.7 - Focused</Typography>
                                                  <Typography variant="caption" color="text.secondary">More precise matching, fewer but higher quality results</Typography>
                                                </Box>
                                              </MenuItem>
                                              <MenuItem value="0.8">
                                                <Box>
                                                  <Typography variant="body2">0.8 - Very Focused</Typography>
                                                  <Typography variant="caption" color="text.secondary">Very precise matching, only highly similar content</Typography>
                                                </Box>
                                              </MenuItem>
                                            </Select>
                                            <FormHelperText>
                                              Lower values = more results (less strict). Higher values = fewer results (more strict).
                                            </FormHelperText>
                                          </FormControl>
                                            </Grid>
                                        
                                        {/* Search Results Limit */}
                                            <Grid item xs={12} md={6}>
                                              <FormControl size="small" fullWidth sx={{ backgroundColor: 'grey.50' }}>
                                            <InputLabel>Max Results</InputLabel>
                                            <Select
                                              value={vectorSearchLimit.toString()}
                                              onChange={e => {
                                                const newValue = Number(e.target.value);
                                                setVectorSearchLimit(newValue);
                                                handleSaveVectorSettings();
                                              }}
                                              label="Max Results"
                                            >
                                              <MenuItem value="3">3 Results</MenuItem>
                                              <MenuItem value="5">5 Results (Default)</MenuItem>
                                              <MenuItem value="10">10 Results</MenuItem>
                                              <MenuItem value="15">15 Results</MenuItem>
                                            </Select>
                                            <FormHelperText>
                                              Maximum number of similar chunks to return in searches
                                            </FormHelperText>
                                          </FormControl>
                                            </Grid>
                                          </Grid>
                                        
                                        {/* Auto-save Notice */}
                                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, p: 1.5, backgroundColor: 'info.50', borderRadius: 1, mt: 2 }}>
                                          <Typography variant="caption" sx={{ color: 'text.secondary', fontStyle: 'italic' }}>
                                            🔄 Settings auto-save when changed
                                          </Typography>
                                        </Box>
                                        </Box>

                                        {/* Configuration Status */}
                                        <Box sx={{ 
                                          p: 2, 
                                          backgroundColor: 'info.50', 
                                          borderRadius: 1,
                                          border: '1px solid',
                                          borderColor: 'info.200'
                                        }}>
                                          <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600, color: 'info.main' }}>
                                            📊 Current Vector Configuration
                                          </Typography>
                                          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                                            <Chip
                                              label={`Similarity: ${vectorSimilarityThreshold}`}
                                              size="small"
                                              color="info"
                                              variant="outlined"
                                            />
                                            <Chip
                                              label={`Max Results: ${vectorSearchLimit}`}
                                              size="small"
                                              color="info"
                                              variant="outlined"
                                            />
                                            <Chip
                                              label="Auto-optimized for MODE 2"
                                              size="small"
                                              color="success"
                                              variant="filled"
                                            />
                                          </Box>
                                          <Typography variant="caption" sx={{ display: 'block', mt: 1, color: 'text.secondary', fontStyle: 'italic' }}>
                                            💡 These settings from "Basic Search Settings" above are automatically applied to MODE 2 processing
                                          </Typography>
                                        </Box>

                                        {/* Call to Action */}
                                        <Box sx={{ 
                                          p: 2, 
                                          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                                          borderRadius: 2,
                                          color: 'white'
                                        }}>
                                          <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                                            🚀 Ready to use MODE 2?
                                          </Typography>
                                          <Typography variant="caption" sx={{ opacity: 0.9 }}>
                                            MODE 2 is automatically activated when you upload Sample Replies and configure Custom Instructions. 
                                            The system will intelligently choose between vector search and full-text analysis based on your content.
                                          </Typography>
                                        </Box>
                                      </Stack>
                                    </AccordionDetails>
                                  </Accordion>
                                </Box>
                              )}
                          </Grid>

                          {/* 📊 Model Support Information */}
                          <Grid item xs={12}>
                              {aiModel && (
                                <Box sx={{ 
                                  p: 2, 
                                  borderRadius: 1, 
                                  backgroundColor: 'info.50',
                                  border: '1px solid',
                                  borderColor: 'info.200'
                                }}>
                                  <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600, color: 'info.main' }}>
                                    📊 Model Settings Support
                                  </Typography>
                                  <Stack spacing={1}>
                                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                      <Typography variant="caption" sx={{ fontWeight: 600, minWidth: 140 }}>
                                        AI Temperature:
                                      </Typography>
                                      {aiModel?.startsWith('gpt-5') ? (
                                        <Chip label="🔒 Fixed at 1.0" size="small" color="warning" />
                                      ) : aiModel?.startsWith('o1') ? (
                                        <Chip label="❌ Not Supported" size="small" color="error" />
                                      ) : (
                                        <Chip label="✅ Fully Supported" size="small" color="success" />
                                      )}
                                    </Box>
                                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                      <Typography variant="caption" sx={{ fontWeight: 600, minWidth: 140 }}>
                                        Max Message Length:
                                      </Typography>
                                      {aiModel?.startsWith('o1') ? (
                                        <Chip label="❌ Ignored (Unlimited)" size="small" color="error" />
                                      ) : (
                                        <Chip label="✅ Fully Supported" size="small" color="success" />
                                      )}
                                    </Box>
                                  </Stack>
                                </Box>
                              )}
                          </Grid>

                          {/* Custom Prompt */}
                          <Grid item xs={12}>
                              <Box>
                                <Typography variant="caption" sx={{ mb: 1, display: 'block', fontWeight: 600, color: useAiGreeting && !aiCustomPrompt.trim() ? 'error.main' : 'text.primary' }}>
                                  Custom Instructions (Required) *
                                </Typography>
                                <TextField
                                  multiline
                                  rows={8}
                                  fullWidth
                                  required
                                  value={aiCustomPrompt}
                                  onChange={e => setAiCustomPrompt(e.target.value)}
                                  placeholder="Write specific instructions for AI responses. AI automatically sees ALL your business data (rating, phone, specialization, location, etc). Example: 'Always mention our 4.0★ rating and phone (213) 816-1560. We specialize in General Contractors. Be friendly and offer free estimates.'"
                                  variant="outlined"
                                  error={useAiGreeting && !aiCustomPrompt.trim()}
                                  sx={{ 
                                    backgroundColor: 'white',
                                    '& .MuiInputBase-root': {
                                      fontSize: '0.9rem',
                                      lineHeight: 1.5,
                                      minHeight: '160px'
                                    },
                                    '& .MuiInputBase-input': {
                                      resize: 'vertical'
                                    },
                                    '& .MuiOutlinedInput-root': {
                                      '&.Mui-error': {
                                        borderColor: 'error.main',
                                        backgroundColor: 'error.50'
                                      }
                                    }
                                  }}
                                  helperText={
                                    useAiGreeting && !aiCustomPrompt.trim() 
                                      ? '⚠️ Required when AI Generation is enabled. Custom Instructions control ALL AI behavior (business data usage, tone, location, response time, etc).' 
                                      : `${aiCustomPrompt.length} characters. AI sees ALL business data automatically - tell AI what to include and how to communicate. Example: "Always mention our rating and phone number."`
                                  }
                                />
                              </Box>

                              {/* Custom Preview Text Field */}
                              <Box>
                                <Typography variant="caption" sx={{ fontWeight: 600, mb: 1, display: 'block' }}>
                                  Custom Preview Text (Optional)
                                </Typography>
                                <TextField
                                  fullWidth
                                  multiline
                                  rows={10}
                                  value={aiCustomPreviewText}
                                  onChange={(e) => setAiCustomPreviewText(e.target.value)}
                                  placeholder="Paste a real customer message here to test your AI settings with realistic data, e.g.:

Hi there! Could you help me with my project? Here are my answers to Yelp's questions regarding my project:

What type of contracting service do you need?
Structural repair

What structural element(s) need repair? Select all that apply.
Foundation

When do you require this service?
I'm flexible

In what location do you need the service?
94103"
                                  variant="outlined"
                                  sx={{
                                    backgroundColor: 'white',
                                    '& .MuiInputBase-root': {
                                      fontSize: '0.9rem',
                                      lineHeight: 1.5,
                                      minHeight: '220px'
                                    },
                                    '& .MuiInputBase-input': {
                                      resize: 'vertical'
                                    }
                                  }}
                                  helperText={`${aiCustomPreviewText.length} characters. If provided, this text will be used instead of mock data for AI Preview generation.`}
                                />
                                
                                {/* Vector Search Status for Preview */}
                                {aiCustomPreviewText && (
                                  <Box sx={{ mt: 1, display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                                    {useSampleReplies ? (
                                      <Chip 
                                        icon={<VectorIcon />}
                                        label="🔍 Vector Search Active for Preview"
                                        size="small"
                                        color="success"
                                        variant="filled"
                                      />
                                    ) : (
                                      <Chip 
                                        label="📝 Standard Preview (No Vector Search)"
                                        size="small"
                                        color="default"
                                        variant="outlined"
                                      />
                                    )}
                                    
                                    {useSampleReplies && (
                                      <Box sx={{ display: 'flex', gap: 0.5 }}>
                                        <Chip 
                                          label={`Threshold: ${vectorSimilarityThreshold}`}
                                          size="small"
                                          color="info"
                                          variant="outlined"
                                        />
                                        <Chip 
                                          label={`Limit: ${vectorSearchLimit}`}
                                          size="small"
                                          color="info"
                                          variant="outlined"
                                        />
                                      </Box>
                                    )}
                                    
                                    <Typography variant="caption" sx={{ color: 'text.secondary', fontStyle: 'italic' }}>
                                      {useSampleReplies 
                                        ? `Preview will use vector search from ${sampleRepliesFilename || 'your Sample Replies'}`
                                        : 'Enable Sample Replies for vector-enhanced previews'
                                      }
                                    </Typography>
                                  </Box>
                                )}
                              </Box>

                              {/* AI Preview */}
                              <Box>
                                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                                  <Typography variant="caption" sx={{ fontWeight: 600 }}>
                                    AI Preview
                                  </Typography>
                                  <Button
                                    size="small"
                                    variant="outlined"
                                    onClick={generateAiPreview}
                                    disabled={aiPreviewLoading || !selectedBusiness}
                                    startIcon={aiPreviewLoading ? <CircularProgress size={16} /> : undefined}
                                    sx={{ minWidth: 100 }}
                                  >
                                    {aiPreviewLoading ? 'Generating...' : 'Generate Preview'}
                                  </Button>
                                </Box>
                                <Paper
                                  sx={{
                                    p: 2,
                                    backgroundColor: 'white',
                                    border: '1px solid',
                                    borderColor: 'grey.300',
                                    minHeight: 60,
                                    display: 'flex',
                                    alignItems: 'center'
                                  }}
                                >
                                  <Typography
                                    variant="body2"
                                    sx={{ 
                                      fontStyle: aiPreview ? 'normal' : 'italic',
                                      color: aiPreview ? 'text.primary' : 'text.secondary'
                                    }}
                                  >
                                    {aiPreview || 'Click "Generate Preview" to see how AI will create your greeting message.'}
                                  </Typography>
                                </Paper>
                              </Box>
                          </Grid>
                        </Grid>
                        {/* End of AI Configuration Grid */}
                        
                        {/* Sample Replies Manager - только для MODE 2: AI Generated */}
                        <Box sx={{ mt: 4 }}>
                          <SampleRepliesManager 
                            selectedBusiness={businesses.find(b => b.business_id === selectedBusiness) || null}
                            phoneAvailable={phoneAvailable}
                            sampleRepliesContent={sampleRepliesContent}
                            sampleRepliesFilename={sampleRepliesFilename}
                            useSampleReplies={useSampleReplies}
                            onSampleRepliesUpdate={() => {
                              // Reload settings after Sample Replies update
                              if (selectedBusiness) {
                                loadSettings(selectedBusiness);
                              }
                            }}
                          />
                        </Box>
                      </>
                    )}

                    {/* Traditional Template Fields - only show when not using AI */}
                    {!useAiGreeting && (
                      <>
                        <Box sx={{ textAlign: 'center', py: 1 }}>
                          <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'primary.main', fontWeight: 700 }}>
                            <MessageIcon sx={{ mr: 1, fontSize: 20 }} />
                            📝 TEMPLATE MESSAGE ACTIVE
                          </Typography>
                        </Box>
                        
                        <Card elevation={1} sx={{ borderRadius: 2, backgroundColor: 'primary.50', border: '2px solid', borderColor: 'primary.main' }}>
                          <CardContent sx={{ p: 2 }}>
                            <Typography variant="subtitle2" sx={{ mb: 2, fontWeight: 600, display: 'flex', alignItems: 'center' }}>
                              <MessageIcon sx={{ mr: 1, color: 'primary.main' }} />
                              Template Configuration
                            </Typography>
                            
                            {/* Template Mode Indicator */}
                            <Box sx={{ mb: 2, p: 2, backgroundColor: 'white', borderRadius: 2, border: '1px solid', borderColor: 'primary.200' }}>
                              <Typography variant="caption" sx={{ display: 'block', mb: 1, fontWeight: 600, color: 'text.secondary' }}>
                                Current Template Mode:
                              </Typography>
                              <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                                <Chip
                                  icon={<AccessTimeIcon sx={{ fontSize: 14 }} />}
                                  label="Business Hours Template"
                                  size="small"
                                  color="success"
                                  variant="filled"
                                  sx={{ fontSize: '0.75rem', fontWeight: 600 }}
                                />
                                {phoneAvailable && greetingAfterTemplate && (
                                  <Chip
                                    icon={<AccessTimeIcon sx={{ fontSize: 14 }} />}
                                    label="Off-Hours Template Available"
                                    size="small"
                                    color="warning"
                                    variant="outlined"
                                    sx={{ fontSize: '0.75rem', fontWeight: 600 }}
                                  />
                                )}
                                {phoneAvailable && !greetingAfterTemplate && (
                                  <Chip
                                    icon={<AccessTimeIcon sx={{ fontSize: 14 }} />}
                                    label="Off-Hours Template Not Set"
                                    size="small"
                                    color="error"
                                    variant="outlined"
                                    sx={{ fontSize: '0.75rem', fontWeight: 600 }}
                                  />
                                )}
                              </Box>
                              
                              {/* Template Usage Info */}
                              <Typography variant="caption" sx={{ display: 'block', mt: 1, color: 'text.secondary', fontStyle: 'italic' }}>
                                {phoneAvailable 
                                  ? 'Business hours template is used during working hours. Off-hours template (if set) is used outside working hours.'
                                  : 'Single template mode - the same template is used 24/7.'
                                }
                              </Typography>
                              
                              {/* Currently Active Template Indicator */}
                              {localTime && phoneAvailable && (
                                <Box sx={{ mt: 2, pt: 2, borderTop: '1px solid', borderColor: 'grey.300' }}>
                                  <Typography variant="caption" sx={{ display: 'block', mb: 1, fontWeight: 600, color: 'text.secondary' }}>
                                    Active Right Now ({localTime}):
                                  </Typography>
                                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                                    <Chip
                                      icon={isWithinBusinessHours() ? <WorkIcon sx={{ fontSize: 14 }} /> : <AccessTimeIcon sx={{ fontSize: 14 }} />}
                                      label={isWithinBusinessHours() 
                                        ? '🕐 Business Hours Template Active' 
                                        : '🌙 Off-Hours Template Active'
                                      }
                                      size="small"
                                      color={isWithinBusinessHours() ? 'success' : 'warning'}
                                      variant="filled"
                                      sx={{ 
                                        fontSize: '0.75rem', 
                                        fontWeight: 600,
                                        '@keyframes pulse': {
                                          '0%': { opacity: 1 },
                                          '50%': { opacity: 0.7 },
                                          '100%': { opacity: 1 }
                                        },
                                        animation: 'pulse 2s infinite ease-in-out'
                                      }}
                                    />
                                  </Box>
                                  <Typography variant="caption" sx={{ display: 'block', mt: 1, color: 'text.secondary' }}>
                                    Business Hours: {greetingOpenFrom.slice(0,5)} - {greetingOpenTo.slice(0,5)}
                                    {greetingOpenDays && ` • ${greetingOpenDays}`}
                                  </Typography>
                                  
                                  {/* Template Preview */}
                                  {(greetingTemplate || greetingAfterTemplate) && (
                                    <Box sx={{ mt: 2, p: 2, backgroundColor: 'grey.50', borderRadius: 1, border: '1px dashed', borderColor: 'grey.400' }}>
                                      <Typography variant="caption" sx={{ display: 'block', mb: 1, fontWeight: 600, color: 'text.secondary' }}>
                                        Current Template Preview:
                                      </Typography>
                                      <Typography 
                                        variant="body2" 
                                        sx={{ 
                                          fontStyle: 'italic',
                                          backgroundColor: 'white',
                                          p: 1,
                                          borderRadius: 1,
                                          border: '1px solid',
                                          borderColor: 'grey.300',
                                          minHeight: 40,
                                          display: 'flex',
                                          alignItems: 'center'
                                        }}
                                      >
                                        {phoneAvailable && !isWithinBusinessHours() && greetingAfterTemplate 
                                          ? greetingAfterTemplate || 'Off-hours template not set'
                                          : greetingTemplate || 'Business hours template not set'
                                        }
                                      </Typography>
                                      <Typography variant="caption" sx={{ display: 'block', mt: 1, color: 'text.secondary' }}>
                                        💡 Placeholders like {'{name}'}, {'{jobs}'}, {'{sep}'}, {'{reason}'} will be replaced with actual customer data when sent.
                                        <br />
                                        📞 {'{reason}'} shows why SMS was sent: "Phone Number Found", "Customer Reply", or "Phone Opt-in"
                                      </Typography>
                                    </Box>
                                  )}
                                </Box>
                              )}
                            </Box>
                            
                            {/* Placeholder buttons */}
                            <Box>
                              <Typography variant="caption" sx={{ mb: 1, display: 'block', fontWeight: 600 }}>
                                Insert Variables
                              </Typography>
                              <Stack spacing={1}>
                                {PLACEHOLDERS.map(ph => (
                                  <Box key={ph} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                    <Chip
                                      label={ph}
                                      size="small"
                                      variant="outlined"
                                      clickable
                                      onClick={() => insertPlaceholder(ph, 'greeting')}
                                      sx={{ 
                                        minWidth: '80px',
                                        fontFamily: 'monospace',
                                        '&:hover': { backgroundColor: 'primary.50' }
                                      }}
                                    />
                                    <Typography variant="caption" sx={{ color: '#888', fontSize: '0.7rem' }}>
                                      {PLACEHOLDER_DESCRIPTIONS[ph]}
                                    </Typography>
                                  </Box>
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
                                mt: 2,
                                '& .MuiOutlinedInput-root': {
                                  backgroundColor: 'white'
                                }
                              }}
                            />
                          </CardContent>
                        </Card>
                      </>
                    )}

                    {/* Options */}
                    <Box>
                      <Typography variant="subtitle2" sx={{ mb: 2, fontWeight: 600 }}>
                        Message Options
                      </Typography>
                      <Stack direction="row" spacing={3} flexWrap="wrap">
                        {/* Include Name/Jobs options always enabled */}
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
                        
                        {/* Improved Days of Week Selector for Real Phone */}
                        {phoneAvailable && (
                          <Box sx={{ mt: 2 }}>
                            <Typography variant="caption" sx={{ mb: 1.5, display: 'block', fontWeight: 600, color: 'text.secondary' }}>
                              Operating Days
                            </Typography>
                            <Box sx={{ 
                              display: 'flex', 
                              flexWrap: 'wrap',
                              gap: 0.5,
                              p: 1,
                              backgroundColor: 'grey.50',
                              borderRadius: 2,
                              border: '1px solid',
                              borderColor: 'grey.200'
                            }}>
                              {DAY_NAMES.map((day, index) => {
                                const isSelected = greetingOpenDays
                                  .split(',')
                                  .map(p => p.trim())
                                  .includes(day);
                                const isWeekend = index >= 5; // Sat, Sun
                                
                                return (
                                  <Button
                                    key={day}
                                    variant={isSelected ? "contained" : "outlined"}
                                    size="small"
                                    onClick={() => toggleDay(day)}
                                    sx={{
                                      minWidth: 'auto',
                                      width: 42,
                                      height: 36,
                                      borderRadius: 1.5,
                                      fontSize: '0.75rem',
                                      fontWeight: 600,
                                      p: 0,
                                      transition: 'all 0.2s ease-in-out',
                                      borderColor: isWeekend ? 'warning.main' : 'primary.main',
                                      color: isSelected 
                                        ? 'white' 
                                        : isWeekend 
                                          ? 'warning.main' 
                                          : 'primary.main',
                                      backgroundColor: isSelected 
                                        ? isWeekend 
                                          ? 'warning.main' 
                                          : 'primary.main'
                                        : 'transparent',
                                      '&:hover': {
                                        backgroundColor: isSelected
                                          ? isWeekend 
                                            ? 'warning.dark'
                                            : 'primary.dark'
                                          : isWeekend
                                            ? 'warning.50'
                                            : 'primary.50',
                                        transform: 'translateY(-1px)',
                                        boxShadow: 2
                                      },
                                      '&:active': {
                                        transform: 'translateY(0)',
                                      }
                                    }}
                                  >
                                    {day}
                                  </Button>
                                );
                              })}
                            </Box>
                            
                            {/* Quick Selection Buttons */}
                            <Box sx={{ mt: 1, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                              <Button
                                variant="text"
                                size="small"
                                onClick={() => setGreetingOpenDays('Mon, Tue, Wed, Thu, Fri')}
                                sx={{ 
                                  fontSize: '0.7rem',
                                  color: 'primary.main',
                                  textTransform: 'none',
                                  '&:hover': { backgroundColor: 'primary.50' }
                                }}
                              >
                                Weekdays
                              </Button>
                              <Button
                                variant="text"
                                size="small"
                                onClick={() => setGreetingOpenDays('Sat, Sun')}
                                sx={{ 
                                  fontSize: '0.7rem',
                                  color: 'warning.main',
                                  textTransform: 'none',
                                  '&:hover': { backgroundColor: 'warning.50' }
                                }}
                              >
                                Weekend
                              </Button>
                              <Button
                                variant="text"
                                size="small"
                                onClick={() => setGreetingOpenDays('Mon, Tue, Wed, Thu, Fri, Sat, Sun')}
                                sx={{ 
                                  fontSize: '0.7rem',
                                  color: 'success.main',
                                  textTransform: 'none',
                                  '&:hover': { backgroundColor: 'success.50' }
                                }}
                              >
                                Every Day
                              </Button>
                              <Button
                                variant="text"
                                size="small"
                                onClick={() => setGreetingOpenDays('')}
                                sx={{ 
                                  fontSize: '0.7rem',
                                  color: 'error.main',
                                  textTransform: 'none',
                                  '&:hover': { backgroundColor: 'error.50' }
                                }}
                              >
                                Clear All
                              </Button>
                            </Box>
                            
                            {/* Selected Days Display */}
                            {greetingOpenDays && (
                              <Box sx={{ mt: 1 }}>
                                <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                                  Selected: {greetingOpenDays || 'None'}
                                </Typography>
                              </Box>
                            )}
                          </Box>
                        )}
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
                        <Stack spacing={1}>
                          {PLACEHOLDERS.map(ph => (
                            <Box key={ph} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                              <Chip
                                label={ph}
                                size="small"
                                variant="outlined"
                                clickable
                                onClick={() => insertPlaceholder(ph, 'after')}
                                sx={{ 
                                  minWidth: '80px',
                                  fontFamily: 'monospace',
                                  '&:hover': { backgroundColor: 'warning.50' }
                                }}
                              />
                              <Typography variant="caption" sx={{ color: '#888', fontSize: '0.7rem' }}>
                                {PLACEHOLDER_DESCRIPTIONS[ph]}
                              </Typography>
                            </Box>
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
                      {templates
                        .slice()
                        .sort((a, b) => a.delay - b.delay)
                        .map((t, index) => (
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
                    <Stack spacing={1} sx={{ mb: 1 }}>
                      {PLACEHOLDERS.map(ph => (
                        <Box key={ph} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Chip
                            label={ph}
                            size="small"
                            variant="outlined"
                            clickable
                            onClick={() => insertPlaceholder(ph, 'template')}
                            sx={{ 
                              minWidth: '80px',
                              fontFamily: 'monospace',
                              '&:hover': { backgroundColor: 'primary.50' }
                            }}
                          />
                          <Typography variant="caption" sx={{ color: '#888', fontSize: '0.7rem' }}>
                            {PLACEHOLDER_DESCRIPTIONS[ph]}
                          </Typography>
                        </Box>
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
                      <Stack spacing={1} sx={{ mb: 1 }}>
                        {PLACEHOLDERS.map(ph => (
                          <Box key={ph} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Chip
                              label={ph}
                              size="small"
                              variant="outlined"
                              clickable
                              onClick={() => setEditText(v => v + ph)}
                              sx={{ 
                                minWidth: '80px',
                                fontFamily: 'monospace',
                                '&:hover': { backgroundColor: 'primary.50' }
                              }}
                            />
                            <Typography variant="caption" sx={{ color: '#888', fontSize: '0.7rem' }}>
                              {PLACEHOLDER_DESCRIPTIONS[ph]}
                            </Typography>
                          </Box>
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

                  {/* 📱 SMS Notification Center */}
                  <Box sx={{ mt: 3 }}>
                    <Typography variant="h6" sx={{ 
                      mb: 2, 
                      fontWeight: 600, 
                      display: 'flex', 
                      alignItems: 'center',
                      color: 'primary.main'
                    }}>
                      📱 SMS Notification Center
                    </Typography>
                    <Typography variant="body2" sx={{ mb: 2, color: 'text.secondary' }}>
                      Configure when to send SMS messages to clients for each scenario
                    </Typography>
                    
                    <Stack spacing={2}>
                      <FormControlLabel
                        control={
                          <Switch 
                            checked={smsOnPhoneFound} 
                            onChange={e => setSmsOnPhoneFound(e.target.checked)}
                            color="primary"
                          />
                        }
                        label={
                          <Box>
                            <Typography variant="body2" sx={{ fontWeight: 500 }}>
                              📞 Phone Number Found
                            </Typography>
                            <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                              Send SMS when the system finds a phone number in the customer's message text
                            </Typography>
                          </Box>
                        }
                      />
                      
                      <FormControlLabel
                        control={
                          <Switch 
                            checked={smsOnCustomerReply} 
                            onChange={e => setSmsOnCustomerReply(e.target.checked)}
                            color="primary"
                          />
                        }
                        label={
                          <Box>
                            <Typography variant="body2" sx={{ fontWeight: 500 }}>
                              💬 Customer Reply
                            </Typography>
                            <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                              Send SMS when customer responds to messages (even without phone number)
                            </Typography>
                          </Box>
                        }
                      />
                      
                      <FormControlLabel
                        control={
                          <Switch 
                            checked={smsOnPhoneOptIn} 
                            onChange={e => setSmsOnPhoneOptIn(e.target.checked)}
                            color="primary"
                          />
                        }
                        label={
                          <Box>
                            <Typography variant="body2" sx={{ fontWeight: 500 }}>
                              ✅ Phone Opt-in
                            </Typography>
                            <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                              Send SMS when customer gives consent to use their phone number
                            </Typography>
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
                        background: useAiGreeting !== initialSettings.current?.use_ai_greeting 
                          ? 'linear-gradient(135deg, #f57c00 0%, #ff9800 100%)'  // Orange for unsaved changes
                          : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', // Normal gradient
                        '&:hover': {
                          background: useAiGreeting !== initialSettings.current?.use_ai_greeting
                            ? 'linear-gradient(135deg, #ef6c00 0%, #ff8f00 100%)'
                            : 'linear-gradient(135deg, #5a6fd8 0%, #6b4190 100%)',
                          transform: 'translateY(-1px)',
                        },
                        animation: useAiGreeting !== initialSettings.current?.use_ai_greeting ? 'pulse 1s infinite' : 'none',
                        '@keyframes pulse': {
                          '0%': { boxShadow: '0 0 0 0 rgba(245, 124, 0, 0.7)' },
                          '70%': { boxShadow: '0 0 0 10px rgba(245, 124, 0, 0)' },
                          '100%': { boxShadow: '0 0 0 0 rgba(245, 124, 0, 0)' }
                        }
                      }}
                    >
                      {useAiGreeting !== initialSettings.current?.use_ai_greeting 
                        ? `💾 Save Mode Change (${useAiGreeting ? 'AI' : 'Template'})` 
                        : 'Save Settings'
                      }
                    </Button>
                  </Box>
                </Stack>
              </CardContent>
            </Card>
          </Stack>
        )}
      </Box>
    </Paper>

    {/* Divider Section */}
    <Box sx={{ py: 6, my: 4 }}>
      <Container maxWidth="lg">
        <Box sx={{ textAlign: 'center' }}>
          <Box
            sx={{
              width: '100%',
              height: '2px',
              background: 'linear-gradient(90deg, transparent 0%, #1976d2 50%, transparent 100%)',
              mb: 3,
              borderRadius: 1
            }}
          />
          <Box 
            sx={{
              display: 'inline-flex',
              alignItems: 'center',
              px: 4,
              py: 2,
              backgroundColor: '#f8f9fa',
              border: '2px solid #e3f2fd',
              borderRadius: 3,
              boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
            }}
          >
            <Typography 
              variant="h6" 
              sx={{ 
                color: '#1976d2',
                fontWeight: 600,
                letterSpacing: '0.5px'
              }}
            >
              🔔 Additional Settings
            </Typography>
          </Box>
          <Typography 
            variant="body2" 
            sx={{ 
              mt: 2,
              color: '#666',
              maxWidth: 400,
              mx: 'auto'
            }}
          >
            Independent configuration section for notifications and other features
          </Typography>
        </Box>
      </Container>
    </Box>

    <NotificationSettings businessId={selectedBusiness} />

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
