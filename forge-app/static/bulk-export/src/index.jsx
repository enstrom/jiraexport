import React, { useState } from 'react';
import { createRoot } from 'react-dom/client';
import { invoke } from '@forge/bridge';

const styles = {
  container: {
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    padding: '24px',
    maxWidth: '800px',
    margin: '0 auto',
    background: '#FAFBFC',
    minHeight: '100vh'
  },
  header: {
    fontSize: '24px',
    color: '#172B4D',
    marginBottom: '8px',
    fontWeight: 600
  },
  description: {
    color: '#5E6C84',
    marginBottom: '24px',
    fontSize: '14px'
  },
  box: {
    background: 'white',
    border: '1px solid #DFE1E6',
    borderRadius: '8px',
    padding: '20px',
    marginBottom: '16px'
  },
  input: {
    width: '100%',
    padding: '10px 12px',
    border: '2px solid #DFE1E6',
    borderRadius: '3px',
    fontSize: '14px',
    fontFamily: 'monospace',
    marginBottom: '12px',
    boxSizing: 'border-box'
  },
  button: {
    padding: '10px 20px',
    background: '#0052CC',
    color: 'white',
    border: 'none',
    borderRadius: '3px',
    fontSize: '14px',
    fontWeight: 500,
    cursor: 'pointer',
    marginRight: '8px'
  },
  buttonGreen: {
    padding: '10px 20px',
    background: '#00875A',
    color: 'white',
    border: 'none',
    borderRadius: '3px',
    fontSize: '14px',
    fontWeight: 500,
    cursor: 'pointer',
    marginRight: '8px'
  },
  buttonDisabled: {
    opacity: 0.5,
    cursor: 'not-allowed'
  },
  status: {
    padding: '12px',
    borderRadius: '3px',
    marginTop: '16px'
  },
  statusLoading: {
    background: '#DEEBFF',
    color: '#0052CC'
  },
  statusSuccess: {
    background: '#E3FCEF',
    color: '#006644'
  },
  statusError: {
    background: '#FFEBE6',
    color: '#BF2600'
  },
  issueList: {
    maxHeight: '200px',
    overflowY: 'auto',
    border: '1px solid #DFE1E6',
    borderRadius: '3px',
    marginTop: '12px'
  },
  issueItem: {
    padding: '10px 12px',
    borderBottom: '1px solid #F4F5F7',
    display: 'flex',
    gap: '12px'
  },
  issueKey: {
    color: '#0052CC',
    fontWeight: 500,
    minWidth: '100px'
  },
  issueSummary: {
    color: '#172B4D',
    flex: 1
  },
  formatSelector: {
    display: 'flex',
    gap: '8px',
    marginTop: '16px',
    marginBottom: '16px'
  },
  formatButton: {
    padding: '8px 16px',
    borderRadius: '4px',
    cursor: 'pointer',
    border: 'none',
    fontWeight: 500
  },
  formatActive: {
    background: '#0052CC',
    color: 'white'
  },
  formatInactive: {
    background: '#F4F5F7',
    color: '#172B4D'
  },
  buttonRow: {
    display: 'flex',
    gap: '8px',
    marginTop: '16px',
    flexWrap: 'wrap'
  },
  downloadItem: {
    padding: '8px 0',
    borderBottom: '1px solid #F4F5F7'
  },
  link: {
    color: '#0052CC',
    textDecoration: 'none'
  }
};

function App() {
  const [issueKeys, setIssueKeys] = useState('SOMU-48');
  const [issues, setIssues] = useState([]);
  const [status, setStatus] = useState({ type: '', message: '' });
  const [isLoading, setIsLoading] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [downloads, setDownloads] = useState([]);
  const [exportFormat, setExportFormat] = useState('pdf');

  const loadIssues = async () => {
    setIsLoading(true);
    setStatus({ type: 'loading', message: 'Hämtar issues...' });
    setDownloads([]);
    setIssues([]);

    const keys = issueKeys
      .split(/[,\s]+/)
      .map(k => k.trim().toUpperCase())
      .filter(k => k.length > 0 && k.includes('-'));

    if (keys.length === 0) {
      setStatus({ type: 'error', message: 'Ange minst en issue key (t.ex. SOMU-48)' });
      setIsLoading(false);
      return;
    }

    const loadedIssues = [];
    const errors = [];

    for (const key of keys) {
      try {
        const result = await invoke('getIssueData', { issueKey: key });
        if (result.issue) {
          loadedIssues.push(result.issue);
        } else if (result.error) {
          errors.push(`${key}: ${result.error}`);
        }
      } catch (error) {
        errors.push(`${key}: ${error.message}`);
      }
    }

    setIssues(loadedIssues);
    
    if (loadedIssues.length > 0) {
      setStatus({ 
        type: 'success', 
        message: `Laddade ${loadedIssues.length} issues` + (errors.length > 0 ? ` (${errors.length} fel)` : '')
      });
    } else {
      setStatus({ type: 'error', message: 'Kunde inte ladda några issues: ' + errors.join(', ') });
    }

    setIsLoading(false);
  };

  // Exportera via extern server (med bilder)
  const exportWithImages = async () => {
    setIsExporting(true);
    setDownloads([]);
    
    const formatNames = { pdf: 'PDF', docx: 'Word', png: 'PNG' };
    setStatus({ type: 'loading', message: `Exporterar till ${formatNames[exportFormat]}...` });

    try {
      const issueKeyList = issues.map(i => i.key);
      
      // Anropa backend som i sin tur anropar extern server
      const result = await invoke('exportViaServer', {
        issueKeys: issueKeyList,
        format: exportFormat
      });

      console.log('Export result:', result);

      if (result.success && result.files) {
        const newDownloads = result.files.map(file => ({
          success: true,
          key: file.issue_key,
          filename: file.filename,
          fileBase64: file.file_base64 || file.pdf_base64,
          format: file.format || exportFormat
        }));

        // Lägg till misslyckade
        (result.errors || []).forEach(err => {
          newDownloads.push({
            success: false,
            key: err.issue_key,
            error: err.error
          });
        });

        setDownloads(newDownloads);
        setStatus({ 
          type: 'success', 
          message: `Export klar! ${result.exported || newDownloads.filter(d => d.success).length} filer skapades.` 
        });
      } else {
        setStatus({ type: 'error', message: result.error || 'Export misslyckades' });
      }
    } catch (error) {
      console.error('Export error:', error);
      setStatus({ type: 'error', message: `Fel: ${error.message}` });
    }

    setIsExporting(false);
  };

  const getMimeType = (format) => {
    const mimeTypes = {
      'pdf': 'application/pdf',
      'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'md': 'text/markdown',
      'png': 'image/png'
    };
    return mimeTypes[format] || 'application/octet-stream';
  };

  const downloadFile = (dl) => {
    const link = document.createElement('a');
    link.href = `data:${getMimeType(dl.format)};base64,${dl.fileBase64}`;
    link.download = dl.filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const downloadAll = () => {
    const successfulDownloads = downloads.filter(d => d.success);
    successfulDownloads.forEach((dl, index) => {
      setTimeout(() => downloadFile(dl), index * 500);
    });
  };

  const getStatusStyle = () => {
    if (!status.type) return { display: 'none' };
    return {
      ...styles.status,
      ...(status.type === 'loading' ? styles.statusLoading : {}),
      ...(status.type === 'success' ? styles.statusSuccess : {}),
      ...(status.type === 'error' ? styles.statusError : {})
    };
  };

  const successCount = downloads.filter(d => d.success).length;

  return (
    <div style={styles.container}>
      <h1 style={styles.header}>📁 Bulk Export</h1>
      <p style={styles.description}>
        Exportera Jira-issues till PDF, Word eller PNG med bilder och bilagor.
      </p>

      <div style={styles.box}>
        <strong>🎫 Issue Keys:</strong>
        <input
          type="text"
          style={styles.input}
          value={issueKeys}
          onChange={(e) => setIssueKeys(e.target.value)}
          placeholder="SOMU-48, SOMU-31, SOMU-217"
        />
        <button
          style={{ ...styles.button, ...(isLoading ? styles.buttonDisabled : {}) }}
          onClick={loadIssues}
          disabled={isLoading}
        >
          {isLoading ? 'Laddar...' : 'Ladda issues'}
        </button>
      </div>

      {status.message && (
        <div style={getStatusStyle()}>
          {status.message}
        </div>
      )}

      {issues.length > 0 && (
        <div style={styles.box}>
          <strong>📋 Resultat: {issues.length} issues</strong>
          <div style={styles.issueList}>
            {issues.map((issue) => (
              <div key={issue.key} style={styles.issueItem}>
                <span style={styles.issueKey}>{issue.key}</span>
                <span style={styles.issueSummary}>{issue.summary}</span>
              </div>
            ))}
          </div>
          
          {/* Format selector - ALLTID SYNLIG */}
          <div style={{ marginTop: '20px' }}>
            <strong>📁 Välj exportformat:</strong>
            <div style={styles.formatSelector}>
              {['pdf', 'docx', 'md', 'png'].map(fmt => (
                <button
                  key={fmt}
                  style={{
                    ...styles.formatButton,
                    ...(exportFormat === fmt ? styles.formatActive : styles.formatInactive)
                  }}
                  onClick={() => setExportFormat(fmt)}
                >
                  {fmt === 'pdf' && '📄 PDF'}
                  {fmt === 'docx' && '📝 Word'}
                  {fmt === 'md' && '📋 Markdown'}
                  {fmt === 'png' && '🖼️ PNG'}
                </button>
              ))}
            </div>
            {exportFormat === 'md' && (
              <p style={{ fontSize: '12px', color: '#5E6C84', marginTop: '8px' }}>
                💡 Markdown är perfekt för GPT/AI-sökning och funktionskataloger
              </p>
            )}
          </div>
          
          <div style={styles.buttonRow}>
            <button
              style={{ ...styles.buttonGreen, ...(isExporting ? styles.buttonDisabled : {}) }}
              onClick={exportWithImages}
              disabled={isExporting}
            >
              {isExporting ? 'Exporterar...' : `🚀 Exportera till ${exportFormat.toUpperCase()} (med bilder)`}
            </button>
          </div>
        </div>
      )}

      {downloads.length > 0 && (
        <div style={styles.box}>
          <strong>📥 Nedladdningar ({successCount} av {downloads.length})</strong>
          
          {successCount > 0 && (
            <div style={styles.buttonRow}>
              <button style={styles.buttonGreen} onClick={downloadAll}>
                ⬇️ Ladda ner alla ({successCount})
              </button>
            </div>
          )}
          
          <div style={{ marginTop: '12px' }}>
            {downloads.map((dl, idx) => (
              <div key={idx} style={styles.downloadItem}>
                {dl.success ? (
                  <>
                    ✅{' '}
                    <a
                      href="#"
                      onClick={(e) => { e.preventDefault(); downloadFile(dl); }}
                      style={styles.link}
                    >
                      {dl.filename}
                    </a>
                  </>
                ) : (
                  <>❌ {dl.key}: {dl.error}</>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

const container = document.getElementById('root');
const root = createRoot(container);
root.render(<App />);
