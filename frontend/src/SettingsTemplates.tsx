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
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';

const PLACEHOLDERS = ['{name}', '{jobs}', '{sep}'] as const;
type Placeholder = typeof PLACEHOLDERS[number];

interface FollowUpTemplate {
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
  greeting_delay: 0,
  greeting_open_from: '08:00:00',
  greeting_open_to: '20:00:00',
  include_name: true,
  include_jobs: true,
  follow_up_template: '',
  follow_up_delay: 7200,
  follow_up_open_from: '08:00:00',
  follow_up_open_to: '20:00:00',
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
  const [followDelayDays, setFollowDelayDays] = useState(0);
  const [followDelayHours, setFollowDelayHours] = useState(0);
  const [followDelayMinutes, setFollowDelayMinutes] = useState(0);
  const [followDelaySeconds, setFollowDelaySeconds] = useState(0);

  const greetingRef = useRef<HTMLTextAreaElement | null>(null);
  const followRef = useRef<HTMLTextAreaElement | null>(null);
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
    target: 'greeting' | 'follow' | 'template'
  ) => {
    let ref: HTMLTextAreaElement | null = null;
    let base = '';
    let setter: (v: string) => void = () => {};
    if (target === 'greeting') {
      ref = greetingRef.current;
      base = data.greeting_template;
      setter = (v: string) => setData({...data, greeting_template: v});
    } else if (target === 'follow') {
      ref = followRef.current;
      base = data.follow_up_template;
      setter = (v: string) => setData({...data, follow_up_template: v});
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
        let fsecs = t.data.follow_up_delay || 0;
        setFollowDelayDays(Math.floor(fsecs / 86400));
        fsecs %= 86400;
        setFollowDelayHours(Math.floor(fsecs / 3600));
        fsecs %= 3600;
        setFollowDelayMinutes(Math.floor(fsecs / 60));
        setFollowDelaySeconds(fsecs % 60);
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
    setFollowDelayDays(Math.floor(defaultData.follow_up_delay / 86400));
    let fsecs = defaultData.follow_up_delay % 86400;
    setFollowDelayHours(Math.floor(fsecs / 3600));
    fsecs %= 3600;
    setFollowDelayMinutes(Math.floor(fsecs / 60));
    setFollowDelaySeconds(fsecs % 60);
    setSaved(false);
    setError('');
    setOpen(true);
  };

  const handleSave = () => {
    const greetDelaySecs =
      greetingDelayHours * 3600 +
      greetingDelayMinutes * 60 +
      greetingDelaySeconds;
    const followDelaySecs =
      followDelayDays * 86400 +
      followDelayHours * 3600 +
      followDelayMinutes * 60 +
      followDelaySeconds;
    const payload = {name, description, data: {...data, greeting_delay: greetDelaySecs, follow_up_delay: followDelaySecs}};
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
            <Stack direction="row" spacing={1} mb={1}>
              {PLACEHOLDERS.map(ph => (
                <Button key={ph} size="small" variant="outlined" onClick={() => insertPlaceholder(ph, 'greeting')}>
                  {ph}
                </Button>
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
            </Stack>
            <FormControlLabel control={<Switch checked={data.include_name}
              onChange={e=>setData({...data, include_name:e.target.checked})}/>} label="Include Name" />
            <FormControlLabel control={<Switch checked={data.include_jobs}
              onChange={e=>setData({...data, include_jobs:e.target.checked})}/>} label="Include Jobs" />
            <Stack direction="row" spacing={1} mb={1}>
              {PLACEHOLDERS.map(ph => (
                <Button key={ph} size="small" variant="outlined" onClick={() => insertPlaceholder(ph, 'follow')}>
                  {ph}
                </Button>
              ))}
            </Stack>
            <TextField
              inputRef={followRef}
              multiline
              minRows={3}
              label="Built-in Follow-up"
              fullWidth
              value={data.follow_up_template}
              onChange={e=>setData({...data, follow_up_template:e.target.value})}
            />
            <Stack direction="row" spacing={1} alignItems="center">
              <TextField label="Days" type="number" inputProps={{min:0}} sx={{ width:80 }}
                value={followDelayDays} onChange={e=>{
                  const v = Number(e.target.value);
                  setFollowDelayDays(v);
                  setData({...data, follow_up_delay: v*86400 + followDelayHours*3600 + followDelayMinutes*60 + followDelaySeconds});
                }}/>
              <TextField label="Hours" type="number" inputProps={{min:0}} sx={{ width:80 }}
                value={followDelayHours} onChange={e=>{
                  const v = Number(e.target.value);
                  setFollowDelayHours(v);
                  setData({...data, follow_up_delay: followDelayDays*86400 + v*3600 + followDelayMinutes*60 + followDelaySeconds});
                }}/>
              <TextField label="Min" type="number" inputProps={{min:0}} sx={{ width:80 }}
                value={followDelayMinutes} onChange={e=>{
                  const v = Number(e.target.value);
                  setFollowDelayMinutes(v);
                  setData({...data, follow_up_delay: followDelayDays*86400 + followDelayHours*3600 + v*60 + followDelaySeconds});
                }}/>
              <TextField label="Sec" type="number" inputProps={{min:0}} sx={{ width:80 }}
                value={followDelaySeconds} onChange={e=>{
                  const v = Number(e.target.value);
                  setFollowDelaySeconds(v);
                  setData({...data, follow_up_delay: followDelayDays*86400 + followDelayHours*3600 + followDelayMinutes*60 + v});
                }}/>
              <TextField label="Open From" type="time" value={data.follow_up_open_from}
                onChange={e=>setData({...data, follow_up_open_from:e.target.value})}
                inputProps={{ step:1 }} size="small"/>
              <TextField label="Open To" type="time" value={data.follow_up_open_to}
                onChange={e=>setData({...data, follow_up_open_to:e.target.value})}
                inputProps={{ step:1 }} size="small"/>
            </Stack>

            <Typography variant="h6">Additional Follow-up Templates</Typography>
            <List dense>
              {(data.follow_up_templates || []).map((t, idx) => (
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
                <Stack direction="row" spacing={1} mb={1}>
                  {PLACEHOLDERS.map(ph => (
                    <Button key={ph} size="small" variant="outlined" onClick={() => insertPlaceholder(ph, 'template')}>
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
