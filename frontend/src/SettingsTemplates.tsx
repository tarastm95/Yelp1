import React, {useEffect, useState} from 'react';
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
  Snackbar,
  Alert,
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';

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
        setData(t.data);
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
    setSaved(false);
    setError('');
    setOpen(true);
  };

  const handleSave = () => {
    const payload = {name, description, data};
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
            <TextField
              multiline
              minRows={3}
              label="Greeting Template"
              fullWidth
              value={data.greeting_template}
              onChange={e=>setData({...data, greeting_template:e.target.value})}
            />
            <Stack direction="row" spacing={1}>
              <TextField type="number" label="Greeting Delay (sec)" value={data.greeting_delay}
                onChange={e=>setData({...data, greeting_delay: Number(e.target.value)})}
              />
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
            <TextField
              multiline
              minRows={3}
              label="Built-in Follow-up"
              fullWidth
              value={data.follow_up_template}
              onChange={e=>setData({...data, follow_up_template:e.target.value})}
            />
            <Stack direction="row" spacing={1}>
              <TextField type="number" label="Follow-up Delay (sec)" value={data.follow_up_delay}
                onChange={e=>setData({...data, follow_up_delay:Number(e.target.value)})}
              />
              <TextField label="Open From" type="time" value={data.follow_up_open_from}
                onChange={e=>setData({...data, follow_up_open_from:e.target.value})}
                inputProps={{ step:1 }} size="small"/>
              <TextField label="Open To" type="time" value={data.follow_up_open_to}
                onChange={e=>setData({...data, follow_up_open_to:e.target.value})}
                inputProps={{ step:1 }} size="small"/>
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
