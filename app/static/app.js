const state = {
  authMode: "login",
  token: localStorage.getItem("jobflow_token") || "",
  jobs: new Map(),
  sockets: new Map(),
};

const payloads = {
  document_ocr: {
    document_uri: "s3://incoming/invoice-1042.pdf",
    pages: 12,
    language: "en",
    entities: ["invoice_number", "vendor", "total", "due_date"],
    duration: 1,
  },
  media_transcode: {
    source_uri: "s3://incoming/product-demo.mov",
    duration_seconds: 95.4,
    codec: "h264",
    container: "mp4",
    renditions: ["1080p", "720p", "480p"],
    duration: 1,
  },
  ai_summarization: {
    model: "gpt-4.1-mini",
    text: "Customer calls mention latency, onboarding friction, and positive support sentiment across enterprise accounts.",
    topics: ["latency", "onboarding", "support"],
    duration: 1.2,
  },
  content_moderation: {
    asset_uri: "s3://incoming/user-upload.jpg",
    labels: { violence: 0.01, self_harm: 0, adult: 0.03 },
    duration: 0.8,
  },
};

const els = {
  authButton: document.querySelector("#authButton"),
  authStatus: document.querySelector("#authStatus"),
  logoutButton: document.querySelector("#logoutButton"),
  email: document.querySelector("#email"),
  password: document.querySelector("#password"),
  modeButtons: document.querySelectorAll("[data-auth-mode]"),
  refreshStats: document.querySelector("#refreshStats"),
  jobForm: document.querySelector("#jobForm"),
  jobType: document.querySelector("#jobType"),
  uploadForm: document.querySelector("#uploadForm"),
  documentFile: document.querySelector("#documentFile"),
  payload: document.querySelector("#payload"),
  priority: document.querySelector("#priority"),
  maxRetries: document.querySelector("#maxRetries"),
  idempotencyKey: document.querySelector("#idempotencyKey"),
  formStatus: document.querySelector("#formStatus"),
  uploadStatus: document.querySelector("#uploadStatus"),
  jobsList: document.querySelector("#jobsList"),
  stats: {
    queued: document.querySelector("#statQueued"),
    processing: document.querySelector("#statProcessing"),
    retrying: document.querySelector("#statRetrying"),
    completed: document.querySelector("#statCompleted"),
    failed: document.querySelector("#statFailed"),
    dlq_size: document.querySelector("#statDlq"),
  },
};

function setStatus(element, message, isError = false) {
  element.textContent = message;
  element.style.color = isError ? "#b3261e" : "";
}

function authHeaders() {
  return state.token ? { Authorization: `Bearer ${state.token}` } : {};
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...(options.headers || {}),
    },
  });
  const text = await response.text();
  const data = text ? JSON.parse(text) : null;
  if (!response.ok) {
    throw new Error(data?.detail || `Request failed with ${response.status}`);
  }
  return data;
}

async function uploadApi(path, formData) {
  const response = await fetch(path, {
    method: "POST",
    headers: authHeaders(),
    body: formData,
  });
  const text = await response.text();
  const data = text ? JSON.parse(text) : null;
  if (!response.ok) {
    throw new Error(data?.detail || `Request failed with ${response.status}`);
  }
  return data;
}

function updateAuthUi() {
  if (state.token) {
    setStatus(els.authStatus, "Connected");
    els.logoutButton.classList.remove("hidden");
    els.authButton.textContent = state.authMode === "login" ? "Login" : "Register";
  } else {
    setStatus(els.authStatus, "Not connected");
    els.logoutButton.classList.add("hidden");
  }
}

function setAuthMode(mode) {
  state.authMode = mode;
  els.authButton.textContent = mode === "login" ? "Login" : "Register";
  els.modeButtons.forEach((button) => {
    button.classList.toggle("active", button.dataset.authMode === mode);
  });
}

async function authenticate() {
  try {
    const result = await api(`/api/v1/auth/${state.authMode}`, {
      method: "POST",
      body: JSON.stringify({ email: els.email.value, password: els.password.value }),
    });
    state.token = result.access_token;
    localStorage.setItem("jobflow_token", state.token);
    updateAuthUi();
    await refreshStats();
  } catch (error) {
    setStatus(els.authStatus, error.message, true);
  }
}

function logout() {
  state.token = "";
  localStorage.removeItem("jobflow_token");
  for (const socket of state.sockets.values()) socket.close();
  state.sockets.clear();
  updateAuthUi();
}

async function refreshStats() {
  if (!state.token) {
    setStatus(els.authStatus, "Login or register to load stats");
    return;
  }
  try {
    const stats = await api("/api/v1/admin/stats");
    Object.entries(els.stats).forEach(([key, element]) => {
      element.textContent = stats[key] ?? 0;
    });
  } catch (error) {
    setStatus(els.authStatus, error.message, true);
  }
}

function renderJobs() {
  if (state.jobs.size === 0) {
    els.jobsList.className = "jobs-list empty";
    els.jobsList.textContent = "No jobs submitted yet.";
    return;
  }

  els.jobsList.className = "jobs-list";
  els.jobsList.innerHTML = "";
  const jobs = Array.from(state.jobs.values()).sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  );

  for (const job of jobs) {
    const card = document.createElement("article");
    card.className = "job-card";
    card.innerHTML = `
      <header>
        <div class="job-title">
          <strong>${job.job_type.replaceAll("_", " ")}</strong>
          <span>${job.id}</span>
        </div>
        <span class="badge ${job.status}">${job.status}</span>
      </header>
      <div class="meta">Priority ${job.priority} &middot; Retries ${job.retry_count}/${job.max_retries}</div>
      <pre>${JSON.stringify(job.result || { error: job.error_message } || {}, null, 2)}</pre>
    `;
    els.jobsList.appendChild(card);
  }
}

function watchJob(jobId) {
  if (!state.token || state.sockets.has(jobId)) return;
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const socket = new WebSocket(`${protocol}://${window.location.host}/api/v1/jobs/ws/${jobId}?token=${state.token}`);
  state.sockets.set(jobId, socket);
  socket.onmessage = (event) => {
    const job = JSON.parse(event.data);
    state.jobs.set(job.id, job);
    renderJobs();
    refreshStats();
  };
  socket.onclose = () => state.sockets.delete(jobId);
}

async function submitJob(event) {
  event.preventDefault();
  if (!state.token) {
    setStatus(els.formStatus, "Login or register before submitting a job.", true);
    return;
  }

  try {
    const body = {
      job_type: els.jobType.value,
      payload: JSON.parse(els.payload.value),
      priority: Number(els.priority.value),
      max_retries: Number(els.maxRetries.value),
    };
    if (els.idempotencyKey.value.trim()) {
      body.idempotency_key = els.idempotencyKey.value.trim();
    }

    const job = await api("/api/v1/jobs", {
      method: "POST",
      body: JSON.stringify(body),
    });
    state.jobs.set(job.id, job);
    renderJobs();
    watchJob(job.id);
    refreshStats();
    setStatus(els.formStatus, `Submitted ${job.id}`);
  } catch (error) {
    setStatus(els.formStatus, error.message, true);
  }
}

async function uploadDocument(event) {
  event.preventDefault();
  if (!state.token) {
    setStatus(els.uploadStatus, "Login or register before uploading a document.", true);
    return;
  }
  const file = els.documentFile.files?.[0];
  if (!file) {
    setStatus(els.uploadStatus, "Choose a PDF, DOCX, text, or Markdown file.", true);
    return;
  }

  try {
    const formData = new FormData();
    formData.append("file", file);
    const job = await uploadApi("/api/v1/jobs/documents", formData);
    state.jobs.set(job.id, job);
    renderJobs();
    watchJob(job.id);
    refreshStats();
    setStatus(els.uploadStatus, `Uploaded ${file.name} as ${job.id}`);
    els.uploadForm.reset();
  } catch (error) {
    setStatus(els.uploadStatus, error.message, true);
  }
}

function setDefaultPayload() {
  els.payload.value = JSON.stringify(payloads[els.jobType.value], null, 2);
}

els.modeButtons.forEach((button) => {
  button.addEventListener("click", () => setAuthMode(button.dataset.authMode));
});
els.authButton.addEventListener("click", authenticate);
els.logoutButton.addEventListener("click", logout);
els.refreshStats.addEventListener("click", refreshStats);
els.jobForm.addEventListener("submit", submitJob);
els.uploadForm.addEventListener("submit", uploadDocument);
els.jobType.addEventListener("change", setDefaultPayload);

setDefaultPayload();
updateAuthUi();
if (state.token) refreshStats();
