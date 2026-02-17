"""
Jira API-klient för att hämta tickets och bilagor
Uppdaterad för Jira API v3
"""
import os
import requests
from typing import Dict, List, Any, Optional
from config import Config


class JiraClient:
    """Klient för Jira API v3-interaktion"""
    
    def __init__(self, jira_url: str = None, email: str = None, api_token: str = None):
        """
        Initiera Jira-klienten
        
        Args:
            jira_url: Jira URL (default: från Config)
            email: Jira email (default: från Config)
            api_token: Jira API token (default: från Config)
        """
        self.base_url = (jira_url or Config.JIRA_URL).rstrip('/')
        self.session = requests.Session()
        self.session.auth = (email or Config.JIRA_EMAIL, api_token or Config.JIRA_API_TOKEN)
        self.session.headers.update({
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        
        # Cache för fältnamn
        self._field_names = None
    
    def _get(self, endpoint: str, params: dict = None) -> dict:
        """Gör GET-request till Jira API"""
        url = f"{self.base_url}/rest/api/3/{endpoint}"
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    def _get_field_names(self) -> Dict[str, str]:
        """Hämta mappning av fält-ID till namn"""
        if self._field_names is None:
            fields = self._get('field')
            self._field_names = {f['id']: f['name'] for f in fields}
        return self._field_names
    
    def get_issue(self, issue_key: str) -> Dict[str, Any]:
        """
        Hämta en specifik issue med alla fält
        
        Args:
            issue_key: Jira issue-nyckel (t.ex. SOMU-31)
            
        Returns:
            Dictionary med all issue-data
        """
        data = self._get(f'issue/{issue_key}', params={
            'expand': 'renderedFields,names,changelog',
            'fields': '*all'
        })
        return self._parse_issue(data)
    
    def get_issues_by_jql(self, jql: str, max_results: int = 100) -> List[Dict[str, Any]]:
        """
        Hämta issues baserat på JQL-query
        
        Args:
            jql: JQL-sökfråga
            max_results: Max antal resultat
            
        Returns:
            Lista med issue-data
        """
        issues = []
        next_page_token = None
        
        while len(issues) < max_results:
            params = {
                'jql': jql,
                'maxResults': min(50, max_results - len(issues)),
                'fields': '*all'
            }
            if next_page_token:
                params['nextPageToken'] = next_page_token
            
            data = self._get('search/jql', params=params)
            
            # Hämta fullständig data för varje issue
            for issue_stub in data.get('issues', []):
                issue_id = issue_stub.get('id')
                if issue_id:
                    try:
                        full_issue = self._get(f'issue/{issue_id}', params={
                            'expand': 'renderedFields,names,changelog',
                            'fields': '*all'
                        })
                        issues.append(self._parse_issue(full_issue))
                    except Exception as e:
                        print(f"⚠️  Kunde inte hämta issue {issue_id}: {e}")
            
            # Kolla om det finns fler sidor
            next_page_token = data.get('nextPageToken')
            if data.get('isLast', True) or not next_page_token:
                break
        
        return issues
    
    def get_project_issues(self, project_key: str, issue_type: str = None) -> List[Dict[str, Any]]:
        """
        Hämta alla issues för ett projekt
        
        Args:
            project_key: Projektets nyckel
            issue_type: Filtrera på issue-typ (t.ex. "Story", "Bug")
            
        Returns:
            Lista med issue-data
        """
        jql = f'project = {project_key}'
        if issue_type:
            jql += f' AND issuetype = "{issue_type}"'
        jql += ' ORDER BY key DESC'
        
        return self.get_issues_by_jql(jql)
    
    def _parse_issue(self, data: dict) -> Dict[str, Any]:
        """
        Parsa en Jira-issue till en strukturerad dictionary
        
        Args:
            data: Rå issue-data från API
            
        Returns:
            Strukturerad dictionary med issue-data
        """
        fields = data.get('fields', {})
        
        # Grundläggande fält
        issue_data = {
            'key': data.get('key'),
            'id': data.get('id'),
            'self': data.get('self'),
            'summary': fields.get('summary', ''),
            'description': self._extract_text(fields.get('description')),
            'rendered_description': '',
            'issue_type': {
                'name': fields.get('issuetype', {}).get('name', 'Unknown') if fields.get('issuetype') else 'Unknown',
                'icon_url': fields.get('issuetype', {}).get('iconUrl') if fields.get('issuetype') else None
            },
            'status': {
                'name': fields.get('status', {}).get('name', 'Unknown') if fields.get('status') else 'Unknown',
                'category': fields.get('status', {}).get('statusCategory', {}).get('name') if fields.get('status') else None
            },
            'priority': {
                'name': fields.get('priority', {}).get('name', 'None') if fields.get('priority') else 'None',
                'icon_url': fields.get('priority', {}).get('iconUrl') if fields.get('priority') else None
            },
            'created': fields.get('created'),
            'updated': fields.get('updated'),
            'resolved': fields.get('resolutiondate'),
        }
        
        # Tilldelning och rapportör
        issue_data['assignee'] = self._parse_user(fields.get('assignee'))
        issue_data['reporter'] = self._parse_user(fields.get('reporter'))
        
        # Story Points (vanliga custom field-namn)
        issue_data['story_points'] = self._find_custom_field(fields, 
            ['story points', 'storypoints', 'story point estimate'])
        
        # Fix versions
        issue_data['fix_versions'] = [
            {'name': v.get('name', ''), 'released': v.get('released', False)}
            for v in (fields.get('fixVersions') or [])
        ]
        
        # Components
        issue_data['components'] = [c.get('name', '') for c in (fields.get('components') or [])]
        
        # Labels
        issue_data['labels'] = fields.get('labels') or []
        
        # Sprint information
        issue_data['sprints'] = self._extract_sprints(fields)
        
        # Epic link
        issue_data['epic'] = self._find_custom_field(fields, ['epic link', 'epic name', 'parent epic'])
        
        # Parent (för subtasks)
        parent = fields.get('parent')
        issue_data['parent'] = {
            'key': parent.get('key'),
            'summary': parent.get('fields', {}).get('summary', '')
        } if parent else None
        
        # Subtasks
        issue_data['subtasks'] = [
            {
                'key': st.get('key'),
                'summary': st.get('fields', {}).get('summary', ''),
                'status': st.get('fields', {}).get('status', {}).get('name', 'Unknown')
            }
            for st in (fields.get('subtasks') or [])
        ]
        
        # Länkade issues
        issue_data['links'] = self._parse_issue_links(fields.get('issuelinks') or [])
        
        # Bilagor
        issue_data['attachments'] = [
            {
                'id': att.get('id'),
                'filename': att.get('filename'),
                'size': att.get('size', 0),
                'mime_type': att.get('mimeType', ''),
                'content_url': att.get('content'),
                'thumbnail_url': att.get('thumbnail'),
                'created': att.get('created'),
                'author': att.get('author', {}).get('displayName', 'Unknown') if att.get('author') else 'Unknown'
            }
            for att in (fields.get('attachment') or [])
        ]
        
        # Kommentarer
        comment_data = fields.get('comment', {})
        comments = comment_data.get('comments', []) if isinstance(comment_data, dict) else []
        issue_data['comments'] = [
            {
                'id': comment.get('id'),
                'author': comment.get('author', {}).get('displayName', 'Unknown') if comment.get('author') else 'Unknown',
                'body': self._extract_text(comment.get('body')),
                'created': comment.get('created'),
                'updated': comment.get('updated')
            }
            for comment in comments
        ]
        
        # Alla custom fields
        issue_data['custom_fields'] = self._get_all_custom_fields(fields)
        
        return issue_data
    
    def _extract_text(self, content) -> str:
        """Extrahera text från Atlassian Document Format (ADF)"""
        if content is None:
            return ''
        if isinstance(content, str):
            return content
        if not isinstance(content, dict):
            return str(content)
        
        # ADF-format
        if content.get('type') == 'doc':
            return self._parse_adf_content(content.get('content', []))
        
        return str(content)
    
    def _parse_adf_content(self, content_list: list) -> str:
        """Parsa ADF content till text"""
        result = []
        
        for node in content_list:
            node_type = node.get('type', '')
            
            if node_type == 'text':
                result.append(node.get('text', ''))
            
            elif node_type == 'paragraph':
                para_text = self._parse_adf_content(node.get('content', []))
                result.append(para_text + '\n')
            
            elif node_type == 'heading':
                heading_text = self._parse_adf_content(node.get('content', []))
                level = node.get('attrs', {}).get('level', 1)
                result.append(f"\n{'#' * level} {heading_text}\n")
            
            elif node_type == 'bulletList':
                for item in node.get('content', []):
                    item_text = self._parse_adf_content(item.get('content', []))
                    result.append(f"* {item_text.strip()}\n")
            
            elif node_type == 'orderedList':
                for i, item in enumerate(node.get('content', []), 1):
                    item_text = self._parse_adf_content(item.get('content', []))
                    result.append(f"{i}. {item_text.strip()}\n")
            
            elif node_type == 'listItem':
                result.append(self._parse_adf_content(node.get('content', [])))
            
            elif node_type == 'codeBlock':
                code_text = self._parse_adf_content(node.get('content', []))
                result.append(f"\n```\n{code_text}\n```\n")
            
            elif node_type == 'blockquote':
                quote_text = self._parse_adf_content(node.get('content', []))
                result.append(f"> {quote_text}")
            
            elif node_type == 'hardBreak':
                result.append('\n')
            
            elif node_type == 'mention':
                result.append(f"@{node.get('attrs', {}).get('text', 'user')}")
            
            elif node_type == 'emoji':
                result.append(node.get('attrs', {}).get('text', ''))
            
            elif node_type == 'inlineCard' or node_type == 'blockCard':
                url = node.get('attrs', {}).get('url', '')
                result.append(f"[{url}]")
            
            elif node_type == 'mediaGroup' or node_type == 'mediaSingle':
                result.append('[Media]')
            
            elif 'content' in node:
                result.append(self._parse_adf_content(node.get('content', [])))
        
        return ''.join(result)
    
    def _parse_user(self, user: dict) -> Optional[Dict[str, str]]:
        """Parsa användarinformation"""
        if not user:
            return None
        return {
            'name': user.get('displayName', 'Unknown'),
            'email': user.get('emailAddress'),
            'avatar_url': user.get('avatarUrls', {}).get('48x48') if user.get('avatarUrls') else None
        }
    
    def _find_custom_field(self, fields: dict, search_terms: list) -> Any:
        """Sök efter custom field baserat på namn"""
        field_names = self._get_field_names()
        
        for field_id, field_name in field_names.items():
            if field_id in fields and fields[field_id] is not None:
                field_name_lower = field_name.lower()
                for term in search_terms:
                    if term.lower() in field_name_lower:
                        value = fields[field_id]
                        # Hantera olika typer av värden
                        if isinstance(value, dict):
                            return value.get('value') or value.get('name') or value
                        return value
        return None
    
    def _extract_sprints(self, fields: dict) -> List[Dict[str, Any]]:
        """Extrahera sprint-information"""
        sprints = []
        field_names = self._get_field_names()
        
        for field_id, field_name in field_names.items():
            if 'sprint' in field_name.lower() and field_id in fields:
                value = fields[field_id]
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            sprints.append({
                                'name': item.get('name', 'Unknown'),
                                'state': item.get('state', 'unknown')
                            })
                        elif isinstance(item, str):
                            sprints.append({'name': item, 'state': 'unknown'})
        return sprints
    
    def _parse_issue_links(self, links: list) -> List[Dict[str, Any]]:
        """Parsa issue-länkar"""
        parsed_links = []
        for link in links:
            link_type = link.get('type', {})
            
            if link.get('outwardIssue'):
                outward = link['outwardIssue']
                parsed_links.append({
                    'type': link_type.get('outward', 'relates to'),
                    'key': outward.get('key'),
                    'summary': outward.get('fields', {}).get('summary', '')
                })
            
            if link.get('inwardIssue'):
                inward = link['inwardIssue']
                parsed_links.append({
                    'type': link_type.get('inward', 'relates to'),
                    'key': inward.get('key'),
                    'summary': inward.get('fields', {}).get('summary', '')
                })
        
        return parsed_links
    
    def _get_all_custom_fields(self, fields: dict) -> Dict[str, Any]:
        """Hämta alla custom fields med deras namn"""
        custom_fields = {}
        field_names = self._get_field_names()
        
        # Fält att hoppa över (redan hanterade)
        skip_patterns = ['story point', 'sprint', 'epic', 'rank', 'flagged', 
                        'development', 'team', 'change reason']
        
        for field_id, value in fields.items():
            if not field_id.startswith('customfield_'):
                continue
            if value is None:
                continue
            
            field_name = field_names.get(field_id, field_id)
            
            # Hoppa över redan hanterade fält
            if any(pattern in field_name.lower() for pattern in skip_patterns):
                continue
            
            # Hantera olika typer av värden
            if isinstance(value, dict):
                if 'value' in value:
                    custom_fields[field_name] = value['value']
                elif 'name' in value:
                    custom_fields[field_name] = value['name']
                elif 'displayName' in value:
                    custom_fields[field_name] = value['displayName']
                elif 'content' in value:  # ADF
                    custom_fields[field_name] = self._extract_text(value)
                else:
                    custom_fields[field_name] = str(value)
            elif isinstance(value, list):
                if value:
                    items = []
                    for v in value:
                        if isinstance(v, dict):
                            items.append(v.get('value') or v.get('name') or str(v))
                        else:
                            items.append(str(v))
                    custom_fields[field_name] = items
            else:
                custom_fields[field_name] = value
        
        return custom_fields
    
    def download_attachment(self, attachment: Dict[str, Any], output_dir: str) -> Optional[str]:
        """
        Ladda ner en bilaga
        
        Args:
            attachment: Attachment-dictionary från parsed issue
            output_dir: Mapp att spara filen i
            
        Returns:
            Sökväg till nedladdad fil eller None vid fel
        """
        os.makedirs(output_dir, exist_ok=True)
        
        try:
            response = self.session.get(attachment['content_url'])
            response.raise_for_status()
            
            filepath = os.path.join(output_dir, attachment['filename'])
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            return filepath
        except Exception as e:
            print(f"⚠️  Kunde inte ladda ner {attachment['filename']}: {e}")
            return None
    
    def download_all_attachments(self, issue_data: Dict[str, Any], output_dir: str) -> List[str]:
        """
        Ladda ner alla bilagor för en issue
        
        Args:
            issue_data: Parsed issue-data
            output_dir: Mapp att spara filerna i
            
        Returns:
            Lista med sökvägar till nedladdade filer
        """
        downloaded = []
        for attachment in issue_data.get('attachments', []):
            filepath = self.download_attachment(attachment, output_dir)
            if filepath:
                downloaded.append(filepath)
        return downloaded
