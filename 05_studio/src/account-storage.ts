let memoryToken = "";
export function customerToken(): string {
  try { return localStorage.getItem("pd_web_token") || ""; }
  catch { return memoryToken; }
}
export function storeCustomer(token: string, user: unknown) {
  memoryToken = token;
  try {
    localStorage.setItem("pd_web_token",token);
    localStorage.setItem("pd_web_user",JSON.stringify(user));
  } catch { /* Sign-in still works for this page when browser storage is unavailable. */ }
}
export function clearCustomer() {
  memoryToken = "";
  try { localStorage.removeItem("pd_web_token");localStorage.removeItem("pd_web_user"); }
  catch { /* Keep the current page signed out. */ }
}
