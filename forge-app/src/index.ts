/**
 * Jira PDF Exporter - Forge App
 * Main entry point
 */
import Resolver from '@forge/resolver';
import { exportIssueToPdf, exportMultipleIssuesToPdf, BulkExportResult } from './pdf-exporter';
import { getIssue, searchIssues } from './jira-client';

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
