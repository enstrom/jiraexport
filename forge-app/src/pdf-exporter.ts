/**
 * PDF Generator for Jira Issues
 * Uses jsPDF for pure JavaScript PDF generation (works in Forge serverless)
 * Includes image attachments in the PDF
 */
import { jsPDF } from 'jspdf';
import { getIssue, downloadAttachment, ParsedIssue, JiraAttachment } from './jira-client';

export interface ExportResult {
  issueKey: string;
  pdfBase64: string;
  filename: string;
  size: number;
}

export interface BulkExportResult {
  successful: ExportResult[];
  failed: Array<{ issueKey: string; error: string }>;
}

// Bildtyper som stöds
const IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.gif', '.webp'];

function isImageFile(filename: string): boolean {
  const lower = filename.toLowerCase();
  return IMAGE_EXTENSIONS.some(ext => lower.endsWith(ext));
}

function getImageType(filename: string): 'PNG' | 'JPEG' | 'GIF' | 'WEBP' {
  const lower = filename.toLowerCase();
  if (lower.endsWith('.png')) return 'PNG';
  if (lower.endsWith('.gif')) return 'GIF';
  if (lower.endsWith('.webp')) return 'WEBP';
  return 'JPEG';
}

/**
 * Konvertera ArrayBuffer till base64
 */
function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

/**
 * Exportera en issue till PDF
 */
export async function exportIssueToPdf(issueKey: string): Promise<ExportResult> {
  console.log('Starting PDF export for:', issueKey);
  
  // Hämta issue-data
  const issue = await getIssue(issueKey);
  console.log('Got issue data:', issue.key, issue.summary);
  console.log('Attachments:', issue.attachments.length);
  console.log('Custom fields:', Object.keys(issue.customFields || {}).length);
  
  // OBS: Bildnedladdning fungerar inte i Forge pga API-begränsningar (406 error)
  // Bilder visas som lista istället för inbäddade
  const imageAttachments: Array<{ filename: string; base64: string; type: string }> = [];
  
  // Skapa PDF
  const pdfBase64 = generatePdf(issue, imageAttachments);
  console.log('Generated PDF, size:', pdfBase64.length);
  
  return {
    issueKey,
    pdfBase64,
    filename: `${issueKey}.pdf`,
    size: pdfBase64.length
  };
}

/**
 * Exportera flera issues till PDF
 */
export async function exportMultipleIssuesToPdf(issueKeys: string[]): Promise<BulkExportResult> {
  const successful: ExportResult[] = [];
  const failed: Array<{ issueKey: string; error: string }> = [];
  
  for (const issueKey of issueKeys) {
    try {
      const result = await exportIssueToPdf(issueKey);
      successful.push(result);
    } catch (error) {
      console.error('Failed to export:', issueKey, error);
      failed.push({
        issueKey,
        error: error instanceof Error ? error.message : 'Unknown error'
      });
    }
  }
  
  return { successful, failed };
}

interface ImageData {
  filename: string;
  base64: string;
  type: string;
}

/**
 * Generera PDF-dokument med jsPDF
 */
function generatePdf(issue: ParsedIssue, images: ImageData[]): string {
  const doc = new jsPDF({
    orientation: 'portrait',
    unit: 'mm',
    format: 'a4'
  });

  const pageWidth = 210;
  const pageHeight = 297;
  const margin = 20;
  const contentWidth = pageWidth - 2 * margin;
  let y = margin;

  // Färger
  const primaryColor: [number, number, number] = [0, 82, 204];  // Jira blå
  const textColor: [number, number, number] = [23, 43, 77];     // Mörk text
  const lightColor: [number, number, number] = [94, 108, 132];  // Ljus text
  const bgColor: [number, number, number] = [244, 245, 247];    // Bakgrund

  // Header - Issue type och key
  doc.setFontSize(11);
  doc.setTextColor(...lightColor);
  doc.text(`${issue.issueType} | `, margin, y);
  const typeWidth = doc.getTextWidth(`${issue.issueType} | `);
  doc.setTextColor(...primaryColor);
  doc.setFont('helvetica', 'bold');
  doc.text(issue.key, margin + typeWidth, y);
  y += 10;

  // Titel
  doc.setFontSize(20);
  doc.setTextColor(...textColor);
  doc.setFont('helvetica', 'bold');
  const titleLines = doc.splitTextToSize(issue.summary, contentWidth);
  doc.text(titleLines, margin, y);
  y += titleLines.length * 8 + 5;

  // Status och prioritet
  doc.setFontSize(10);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(...textColor);
  doc.text('Status: ', margin, y);
  
  // Status färg
  const statusLower = issue.status.toLowerCase();
  if (statusLower.includes('done') || statusLower.includes('closed')) {
    doc.setTextColor(0, 135, 90); // Grön
  } else if (statusLower.includes('progress')) {
    doc.setTextColor(...primaryColor);
  } else {
    doc.setTextColor(...lightColor);
  }
  doc.text(issue.status, margin + 15, y);
  
  doc.setTextColor(...textColor);
  doc.text('     Prioritet: ', margin + 40, y);
  doc.setFont('helvetica', 'normal');
  doc.text(issue.priority || 'N/A', margin + 65, y);
  y += 8;

  // Separator
  doc.setDrawColor(223, 225, 230);
  doc.setLineWidth(0.5);
  doc.line(margin, y, pageWidth - margin, y);
  y += 8;

  // Detaljer-sektion
  doc.setFontSize(14);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(...textColor);
  doc.text('Detaljer', margin, y);
  y += 6;

  // Bakgrundsruta för detaljer
  const details: [string, string][] = [];
  if (issue.assignee) details.push(['Tilldelad', issue.assignee]);
  if (issue.reporter) details.push(['Rapportör', issue.reporter]);
  if (issue.fixVersions.length) details.push(['Fix Versions', issue.fixVersions.join(', ')]);
  if (issue.components.length) details.push(['Komponenter', issue.components.join(', ')]);
  if (issue.labels.length) details.push(['Etiketter', issue.labels.join(', ')]);
  if (issue.sprints.length) details.push(['Sprint', issue.sprints.join(', ')]);
  if (issue.storyPoints) details.push(['Story Points', String(issue.storyPoints)]);
  if (issue.epic) details.push(['Epic', String(issue.epic)]);
  if (issue.parent) details.push(['Parent', `${issue.parent.key} - ${issue.parent.summary}`]);
  if (issue.created) details.push(['Skapad', formatDate(issue.created)]);
  if (issue.updated) details.push(['Uppdaterad', formatDate(issue.updated)]);
  if (issue.resolved) details.push(['Löst', formatDate(issue.resolved)]);

  const boxHeight = Math.ceil(details.length / 2) * 6 + 8;
  doc.setFillColor(...bgColor);
  doc.rect(margin, y, contentWidth, boxHeight, 'F');
  y += 4;

  // Detaljer i två kolumner
  const colWidth = contentWidth / 2;
  doc.setFontSize(9);
  
  for (let i = 0; i < details.length; i++) {
    const [label, value] = details[i];
    const col = i % 2;
    const x = margin + 3 + col * colWidth;
    
    if (col === 0 && i > 0) {
      y += 5;
    }
    
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(...lightColor);
    doc.text(`${label}: `, x, y);
    
    doc.setFont('helvetica', 'normal');
    doc.setTextColor(...textColor);
    const labelWidth = doc.getTextWidth(`${label}: `);
    doc.text(truncate(value, 30), x + labelWidth, y);
  }
  
  y += boxHeight - 4 + 10;

  // Beskrivning
  if (issue.description) {
    y = checkNewPage(doc, y, 30);
    
    doc.setFontSize(14);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(...textColor);
    doc.text('Beskrivning', margin, y);
    y += 6;
    
    doc.setFontSize(10);
    doc.setFont('helvetica', 'normal');
    
    const paragraphs = issue.description.split('\n').filter(p => p.trim());
    for (const para of paragraphs) {
      y = checkNewPage(doc, y, 10);
      const lines = doc.splitTextToSize(para.trim(), contentWidth);
      doc.text(lines, margin, y);
      y += lines.length * 4 + 2;
    }
    y += 5;
  }

  // CUSTOM FIELDS / Ytterligare fält
  const customFieldEntries = Object.entries(issue.customFields || {});
  if (customFieldEntries.length > 0) {
    y = checkNewPage(doc, y, 30);
    
    doc.setFontSize(14);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(...textColor);
    doc.text('Ytterligare falt', margin, y);
    y += 8;
    
    for (const [fieldName, fieldValue] of customFieldEntries) {
      y = checkNewPage(doc, y, 15);
      
      // Fältnamn
      doc.setFontSize(10);
      doc.setFont('helvetica', 'bold');
      doc.setTextColor(...lightColor);
      doc.text(`${fieldName}:`, margin, y);
      y += 5;
      
      // Fältvärde (kan vara långt)
      doc.setFont('helvetica', 'normal');
      doc.setTextColor(...textColor);
      const valueText = String(fieldValue);
      const valueLines = doc.splitTextToSize(valueText, contentWidth - 10);
      
      // Begränsa till max 10 rader per fält
      const maxLines = Math.min(valueLines.length, 10);
      for (let i = 0; i < maxLines; i++) {
        y = checkNewPage(doc, y, 5);
        doc.text(valueLines[i], margin + 5, y);
        y += 4;
      }
      if (valueLines.length > 10) {
        doc.text('...', margin + 5, y);
        y += 4;
      }
      y += 3;
    }
    y += 5;
  }

  // BILDER - Ny sektion för bildbilagor
  if (images.length > 0) {
    y = checkNewPage(doc, y, 60);
    
    doc.setFontSize(14);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(...textColor);
    doc.text('Bilder och Skärmdumpar', margin, y);
    y += 8;
    
    for (const img of images) {
      try {
        y = checkNewPage(doc, y, 90);
        
        // Bildfilnamn
        doc.setFontSize(9);
        doc.setFont('helvetica', 'normal');
        doc.setTextColor(...lightColor);
        doc.text(`[Bild] ${img.filename}`, margin, y);
        y += 5;
        
        // Lägg till bilden med korrekt skalning
        const maxImgWidth = contentWidth;
        const maxImgHeight = 80; // Max höjd i mm
        
        try {
          // Skapa data URL för bilden
          const imageData = `data:image/${img.type.toLowerCase()};base64,${img.base64}`;
          
          doc.addImage(
            imageData,
            img.type as 'PNG' | 'JPEG' | 'GIF' | 'WEBP',
            margin,
            y,
            maxImgWidth,
            maxImgHeight,
            undefined,
            'FAST'
          );
          y += maxImgHeight + 8;
          console.log('Added image to PDF:', img.filename);
        } catch (imgError) {
          console.error('Failed to add image to PDF:', img.filename, imgError);
          doc.setTextColor(190, 38, 0);
          doc.text(`[Kunde inte visa bild: ${img.filename}]`, margin, y);
          y += 6;
        }
      } catch (error) {
        console.error('Error processing image:', img.filename, error);
      }
    }
    y += 5;
  }

  // Bilagor (lista)
  if (issue.attachments.length > 0) {
    y = checkNewPage(doc, y, 30);
    
    doc.setFontSize(14);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(...textColor);
    doc.text('Bilagor', margin, y);
    y += 6;
    
    doc.setFontSize(10);
    doc.setFont('helvetica', 'normal');
    
    for (const att of issue.attachments) {
      y = checkNewPage(doc, y, 8);
      const sizeKb = att.size / 1024;
      const sizeStr = sizeKb < 1024 ? `${sizeKb.toFixed(1)} KB` : `${(sizeKb / 1024).toFixed(1)} MB`;
      const prefix = isImageFile(att.filename) ? '[Bild]' : '[Fil]';
      doc.text(`${prefix} ${att.filename} (${sizeStr})`, margin, y);
      y += 5;
    }
    y += 5;
  }

  // Underuppgifter
  if (issue.subtasks.length > 0) {
    y = checkNewPage(doc, y, 30);
    
    doc.setFontSize(14);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(...textColor);
    doc.text('Underuppgifter', margin, y);
    y += 6;
    
    doc.setFontSize(10);
    
    for (const st of issue.subtasks) {
      y = checkNewPage(doc, y, 8);
      doc.setFont('helvetica', 'normal');
      doc.setTextColor(...primaryColor);
      doc.text(st.key, margin, y);
      doc.setTextColor(...textColor);
      doc.text(` - ${truncate(st.summary, 50)} [${st.status}]`, margin + 20, y);
      y += 5;
    }
    y += 5;
  }

  // Länkade ärenden
  if (issue.links.length > 0) {
    y = checkNewPage(doc, y, 30);
    
    doc.setFontSize(14);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(...textColor);
    doc.text('Länkade ärenden', margin, y);
    y += 6;
    
    doc.setFontSize(10);
    
    for (const link of issue.links) {
      y = checkNewPage(doc, y, 8);
      doc.setFont('helvetica', 'normal');
      doc.setTextColor(...lightColor);
      doc.text(`${link.type} `, margin, y);
      doc.setTextColor(...primaryColor);
      doc.text(link.key, margin + doc.getTextWidth(`${link.type} `), y);
      doc.setTextColor(...textColor);
      doc.text(` - ${truncate(link.summary, 40)}`, margin + doc.getTextWidth(`${link.type} ${link.key}`), y);
      y += 5;
    }
    y += 5;
  }

  // Kommentarer
  if (issue.comments.length > 0) {
    y = checkNewPage(doc, y, 30);
    
    doc.setFontSize(14);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(...textColor);
    doc.text(`Kommentarer (${issue.comments.length})`, margin, y);
    y += 6;
    
    for (const comment of issue.comments.slice(0, 10)) {
      y = checkNewPage(doc, y, 15);
      
      doc.setFontSize(9);
      doc.setFont('helvetica', 'bold');
      doc.setTextColor(...lightColor);
      doc.text(`${comment.author} - ${formatDate(comment.created)}`, margin, y);
      y += 4;
      
      doc.setFont('helvetica', 'normal');
      doc.setTextColor(...textColor);
      const commentLines = doc.splitTextToSize(truncate(comment.body, 300), contentWidth - 5);
      doc.text(commentLines, margin + 3, y);
      y += commentLines.length * 3.5 + 3;
    }
  }

  // Footer på varje sida
  const totalPages = doc.getNumberOfPages();
  for (let i = 1; i <= totalPages; i++) {
    doc.setPage(i);
    const footerY = pageHeight - 15;
    doc.setDrawColor(223, 225, 230);
    doc.setLineWidth(0.3);
    doc.line(margin, footerY - 3, pageWidth - margin, footerY - 3);
    
    doc.setFontSize(8);
    doc.setFont('helvetica', 'normal');
    doc.setTextColor(...lightColor);
    doc.text(
      `Exporterad: ${new Date().toISOString().slice(0, 16).replace('T', ' ')} | Issue: ${issue.key} | Sida ${i}/${totalPages}`,
      pageWidth / 2,
      footerY,
      { align: 'center' }
    );
  }

  // Returnera som base64
  return doc.output('datauristring').split(',')[1];
}

/**
 * Kontrollera om ny sida behövs
 */
function checkNewPage(doc: jsPDF, y: number, needed: number): number {
  const pageHeight = 297;
  const margin = 20;
  
  if (y + needed > pageHeight - margin) {
    doc.addPage();
    return margin;
  }
  return y;
}

/**
 * Formatera datum
 */
function formatDate(dateStr: string): string {
  if (!dateStr) return 'N/A';
  try {
    const date = new Date(dateStr);
    return date.toISOString().slice(0, 16).replace('T', ' ');
  } catch {
    return dateStr.slice(0, 19);
  }
}

/**
 * Trunkera text
 */
function truncate(text: string, maxLength: number): string {
  if (!text) return '';
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength - 3) + '...';
}
