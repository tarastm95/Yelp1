import React, { useState } from 'react';
import { 
  Box, 
  Button, 
  Typography, 
  TextField, 
  Paper, 
  CircularProgress,
  Alert,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Chip
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import axios from 'axios';

interface Business {
  business_id: string;
  name: string;
}

interface DebugResponse {
  business_id: string;
  diagnostics: {
    documents: any;
    chunks: any;
    settings: any;
    vector_search_test: any;
    classifier: any;
  };
}

const VectorDebug: React.FC<{ businesses: Business[]; selectedBusiness: string }> = ({
  businesses,
  selectedBusiness
}) => {
  const [debugData, setDebugData] = useState<DebugResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [testText, setTestText] = useState('Name: Beau S.\\nRoof replacement\\nSan Fernando Valley, CA 91331');
  const [analysisResult, setAnalysisResult] = useState<any>(null);

  const runDebug = async () => {
    if (!selectedBusiness) {
      setError('Please select a business first');
      return;
    }

    setLoading(true);
    setError('');
    
    console.log('🔍 [DEBUG] Running vector debug for business:', selectedBusiness);

    try {
      const response = await axios.get(`/api/debug/vector/?business_id=${selectedBusiness}`);
      console.log('✅ [DEBUG] Debug response:', response.data);
      setDebugData(response.data);
    } catch (err: any) {
      console.error('❌ [DEBUG] Error:', err);
      setError(err.response?.data?.error || err.message);
    } finally {
      setLoading(false);
    }
  };

  const analyzeText = async () => {
    if (!testText.trim()) {
      setError('Please enter text to analyze');
      return;
    }

    setLoading(true);
    console.log('🔬 [DEBUG] Analyzing text:', testText);

    try {
      const response = await axios.post('/api/debug/chunk-analysis/', { text: testText });
      console.log('✅ [DEBUG] Analysis result:', response.data);
      setAnalysisResult(response.data);
    } catch (err: any) {
      console.error('❌ [DEBUG] Analysis error:', err);
      setError(err.response?.data?.error || err.message);
    } finally {
      setLoading(false);
    }
  };

  const selectedBusinessName = businesses.find(b => b.business_id === selectedBusiness)?.name || selectedBusiness;

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h5" gutterBottom>
        🔍 Vector Search Debug Panel
      </Typography>
      
      {selectedBusiness && (
        <Alert severity="info" sx={{ mb: 2 }}>
          Selected Business: <strong>{selectedBusinessName}</strong>
        </Alert>
      )}

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
        <Button 
          variant="contained" 
          onClick={runDebug} 
          disabled={loading || !selectedBusiness}
          startIcon={loading ? <CircularProgress size={20} /> : null}
        >
          {loading ? 'Running Debug...' : 'Run Vector Debug'}
        </Button>
      </Box>

      {debugData && (
        <Box sx={{ mb: 4 }}>
          <Typography variant="h6" gutterBottom>Debug Results:</Typography>
          
          <Accordion>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography>📄 Documents ({debugData.diagnostics.documents.count})</Typography>
            </AccordionSummary>
            <AccordionDetails>
              <pre>{JSON.stringify(debugData.diagnostics.documents, null, 2)}</pre>
            </AccordionDetails>
          </Accordion>

          <Accordion>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography>
                🧩 Chunks ({debugData.diagnostics.chunks.total_count}) - 
                <Chip label={`inquiry: ${debugData.diagnostics.chunks.by_type.inquiry}`} size="small" sx={{ ml: 1 }} />
                <Chip label={`response: ${debugData.diagnostics.chunks.by_type.response}`} size="small" sx={{ ml: 1 }} />
                <Chip label={`general: ${debugData.diagnostics.chunks.by_type.general}`} size="small" sx={{ ml: 1 }} />
              </Typography>
            </AccordionSummary>
            <AccordionDetails>
              <pre>{JSON.stringify(debugData.diagnostics.chunks, null, 2)}</pre>
            </AccordionDetails>
          </Accordion>

          <Accordion>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography>⚙️ Settings</Typography>
            </AccordionSummary>
            <AccordionDetails>
              <pre>{JSON.stringify(debugData.diagnostics.settings, null, 2)}</pre>
            </AccordionDetails>
          </Accordion>

          <Accordion>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography>🔍 Vector Search Test</Typography>
            </AccordionSummary>
            <AccordionDetails>
              <pre>{JSON.stringify(debugData.diagnostics.vector_search_test, null, 2)}</pre>
            </AccordionDetails>
          </Accordion>
        </Box>
      )}

      <Paper sx={{ p: 2, mt: 3 }}>
        <Typography variant="h6" gutterBottom>
          🔬 Text Analysis Tool
        </Typography>
        
        <TextField
          multiline
          rows={4}
          fullWidth
          label="Text to Analyze"
          value={testText}
          onChange={(e) => setTestText(e.target.value)}
          sx={{ mb: 2 }}
        />
        
        <Button 
          variant="outlined" 
          onClick={analyzeText}
          disabled={loading}
        >
          Analyze Text
        </Button>

        {analysisResult && (
          <Box sx={{ mt: 2 }}>
            <Typography variant="subtitle1" gutterBottom>Analysis Result:</Typography>
            <pre style={{ fontSize: '12px', overflow: 'auto' }}>
              {JSON.stringify(analysisResult, null, 2)}
            </pre>
          </Box>
        )}
      </Paper>
    </Box>
  );
};

export default VectorDebug;
