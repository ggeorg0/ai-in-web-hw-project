const API = "/api";

function uid() {
  return localStorage.getItem("user_id");
}

function authHeaders() {
  return { "X-User-ID": uid(), "Content-Type": "application/json" };
}

export function setUserId(id) {
  localStorage.setItem("user_id", id);
}

export function clearUserId() {
  localStorage.removeItem("user_id");
}

export async function register(username) {
  const res = await fetch(`${API}/users/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username }),
  });
  return res.json();
}

export async function uploadVoice(blob) {
  const form = new FormData();
  form.append("file", blob, "recording.webm");
  const res = await fetch(`${API}/tasks/voice`, {
    method: "POST",
    headers: { "X-User-ID": uid() },
    body: form,
  });
  return res.json();
}

export async function getTaskStatus(taskId) {
  const res = await fetch(`${API}/tasks/${taskId}/status`, {
    headers: { "X-User-ID": uid() },
  });
  return res.json();
}

export async function getShoppingList() {
  const res = await fetch(`${API}/lists`, { headers: authHeaders() });
  return res.json();
}

export async function addItem(productName) {
  const res = await fetch(`${API}/lists/items`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ product_name: productName }),
  });
  if (res.status === 409) return null;
  return res.json();
}

export async function deleteItem(itemId) {
  await fetch(`${API}/lists/items/${itemId}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
}
