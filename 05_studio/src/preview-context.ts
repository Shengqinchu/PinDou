export const isContentPreview = () => parent !== window && new URLSearchParams(location.search).has('content-preview');

// The same-origin HTML endpoint avoids www -> apex redirects inside the iframe.
// Only known public routes can be selected, before Vue Router is initialized.
export function preparePreviewRoute() {
  if (!isContentPreview() || location.pathname !== '/studio-api/site') return;
  const query=new URLSearchParams(location.search),route=query.get('preview-path') || '/';
  const safe=['/','/visit','/details','/journal','/shop'].includes(route)?route:'/';
  query.delete('preview-path');
  history.replaceState(history.state,'',safe+'?'+query.toString());
}
