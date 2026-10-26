(function () {
  "use strict";

  const csrfToken = () => {
    const m = document.querySelector('meta[name="csrf-token"]');
    return m ? m.getAttribute("content") : "";
  };

  async function api(path, options) {
    const opts = Object.assign({ headers: {} }, options || {});
    opts.headers = Object.assign({ "Content-Type": "application/json", "X-CSRFToken": csrfToken() }, opts.headers || {});
    const res = await fetch(path, opts);
    let data = null;
    try { data = await res.json(); } catch (e) { data = null; }
    if (!res.ok) {
      const msg = (data && (data.error || data.message)) || res.statusText || "Request failed";
      throw new Error(msg);
    }
    return data;
  }

  function escapeHtml(s) {
    if (s === null || s === undefined) return "";
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function sevBadge(sev) {
    const map = { critical: "bg-danger", high: "bg-warning text-dark", medium: "bg-info text-dark", low: "bg-secondary" };
    return `<span class="badge ${map[sev] || "bg-secondary"}">${escapeHtml(sev)}</span>`;
  }

  const form = document.getElementById("reviewForm");
  if (form) {
    const contentInput = document.getElementById("contentInput");
    const charCount = document.getElementById("charCount");
    const checkBtn = document.getElementById("checkBtn");
    const spinner = document.getElementById("checkSpinner");
    const formError = document.getElementById("formError");

    function updateCount() {
      charCount.textContent = `${contentInput.value.length} / 10000`;
    }
    contentInput.addEventListener("input", updateCount);
    updateCount();

    document.getElementById("clearBtn").addEventListener("click", () => {
      contentInput.value = "";
      updateCount();
      hideResults();
    });

    document.getElementById("sampleBtn").addEventListener("click", () => {
      contentInput.value =
        "Welcome to BrandGuard! Our stuff is cheap and obviously the best in the world. " +
        "We were founded in 2020 and are based in New York. We guarantee 100% effective results " +
        "for all users. Click here to learn more!!! THIS IS AMAZING. We serve over 50000 customers. " +
        "Read more about our amazing product.";
      updateCount();
    });

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      formError.classList.add("d-none");
      const content = contentInput.value.trim();
      const profile_id = document.getElementById("profileSelect").value;
      if (!content) {
        formError.textContent = "Please enter content to review.";
        formError.classList.remove("d-none");
        return;
      }
      setLoading(true);
      try {
        const data = await api("/api/check", {
          method: "POST",
          body: JSON.stringify({ content, profile_id: Number(profile_id) }),
        });
        renderResults(data);
      } catch (err) {
        formError.textContent = err.message;
        formError.classList.remove("d-none");
      } finally {
        setLoading(false);
      }
    });

    function setLoading(on) {
      checkBtn.disabled = on;
      spinner.classList.toggle("d-none", !on);
    }

    function hideResults() {
      document.getElementById("resultsCard").style.display = "none";
    }

    let currentReviewId = null;
    const findingsState = [];

    function renderResults(data) {
      currentReviewId = data.review_id;
      findingsState.length = 0;
      data.findings.forEach((f) => findingsState.push(f));

      document.getElementById("resultsCard").style.display = "block";
      document.getElementById("profileName").textContent = data.profile_name;
      document.getElementById("issueCount").textContent = data.total_issues;
      document.getElementById("aiUsed").textContent = data.ai_used ? "Yes" : "No";

      const counts = { critical: 0, high: 0, medium: 0, low: 0 };
      data.findings.forEach((f) => { if (counts[f.severity] !== undefined) counts[f.severity]++; });
      const summaryEl = document.getElementById("severitySummary");
      summaryEl.innerHTML =
        `<span class="badge bg-danger me-1">critical ${counts.critical}</span>` +
        `<span class="badge bg-warning text-dark me-1">high ${counts.high}</span>` +
        `<span class="badge bg-info text-dark me-1">medium ${counts.medium}</span>` +
        `<span class="badge bg-secondary me-1">low ${counts.low}</span>` +
        (data.findings.length === 0 ? '<span class="text-success ms-2">No issues — ready to publish (after human approval).</span>' : '');

      const badge = document.getElementById("overallBadge");
      badge.textContent = data.overall_status;
      badge.className = "badge " + (data.overall_status === "Passed" ? "bg-success" : "bg-warning text-dark");

      const list = document.getElementById("findingsList");
      list.innerHTML = "";
      document.getElementById("noIssues").classList.toggle("d-none", data.findings.length !== 0);

      data.findings.forEach((f, idx) => {
        const card = document.createElement("div");
        card.className = `card finding-card sev-${f.severity} mb-3`;
        card.innerHTML = `
          <div class="card-body">
            <div class="d-flex justify-content-between align-items-start mb-2">
              <div>
                <span class="badge bg-secondary me-1">${escapeHtml(f.issue_type)}</span>
                ${sevBadge(f.severity)}
                ${f.requires_evidence ? '<span class="badge bg-light text-dark border ms-1">needs evidence</span>' : ""}
              </div>
              <button class="btn btn-sm btn-outline-primary review-btn" data-idx="${idx}">Review</button>
            </div>
            <div class="mb-2">
              <div class="small text-muted mb-1">Original text</div>
              <div class="finding-original">${escapeHtml(f.original_text)}</div>
            </div>
            <div class="mb-2"><strong>Explanation:</strong> ${escapeHtml(f.explanation)}</div>
            ${f.rule_reference ? `<div class="mb-2 small"><strong>Rule / fact:</strong> ${escapeHtml(f.rule_reference)}</div>` : ""}
            ${f.suggested_correction ? `<div class="mb-2"><strong>Suggested correction:</strong> ${escapeHtml(f.suggested_correction)}</div>` : ""}
            <div class="small text-muted">Status: <span class="badge bg-light text-dark border badge-status" id="status-${idx}">${escapeHtml(f.status || "Needs Review")}</span></div>
          </div>`;
        list.appendChild(card);
      });

      list.querySelectorAll(".review-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
          const idx = Number(btn.getAttribute("data-idx"));
          openFindingModal(idx);
        });
      });

      document.getElementById("approveBtn").onclick = () => finalize("approved");
      document.getElementById("rejectBtn").onclick = () => finalize("rejected");
      const printBtn = document.getElementById("printBtn");
      if (printBtn) printBtn.addEventListener("click", () => window.print());
    }

    const findingModal = new bootstrap.Modal(document.getElementById("findingModal"));
    let activeFindingIdx = null;

    function openFindingModal(idx) {
      activeFindingIdx = idx;
      const f = findingsState[idx];
      if (!f) return;
      document.getElementById("mOriginal").textContent = f.original_text || "";
      document.getElementById("mType").textContent = f.issue_type || "";
      document.getElementById("mSeverity").textContent = f.severity || "";
      document.getElementById("mExplanation").textContent = f.explanation || "";
      document.getElementById("mRule").textContent = f.rule_reference || "";
      document.getElementById("mSuggestion").textContent = f.suggested_correction || "";
      document.getElementById("mNotes").value = "";
      findingModal.show();
    }

    async function sendDecision(decision) {
      if (currentReviewId === null) return;
      const review = await api(`/api/review/${currentReviewId}`);
      const dbFinding = review.findings[activeFindingIdx];
      if (!dbFinding) throw new Error("Finding not found.");
      const notes = document.getElementById("mNotes").value.trim();
      await api(`/api/finding/${dbFinding.id}/decision`, {
        method: "POST",
        body: JSON.stringify({ decision, notes }),
      });
      const statusMap = { accepted: "Accepted", rejected: "Rejected", resolved: "Resolved", needs_review: "Needs Review" };
      findingsState[activeFindingIdx].status = statusMap[decision];
      const badge = document.getElementById(`status-${activeFindingIdx}`);
      if (badge) badge.textContent = statusMap[decision];
      findingModal.hide();
    }

    document.getElementById("mAccept").addEventListener("click", () => sendDecision("accepted").catch((e) => alert(e.message)));
    document.getElementById("mReject").addEventListener("click", () => sendDecision("rejected").catch((e) => alert(e.message)));
    document.getElementById("mResolve").addEventListener("click", () => sendDecision("resolved").catch((e) => alert(e.message)));
    document.getElementById("mNeedsReview").addEventListener("click", () => sendDecision("needs_review").catch((e) => alert(e.message)));

    async function finalize(decision) {
      if (currentReviewId === null) return;
      const notes = document.getElementById("finalNotes").value.trim();
      try {
        await api(`/api/review/${currentReviewId}/finalize`, {
          method: "POST",
          body: JSON.stringify({ decision, notes }),
        });
        document.getElementById("finalizeMsg").textContent =
          decision === "approved" ? "Content approved and recorded." : "Content rejected and recorded.";
      } catch (e) {
        document.getElementById("finalizeMsg").textContent = e.message;
      }
    }
  }

  const historyBody = document.getElementById("historyBody");
  if (historyBody) {
    async function loadHistory() {
      const err = document.getElementById("historyError");
      err.classList.add("d-none");
      try {
        const data = await api("/api/history?limit=50");
        renderHistory(data.reviews || []);
      } catch (e) {
        err.textContent = e.message;
        err.classList.remove("d-none");
      }
    }

    function renderHistory(rows) {
      historyBody.innerHTML = "";
      document.getElementById("historyEmpty").classList.toggle("d-none", rows.length !== 0);
      rows.forEach((r) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td>${r.id}</td>
          <td>${escapeHtml(r.profile_name || "")}</td>
          <td>${escapeHtml(r.overall_status || "")}</td>
          <td>${r.total_issues}</td>
          <td>${escapeHtml(r.final_decision || "—")}</td>
          <td class="small">${escapeHtml(r.created_at || "")}</td>
          <td><button class="btn btn-sm btn-outline-secondary" data-id="${r.id}">View</button></td>`;
        historyBody.appendChild(tr);
      });
      historyBody.querySelectorAll("button[data-id]").forEach((btn) => {
        btn.addEventListener("click", () => viewReview(Number(btn.getAttribute("data-id"))));
      });
    }

    async function viewReview(id) {
      try {
        const data = await api(`/api/review/${id}`);
        const r = data.review;
        let html = `<p><strong>Profile:</strong> ${escapeHtml(data.profile_name)}</p>`;
        html += `<p><strong>Status:</strong> ${escapeHtml(r.overall_status)} &nbsp; <strong>Issues:</strong> ${r.total_issues}</p>`;
        html += `<p><strong>Final decision:</strong> ${escapeHtml(r.final_decision || "—")}</p>`;
        if (r.final_notes) html += `<p><strong>Notes:</strong> ${escapeHtml(r.final_notes)}</p>`;
        html += `<div class="mb-2 small text-muted">Submitted: ${escapeHtml(r.created_at)}</div>`;
        html += `<hr><h6>Findings</h6>`;
        if (!data.findings || data.findings.length === 0) {
          html += `<p class="text-muted">No findings.</p>`;
        } else {
          data.findings.forEach((f) => {
            html += `<div class="border rounded p-2 mb-2">
              <div class="mb-1"><span class="badge bg-secondary">${escapeHtml(f.issue_type)}</span> ${sevBadge(f.severity)}
                <span class="badge bg-light text-dark border ms-1">${escapeHtml(f.status)}</span>
                ${f.reviewer_decision ? `<span class="badge bg-info text-dark ms-1">${escapeHtml(f.reviewer_decision)}</span>` : ""}
              </div>
              <div class="finding-original mb-1">${escapeHtml(f.original_text)}</div>
              <div class="small">${escapeHtml(f.explanation)}</div>
              ${f.suggested_correction ? `<div class="small mt-1"><strong>Suggestion:</strong> ${escapeHtml(f.suggested_correction)}</div>` : ""}
              ${f.reviewer_notes ? `<div class="small mt-1 text-muted"><strong>Reviewer notes:</strong> ${escapeHtml(f.reviewer_notes)}</div>` : ""}
            </div>`;
          });
        }
        document.getElementById("historyModalBody").innerHTML = html;
        new bootstrap.Modal(document.getElementById("historyModal")).show();
      } catch (e) {
        alert(e.message);
      }
    }

    document.getElementById("refreshHistory").addEventListener("click", loadHistory);
    loadHistory();
  }
})();