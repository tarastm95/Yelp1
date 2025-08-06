import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  Container,
  Paper,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  IconButton,
  Box,
  Snackbar,
  Alert,
  Switch,
  FormControlLabel,
  Chip,
  Stack,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import WorkIcon from '@mui/icons-material/Work';

interface JobMapping {
  id: number;
  original_name: string;
  custom_name: string;
  active: boolean;
  created_at: string;
  updated_at: string;
}

const JobMappings: React.FC = () => {
  const [jobMappings, setJobMappings] = useState<JobMapping[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingMapping, setEditingMapping] = useState<JobMapping | null>(null);
  const [formData, setFormData] = useState({
    original_name: '',
    custom_name: '',
    active: true,
  });
  const [snackbar, setSnackbar] = useState({
    open: false,
    message: '',
    severity: 'success' as 'success' | 'error',
  });

  const loadJobMappings = async () => {
    try {
      setLoading(true);
      const response = await axios.get('/job-mappings/');
      setJobMappings(response.data);
    } catch (error) {
      console.error('Error loading job mappings:', error);
      setSnackbar({
        open: true,
        message: 'Error loading settings',
        severity: 'error',
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadJobMappings();
  }, []);

  const handleOpenDialog = (mapping?: JobMapping) => {
    if (mapping) {
      setEditingMapping(mapping);
      setFormData({
        original_name: mapping.original_name,
        custom_name: mapping.custom_name,
        active: mapping.active,
      });
    } else {
      setEditingMapping(null);
      setFormData({
        original_name: '',
        custom_name: '',
        active: true,
      });
    }
    setDialogOpen(true);
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    setEditingMapping(null);
    setFormData({
      original_name: '',
      custom_name: '',
      active: true,
    });
  };

  const handleSave = async () => {
    try {
      if (editingMapping) {
        // Update existing mapping
        await axios.put(`/job-mappings/${editingMapping.id}/`, formData);
        setSnackbar({
          open: true,
          message: 'Settings updated successfully',
          severity: 'success',
        });
      } else {
        // Create new mapping
        await axios.post('/job-mappings/', formData);
        setSnackbar({
          open: true,
          message: 'Settings created successfully',
          severity: 'success',
        });
      }
      handleCloseDialog();
      loadJobMappings();
    } catch (error: any) {
      console.error('Error saving job mapping:', error);
      const errorMessage = error.response?.data?.original_name?.[0] || 
                          error.response?.data?.detail || 
                          'Error saving settings';
      setSnackbar({
        open: true,
        message: errorMessage,
        severity: 'error',
      });
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm('Are you sure you want to delete this setting?')) {
      return;
    }

    try {
      await axios.delete(`/job-mappings/${id}/`);
      setSnackbar({
        open: true,
        message: 'Settings deleted successfully',
        severity: 'success',
      });
      loadJobMappings();
    } catch (error) {
      console.error('Error deleting job mapping:', error);
      setSnackbar({
        open: true,
        message: 'Error deleting settings',
        severity: 'error',
      });
    }
  };

  const handleToggleActive = async (mapping: JobMapping) => {
    try {
      await axios.put(`/job-mappings/${mapping.id}/`, {
        ...mapping,
        active: !mapping.active,
      });
      setSnackbar({
        open: true,
        message: `Settings ${!mapping.active ? 'activated' : 'deactivated'}`,
        severity: 'success',
      });
      loadJobMappings();
    } catch (error) {
      console.error('Error toggling job mapping:', error);
      setSnackbar({
        open: true,
        message: 'Error changing status',
        severity: 'error',
      });
    }
  };

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Paper sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <WorkIcon color="primary" />
            <Typography variant="h4">
              Job Name Settings
            </Typography>
          </Box>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => handleOpenDialog()}
          >
            Add Setting
          </Button>
        </Box>

        <Typography variant="body1" sx={{ mb: 3, color: 'text.secondary' }}>
          Here you can configure replacement of original service names from Yelp with your custom names.
          These settings will be applied globally for all messages with the {'{jobs}'} placeholder.
        </Typography>

        <Stack spacing={2} sx={{ mb: 3 }}>
          <Box sx={{ p: 2, backgroundColor: 'info.50', borderRadius: 1, border: '1px solid', borderColor: 'info.200' }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 600, color: 'info.main', mb: 1 }}>
              💡 How it works:
            </Typography>
            <Typography variant="body2" sx={{ color: 'info.dark' }}>
              • When a lead comes from Yelp with a service "Kitchen remodeling", the system will check your settings
              <br />
              • If you configured a replacement "Kitchen remodeling" → "Kitchen Renovation", then "Kitchen Renovation" will be used in messages
              <br />
              • If there's no replacement, the original name is used
            </Typography>
          </Box>
        </Stack>

        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
            <Typography>Loading...</Typography>
          </Box>
        ) : (
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell><strong>Original Name</strong></TableCell>
                  <TableCell><strong>Your Name</strong></TableCell>
                  <TableCell><strong>Status</strong></TableCell>
                  <TableCell><strong>Actions</strong></TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {jobMappings.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={4} sx={{ textAlign: 'center', py: 4 }}>
                      <Typography variant="body2" color="text.secondary">
                        No configured replacements yet. Click "Add Setting" to create your first replacement.
                      </Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  jobMappings.map((mapping) => (
                    <TableRow key={mapping.id}>
                      <TableCell>
                        <Chip 
                          label={mapping.original_name}
                          variant="outlined"
                          size="small"
                          sx={{ fontFamily: 'monospace' }}
                        />
                      </TableCell>
                      <TableCell>
                        <Chip 
                          label={mapping.custom_name}
                          color="primary"
                          size="small"
                          sx={{ fontFamily: 'monospace' }}
                        />
                      </TableCell>
                      <TableCell>
                        <FormControlLabel
                          control={
                            <Switch
                              checked={mapping.active}
                              onChange={() => handleToggleActive(mapping)}
                              color="primary"
                            />
                          }
                          label={mapping.active ? "Active" : "Inactive"}
                        />
                      </TableCell>
                      <TableCell>
                        <IconButton
                          onClick={() => handleOpenDialog(mapping)}
                          color="primary"
                          size="small"
                        >
                          <EditIcon />
                        </IconButton>
                        <IconButton
                          onClick={() => handleDelete(mapping.id)}
                          color="error"
                          size="small"
                        >
                          <DeleteIcon />
                        </IconButton>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Paper>

      {/* Dialog for adding/editing job mappings */}
      <Dialog open={dialogOpen} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
        <DialogTitle>
          {editingMapping ? 'Edit Setting' : 'Add Setting'}
        </DialogTitle>
        <DialogContent>
          <Stack spacing={3} sx={{ mt: 1 }}>
            <TextField
              label="Original Service Name"
              value={formData.original_name}
              onChange={(e) => setFormData({ ...formData, original_name: e.target.value })}
              placeholder="Kitchen remodeling"
              fullWidth
              helperText="Exact service name that comes from Yelp"
            />
            <TextField
              label="Your Service Name"
              value={formData.custom_name}
              onChange={(e) => setFormData({ ...formData, custom_name: e.target.value })}
              placeholder="Kitchen Renovation"
              fullWidth
              helperText="Name that will be used in messages instead of the original"
            />
            <FormControlLabel
              control={
                <Switch
                  checked={formData.active}
                  onChange={(e) => setFormData({ ...formData, active: e.target.checked })}
                />
              }
              label="Active Setting"
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancel</Button>
          <Button 
            onClick={handleSave} 
            variant="contained"
            disabled={!formData.original_name.trim() || !formData.custom_name.trim()}
          >
            {editingMapping ? 'Update' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar for notifications */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
      >
        <Alert
          onClose={() => setSnackbar({ ...snackbar, open: false })}
          severity={snackbar.severity}
          sx={{ width: '100%' }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Container>
  );
};

export default JobMappings;