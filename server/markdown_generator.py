"""
Markdown-generator för Jira-tickets
Skapar AI-optimerade Markdown-dokument för GPT/sökning
"""
import os
import re
from typing import Dict, Any, List
from datetime import datetime


class MarkdownGenerator:
    """Genererar Markdown-dokument från Jira-data, optimerat för AI/GPT"""
    
    def __init__(self, output_dir: str = None, images_dir: str = None):
        """
        Initiera Markdown-generatorn
        
        Args:
            output_dir: Mapp för exporterade Markdown-filer
            images_dir: Mapp för bilder (relativt output_dir)
        """
        self.output_dir = output_dir or 'exports'
        self.images_dir = images_dir or 'images'
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(os.path.join(self.output_dir, self.images_dir), exist_ok=True)
    
    def generate_markdown(self, issue_data: Dict[str, Any], 
                          attachment_paths: List[str] = None) -> str:
        """
        Generera Markdown för en Jira-issue
        
        Args:
            issue_data: Parsad issue-data från JiraClient
            attachment_paths: Lista med sökvägar till nedladdade bilagor
            
        Returns:
            Sökväg till genererad Markdown-fil
        """
        issue_key = issue_data['key']
        filename = f"{issue_key}.md"
        filepath = os.path.join(self.output_dir, filename)
        
        md_content = self._build_markdown(issue_data, attachment_paths)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        return filepath
    
    def _build_markdown(self, issue_data: Dict[str, Any], 
                        attachment_paths: List[str] = None) -> str:
        """Bygg Markdown-innehåll"""
        lines = []
        
        # Frontmatter (YAML) för metadata - bra för AI-indexering
        lines.append('---')
        lines.append(f'issue_key: {issue_data["key"]}')
        lines.append(f'type: {issue_data["issue_type"]["name"]}')
        lines.append(f'status: {issue_data["status"]["name"]}')
        lines.append(f'priority: {issue_data["priority"]["name"]}')
        if issue_data.get('assignee'):
            lines.append(f'assignee: {issue_data["assignee"]["name"]}')
        if issue_data.get('labels'):
            lines.append(f'labels: [{", ".join(issue_data["labels"])}]')
        if issue_data.get('components'):
            lines.append(f'components: [{", ".join(issue_data["components"])}]')
        lines.append(f'created: {self._format_date(issue_data.get("created"))}')
        lines.append(f'updated: {self._format_date(issue_data.get("updated"))}')
        lines.append('---')
        lines.append('')
        
        # Huvudrubrik
        lines.append(f'# {issue_data["key"]} – {issue_data["summary"]}')
        lines.append('')
        
        # Quick info (för snabb scanning)
        lines.append('## Översikt')
        lines.append('')
        lines.append(f'| Fält | Värde |')
        lines.append(f'|------|-------|')
        lines.append(f'| **Typ** | {issue_data["issue_type"]["name"]} |')
        lines.append(f'| **Status** | {issue_data["status"]["name"]} |')
        lines.append(f'| **Prioritet** | {issue_data["priority"]["name"]} |')
        
        if issue_data.get('assignee'):
            lines.append(f'| **Tilldelad** | {issue_data["assignee"]["name"]} |')
        if issue_data.get('reporter'):
            lines.append(f'| **Rapportör** | {issue_data["reporter"]["name"]} |')
        if issue_data.get('story_points'):
            lines.append(f'| **Story Points** | {issue_data["story_points"]} |')
        if issue_data.get('epic'):
            lines.append(f'| **Epic** | {issue_data["epic"]} |')
        if issue_data.get('sprints'):
            sprint_names = [s['name'] for s in issue_data['sprints']]
            lines.append(f'| **Sprint** | {", ".join(sprint_names)} |')
        
        lines.append('')
        
        # Beskrivning
        description = issue_data.get('description', '')
        if description:
            lines.append('## Beskrivning')
            lines.append('')
            lines.append(self._clean_text(description))
            lines.append('')
        
        # Custom fields (viktigt för AI-sökning)
        custom_fields = issue_data.get('custom_fields', {})
        if custom_fields:
            # Filtrera bort redan visade fält
            skip_patterns = ['story point', 'sprint', 'epic', 'rank', 'flagged']
            filtered = {}
            for name, value in custom_fields.items():
                if any(p in name.lower() for p in skip_patterns):
                    continue
                if value is None or value == '' or value == []:
                    continue
                if isinstance(value, list):
                    value = ', '.join(str(v) for v in value)
                filtered[name] = value
            
            if filtered:
                lines.append('## Ytterligare information')
                lines.append('')
                for name, value in filtered.items():
                    lines.append(f'### {name}')
                    lines.append('')
                    lines.append(str(value))
                    lines.append('')
        
        # Labels (viktigt för kategorisering)
        if issue_data.get('labels'):
            lines.append('## Etiketter')
            lines.append('')
            lines.append(' '.join([f'`{label}`' for label in issue_data['labels']]))
            lines.append('')
        
        # Komponenter
        if issue_data.get('components'):
            lines.append('## Komponenter')
            lines.append('')
            lines.append(' '.join([f'`{comp}`' for comp in issue_data['components']]))
            lines.append('')
        
        # Subtasks
        subtasks = issue_data.get('subtasks', [])
        if subtasks:
            lines.append('## Underuppgifter')
            lines.append('')
            for st in subtasks:
                status_icon = '✅' if st['status'].lower() in ['done', 'closed'] else '⬜'
                lines.append(f'- {status_icon} **{st["key"]}**: {st["summary"]} ({st["status"]})')
            lines.append('')
        
        # Länkade issues
        links = issue_data.get('links', [])
        if links:
            lines.append('## Relaterade ärenden')
            lines.append('')
            for link in links:
                lines.append(f'- {link["type"]} **{link["key"]}**: {link["summary"]}')
            lines.append('')
        
        # Bilagor och bilder
        attachments = issue_data.get('attachments', [])
        if attachments:
            lines.append('## Bilagor & Skärmbilder')
            lines.append('')
            
            # Skapa mappning av filnamn till sökvägar
            path_map = {}
            if attachment_paths:
                for path in attachment_paths:
                    filename = os.path.basename(path)
                    path_map[filename] = path
            
            image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}
            
            for att in attachments:
                filename = att['filename']
                file_ext = os.path.splitext(filename)[1].lower()
                
                if file_ext in image_extensions:
                    # Bild - visa inline
                    image_path = f'{self.images_dir}/{issue_data["key"]}-{filename}'
                    lines.append(f'### {filename}')
                    lines.append('')
                    lines.append(f'![{filename}]({image_path})')
                    lines.append('')
                else:
                    # Annan fil
                    size_kb = att['size'] / 1024
                    size_str = f"{size_kb:.1f} KB" if size_kb < 1024 else f"{size_kb/1024:.1f} MB"
                    lines.append(f'- 📎 **{filename}** ({size_str})')
            
            lines.append('')
        
        # Kommentarer (värdefulla för kontext)
        comments = issue_data.get('comments', [])
        if comments:
            lines.append('## Kommentarer')
            lines.append('')
            for comment in comments:
                date_str = self._format_date(comment['created'])
                lines.append(f'### {comment["author"]} ({date_str})')
                lines.append('')
                lines.append(self._clean_text(comment['body']))
                lines.append('')
        
        # Footer med metadata
        lines.append('---')
        lines.append('')
        lines.append(f'*Exporterad: {datetime.now().strftime("%Y-%m-%d %H:%M")}*')
        lines.append('')
        
        return '\n'.join(lines)
    
    def _clean_text(self, text: str) -> str:
        """Rensa och formatera text för Markdown"""
        if not text:
            return ''
        
        # Ta bort Jira-specifik markup
        patterns = [
            (r'\{code[^}]*\}(.*?)\{code\}', r'```\n\1\n```'),  # Kodblock
            (r'\{noformat\}(.*?)\{noformat\}', r'```\n\1\n```'),  # Noformat
            (r'\{color[^}]*\}(.*?)\{color\}', r'\1'),  # Färger
            (r'\{panel[^}]*\}(.*?)\{panel\}', r'\1'),  # Paneler
            (r'h1\.\s*(.+)', r'# \1'),  # Rubriker
            (r'h2\.\s*(.+)', r'## \1'),
            (r'h3\.\s*(.+)', r'### \1'),
            (r'h4\.\s*(.+)', r'#### \1'),
            (r'h5\.\s*(.+)', r'##### \1'),
            (r'h6\.\s*(.+)', r'###### \1'),
            (r'\[([^\]|]+)\|([^\]]+)\]', r'[\1](\2)'),  # Länkar
            (r'\*([^*]+)\*', r'**\1**'),  # Fetstil
            (r'_([^_]+)_', r'*\1*'),  # Kursiv
            (r'\+([^+]+)\+', r'<u>\1</u>'),  # Understruken
            (r'\-([^-]+)\-', r'~~\1~~'),  # Genomstruken
            (r'\{\{([^}]+)\}\}', r'`\1`'),  # Monospace
            (r'bq\.\s*(.+)', r'> \1'),  # Blockcitat
        ]
        
        result = text
        for pattern, replacement in patterns:
            try:
                result = re.sub(pattern, replacement, result, flags=re.DOTALL)
            except:
                pass
        
        return result.strip()
    
    def _format_date(self, date_str: str) -> str:
        """Formatera datum"""
        if not date_str:
            return 'N/A'
        
        try:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d %H:%M')
        except (ValueError, AttributeError):
            return str(date_str)[:19]
    
    def generate_index(self, issues: List[Dict[str, Any]]) -> str:
        """
        Generera en index-fil för alla issues (bra för GPT-navigering)
        
        Args:
            issues: Lista med issue-data
            
        Returns:
            Sökväg till index-fil
        """
        filepath = os.path.join(self.output_dir, 'INDEX.md')
        
        lines = []
        lines.append('# Funktionskatalog')
        lines.append('')
        lines.append(f'*Genererad: {datetime.now().strftime("%Y-%m-%d %H:%M")}*')
        lines.append(f'*Antal issues: {len(issues)}*')
        lines.append('')
        
        # Gruppera efter typ
        by_type = {}
        for issue in issues:
            issue_type = issue['issue_type']['name']
            if issue_type not in by_type:
                by_type[issue_type] = []
            by_type[issue_type].append(issue)
        
        lines.append('## Innehåll')
        lines.append('')
        
        for issue_type, type_issues in sorted(by_type.items()):
            lines.append(f'### {issue_type} ({len(type_issues)})')
            lines.append('')
            for issue in sorted(type_issues, key=lambda x: x['key']):
                status = issue['status']['name']
                status_icon = '✅' if status.lower() in ['done', 'closed'] else '🔄' if 'progress' in status.lower() else '⬜'
                lines.append(f'- {status_icon} [{issue["key"]}]({issue["key"]}.md) – {issue["summary"]}')
            lines.append('')
        
        # Sökord / taggar
        all_labels = set()
        all_components = set()
        for issue in issues:
            all_labels.update(issue.get('labels', []))
            all_components.update(issue.get('components', []))
        
        if all_labels:
            lines.append('## Etiketter')
            lines.append('')
            lines.append(' '.join([f'`{label}`' for label in sorted(all_labels)]))
            lines.append('')
        
        if all_components:
            lines.append('## Komponenter')
            lines.append('')
            lines.append(' '.join([f'`{comp}`' for comp in sorted(all_components)]))
            lines.append('')
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        return filepath
