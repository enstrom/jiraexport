/**
 * Frontend PDF Generator
 * Genererar PDF i webbläsaren med bilder via session
 */
import { jsPDF } from 'jspdf';

// Färger
const COLORS = {
  primary: [0, 82, 204],      // Jira blå
  text: [23, 43, 77],         // Mörk text
  light: [94, 108, 132],      // Ljus text
  bg: [244, 245, 247],        // Bakgrund
  accent: [0, 135, 90],       // Grön (Done)
};

/**
 * Ladda bild som base64 via fetch
 */
async function loadImageAsBase64(url) {
  try {
    const response = await fetch(url, { credentials: 'include' });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    
    const blob = await response.blob();
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => resolve(reader.result);
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
  } catch (error) {
    console.error('Failed to load image:', url, error);
    return null;
  }
}

/**
 * Generera PDF för en issue
 */
export async function generatePdfInBrowser(issue, onProgress) {
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

  // Helper för ny sida
  const checkNewPage = (needed) => {
    if (y + needed > pageHeight - margin) {
      doc.addPage();
      y = margin;
    }
  };

  // Header - Issue type och key
  doc.setFontSize(11);
  doc.setTextColor(...COLORS.light);
  doc.text(`${issue.issueType} | `, margin, y);
  const typeWidth = doc.getTextWidth(`${issue.issueType} | `);
  doc.setTextColor(...COLORS.primary);
  doc.setFont('helvetica', 'bold');
  doc.text(issue.key, margin + typeWidth, y);
  y += 10;

  // Titel
  doc.setFontSize(20);
  doc.setTextColor(...COLORS.text);
  const titleLines = doc.splitTextToSize(issue.summary, contentWidth);
  doc.text(titleLines, margin, y);
  y += titleLines.length * 8 + 5;

  // Status och prioritet
  doc.setFontSize(10);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(...COLORS.text);
  doc.text('Status: ', margin, y);
  
  const statusLower = (issue.status || '').toLowerCase();
  if (statusLower.includes('done') || statusLower.includes('closed')) {
    doc.setTextColor(...COLORS.accent);
  } else if (statusLower.includes('progress')) {
    doc.setTextColor(...COLORS.primary);
  } else {
    doc.setTextColor(...COLORS.light);
  }
  doc.text(issue.status || 'Unknown', margin + 15, y);
  
  doc.setTextColor(...COLORS.text);
  doc.text('     Prioritet: ', margin + 40, y);
  doc.setFont('helvetica', 'normal');
  doc.text(issue.priority || 'N/A', margin + 65, y);
  y += 8;

  // Separator
  doc.setDrawColor(223, 225, 230);
  doc.setLineWidth(0.5);
  doc.line(margin, y, pageWidth - margin, y);
  y += 8;

  // Detaljer
  doc.setFontSize(14);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(...COLORS.text);
  doc.text('Detaljer', margin, y);
  y += 6;

  const details = [];
  if (issue.assignee) details.push(['Tilldelad', issue.assignee]);
  if (issue.reporter) details.push(['Rapportor', issue.reporter]);
  if (issue.fixVersions?.length) details.push(['Fix Versions', issue.fixVersions.join(', ')]);
  if (issue.components?.length) details.push(['Komponenter', issue.components.join(', ')]);
  if (issue.labels?.length) details.push(['Etiketter', issue.labels.join(', ')]);
  if (issue.sprints?.length) details.push(['Sprint', issue.sprints.join(', ')]);
  if (issue.storyPoints) details.push(['Story Points', String(issue.storyPoints)]);
  if (issue.epic) details.push(['Epic', String(issue.epic)]);
  if (issue.parent) details.push(['Parent', `${issue.parent.key} - ${issue.parent.summary}`]);
  if (issue.created) details.push(['Skapad', formatDate(issue.created)]);
  if (issue.updated) details.push(['Uppdaterad', formatDate(issue.updated)]);

  // Bakgrundsruta
  const boxHeight = Math.ceil(details.length / 2) * 6 + 8;
  doc.setFillColor(...COLORS.bg);
  doc.rect(margin, y, contentWidth, boxHeight, 'F');
  y += 4;

  // Detaljer i två kolumner
  const colWidth = contentWidth / 2;
  doc.setFontSize(9);
  
  for (let i = 0; i < details.length; i++) {
    const [label, value] = details[i];
    const col = i % 2;
    const x = margin + 3 + col * colWidth;
    
    if (col === 0 && i > 0) y += 5;
    
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(...COLORS.light);
    doc.text(`${label}: `, x, y);
    
    doc.setFont('helvetica', 'normal');
    doc.setTextColor(...COLORS.text);
    const labelWidth = doc.getTextWidth(`${label}: `);
    doc.text(truncate(value, 30), x + labelWidth, y);
  }
  
  y += boxHeight - 4 + 10;

  // Beskrivning
  if (issue.description) {
    checkNewPage(30);
    
    doc.setFontSize(14);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(...COLORS.text);
    doc.text('Beskrivning', margin, y);
    y += 6;
    
    doc.setFontSize(10);
    doc.setFont('helvetica', 'normal');
    
    const paragraphs = issue.description.split('\n').filter(p => p.trim());
    for (const para of paragraphs) {
      checkNewPage(10);
      const lines = doc.splitTextToSize(para.trim(), contentWidth);
      doc.text(lines, margin, y);
      y += lines.length * 4 + 2;
    }
    y += 5;
  }

  // Custom Fields / Ytterligare fält
  const customFields = Object.entries(issue.customFields || {});
  if (customFields.length > 0) {
    checkNewPage(30);
    
    doc.setFontSize(14);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(...COLORS.text);
    doc.text('Ytterligare falt', margin, y);
    y += 8;
    
    for (const [fieldName, fieldValue] of customFields) {
      checkNewPage(15);
      
      doc.setFontSize(10);
      doc.setFont('helvetica', 'bold');
      doc.setTextColor(...COLORS.light);
      doc.text(`${fieldName}:`, margin, y);
      y += 5;
      
      doc.setFont('helvetica', 'normal');
      doc.setTextColor(...COLORS.text);
      const valueText = String(fieldValue);
      const valueLines = doc.splitTextToSize(valueText, contentWidth - 10);
      
      const maxLines = Math.min(valueLines.length, 10);
      for (let i = 0; i < maxLines; i++) {
        checkNewPage(5);
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

  // BILDER - Ladda och bädda in från webbläsaren
  const imageAttachments = (issue.attachments || []).filter(att => 
    /\.(png|jpg|jpeg|gif|webp)$/i.test(att.filename)
  );
  
  if (imageAttachments.length > 0) {
    checkNewPage(30);
    
    doc.setFontSize(14);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(...COLORS.text);
    doc.text('Bilder och Skarmdumpar', margin, y);
    y += 8;
    
    let loadedCount = 0;
    for (const att of imageAttachments) {
      if (onProgress) {
        onProgress(`Laddar bild ${++loadedCount}/${imageAttachments.length}: ${att.filename}`);
      }
      
      try {
        checkNewPage(90);
        
        // Bildfilnamn
        doc.setFontSize(9);
        doc.setFont('helvetica', 'normal');
        doc.setTextColor(...COLORS.light);
        doc.text(`[Bild] ${att.filename}`, margin, y);
        y += 5;
        
        // Ladda bild via webbläsarens session
        const imageData = await loadImageAsBase64(att.content);
        
        if (imageData) {
          const imgType = att.filename.toLowerCase().endsWith('.png') ? 'PNG' : 'JPEG';
          
          try {
            doc.addImage(
              imageData,
              imgType,
              margin,
              y,
              contentWidth,
              80,
              undefined,
              'FAST'
            );
            y += 85;
            console.log('Added image:', att.filename);
          } catch (imgError) {
            console.error('Failed to add image to PDF:', att.filename, imgError);
            doc.setTextColor(190, 38, 0);
            doc.text(`[Kunde inte visa bild]`, margin, y);
            y += 6;
          }
        } else {
          doc.setTextColor(190, 38, 0);
          doc.text(`[Kunde inte ladda bild]`, margin, y);
          y += 6;
        }
      } catch (error) {
        console.error('Error processing image:', att.filename, error);
      }
    }
    y += 5;
  }

  // Bilagor lista
  if (issue.attachments?.length > 0) {
    checkNewPage(30);
    
    doc.setFontSize(14);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(...COLORS.text);
    doc.text('Bilagor', margin, y);
    y += 6;
    
    doc.setFontSize(10);
    doc.setFont('helvetica', 'normal');
    
    for (const att of issue.attachments) {
      checkNewPage(8);
      const sizeKb = att.size / 1024;
      const sizeStr = sizeKb < 1024 ? `${sizeKb.toFixed(1)} KB` : `${(sizeKb / 1024).toFixed(1)} MB`;
      const isImage = /\.(png|jpg|jpeg|gif|webp)$/i.test(att.filename);
      const prefix = isImage ? '[Bild]' : '[Fil]';
      doc.text(`${prefix} ${att.filename} (${sizeStr})`, margin, y);
      y += 5;
    }
    y += 5;
  }

  // Underuppgifter
  if (issue.subtasks?.length > 0) {
    checkNewPage(30);
    
    doc.setFontSize(14);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(...COLORS.text);
    doc.text('Underuppgifter', margin, y);
    y += 6;
    
    doc.setFontSize(10);
    
    for (const st of issue.subtasks) {
      checkNewPage(8);
      doc.setFont('helvetica', 'normal');
      doc.setTextColor(...COLORS.primary);
      doc.text(st.key, margin, y);
      doc.setTextColor(...COLORS.text);
      doc.text(` - ${truncate(st.summary, 50)} [${st.status}]`, margin + 20, y);
      y += 5;
    }
    y += 5;
  }

  // Länkade ärenden
  if (issue.links?.length > 0) {
    checkNewPage(30);
    
    doc.setFontSize(14);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(...COLORS.text);
    doc.text('Lankade arenden', margin, y);
    y += 6;
    
    doc.setFontSize(10);
    
    for (const link of issue.links) {
      checkNewPage(8);
      doc.setFont('helvetica', 'normal');
      doc.setTextColor(...COLORS.light);
      doc.text(`${link.type} `, margin, y);
      doc.setTextColor(...COLORS.primary);
      doc.text(link.key, margin + doc.getTextWidth(`${link.type} `), y);
      doc.setTextColor(...COLORS.text);
      doc.text(` - ${truncate(link.summary, 40)}`, margin + doc.getTextWidth(`${link.type} ${link.key}`), y);
      y += 5;
    }
    y += 5;
  }

  // Kommentarer
  if (issue.comments?.length > 0) {
    checkNewPage(30);
    
    doc.setFontSize(14);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(...COLORS.text);
    doc.text(`Kommentarer (${issue.comments.length})`, margin, y);
    y += 6;
    
    for (const comment of issue.comments.slice(0, 10)) {
      checkNewPage(15);
      
      doc.setFontSize(9);
      doc.setFont('helvetica', 'bold');
      doc.setTextColor(...COLORS.light);
      doc.text(`${comment.author} - ${formatDate(comment.created)}`, margin, y);
      y += 4;
      
      doc.setFont('helvetica', 'normal');
      doc.setTextColor(...COLORS.text);
      const commentLines = doc.splitTextToSize(truncate(comment.body, 300), contentWidth - 5);
      doc.text(commentLines, margin + 3, y);
      y += commentLines.length * 3.5 + 3;
    }
  }

  // Footer på alla sidor
  const totalPages = doc.getNumberOfPages();
  for (let i = 1; i <= totalPages; i++) {
    doc.setPage(i);
    const footerY = pageHeight - 15;
    doc.setDrawColor(223, 225, 230);
    doc.setLineWidth(0.3);
    doc.line(margin, footerY - 3, pageWidth - margin, footerY - 3);
    
    doc.setFontSize(8);
    doc.setFont('helvetica', 'normal');
    doc.setTextColor(...COLORS.light);
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

function formatDate(dateStr) {
  if (!dateStr) return 'N/A';
  try {
    const date = new Date(dateStr);
    return date.toISOString().slice(0, 16).replace('T', ' ');
  } catch {
    return dateStr.slice(0, 19);
  }
}

function truncate(text, maxLength) {
  if (!text) return '';
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength - 3) + '...';
}
