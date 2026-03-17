const API_BASE = "https://seat-finder-api.harjeetgowda644.workers.dev";

// ---------- STUDENT LOOKUP ----------
function findSeat() {
  const reg = document.getElementById("reg").value.trim();
  const resultDiv = document.getElementById("result");

  resultDiv.innerHTML = "";

  if (!reg) {
    resultDiv.innerHTML = `<div class="error">Enter register number</div>`;
    return;
  }

  fetch(API_BASE + "/lookup", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reg })
  })
    .then(res => res.json().then(data => ({ status: res.status, data })))
    .then(({ status, data }) => {
      if (status !== 200) {
        resultDiv.innerHTML = `<div class="error">${data.error}</div>`;
        return;
      }

      let html = `<div class="results">`;

      if (data.FN) {
        html += `
          <div class="session-box">
            <div class="session-title">FN</div>
            <p><b>Name:</b> ${data.FN.name}</p>
            <p><b>Hall:</b> ${data.FN.hall}</p>
            <p><b>Seat:</b> ${data.FN.seat}</p>
           ${data.FN.side ? `<p class="side"><b>Side:</b> ${data.FN.side}</p>` : ""}
          </div>
        `;
      }

      if (data.AN) {
        html += `
          <div class="session-box">
            <div class="session-title">AN</div>
            <p><b>Name:</b> ${data.AN.name}</p>
            <p><b>Hall:</b> ${data.AN.hall}</p>
            <p><b>Seat:</b> ${data.AN.seat}</p>
            ${data.AN.side ? `<p class="side"><b>Side:</b> ${data.AN.side}</p>` : ""}
          </div>
        `;
      }

      html += `</div>`;
      resultDiv.innerHTML = html;
    })
    .catch(() => {
      resultDiv.innerHTML = `<div class="error">Server error</div>`;
    });
}
// ---------- LAST UPDATED INFO ----------
async function loadLastUpdated() {
  try {
    const res = await fetch(API_BASE + "/meta");
    const meta = await res.json();

    let text = "";

    if (meta.FN) {
      text += `FN Updated: ${new Date(meta.FN.uploaded_at).toLocaleString()}<br>`;
    }

    if (meta.AN) {
      text += `AN Updated: ${new Date(meta.AN.uploaded_at).toLocaleString()}`;
    }

    if (!text) {
      text = "Seating data not uploaded yet";
    }

    document.getElementById("lastUpdated").innerHTML = text;
  } catch (err) {
    document.getElementById("lastUpdated").innerText =
      "Unable to load seating update info";
  }
}

// load on page open
loadLastUpdated();

