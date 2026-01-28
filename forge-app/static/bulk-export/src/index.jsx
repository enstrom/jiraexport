import React, { useState } from 'react';
import { createRoot } from 'react-dom/client';
import { invoke } from '@forge/bridge';

// Server URL - ändra till din deployade server
const PDF_SERVER_URL = 'https://jira-pdf-export.onrender.com';  // Uppdatera efter deployment

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
    marginBottom: '16px',
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
    maxHeight: '300px',
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
    flex: 1,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap'
  },
  downloadItem: {
    padding: '8px 0',
    borderBottom: '1px solid #F4F5F7'
  },
  link: {
    color: '#0052CC',
    textDecoration: 'none'
  },
  buttonRow: {
    display: 'flex',
    gap: '8px',
    marginTop: '16px',
    flexWrap: 'wrap'
  },
  progressBar: {
    width: '100%',
    height: '4px',
    background: '#DFE1E6',
    borderRadius: '2px',
    marginTop: '8px',
    overflow: 'hidden'
  },
  progressFill: {
    height: '100%',
    background: '#0052CC',
    transition: 'width 0.3s ease'
  },
  configBox: {
    background: '#FFFAE6',
    border: '1px solid #FFE380',
    borderRadius: '8px',
    padding: '16px',
    marginBottom: '16px',
    fontSize: '13px'
  }
};

function App() {
  const [issueKeys, setIssueKeys] = useState('SOMU-2, SOMU-31, SOMU-48');
  const [issues, setIssues] = useState([]);
  const [status, setStatus] = useState({ type: '', message: '' });
  const [isLoading, setIsLoading] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [downloads, setDownloads] = useState([]);
  const [progress, setProgress] = useState(0);
  const [serverConnected, setServerConnected] = useState(null);

  // Kontrollera serveranslutning
  const checkServer = async () => {
    try {
      const response = await fetch(`${PDF_SERVER_URL}/health`);
      if (response.ok) {
        setServerConnected(true);
        return true;
      }
    } catch (e) {
      console.log('Server not available:', e);
    }
    setServerConnected(false);
    return false;
  };

  const loadIssues = async () => {
    setIsLoading(true);
    setStatus({ type: 'loading', message: 'Hamtar issues...' });
    setDownloads([]);
    setIssues([]);
    setProgress(0);

    // Kolla server
    await checkServer();

    const keys = issueKeys
      .split(/[,\s]+/)
      .map(k => k.trim().toUpperCase())
      .filter(k => k.length > 0 && k.includes('-'));

    if (keys.length === 0) {
      setStatus({ type: 'error', message: 'Ange minst en issue key (t.ex. SOMU-31)' });
      setIsLoading(false);
      return;
    }

    const loadedIssues = [];
    const errors = [];

    for (let i = 0; i < keys.length; i++) {
      const key = keys[i];
      setProgress(((i + 1) / keys.length) * 100);
      
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
      setStatus({ type: 'error', message: 'Kunde inte ladda nagra issues: ' + errors.join(', ') });
    }

    setIsLoading(false);
  };

  // Exportera via extern server (med bilder)
  const exportViaServer = async () => {
    if (!serverConnected) {
      setStatus({ type: 'error', message: 'PDF-servern ar inte tillganglig. Kontakta administratoren.' });
      return;
    }

    setIsExporting(true);
    setDownloads([]);
    setProgress(0);
    setStatus({ type: 'loading', message: 'Skickar till PDF-server...' });

    try {
      const issueKeyList = issues.map(i => i.key);
      
      const response = await fetch(`${PDF_SERVER_URL}/api/export`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ issue_keys: issueKeyList })
      });

      const result = await response.json();

      if (result.success) {
        const newDownloads = result.pdfs.map(pdf => ({
          success: true,
          key: pdf.issue_key,
          filename: pdf.filename,
          pdfBase64: pdf.pdf_base64
        }));

        // Lägg till misslyckade
        result.errors.forEach(err => {
          newDownloads.push({
            success: false,
            key: err.issue_key,
            error: err.error
          });
        });

        setDownloads(newDownloads);
        setStatus({ 
          type: 'success', 
          message: `Export klar! ${result.exported} av ${result.total} lyckades.` 
        });
      } else {
        setStatus({ type: 'error', message: result.error || 'Export misslyckades' });
      }
    } catch (error) {
      console.error('Server export error:', error);
      setStatus({ type: 'error', message: `Serverfel: ${error.message}` });
    }

    setIsExporting(false);
  };

  // Exportera via Forge backend (utan bilder)
  const exportViaForge = async () => {
    setIsExporting(true);
    setDownloads([]);
    setProgress(0);

    for (let i = 0; i < issues.length; i++) {
      const issue = issues[i];
      setStatus({ 
        type: 'loading', 
        message: `Genererar PDF for ${issue.key}... (${i + 1}/${issues.length})` 
      });
      setProgress(((i + 1) / issues.length) * 100);

      try {
        const result = await invoke('exportToPdf', { issueKey: issue.key });

        if (result.success && result.pdfBase64) {
          setDownloads(prev => [...prev, {
            success: true,
            key: issue.key,
            filename: result.filename,
            pdfBase64: result.pdfBase64
          }]);
        } else {
          setDownloads(prev => [...prev, {
            success: false,
            key: issue.key,
            error: result.error || 'Okant fel'
          }]);
        }
      } catch (error) {
        setDownloads(prev => [...prev, {
          success: false,
          key: issue.key,
          error: error.message
        }]);
      }
    }

    setStatus({ type: 'success', message: 'Export klar!' });
    setIsExporting(false);
  };

  const downloadAll = () => {
    const successfulDownloads = downloads.filter(d => d.success);
    
    if (successfulDownloads.length === 0) {
      setStatus({ type: 'error', message: 'Inga PDFer att ladda ner' });
      return;
    }

    successfulDownloads.forEach((dl, index) => {
      setTimeout(() => {
        const link = document.createElement('a');
        link.href = `data:application/pdf;base64,${dl.pdfBase64}`;
        link.download = dl.filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      }, index * 500);
    });

    setStatus({ type: 'success', message: `Startar nedladdning av ${successfulDownloads.length} filer...` });
  };

  const copyIssueKeys = () => {
    const keys = issues.map(i => i.key).join(', ');
    navigator.clipboard.writeText(keys);
    setStatus({ type: 'success', message: `Kopierade ${issues.length} issue-keys till urklipp!` });
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
      <h1 style={styles.header}>📄 Bulk PDF Export</h1>
      <p style={styles.description}>
        Exportera Jira-issues till PDF med bilder och alla falt.
      </p>

      {serverConnected === false && (
        <div style={styles.configBox}>
          ⚠️ <strong>PDF-server ej tillganglig.</strong> Export utan bilder fungerar fortfarande.
          For bilder, kontrollera att servern ar deployad.
        </div>
      )}

      <div style={styles.box}>
        <strong>🎫 Issue Keys:</strong>
        <input
          type="text"
          style={styles.input}
          value={issueKeys}
          onChange={(e) => setIssueKeys(e.target.value)}
          placeholder="SOMU-31, SOMU-48, SOMU-217"
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
          {(isLoading || isExporting) && (
            <div style={styles.progressBar}>
              <div style={{ ...styles.progressFill, width: `${progress}%` }} />
            </div>
          )}
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
          <div style={styles.buttonRow}>
            {serverConnected && (
              <button
                style={{ ...styles.buttonGreen, ...(isExporting ? styles.buttonDisabled : {}) }}
                onClick={exportViaServer}
                disabled={isExporting}
              >
                {isExporting ? 'Exporterar...' : `🖼️ Exportera med bilder (${issues.length})`}
              </button>
            )}
            <button
              style={{ ...styles.button, ...(isExporting ? styles.buttonDisabled : {}) }}
              onClick={exportViaForge}
              disabled={isExporting}
            >
              {isExporting ? 'Exporterar...' : `📄 Snabb export (${issues.length})`}
            </button>
            <button
              style={styles.button}
              onClick={copyIssueKeys}
            >
              📋 Kopiera keys
            </button>
          </div>
        </div>
      )}

      {downloads.length > 0 && (
        <div style={styles.box}>
          <strong>📥 Nedladdningar: ({successCount} av {downloads.length} lyckades)</strong>
          
          {successCount > 0 && (
            <div style={styles.buttonRow}>
              <button
                style={styles.buttonGreen}
                onClick={downloadAll}
              >
                ⬇️ Ladda ner alla ({successCount}) PDFer
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
                      href={`data:application/pdf;base64,${dl.pdfBase64}`}
                      download={dl.filename}
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
