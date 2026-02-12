/**
 * Jira PDF Exporter - Forge App
 * Main entry point
 */
import Resolver from '@forge/resolver';
import api, { fetch } from '@forge/api';
import { exportIssueToPdf, exportMultipleIssuesToPdf, BulkExportResult } from './pdf-exporter';
import { getIssue, searchIssues } from './jira-client';

// External server URL
const PDF_SERVER_URL = 'https://jiraexport.onrender.com';

const resolver = new Resolver();

interface ResolverContext {
  payload: Record<string, any>;
  context: {
    extension?: {
      issue?: {
        key?: string;
      };
    };
  };
}

/**
 * Resolver för UI-komponenterna
 */
resolver.define('getIssueData', async (req: ResolverContext) => {
  // Acceptera issueKey från payload eller context
  const issueKey = req.payload?.issueKey || req.context.extension?.issue?.key;
  
  if (!issueKey) {
    return { error: 'No issue key found' };
  }
  
  try {
    console.log('Fetching issue:', issueKey);
    const issue = await getIssue(issueKey);
    console.log('Fetched issue:', issueKey, issue.summary);
    return { issue };
  } catch (error) {
    console.error('Error fetching issue:', issueKey, error);
    return { error: `Failed to fetch issue ${issueKey}` };
  }
});

resolver.define('exportToPdf', async (req: ResolverContext) => {
  const issueKey = req.payload?.issueKey || req.context.extension?.issue?.key;
  
  if (!issueKey) {
    return { success: false, error: 'No issue key provided' };
  }
  
  try {
    const result = await exportIssueToPdf(issueKey);
    return { success: true, ...result };
  } catch (error) {
    console.error('Error exporting to PDF:', error);
    return { success: false, error: 'Failed to export PDF' };
  }
});

resolver.define('searchIssues', async (req: ResolverContext) => {
  const { jql, maxResults = 50 } = req.payload || {};
  
  try {
    const issues = await searchIssues(jql, maxResults);
    return { issues };
  } catch (error) {
    console.error('Error searching issues:', error);
    return { error: 'Failed to search issues' };
  }
});

resolver.define('exportBulkToPdf', async (req: ResolverContext) => {
  const { issueKeys } = req.payload || {};
  
  if (!issueKeys || !Array.isArray(issueKeys) || issueKeys.length === 0) {
    return { success: false, error: 'No issue keys provided' };
  }
  
  try {
    const results = await exportMultipleIssuesToPdf(issueKeys);
    return { success: true, results };
  } catch (error) {
    console.error('Error exporting bulk PDFs:', error);
    return { success: false, error: 'Failed to export PDFs' };
  }
});

/**
 * Check if external server is available
 */
resolver.define('checkServer', async () => {
  console.log('checkServer called, checking:', PDF_SERVER_URL);
  try {
    const response = await fetch(`${PDF_SERVER_URL}/health`, {
      method: 'GET',
      headers: { 'Accept': 'application/json' }
    });
    
    console.log('Server response status:', response.status);
    
    if (response.ok) {
      const data = await response.json();
      console.log('Server connected successfully:', data);
      return { connected: true, data };
    }
    console.log('Server not responding');
    return { connected: false, error: 'Server not responding' };
  } catch (error) {
    console.error('Server check failed:', error);
    return { connected: false, error: 'Failed to connect to server' };
  }
});

/**
 * Get available export formats from server
 */
resolver.define('getFormats', async () => {
  try {
    const response = await fetch(`${PDF_SERVER_URL}/api/formats`, {
      method: 'GET',
      headers: { 'Accept': 'application/json' }
    });
    
    if (response.ok) {
      const data = await response.json();
      return { success: true, formats: data.formats };
    }
    return { success: false, formats: [] };
  } catch (error) {
    console.error('Failed to get formats:', error);
    return { success: false, formats: [] };
  }
});

/**
 * Export issues via external server (with images)
 */
resolver.define('exportViaServer', async (req: ResolverContext) => {
  const { issueKeys, format = 'pdf' } = req.payload || {};
  
  if (!issueKeys || !Array.isArray(issueKeys) || issueKeys.length === 0) {
    return { success: false, error: 'No issue keys provided' };
  }
  
  try {
    console.log(`Exporting ${issueKeys.length} issues via server, format: ${format}`);
    
    const response = await fetch(`${PDF_SERVER_URL}/api/export`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: JSON.stringify({
        issue_keys: issueKeys,
        format: format
      })
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error('Server error:', response.status, errorText);
      return { success: false, error: `Server error: ${response.status}` };
    }
    
    const data = await response.json();
    console.log(`Export complete: ${data.exported} files`);
    
    return {
      success: true,
      files: data.files || data.pdfs || [],
      errors: data.errors || [],
      exported: data.exported,
      total: data.total,
      format: format
    };
  } catch (error) {
    console.error('Export via server failed:', error);
    return { success: false, error: 'Failed to export via server' };
  }
});

/**
 * Issue action handler - direkt export från issue-menyn
 */
export async function exportSingleIssue(event: any): Promise<any> {
  const issueKey = event.context?.extension?.issue?.key;
  
  if (!issueKey) {
    return { success: false, error: 'No issue key found' };
  }
  
  try {
    const result = await exportIssueToPdf(issueKey);
    return { 
      success: true, 
      message: `PDF exported successfully for ${issueKey}`,
      ...result 
    };
  } catch (error) {
    console.error('Error in exportSingleIssue:', error);
    return { success: false, error: 'Failed to export PDF' };
  }
}

/**
 * Bulk export handler
 */
export async function exportBulkIssues(event: any): Promise<any> {
  const { issueKeys } = event.payload || {};
  
  if (!issueKeys || !Array.isArray(issueKeys) || issueKeys.length === 0) {
    return { success: false, error: 'No issue keys provided' };
  }
  
  try {
    const results: BulkExportResult = await exportMultipleIssuesToPdf(issueKeys);
    return { 
      success: true, 
      message: `Exported ${results.successful.length} PDFs`,
      results 
    };
  } catch (error) {
    console.error('Error in exportBulkIssues:', error);
    return { success: false, error: 'Failed to export PDFs' };
  }
}

// Export resolver handler för Custom UI
export const handler = resolver.getDefinitions();
