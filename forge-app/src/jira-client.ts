/**
 * Jira API Client for Forge
 * Uses Forge's built-in API to access Jira data
 */
import api, { route, Route } from '@forge/api';

export interface JiraUser {
  accountId: string;
  displayName: string;
  emailAddress?: string;
  avatarUrls?: Record<string, string>;
}

export interface JiraAttachment {
  id: string;
  filename: string;
  size: number;
  mimeType: string;
  content: string;
  thumbnail?: string;
  created: string;
  author: JiraUser;
}

export interface JiraComment {
  id: string;
  author: JiraUser;
  body: any; // ADF format
  created: string;
  updated?: string;
}

export interface JiraIssue {
  key: string;
  id: string;
  self: string;
  fields: {
    summary: string;
    description: any;
    issuetype: { name: string; iconUrl?: string };
    status: { name: string; statusCategory?: { name: string } };
    priority: { name: string; iconUrl?: string };
    assignee?: JiraUser;
    reporter?: JiraUser;
    created: string;
    updated: string;
    resolutiondate?: string;
    fixVersions?: Array<{ name: string; released?: boolean }>;
    components?: Array<{ name: string }>;
    labels?: string[];
    attachment?: JiraAttachment[];
    comment?: { comments: JiraComment[] };
    subtasks?: Array<{ key: string; fields: { summary: string; status: { name: string } } }>;
    issuelinks?: Array<{
      type: { inward: string; outward: string };
      inwardIssue?: { key: string; fields: { summary: string } };
      outwardIssue?: { key: string; fields: { summary: string } };
    }>;
    parent?: { key: string; fields: { summary: string } };
    [key: string]: any; // Custom fields
  };
}

export interface ParsedIssue {
  key: string;
  id: string;
  summary: string;
  description: string;
  issueType: string;
  status: string;
  statusCategory?: string;
  priority: string;
  assignee?: string;
  reporter?: string;
  created: string;
  updated: string;
  resolved?: string;
  fixVersions: string[];
  components: string[];
  labels: string[];
  storyPoints?: number;
  sprints: string[];
  epic?: string;
  parent?: { key: string; summary: string };
  subtasks: Array<{ key: string; summary: string; status: string }>;
  links: Array<{ type: string; key: string; summary: string }>;
  attachments: JiraAttachment[];
  comments: Array<{ author: string; body: string; created: string }>;
  customFields: Record<string, any>;
}

/**
 * Hämta en issue med alla fält
 */
export async function getIssue(issueKey: string): Promise<ParsedIssue> {
  const response = await api.asApp().requestJira(
    route`/rest/api/3/issue/${issueKey}?expand=renderedFields,names&fields=*all`
  );
  
  if (!response.ok) {
    throw new Error(`Failed to fetch issue: ${response.status}`);
  }
  
  const data: JiraIssue = await response.json();
  
  // Hämta fältnamn för bättre visning
  let fieldNames: Record<string, string> = {};
  try {
    fieldNames = await getFieldNames();
  } catch (e) {
    console.log('Could not fetch field names, using raw keys');
  }
  
  return parseIssueWithFieldNames(data, fieldNames);
}

/**
 * Sök efter issues med JQL (POST /rest/api/3/search/jql)
 */
export async function searchIssues(jql: string, maxResults: number = 50): Promise<ParsedIssue[]> {
  const issues: ParsedIssue[] = [];
  let startAt = 0;
  
  while (issues.length < maxResults) {
    const batchSize = Math.min(50, maxResults - issues.length);
    
    // Bygg request body enligt Atlassian migration guide
    const requestBody = {
      jql,
      maxResults: batchSize,
      startAt,
      fields: [
        'summary',
        'description', 
        'issuetype',
        'status',
        'priority',
        'assignee',
        'reporter',
        'created',
        'updated',
        'resolutiondate',
        'fixVersions',
        'components',
        'labels',
        'attachment',
        'comment',
        'subtasks',
        'issuelinks',
        'parent'
      ]
    };
    
    console.log('Sending search request:', JSON.stringify(requestBody, null, 2));
    
    // Använd asUser() för att köra med användarens behörigheter
    const response = await api.asUser().requestJira(route`/rest/api/3/search/jql`, {
      method: 'POST',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(requestBody)
    });
    
    console.log('Response status:', response.status);
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error('Search API error:', response.status, errorText);
      throw new Error(`Failed to search issues: ${response.status} - ${errorText}`);
    }
    
    const data = await response.json();
    console.log('Found issues:', data.issues?.length || 0, 'of', data.total);
    
    for (const issue of data.issues || []) {
      issues.push(parseIssue(issue));
    }
    
    if (!data.issues || data.issues.length === 0 || issues.length >= data.total) {
      break;
    }
    
    startAt += data.issues.length;
  }
  
  return issues;
}

/**
 * Ladda ner en bilaga via attachment ID
 * Använder /rest/api/3/attachment/content/{id} med rätt redirect-hantering
 */
export async function downloadAttachment(attachmentId: string): Promise<ArrayBuffer> {
  console.log('Downloading attachment ID:', attachmentId);
  
  // Först hämta attachment metadata för att få content URL
  const metaResponse = await api.asApp().requestJira(route`/rest/api/3/attachment/${attachmentId}`);
  
  if (!metaResponse.ok) {
    console.error('Failed to get attachment metadata:', metaResponse.status);
    throw new Error(`Failed to get attachment metadata: ${metaResponse.status}`);
  }
  
  const metadata = await metaResponse.json();
  console.log('Attachment metadata:', metadata.filename, 'mimeType:', metadata.mimeType);
  
  // Använd content URL direkt med media API
  // Forge kräver att vi använder requestJira för alla Jira-anrop
  const contentResponse = await api.asApp().requestJira(route`/rest/api/3/attachment/content/${attachmentId}`, {
    headers: { 
      'Accept': metadata.mimeType || 'image/png'
    }
  });
  
  console.log('Content response status:', contentResponse.status);
  
  if (!contentResponse.ok) {
    // Försök med thumbnail istället
    console.log('Trying thumbnail...');
    const thumbResponse = await api.asApp().requestJira(route`/rest/api/3/attachment/thumbnail/${attachmentId}`, {
      headers: { 
        'Accept': 'image/png'
      }
    });
    
    console.log('Thumbnail response status:', thumbResponse.status);
    
    if (!thumbResponse.ok) {
      throw new Error(`Failed to download attachment: ${contentResponse.status}`);
    }
    
    return thumbResponse.arrayBuffer();
  }
  
  return contentResponse.arrayBuffer();
}

/**
 * Hämta fältnamn för custom fields
 */
export async function getFieldNames(): Promise<Record<string, string>> {
  const response = await api.asApp().requestJira(route`/rest/api/3/field`);
  
  if (!response.ok) {
    throw new Error(`Failed to fetch fields: ${response.status}`);
  }
  
  const fields = await response.json();
  const fieldMap: Record<string, string> = {};
  
  for (const field of fields) {
    fieldMap[field.id] = field.name;
  }
  
  return fieldMap;
}

/**
 * Parsa en Jira issue till strukturerad data
 */
function parseIssue(data: JiraIssue): ParsedIssue {
  return parseIssueWithFieldNames(data, {});
}

/**
 * Parsa en Jira issue med fältnamn
 */
function parseIssueWithFieldNames(data: JiraIssue, fieldNames: Record<string, string>): ParsedIssue {
  const fields = data.fields;
  
  // Extrahera custom fields med läsbara namn
  const customFields: Record<string, any> = {};
  const skipPatterns = ['sprint', 'story point', 'epic', 'rank', 'flagged', 'development', 'team', 'color', 'change'];
  
  for (const [key, value] of Object.entries(fields)) {
    if (!key.startsWith('customfield_') || value === null || value === undefined) continue;
    
    // Hämta läsbart fältnamn
    const fieldName = fieldNames[key] || key;
    const fieldNameLower = fieldName.toLowerCase();
    
    // Hoppa över system-/irrelevanta fält
    if (skipPatterns.some(p => fieldNameLower.includes(p))) continue;
    
    // Formatera värdet
    let formattedValue: any = null;
    
    if (typeof value === 'string') {
      if (value.trim()) formattedValue = value;
    } else if (typeof value === 'number') {
      formattedValue = String(value);
    } else if (typeof value === 'object') {
      if (Array.isArray(value)) {
        const items = value.map(v => {
          if (typeof v === 'string') return v;
          if (typeof v === 'object' && v !== null) {
            return v.value || v.name || v.displayName || '';
          }
          return String(v);
        }).filter(s => s);
        if (items.length) formattedValue = items.join(', ');
      } else if (value.type === 'doc') {
        formattedValue = extractText(value);
      } else if ('value' in value) {
        formattedValue = value.value;
      } else if ('name' in value) {
        formattedValue = value.name;
      } else if ('displayName' in value) {
        formattedValue = value.displayName;
      } else if ('content' in value) {
        formattedValue = extractText(value);
      }
    }
    
    if (formattedValue !== null && formattedValue !== '' && formattedValue !== undefined) {
      customFields[fieldName] = formattedValue;
    }
  }
  
  return {
    key: data.key,
    id: data.id,
    summary: fields.summary || '',
    description: extractText(fields.description),
    issueType: fields.issuetype?.name || 'Unknown',
    status: fields.status?.name || 'Unknown',
    statusCategory: fields.status?.statusCategory?.name,
    priority: fields.priority?.name || 'None',
    assignee: fields.assignee?.displayName,
    reporter: fields.reporter?.displayName,
    created: fields.created,
    updated: fields.updated,
    resolved: fields.resolutiondate,
    fixVersions: (fields.fixVersions || []).map(v => v.name),
    components: (fields.components || []).map(c => c.name),
    labels: fields.labels || [],
    storyPoints: findCustomField(fields, 'story points', 'story point'),
    sprints: extractSprints(fields),
    epic: findCustomField(fields, 'epic'),
    parent: fields.parent ? {
      key: fields.parent.key,
      summary: fields.parent.fields?.summary || ''
    } : undefined,
    subtasks: (fields.subtasks || []).map(st => ({
      key: st.key,
      summary: st.fields?.summary || '',
      status: st.fields?.status?.name || 'Unknown'
    })),
    links: parseIssueLinks(fields.issuelinks || []),
    attachments: fields.attachment || [],
    comments: (fields.comment?.comments || []).map(c => ({
      author: c.author?.displayName || 'Unknown',
      body: extractText(c.body),
      created: c.created
    })),
    customFields
  };
}

/**
 * Extrahera text från ADF (Atlassian Document Format)
 */
function extractText(content: any): string {
  if (!content) return '';
  if (typeof content === 'string') return content;
  if (content.type !== 'doc') return String(content);
  
  return parseAdfContent(content.content || []);
}

function parseAdfContent(nodes: any[]): string {
  const result: string[] = [];
  
  for (const node of nodes) {
    switch (node.type) {
      case 'text':
        result.push(node.text || '');
        break;
      case 'paragraph':
        result.push(parseAdfContent(node.content || []) + '\n');
        break;
      case 'heading':
        const level = node.attrs?.level || 1;
        result.push('\n' + '#'.repeat(level) + ' ' + parseAdfContent(node.content || []) + '\n');
        break;
      case 'bulletList':
        for (const item of node.content || []) {
          result.push('• ' + parseAdfContent(item.content || []).trim() + '\n');
        }
        break;
      case 'orderedList':
        let i = 1;
        for (const item of node.content || []) {
          result.push(`${i++}. ` + parseAdfContent(item.content || []).trim() + '\n');
        }
        break;
      case 'listItem':
        result.push(parseAdfContent(node.content || []));
        break;
      case 'codeBlock':
        result.push('\n```\n' + parseAdfContent(node.content || []) + '\n```\n');
        break;
      case 'hardBreak':
        result.push('\n');
        break;
      case 'mention':
        result.push('@' + (node.attrs?.text || 'user'));
        break;
      default:
        if (node.content) {
          result.push(parseAdfContent(node.content));
        }
    }
  }
  
  return result.join('');
}

/**
 * Hitta custom field baserat på namn
 */
function findCustomField(fields: Record<string, any>, ...searchTerms: string[]): any {
  for (const [key, value] of Object.entries(fields)) {
    if (!key.startsWith('customfield_') || value === null) continue;
    
    const valueStr = JSON.stringify(value).toLowerCase();
    for (const term of searchTerms) {
      if (valueStr.includes(term.toLowerCase())) {
        if (typeof value === 'object' && value !== null) {
          return value.value || value.name || value;
        }
        return value;
      }
    }
  }
  return undefined;
}

/**
 * Extrahera sprint-information
 */
function extractSprints(fields: Record<string, any>): string[] {
  const sprints: string[] = [];
  
  for (const [key, value] of Object.entries(fields)) {
    if (!key.startsWith('customfield_') || !Array.isArray(value)) continue;
    
    for (const item of value) {
      if (item && typeof item === 'object' && 'name' in item) {
        if (item.name?.toLowerCase().includes('sprint') || key.toLowerCase().includes('sprint')) {
          sprints.push(item.name);
        }
      }
    }
  }
  
  return sprints;
}

/**
 * Parsa issue-länkar
 */
function parseIssueLinks(links: any[]): Array<{ type: string; key: string; summary: string }> {
  const parsed: Array<{ type: string; key: string; summary: string }> = [];
  
  for (const link of links) {
    if (link.outwardIssue) {
      parsed.push({
        type: link.type?.outward || 'relates to',
        key: link.outwardIssue.key,
        summary: link.outwardIssue.fields?.summary || ''
      });
    }
    if (link.inwardIssue) {
      parsed.push({
        type: link.type?.inward || 'relates to',
        key: link.inwardIssue.key,
        summary: link.inwardIssue.fields?.summary || ''
      });
    }
  }
  
  return parsed;
}

/**
 * Extrahera alla custom fields med deras namn
 */
async function extractCustomFieldsWithNames(fields: Record<string, any>): Promise<Record<string, any>> {
  const customFields: Record<string, any> = {};
  const skipPatterns = ['sprint', 'story point', 'epic', 'rank', 'flagged', 'development', 'team'];
  
  // Hämta fältnamn
  let fieldNames: Record<string, string> = {};
  try {
    fieldNames = await getFieldNames();
  } catch (e) {
    console.log('Could not fetch field names');
  }
  
  for (const [key, value] of Object.entries(fields)) {
    if (!key.startsWith('customfield_') || value === null || value === undefined) continue;
    
    // Hämta fältnamn
    const fieldName = fieldNames[key] || key;
    const fieldNameLower = fieldName.toLowerCase();
    
    // Hoppa över redan hanterade fält
    if (skipPatterns.some(p => fieldNameLower.includes(p))) continue;
    
    // Formatera värdet
    let formattedValue: any = null;
    
    if (typeof value === 'string') {
      formattedValue = value;
    } else if (typeof value === 'number') {
      formattedValue = value;
    } else if (typeof value === 'object') {
      if (Array.isArray(value)) {
        formattedValue = value.map(v => 
          typeof v === 'object' ? (v.value || v.name || v.displayName || JSON.stringify(v)) : String(v)
        ).join(', ');
      } else if ('value' in value) {
        formattedValue = value.value;
      } else if ('name' in value) {
        formattedValue = value.name;
      } else if ('displayName' in value) {
        formattedValue = value.displayName;
      } else if ('content' in value) {
        formattedValue = extractText(value);
      } else if (value.type === 'doc') {
        formattedValue = extractText(value);
      }
    }
    
    if (formattedValue !== null && formattedValue !== '' && formattedValue !== undefined) {
      customFields[fieldName] = formattedValue;
    }
  }
  
  return customFields;
}

/**
 * Extrahera alla custom fields (sync version)
 */
function extractCustomFields(fields: Record<string, any>): Record<string, any> {
  const customFields: Record<string, any> = {};
  const skipPatterns = ['sprint', 'story point', 'epic', 'rank', 'flagged', 'development', 'team'];
  
  for (const [key, value] of Object.entries(fields)) {
    if (!key.startsWith('customfield_') || value === null || value === undefined) continue;
    
    // Hoppa över redan hanterade fält baserat på innehåll
    const valueStr = JSON.stringify(value).toLowerCase();
    if (skipPatterns.some(p => valueStr.includes(p))) continue;
    
    // Formatera värdet
    let formattedValue: any = null;
    
    if (typeof value === 'string') {
      formattedValue = value;
    } else if (typeof value === 'number') {
      formattedValue = value;
    } else if (typeof value === 'object') {
      if (Array.isArray(value)) {
        formattedValue = value.map(v => 
          typeof v === 'object' ? (v.value || v.name || v.displayName || JSON.stringify(v)) : String(v)
        ).join(', ');
      } else if ('value' in value) {
        formattedValue = value.value;
      } else if ('name' in value) {
        formattedValue = value.name;
      } else if ('displayName' in value) {
        formattedValue = value.displayName;
      } else if ('content' in value) {
        formattedValue = extractText(value);
      } else if (value.type === 'doc') {
        formattedValue = extractText(value);
      }
    }
    
    if (formattedValue !== null && formattedValue !== '' && formattedValue !== undefined) {
      customFields[key] = formattedValue;
    }
  }
  
  return customFields;
}
