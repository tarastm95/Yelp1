/**
 * 📄 Sample Replies Manager Component (MODE 2: AI Generated)
 * Управління Sample Replies тільки для режиму AI Generated
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  Card,
  CardContent,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  Chip,
  Stack,
  Divider,
  IconButton,
  Collapse,
  LinearProgress,
} from '@mui/material';
import {
  CloudUpload as UploadIcon,
  Save as SaveIcon,
  Visibility as PreviewIcon,
  ExpandMore as ExpandMoreIcon,
  AutoStories as SampleIcon,
  Description as TextIcon,
  CheckCircle as SuccessIcon,
  Warning as WarningIcon,
  Psychology as VectorIcon,
  Search as SearchIcon,
  Analytics as StatsIcon,
} from '@mui/icons-material';
import axios from 'axios';

interface Business {
  business_id: string;
  name: string;
}

interface Props {
  selectedBusiness: Business | null;
  phoneAvailable: boolean;
  sampleRepliesContent?: string;
  sampleRepliesFilename?: string;
  useSampleReplies?: boolean;
  onSampleRepliesUpdate: () => void;
}

const SampleRepliesManager: React.FC<Props> = ({ 
  selectedBusiness, 
  phoneAvailable, 
  sampleRepliesContent = '',
  sampleRepliesFilename = '',
  useSampleReplies = false,
  onSampleRepliesUpdate 
}) => {
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [textDialogOpen, setTextDialogOpen] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [sampleText, setSampleText] = useState('');
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [messageType, setMessageType] = useState<'success' | 'error' | 'info'>('success');
  const [previewExpanded, setPreviewExpanded] = useState(false);
  const [statusLoading, setStatusLoading] = useState(false);
  
  // Vector functionality state
  const [vectorStats, setVectorStats] = useState<any>(null);
  const [vectorTestDialogOpen, setVectorTestDialogOpen] = useState(false);
  const [vectorTestQuery, setVectorTestQuery] = useState('roof repair service');
  const [vectorTestResult, setVectorTestResult] = useState<any>(null);
  const [vectorTesting, setVectorTesting] = useState(false);
  const [chunksDialogOpen, setChunksDialogOpen] = useState(false);
  const [chunks, setChunks] = useState<any[]>([]);

  const showMessage = (msg: string, type: 'success' | 'error' | 'info') => {
    setMessage(msg);
    setMessageType(type);
    setTimeout(() => setMessage(null), 6000);
  };

  // Load status on component mount
  useEffect(() => {
    if (selectedBusiness) {
      loadStatus();
    }
  }, [selectedBusiness, phoneAvailable]);

  const loadStatus = async () => {
    if (!selectedBusiness) return;

    setStatusLoading(true);
    try {
      const response = await axios.get('/api/webhooks/sample-replies/status/', {
        params: {
          business_id: selectedBusiness.business_id,
          phone_available: phoneAvailable
        }
      });

      // Status is loaded but we rely on props for actual content
      console.log('[SAMPLE-REPLIES] Status loaded:', response.data);
      
    } catch (error) {
      console.error('[SAMPLE-REPLIES] Failed to load status:', error);
    } finally {
      setStatusLoading(false);
    }
  };

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      // Validate file size (5MB max)
      if (file.size > 5 * 1024 * 1024) {
        showMessage('File too large. Maximum size is 5MB.', 'error');
        return;
      }
      setSelectedFile(file);
    }
  };

  const handleFileUpload = async () => {
    if (!selectedFile || !selectedBusiness) return;

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('business_id', selectedBusiness.business_id);
      formData.append('phone_available', phoneAvailable.toString());

      const response = await axios.post('/api/webhooks/sample-replies/upload/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      if (response.data.vector_search_enabled) {
        showMessage(
          `✅ MODE 2: Vector processing completed! Created ${response.data.chunks_count} semantic chunks with embeddings.`,
          'success'
        );
      } else {
        showMessage(
          `✅ MODE 2: Sample replies uploaded (legacy mode) - ${response.data.message}`,
          'info'
        );
      }
      setUploadDialogOpen(false);
      setSelectedFile(null);
      onSampleRepliesUpdate(); // Reload settings

    } catch (error: any) {
      console.error('[SAMPLE-REPLIES] Upload error:', error);
      const errorData = error.response?.data;
      
      if (errorData?.error === 'PDF binary detected') {
        showMessage(
          `❌ ${errorData.message} ${errorData.instruction}`, 
          'info'
        );
      } else {
        const errorMessage = errorData?.message || errorData?.error || 'Upload failed';
        showMessage(`❌ Upload failed: ${errorMessage}`, 'error');
      }
    } finally {
      setUploading(false);
    }
  };

  const handleTextSave = async () => {
    if (!sampleText.trim() || !selectedBusiness) return;

    setUploading(true);
    try {
      const response = await axios.post('/api/webhooks/sample-replies/save-text/', {
        business_id: selectedBusiness.business_id,
        phone_available: phoneAvailable,
        sample_text: sampleText
      });

      showMessage(`✅ MODE 2: Sample Replies text saved successfully!`, 'success');
      setTextDialogOpen(false);
      setSampleText('');
      onSampleRepliesUpdate(); // Reload settings

    } catch (error: any) {
      console.error('[SAMPLE-REPLIES] Text save error:', error);
      const errorData = error.response?.data;
      const errorMessage = errorData?.message || errorData?.error || 'Save failed';
      showMessage(`❌ Save failed: ${errorMessage}`, 'error');
    } finally {
      setUploading(false);
    }
  };

  // 🔍 Vector functionality methods
  const testVectorSearch = async () => {
    if (!selectedBusiness || !vectorTestQuery.trim()) return;

    setVectorTesting(true);
    try {
      const response = await axios.post('/api/webhooks/sample-replies/vector-test/', {
        business_id: selectedBusiness.business_id,
        test_query: vectorTestQuery
      });

      setVectorTestResult(response.data);
      
      if (response.data.success) {
        showMessage(`✅ Vector search test successful! Found ${response.data.results_count} similar chunks.`, 'success');
      } else {
        showMessage(`⚠️ Vector search test: ${response.data.message}`, 'info');
      }

    } catch (error: any) {
      console.error('[VECTOR-TEST] Error:', error);
      showMessage(`❌ Vector test failed: ${error.response?.data?.message || 'Unknown error'}`, 'error');
    } finally {
      setVectorTesting(false);
    }
  };

  const loadChunks = async () => {
    if (!selectedBusiness) return;

    try {
      const response = await axios.get('/api/webhooks/sample-replies/chunks/', {
        params: {
          business_id: selectedBusiness.business_id,
          limit: 20
        }
      });

      setChunks(response.data.chunks || []);
      setVectorStats(response.data.statistics);
      setChunksDialogOpen(true);

    } catch (error: any) {
      console.error('[CHUNKS] Load error:', error);
      showMessage('Failed to load chunks', 'error');
    }
  };

  if (!selectedBusiness) {
    return (
      <Paper sx={{ p: 3, textAlign: 'center', backgroundColor: 'grey.50' }}>
        <SampleIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
        <Typography variant="h6" color="text.secondary">
          Select a business to configure Sample Replies
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
          MODE 2: AI Generated - Upload sample customer replies to train AI
        </Typography>
      </Paper>
    );
  }

  return (
    <Box>
      {message && (
        <Alert severity={messageType} sx={{ mb: 2 }}>
          {message}
        </Alert>
      )}

      {statusLoading && <LinearProgress sx={{ mb: 2 }} />}

      <Card elevation={3} sx={{ borderRadius: 3, border: '2px solid', borderColor: 'info.main' }}>
        <Box sx={{ 
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          p: 3,
          color: 'white'
        }}>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Box>
              <Typography variant="h5" sx={{ display: 'flex', alignItems: 'center', fontWeight: 700, mb: 1 }}>
                <VectorIcon sx={{ mr: 2, fontSize: 32 }} />
                🔍 MODE 2: Vector-Enhanced Sample Replies
              </Typography>
              <Typography variant="body1" sx={{ opacity: 0.95 }}>
                Advanced semantic chunking with OpenAI embeddings for intelligent contextual replies
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', gap: 1 }}>
              <Chip 
                label="AI Generated Mode" 
                sx={{ 
                  backgroundColor: 'rgba(255,255,255,0.2)', 
                  color: 'white',
                  fontWeight: 600 
                }} 
              />
              <Chip 
                label="🔍 Vector Search" 
                sx={{ 
                  backgroundColor: 'rgba(255,255,255,0.15)', 
                  color: 'white',
                  fontWeight: 600 
                }} 
              />
            </Box>
          </Box>
        </Box>
        
        <CardContent sx={{ p: 3 }}>
          <Stack spacing={3}>
            {/* Current Status */}
            {useSampleReplies ? (
              <Box>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
                  <SuccessIcon color="success" />
                  <Typography variant="h6" color="success.main" sx={{ fontWeight: 600 }}>
                    ✅ Vector Sample Replies Active
                  </Typography>
                  <Chip 
                    label="🔍 Vector Enhanced"
                    size="small" 
                    color="info" 
                    variant="filled"
                  />
                  {vectorStats && (
                    <Chip 
                      label={`${vectorStats.total_chunks || 0} chunks`}
                      size="small" 
                      color="success" 
                      variant="outlined"
                    />
                  )}
                </Box>
                
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  <strong>Source:</strong> {sampleRepliesFilename || 'Manual Input'} 
                  {vectorStats && (
                    <span> • <strong>Documents:</strong> {vectorStats.total_documents} • <strong>Tokens:</strong> {vectorStats.total_tokens?.toLocaleString()}</span>
                  )}
                </Typography>
                
                {/* Vector Statistics */}
                {vectorStats && vectorStats.chunk_types && (
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="caption" sx={{ display: 'block', mb: 1, fontWeight: 600 }}>
                      🔍 Semantic Chunk Types:
                    </Typography>
                    <Stack direction="row" spacing={1} flexWrap="wrap">
                      {Object.entries(vectorStats.chunk_types).map(([type, count]) => (
                        <Chip 
                          key={type}
                          label={`${type}: ${count}`}
                          size="small"
                          variant="outlined"
                          color={type === 'example' ? 'primary' : type === 'response' ? 'success' : 'default'}
                        />
                      ))}
                    </Stack>
                  </Box>
                )}
                
                {/* Preview */}
                <Box>
                  <Button
                    startIcon={<PreviewIcon />}
                    endIcon={<ExpandMoreIcon sx={{ 
                      transform: previewExpanded ? 'rotate(180deg)' : 'rotate(0deg)',
                      transition: 'transform 0.2s'
                    }} />}
                    onClick={() => setPreviewExpanded(!previewExpanded)}
                    size="small"
                    sx={{ mb: 1 }}
                  >
                    Preview Training Content
                  </Button>
                  
                  <Collapse in={previewExpanded}>
                    <Paper 
                      sx={{ 
                        p: 2, 
                        backgroundColor: 'grey.50',
                        maxHeight: 400,
                        overflow: 'auto',
                        fontFamily: 'monospace',
                        fontSize: '0.85rem',
                        border: '1px solid',
                        borderColor: 'grey.300'
                      }}
                    >
                      {sampleRepliesContent.substring(0, 2000)}
                      {sampleRepliesContent.length > 2000 && (
                        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
                          ... and {sampleRepliesContent.length - 2000} more characters
                        </Typography>
                      )}
                    </Paper>
                  </Collapse>
                </Box>
              </Box>
            ) : (
              <Alert severity="info" sx={{ display: 'flex', alignItems: 'center' }}>
                <Box>
                  <Typography variant="body1" sx={{ fontWeight: 600, mb: 1 }}>
                    🤖 MODE 2: No Sample Replies configured yet
                  </Typography>
                  <Typography variant="body2">
                    Upload a file or paste text content to train AI with your actual customer interactions. 
                    The AI will learn your communication style and generate similar contextual responses.
                  </Typography>
                </Box>
              </Alert>
            )}

            <Divider />

            {/* Action Buttons */}
            <Box>
              <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
                📤 Upload Sample Replies
              </Typography>
              
              <Stack direction="row" spacing={2} justifyContent="center">
                <Button
                  variant="outlined"
                  startIcon={<UploadIcon />}
                  onClick={() => setUploadDialogOpen(true)}
                  disabled={uploading}
                  size="large"
                >
                  Upload File
                </Button>
                
                <Button
                  variant="outlined"
                  startIcon={<TextIcon />}
                  onClick={() => setTextDialogOpen(true)}
                  disabled={uploading}
                  size="large"
                >
                  Paste Text
                </Button>
              </Stack>
              
              <Typography variant="caption" color="text.secondary" display="block" textAlign="center" sx={{ mt: 2 }}>
                Supported: PDF files, Text files, or manual text paste • Max 5MB
              </Typography>
            </Box>

            {/* Vector Diagnostics Section */}
            {useSampleReplies && (
              <>
                <Divider />
                <Box>
                  <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
                    🔍 Vector Search Diagnostics
                  </Typography>
                  
                  <Stack direction="row" spacing={2} justifyContent="center">
                    <Button
                      variant="outlined"
                      startIcon={<SearchIcon />}
                      onClick={() => setVectorTestDialogOpen(true)}
                      disabled={uploading}
                      color="info"
                    >
                      Test Vector Search
                    </Button>
                    
                    <Button
                      variant="outlined"
                      startIcon={<StatsIcon />}
                      onClick={loadChunks}
                      disabled={uploading}
                      color="secondary"
                    >
                      View Chunks
                    </Button>
                  </Stack>
                  
                  <Typography variant="caption" color="text.secondary" display="block" textAlign="center" sx={{ mt: 1 }}>
                    Test semantic similarity search and view generated chunks
                  </Typography>
                </Box>
              </>
            )}
          </Stack>
        </CardContent>
      </Card>

      {/* File Upload Dialog */}
      <Dialog open={uploadDialogOpen} onClose={() => !uploading && setUploadDialogOpen(false)}>
        <DialogTitle>
          🔍 Upload Sample Replies File (MODE 2: Vector-Enhanced AI)
        </DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" paragraph>
            Select a PDF or text file containing your sample customer inquiries and responses. 
            The system will automatically create semantic chunks and generate OpenAI embeddings for intelligent similarity search.
          </Typography>
          
          <Alert severity="info" sx={{ mb: 2 }}>
            <Typography variant="body2">
              <strong>🔍 Vector Processing:</strong> Files will be semantically chunked and embedded using OpenAI text-embedding-3-small (1536 dimensions) for advanced similarity search.
            </Typography>
          </Alert>
          
          <Alert severity="warning" sx={{ mb: 2 }}>
            <Typography variant="body2">
              <strong>Note:</strong> If vector processing fails, the system will fallback to simple text processing. 
              For binary PDFs, please copy text and use "Paste Text" option.
            </Typography>
          </Alert>
          
          <Box sx={{ 
            border: '2px dashed',
            borderColor: uploading ? 'primary.main' : 'grey.300',
            borderRadius: 2,
            p: 3,
            textAlign: 'center',
            cursor: 'pointer',
            '&:hover': { borderColor: 'primary.main' },
            mt: 2
          }}>
            <input
              type="file"
              accept=".pdf,.txt"
              onChange={handleFileSelect}
              style={{ display: 'none' }}
              id="file-upload"
            />
            
            <label htmlFor="file-upload" style={{ cursor: 'pointer' }}>
              {selectedFile ? (
                <Box>
                  <UploadIcon sx={{ fontSize: 48, color: 'primary.main', mb: 1 }} />
                  <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                    {selectedFile.name}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {Math.round(selectedFile.size / 1024)} KB
                  </Typography>
                </Box>
              ) : (
                <Box>
                  <UploadIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 1 }} />
                  <Typography variant="body1" color="text.secondary">
                    Click to select file
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    PDF or Text files • Maximum 5MB
                  </Typography>
                </Box>
              )}
            </label>
          </Box>
        </DialogContent>
        
        <DialogActions>
          <Button onClick={() => setUploadDialogOpen(false)} disabled={uploading}>
            Cancel
          </Button>
          <Button 
            onClick={handleFileUpload}
            variant="contained"
            disabled={!selectedFile || uploading}
            startIcon={uploading ? undefined : <UploadIcon />}
          >
            {uploading ? 'Processing...' : 'Upload & Train AI'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Text Input Dialog */}
      <Dialog 
        open={textDialogOpen} 
        onClose={() => !uploading && setTextDialogOpen(false)} 
        maxWidth="md" 
        fullWidth
      >
        <DialogTitle>
          📝 Paste Sample Replies Text (MODE 2: Vector-Enhanced AI)
        </DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" paragraph>
            Copy and paste your sample customer inquiries and responses. The system will automatically 
            create semantic chunks and generate embeddings for intelligent similarity-based AI responses.
          </Typography>
          
          <Alert severity="info" sx={{ mb: 2 }}>
            <Typography variant="body2">
              <strong>🔍 Semantic Processing:</strong> Text will be intelligently chunked and embedded for vector similarity search, enabling AI to find the most relevant examples for each customer inquiry.
            </Typography>
          </Alert>
          
          <TextField
            multiline
            rows={15}
            fullWidth
            value={sampleText}
            onChange={(e) => setSampleText(e.target.value)}
            placeholder="Paste your sample replies content here...

Example format:
Inquiry information:
Name: John D.
Service: Roofing repair
...

Response:
Hello John,
Thanks for reaching out about roofing repair..."
            sx={{ mt: 2 }}
            helperText={`Characters: ${sampleText.length} ${sampleText.length < 50 ? '(minimum 50)' : sampleText.length > 50000 ? '(maximum 50,000)' : '✓'}`}
          />
        </DialogContent>
        
        <DialogActions>
          <Button onClick={() => setTextDialogOpen(false)} disabled={uploading}>
            Cancel
          </Button>
          <Button 
            onClick={handleTextSave}
            variant="contained"
            disabled={!sampleText.trim() || sampleText.length < 50 || uploading}
            startIcon={uploading ? undefined : <SaveIcon />}
          >
            {uploading ? 'Saving...' : 'Save & Train AI'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Vector Search Test Dialog */}
      <Dialog open={vectorTestDialogOpen} onClose={() => !vectorTesting && setVectorTestDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>
          🔍 Test Vector Search (MODE 2: AI Generated)
        </DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" paragraph>
            Test the semantic similarity search with a sample query to see how the AI finds relevant examples from your uploaded Sample Replies.
          </Typography>
          
          <TextField
            fullWidth
            label="Test Query"
            value={vectorTestQuery}
            onChange={(e) => setVectorTestQuery(e.target.value)}
            placeholder="Enter a customer inquiry to test (e.g., 'roof repair service', 'need roofing help')"
            sx={{ mt: 2, mb: 3 }}
            helperText="This simulates what a customer might write to your business"
          />

          {vectorTestResult && (
            <Box sx={{ mt: 3 }}>
              {vectorTestResult.success ? (
                <Alert severity="success" sx={{ mb: 2 }}>
                  <Typography variant="body2">
                    ✅ <strong>Vector Search Successful!</strong><br/>
                    Found {vectorTestResult.results_count} similar chunks with max similarity of {(vectorTestResult.top_similarity * 100).toFixed(1)}%
                  </Typography>
                </Alert>
              ) : (
                <Alert severity="warning" sx={{ mb: 2 }}>
                  <Typography variant="body2">
                    ⚠️ <strong>Vector Search Result:</strong><br/>
                    {vectorTestResult.message}
                  </Typography>
                </Alert>
              )}

              {vectorTestResult.generated_response && (
                <Box sx={{ p: 2, backgroundColor: 'grey.50', borderRadius: 1, border: '1px solid', borderColor: 'grey.300' }}>
                  <Typography variant="caption" sx={{ display: 'block', mb: 1, fontWeight: 600 }}>
                    🤖 AI Generated Response (Based on Similar Chunks):
                  </Typography>
                  <Typography variant="body2" sx={{ fontStyle: 'italic' }}>
                    "{vectorTestResult.generated_response}"
                  </Typography>
                </Box>
              )}

              {vectorTestResult.sample_results && vectorTestResult.sample_results.length > 0 && (
                <Box sx={{ mt: 2 }}>
                  <Typography variant="caption" sx={{ display: 'block', mb: 1, fontWeight: 600 }}>
                    📋 Top Similar Chunks Found:
                  </Typography>
                  {vectorTestResult.sample_results.map((chunk: any, index: number) => (
                    <Box key={index} sx={{ p: 1, mb: 1, backgroundColor: 'white', borderRadius: 1, border: '1px solid', borderColor: 'grey.200' }}>
                      <Typography variant="caption" sx={{ color: 'info.main', fontWeight: 600 }}>
                        Similarity: {(chunk.similarity_score * 100).toFixed(1)}% • Type: {chunk.chunk_type}
                      </Typography>
                      <Typography variant="body2" sx={{ fontSize: '0.85rem' }}>
                        {chunk.content.substring(0, 200)}...
                      </Typography>
                    </Box>
                  ))}
                </Box>
              )}
            </Box>
          )}
        </DialogContent>
        
        <DialogActions>
          <Button onClick={() => setVectorTestDialogOpen(false)} disabled={vectorTesting}>
            Close
          </Button>
          <Button 
            onClick={testVectorSearch}
            variant="contained"
            disabled={!vectorTestQuery.trim() || vectorTesting}
            startIcon={vectorTesting ? undefined : <SearchIcon />}
          >
            {vectorTesting ? 'Testing...' : 'Test Search'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Vector Chunks View Dialog */}
      <Dialog open={chunksDialogOpen} onClose={() => setChunksDialogOpen(false)} maxWidth="lg" fullWidth>
        <DialogTitle>
          📋 Vector Chunks Analysis (MODE 2: AI Generated)
        </DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" paragraph>
            View the semantic chunks created from your Sample Replies with their types and metadata.
          </Typography>

          {vectorStats && (
            <Box sx={{ mb: 3, p: 2, backgroundColor: 'grey.50', borderRadius: 1 }}>
              <Typography variant="h6" sx={{ mb: 1 }}>📊 Statistics</Typography>
              <Stack direction="row" spacing={2} flexWrap="wrap">
                <Chip label={`${vectorStats.total_documents} documents`} color="primary" />
                <Chip label={`${vectorStats.total_chunks} chunks`} color="success" />
                <Chip label={`${vectorStats.total_tokens?.toLocaleString()} tokens`} color="info" />
              </Stack>
            </Box>
          )}

          {chunks.length > 0 ? (
            <Stack spacing={2} sx={{ maxHeight: 400, overflow: 'auto' }}>
              {chunks.map((chunk, index) => (
                <Box key={chunk.id} sx={{ p: 2, border: '1px solid', borderColor: 'grey.300', borderRadius: 1 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                    <Typography variant="caption" sx={{ fontWeight: 600 }}>
                      Chunk #{chunk.chunk_index} • Page {chunk.page_number} • {chunk.token_count} tokens
                    </Typography>
                    <Chip 
                      label={chunk.chunk_type} 
                      size="small" 
                      color={chunk.chunk_type === 'example' ? 'primary' : chunk.chunk_type === 'response' ? 'success' : 'default'} 
                    />
                  </Box>
                  <Typography variant="body2" sx={{ fontSize: '0.9rem' }}>
                    {chunk.content}
                  </Typography>
                  {chunk.metadata && Object.keys(chunk.metadata).length > 0 && (
                    <Box sx={{ mt: 1 }}>
                      <Typography variant="caption" color="text.secondary">
                        Metadata: {JSON.stringify(chunk.metadata)}
                      </Typography>
                    </Box>
                  )}
                </Box>
              ))}
            </Stack>
          ) : (
            <Alert severity="info">
              No chunks found. Upload Sample Replies first to see semantic chunks.
            </Alert>
          )}
        </DialogContent>
        
        <DialogActions>
          <Button onClick={() => setChunksDialogOpen(false)}>
            Close
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default SampleRepliesManager;
