import React, {useEffect, useState, useRef} from 'react';
import axios from 'axios';
import {
  Container,
  Typography,
  List,
  ListItem,
  ListItemText,
  IconButton,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Switch,
  FormControlLabel,
  Stack,
  Box,
  Snackbar,
  Alert,
  Chip,
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';

const PLACEHOLDERS = ['{name}', '{jobs}'] as const;
type Placeholder = typeof PLACEHOLDERS[number];

const PLACEHOLDER_DESCRIPTIONS: Record<string, string> = {
  '{name}': 'Customer display name',
  '{jobs}': 'List of services requested'
};

interface FollowUpTemplate {
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
  follow_up_templates: FollowUpTemplate[];
}

interface SettingsTemplate {
  id: number;
  name: string;
  description: string;
  data: AutoResponseSettingsData;
}

const defaultData: AutoResponseSettingsData = {
  enabled: false,
  greeting_template: '',
  greeting_off_hours_template: '',
  greeting_delay: 0,
  greeting_open_from: '08:00:00',
  greeting_open_to: '20:00:00',
  greeting_open_days: 'Mon, Tue, Wed, Thu, Fri',
  export_to_sheets: false,
  follow_up_templates: [],
};

const SettingsTemplates: React.FC = () => {
  const [templates, setTemplates] = useState<SettingsTemplate[]>([]);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<SettingsTemplate | null>(null);

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [data, setData] = useState<AutoResponseSettingsData>(defaultData);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState('');

  const [greetingDelayHours, setGreetingDelayHours] = useState(0);
  const [greetingDelayMinutes, setGreetingDelayMinutes] = useState(0);
  const [greetingDelaySeconds, setGreetingDelaySeconds] = useState(0);

  const greetingRef = useRef<HTMLTextAreaElement | null>(null);
  const tplRef = useRef<HTMLTextAreaElement | null>(null);

  const [newText, setNewText] = useState('');
  const [newDelayDays, setNewDelayDays] = useState(0);
  const [newDelayHours, setNewDelayHours] = useState(1);
  const [newDelayMinutes, setNewDelayMinutes] = useState(0);
  const [newDelaySeconds, setNewDelaySeconds] = useState(0);
  const [newOpenFrom, setNewOpenFrom] = useState('08:00:00');
  const [newOpenTo, setNewOpenTo] = useState('20:00:00');

  const insertPlaceholder = (
    ph: Placeholder,
    target: 'greeting' | 'template'
  ) => {
    let ref: HTMLTextAreaElement | null = null;
    let base = '';
    let setter: (v: string) => void = () => {};
    if (target === 'greeting') {
      ref = greetingRef.current;
      base = data.greeting_template;
      setter = (v: string) => setData({...data, greeting_template: v});
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

  const load = () => {
    axios.get<SettingsTemplate[]>('/settings-templates/')
      .then(r => setTemplates(r.data))
      .catch(() => setTemplates([]));
  };

  useEffect(() => {
    load();
  }, []);

  const handleEdit = (tpl: SettingsTemplate) => {
    axios.get<SettingsTemplate>(`/settings-templates/${tpl.id}/`)
      .then(r => {
        const t = r.data;
        setEditing(t);
        setName(t.name);
        setDescription(t.description);
        setData({
          ...t.data,
          follow_up_templates: t.data.follow_up_templates || [],
        });
        let gsecs = t.data.greeting_delay || 0;
        setGreetingDelayHours(Math.floor(gsecs / 3600));
        gsecs %= 3600;
        setGreetingDelayMinutes(Math.floor(gsecs / 60));
        setGreetingDelaySeconds(gsecs % 60);
        setSaved(false);
        setError('');
        setOpen(true);
      })
      .catch(() => setError('Failed to load template.'));
  };

  const handleAdd = () => {
    setEditing(null);
    setName('');
    setDescription('');
    setData(defaultData);
    setGreetingDelayHours(0);
    setGreetingDelayMinutes(0);
    setGreetingDelaySeconds(0);
    setSaved(false);
    setError('');
    setOpen(true);
  };

  const handleSave = () => {
    const greetDelaySecs =
      greetingDelayHours * 3600 +
      greetingDelayMinutes * 60 +
      greetingDelaySeconds;
    const payload = {name, description, data: {...data, greeting_delay: greetDelaySecs}};
    if (editing) {
      axios.put<SettingsTemplate>(`/settings-templates/${editing.id}/`, payload)
        .then(() => {
          load();
          setSaved(true);
          setOpen(false);
        })
        .catch(() => setError('Failed to save template.'));
    } else {
      axios.post<SettingsTemplate>('/settings-templates/', payload)
        .then(() => {
          load();
          setSaved(true);
          setOpen(false);
        })
        .catch(() => setError('Failed to save template.'));
    }
  };

  const handleAddFollowTemplate = () => {
    const delaySecs =
      newDelayDays * 86400 +
      newDelayHours * 3600 +
      newDelayMinutes * 60 +
      newDelaySeconds;
    const tpl: FollowUpTemplate = {
      template: newText,
      delay: delaySecs,
      open_from: newOpenFrom,
      open_to: newOpenTo,
    };
    setData({
      ...data,
      follow_up_templates: [...(data.follow_up_templates || []), tpl],
    });

    // Persist template so it appears on the settings page
    axios
      .post('/follow-up-templates/', {
        name: `Custom ${Date.now()}`,
        template: newText,
        delay: delaySecs,
        open_from: newOpenFrom,
        open_to: newOpenTo,
        active: true,
      })
      .then(() => {
        // notify other tabs/pages to refresh templates
        localStorage.setItem('followTemplateUpdated', Date.now().toString());
      })
      .catch(() => {
        // ignore error, template still stored locally in this dialog
      });

    setNewText('');
    setNewDelayDays(0);
    setNewDelayHours(1);
    setNewDelayMinutes(0);
    setNewDelaySeconds(0);
    setNewOpenFrom('08:00:00');
    setNewOpenTo('20:00:00');
  };

  const handleDeleteFollowTemplate = (idx: number) => {
    const arr = [...(data.follow_up_templates || [])];
    arr.splice(idx, 1);
    setData({...data, follow_up_templates: arr});
  };

  const handleDelete = (id: number) => {
    axios.delete(`/settings-templates/${id}/`).then(() => load());
  };

  const handleCloseSnackbar = () => {
    setSaved(false);
    setError('');
  };

  return (
    <Container sx={{ mt:4 }}>
      <Typography variant="h5" gutterBottom>Auto-response Templates</Typography>
      <List>
        {templates.map(t => (
          <ListItem key={t.id}
            secondaryAction={
              <>
                <IconButton onClick={() => handleEdit(t)}><EditIcon/></IconButton>
                <IconButton onClick={() => handleDelete(t.id)}><DeleteIcon/></IconButton>
              </>
            }
          >
            <ListItemText primary={t.name} secondary={t.description}/>
          </ListItem>
        ))}
      </List>
      <Button variant="contained" onClick={handleAdd}>Add Template</Button>

      <Dialog open={open} onClose={() => setOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>{editing ? 'Edit Template' : 'New Template'}</DialogTitle>
        <DialogContent dividers>
          <Stack spacing={2} sx={{ mt:1 }}>
            <TextField label="Name" fullWidth value={name} onChange={e=>setName(e.target.value)}/>
            <TextField label="Description" fullWidth value={description} onChange={e=>setDescription(e.target.value)}/>
            <Stack spacing={1} sx={{ mb: 1 }}>
              <Typography variant="caption" sx={{ fontWeight: 600 }}>Insert Variables:</Typography>
              {PLACEHOLDERS.map(ph => (
                <Box key={ph} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Button 
                    size="small" 
                    variant="outlined" 
                    onClick={() => insertPlaceholder(ph, 'greeting')}
                    sx={{ 
                      minWidth: '80px',
                      fontFamily: 'monospace',
                      fontSize: '0.7rem'
                    }}
                  >
                    {ph}
                  </Button>
                  <Typography variant="caption" sx={{ color: '#888', fontSize: '0.7rem' }}>
                    {PLACEHOLDER_DESCRIPTIONS[ph]}
                  </Typography>
                </Box>
              ))}
            </Stack>
            <TextField
              inputRef={greetingRef}
              multiline
              minRows={3}
              label="Greeting Template"
              fullWidth
              value={data.greeting_template}
              onChange={e=>setData({...data, greeting_template:e.target.value})}
            />
            <Stack direction="row" spacing={1} alignItems="center">
              <TextField label="Hours" type="number" inputProps={{min:0}} sx={{ width:80 }}
                value={greetingDelayHours} onChange={e=>setGreetingDelayHours(Number(e.target.value))}/>
              <TextField label="Min" type="number" inputProps={{min:0}} sx={{ width:80 }}
                value={greetingDelayMinutes} onChange={e=>setGreetingDelayMinutes(Number(e.target.value))}/>
              <TextField label="Sec" type="number" inputProps={{min:0}} sx={{ width:80 }}
                value={greetingDelaySeconds} onChange={e=>setGreetingDelaySeconds(Number(e.target.value))}/>
              <TextField label="Open From" type="time" value={data.greeting_open_from}
                onChange={e=>setData({...data, greeting_open_from:e.target.value})}
                inputProps={{ step:1 }} size="small"/>
              <TextField label="Open To" type="time" value={data.greeting_open_to}
                onChange={e=>setData({...data, greeting_open_to:e.target.value})}
                inputProps={{ step:1 }} size="small"/>
              <TextField label="Days" type="text" value={data.greeting_open_days}
                onChange={e=>setData({...data, greeting_open_days:e.target.value})}
                size="small"/>
            </Stack>
            {/* Include Name and Jobs always enabled */}

            <Typography variant="h6">Additional Follow-up Templates</Typography>
            <List dense>
              {(data.follow_up_templates || [])
                .slice()
                .sort((a, b) => a.delay - b.delay)
                .map((t, idx) => (
                <ListItem key={idx} secondaryAction={
                  <IconButton edge="end" onClick={() => handleDeleteFollowTemplate(idx)}>
                    <DeleteIcon />
                  </IconButton>
                }>
                  <ListItemText
                    primary={t.template}
                    secondary={`In ${Math.floor(t.delay/86400)}d ${Math.floor((t.delay%86400)/3600)}h | ${t.open_from} - ${t.open_to}`}
                  />
                </ListItem>
              ))}
            </List>
            <Stack direction="row" spacing={2} alignItems="flex-start" flexWrap="wrap" mt={2}>
              <Box flexGrow={1}>
                <Stack spacing={1} sx={{ mb: 1 }}>
                  <Typography variant="caption" sx={{ fontWeight: 600 }}>Insert Variables:</Typography>
                  {PLACEHOLDERS.map(ph => (
                    <Box key={ph} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Button 
                        size="small" 
                        variant="outlined" 
                        onClick={() => insertPlaceholder(ph, 'template')}
                        sx={{ 
                          minWidth: '80px',
                          fontFamily: 'monospace',
                          fontSize: '0.7rem'
                        }}
                      >
                        {ph}
                      </Button>
                      <Typography variant="caption" sx={{ color: '#888', fontSize: '0.7rem' }}>
                        {PLACEHOLDER_DESCRIPTIONS[ph]}
                      </Typography>
                    </Box>
                  ))}
                </Stack>
                <TextField
                  inputRef={tplRef}
                  multiline
                  minRows={2}
                  fullWidth
                  value={newText}
                  onChange={e=>setNewText(e.target.value)}
                  placeholder="New follow-up template..."
                />
              </Box>
              <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
                <TextField label="Days" type="number" inputProps={{min:0}} sx={{width:70}}
                  value={newDelayDays} onChange={e=>setNewDelayDays(Number(e.target.value))}/>
                <TextField label="Hours" type="number" inputProps={{min:0}} sx={{width:70}}
                  value={newDelayHours} onChange={e=>setNewDelayHours(Number(e.target.value))}/>
                <TextField label="Min" type="number" inputProps={{min:0}} sx={{width:70}}
                  value={newDelayMinutes} onChange={e=>setNewDelayMinutes(Number(e.target.value))}/>
                <TextField label="Sec" type="number" inputProps={{min:0}} sx={{width:70}}
                  value={newDelaySeconds} onChange={e=>setNewDelaySeconds(Number(e.target.value))}/>
              </Stack>
              <Box sx={{ mt: 1 }}>
                <Typography variant="body2" gutterBottom>Business Hours</Typography>
                <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
                  <TextField label="From" type="time" inputProps={{ step: 1 }} value={newOpenFrom}
                    onChange={e=>setNewOpenFrom(e.target.value)} size="small"/>
                  <TextField label="To" type="time" inputProps={{ step: 1 }} value={newOpenTo}
                    onChange={e=>setNewOpenTo(e.target.value)} size="small"/>
                </Stack>
              </Box>
              <Button onClick={handleAddFollowTemplate} sx={{ mt:1 }}>Add</Button>
            </Stack>

            <FormControlLabel control={<Switch checked={data.enabled}
              onChange={e=>setData({...data, enabled:e.target.checked})}/>} label="Enable Auto-response" />
            <FormControlLabel control={<Switch checked={data.export_to_sheets}
              onChange={e=>setData({...data, export_to_sheets:e.target.checked})}/>} label="Export to Sheets" />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={()=>setOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleSave}>Save</Button>
        </DialogActions>
      </Dialog>
      <Snackbar
        open={saved || Boolean(error)}
        autoHideDuration={4000}
        onClose={handleCloseSnackbar}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        {saved ? (
          <Alert onClose={handleCloseSnackbar} severity="success" sx={{ width: '100%' }}>
            Template saved!
          </Alert>
        ) : error ? (
          <Alert onClose={handleCloseSnackbar} severity="error" sx={{ width: '100%' }}>
            {error}
          </Alert>
        ) : undefined}
      </Snackbar>
    </Container>
  );
};

export default SettingsTemplates;
