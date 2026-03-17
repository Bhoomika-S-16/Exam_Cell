function findSeat(){
  const reg = document.getElementById("reg").value.trim();
  const result = document.getElementById("result");

  if(!reg){
    result.innerHTML = `<div class="error">Enter a register number</div>`;
    return;
  }

  result.innerHTML = "Searching...";

  fetch("/lookup", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({ reg })
  })
  .then(res => res.json())
  .then(data => {
    if(data.error){
      result.innerHTML = `<div class="error">${data.error}</div>`;
      return;
    }

    let html = `<div class="results">`;

    if(data.FN){
      html += `
        <div class="session-box">
          <div class="session-title">FN</div>
          <p><span>Name:</span> ${data.FN.name}</p>
          <p><span>Hall:</span> ${data.FN.hall}</p>
          <p><span>Seat:</span> ${data.FN.seat}</p>
        </div>
      `;
    }

    if(data.AN){
      html += `
        <div class="session-box">
          <div class="session-title">AN</div>
          <p><span>Name:</span> ${data.AN.name}</p>
          <p><span>Hall:</span> ${data.AN.hall}</p>
          <p><span>Seat:</span> ${data.AN.seat}</p>
        </div>
      `;
    }

    html += `</div>`;
    result.innerHTML = html;
  })
  .catch(() => {
    result.innerHTML = `<div class="error">Server error</div>`;
  });
}
