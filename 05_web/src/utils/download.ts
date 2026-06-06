export type DownloadImageResult = 'downloaded' | 'opened';

export async function downloadImage(url: string, filename: string): Promise<DownloadImageResult> {
  let objectUrl = '';
  try {
    const response = await fetch(url, { mode: 'cors' });
    if (!response.ok) {
      throw new Error('download failed');
    }
    const blob = await response.blob();
    objectUrl = URL.createObjectURL(blob);
    triggerDownload(objectUrl, filename);
    return 'downloaded';
  } catch (_error) {
    window.open(url, '_blank', 'noopener,noreferrer');
    return 'opened';
  } finally {
    if (objectUrl) {
      window.setTimeout(() => URL.revokeObjectURL(objectUrl), 0);
    }
  }
}

function triggerDownload(url: string, filename: string): void {
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.rel = 'noopener';
  document.body.appendChild(link);
  link.click();
  link.remove();
}
