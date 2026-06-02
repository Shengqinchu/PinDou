const DEFAULT_BACKEND_ORIGIN = 'https://pindou-backend-263102-4-1437642655.sh.run.tcloudbase.com';

interface Env {
  BACKEND_ORIGIN?: string;
}

export async function onRequest(context: EventContext<Env, string, unknown>): Promise<Response> {
  const backendOrigin = normalizeOrigin(context.env.BACKEND_ORIGIN || DEFAULT_BACKEND_ORIGIN);
  const incomingUrl = new URL(context.request.url);
  const upstreamUrl = new URL(`${incomingUrl.pathname}${incomingUrl.search}`, backendOrigin);
  const upstreamHeaders = new Headers(context.request.headers);
  const cfConnectingIp = context.request.headers.get('CF-Connecting-IP');
  const existingForwardedFor = context.request.headers.get('X-Forwarded-For');

  upstreamHeaders.delete('Host');
  upstreamHeaders.set('X-Forwarded-Host', incomingUrl.host);
  upstreamHeaders.set('X-Forwarded-Proto', incomingUrl.protocol.replace(':', ''));
  if (cfConnectingIp) {
    upstreamHeaders.set(
      'X-Forwarded-For',
      existingForwardedFor ? `${existingForwardedFor}, ${cfConnectingIp}` : cfConnectingIp
    );
  }

  const upstreamResponse = await fetch(upstreamUrl, {
    method: context.request.method,
    headers: upstreamHeaders,
    body: shouldForwardBody(context.request.method) ? context.request.body : undefined,
    redirect: 'manual'
  });

  const responseHeaders = new Headers(upstreamResponse.headers);
  responseHeaders.set('Cache-Control', 'no-store');
  responseHeaders.delete('Content-Encoding');
  responseHeaders.delete('Content-Length');

  return new Response(upstreamResponse.body, {
    status: upstreamResponse.status,
    statusText: upstreamResponse.statusText,
    headers: responseHeaders
  });
}

function shouldForwardBody(method: string): boolean {
  return !['GET', 'HEAD'].includes(method.toUpperCase());
}

function normalizeOrigin(origin: string): string {
  return origin.replace(/\/+$/, '');
}

