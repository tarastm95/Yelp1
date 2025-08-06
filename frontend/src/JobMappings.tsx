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
        message: 'Помилка завантаження налаштувань',
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
          message: 'Налаштування оновлено успішно',
          severity: 'success',
        });
      } else {
        // Create new mapping
        await axios.post('/job-mappings/', formData);
        setSnackbar({
          open: true,
          message: 'Налаштування створено успішно',
          severity: 'success',
        });
      }
      handleCloseDialog();
      loadJobMappings();
    } catch (error: any) {
      console.error('Error saving job mapping:', error);
      const errorMessage = error.response?.data?.original_name?.[0] || 
                          error.response?.data?.detail || 
                          'Помилка збереження налаштувань';
      setSnackbar({
        open: true,
        message: errorMessage,
        severity: 'error',
      });
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm('Ви впевнені, що хочете видалити це налаштування?')) {
      return;
    }

    try {
      await axios.delete(`/job-mappings/${id}/`);
      setSnackbar({
        open: true,
        message: 'Налаштування видалено успішно',
        severity: 'success',
      });
      loadJobMappings();
    } catch (error) {
      console.error('Error deleting job mapping:', error);
      setSnackbar({
        open: true,
        message: 'Помилка видалення налаштувань',
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
        message: `Налаштування ${!mapping.active ? 'активовано' : 'деактивовано'}`,
        severity: 'success',
      });
      loadJobMappings();
    } catch (error) {
      console.error('Error toggling job mapping:', error);
      setSnackbar({
        open: true,
        message: 'Помилка зміни статусу',
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
              Налаштування назв послуг
            </Typography>
          </Box>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => handleOpenDialog()}
          >
            Додати налаштування
          </Button>
        </Box>

        <Typography variant="body1" sx={{ mb: 3, color: 'text.secondary' }}>
          Тут ви можете налаштувати заміну оригінальних назв послуг з Yelp на ваші власні назви.
          Ці налаштування будуть застосовуватися глобально для всіх повідомлень з плейсхолдером {'{jobs}'}.
        </Typography>

        <Stack spacing={2} sx={{ mb: 3 }}>
          <Box sx={{ p: 2, backgroundColor: 'info.50', borderRadius: 1, border: '1px solid', borderColor: 'info.200' }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 600, color: 'info.main', mb: 1 }}>
              💡 Як це працює:
            </Typography>
            <Typography variant="body2" sx={{ color: 'info.dark' }}>
              • Коли з Yelp приходить lead з послугою "Kitchen remodeling", система перевірить ваші налаштування
              <br />
              • Якщо ви налаштували заміну "Kitchen remodeling" → "Кухонний ремонт", то в повідомленнях буде використано "Кухонний ремонт"
              <br />
              • Якщо заміни немає, використовується оригінальна назва
            </Typography>
          </Box>
        </Stack>

        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
            <Typography>Завантаження...</Typography>
          </Box>
        ) : (
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell><strong>Оригінальна назва</strong></TableCell>
                  <TableCell><strong>Ваша назва</strong></TableCell>
                  <TableCell><strong>Статус</strong></TableCell>
                  <TableCell><strong>Дії</strong></TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {jobMappings.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={4} sx={{ textAlign: 'center', py: 4 }}>
                      <Typography variant="body2" color="text.secondary">
                        Поки що немає налаштованих замін. Натисніть "Додати налаштування" щоб створити першу заміну.
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
                          label={mapping.active ? "Активно" : "Неактивно"}
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
          {editingMapping ? 'Редагувати налаштування' : 'Додати налаштування'}
        </DialogTitle>
        <DialogContent>
          <Stack spacing={3} sx={{ mt: 1 }}>
            <TextField
              label="Оригінальна назва послуги"
              value={formData.original_name}
              onChange={(e) => setFormData({ ...formData, original_name: e.target.value })}
              placeholder="Kitchen remodeling"
              fullWidth
              helperText="Точна назва послуги, яка приходить з Yelp"
            />
            <TextField
              label="Ваша назва послуги"
              value={formData.custom_name}
              onChange={(e) => setFormData({ ...formData, custom_name: e.target.value })}
              placeholder="Кухонний ремонт"
              fullWidth
              helperText="Назва, яка буде використовуватися в повідомленнях замість оригінальної"
            />
            <FormControlLabel
              control={
                <Switch
                  checked={formData.active}
                  onChange={(e) => setFormData({ ...formData, active: e.target.checked })}
                />
              }
              label="Активне налаштування"
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Скасувати</Button>
          <Button 
            onClick={handleSave} 
            variant="contained"
            disabled={!formData.original_name.trim() || !formData.custom_name.trim()}
          >
            {editingMapping ? 'Оновити' : 'Створити'}
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