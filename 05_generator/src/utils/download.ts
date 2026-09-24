export type DownloadImageResult = 'downloaded' | 'opened' | 'shared' | 'cancelled';

interface DownloadImageOptions {
  preferNativeShare?: boolean;
  shareTitle?: string;
  shareText?: string;
}

type ShareDataWithFiles = ShareData & { files?: File[] };
type NavigatorWithFileShare = Navigator & {
  canShare?: (data?: ShareDataWithFiles) => boolean;
  share?: (data?: ShareDataWithFiles) => Promise<void>;
};

export async function downloadImage(
  url: string,
  filename: string,
  options: DownloadImageOptions = {}
): Promise<DownloadImageResult> {
  let objectUrl = '';
  try {
    const response = await fetch(url, { mode: 'cors' });
    if (!response.ok) {
      throw new Error('download failed');
    }
    const blob = await response.blob();
    if (options.preferNativeShare) {
      const shared = await tryNativeShare(blob, filename, options);
      if (shared) {
        return shared;
      }
    }
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

async function tryNativeShare(
  blob: Blob,
  filename: string,
  options: DownloadImageOptions
): Promise<DownloadImageResult | null> {
  const nav = navigator as NavigatorWithFileShare;
  if (!nav.share || !window.File) {
    return null;
  }
  const file = new File([blob], filename, { type: blob.type || 'image/png' });
  const shareData: ShareDataWithFiles = {
    files: [file],
    title: options.shareTitle || 'Pindou Puppy 拼豆图纸',
    text: options.shareText
  };
  if (nav.canShare && !nav.canShare({ files: shareData.files })) {
    return null;
  }
  try {
    await nav.share(shareData);
    return 'shared';
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      return 'cancelled';
    }
    return null;
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
