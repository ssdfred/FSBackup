function diagnosticFormatBytes(value){
  if(!value)return "0 octet";
  const units=["octets","Ko","Mo","Go","To"];
  const index=Math.min(Math.floor(Math.log(value)/Math.log(1024)),units.length-1);
  return `${(value/(1024**index)).toLocaleString("fr-FR",{maximumFractionDigits:index?1:0})} ${units[index]}`;
}

function ensureDiagnosticPanel(){
  let panel=document.querySelector("#source-diagnostic");
  if(panel)return panel;
  const form=document.querySelector("#backup-form");
  const grid=form?.querySelector(".form-grid");
  if(!form||!grid)return null;
  panel=document.createElement("section");
  panel.id="source-diagnostic";
  panel.className="diagnostic-panel hidden";
  panel.setAttribute("aria-live","polite");
  grid.insertAdjacentElement("afterend",panel);
  if(!document.querySelector("#diagnostic-styles")){
    const style=document.createElement("style");
    style.id="diagnostic-styles";
    style.textContent=`
      .diagnostic-panel{margin:1.25rem 0;padding:1.25rem;border:1px solid #dfe3f2;border-radius:18px;background:#f8f9ff}
      .diagnostic-panel.loading{opacity:.75}
      .diagnostic-heading{display:flex;justify-content:space-between;gap:1rem;align-items:flex-start;margin-bottom:1rem}
      .diagnostic-heading h2{margin:.2rem 0}.diagnostic-badge{padding:.35rem .65rem;border-radius:999px;background:#e8ebff;color:#3f4bc1;font-weight:700}
      .diagnostic-badge.warning{background:#fff0d8;color:#925c00}.diagnostic-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.8rem}
      .diagnostic-card{background:white;border:1px solid #e6e8f1;border-radius:14px;padding:1rem}.diagnostic-card strong{display:block;font-size:1.2rem;margin:.25rem 0}
      .diagnostic-list{display:flex;flex-wrap:wrap;gap:.4rem;margin-top:.5rem}.diagnostic-list span{background:#eef0ff;border-radius:999px;padding:.28rem .55rem;font-size:.86rem}
      .diagnostic-users{margin-top:1rem}.diagnostic-user{padding:.7rem 0;border-top:1px solid #e2e5ef}.diagnostic-error{color:#a11b1b}
      @media(max-width:900px){.diagnostic-grid{grid-template-columns:1fr}}
    `;
    document.head.appendChild(style);
  }
  return panel;
}

function diagnosticNames(items,property="name"){
  return items?.length?items.map(item=>item[property]).join(", "):"Aucun";
}

function renderSourceDiagnostic(data){
  const panel=ensureDiagnosticPanel();
  if(!panel)return;
  const users=data.users??[];
  const applications=data.applications??[];
  const mail=data.messaging_profiles??[];
  const system=data.system??{};
  const markerText=data.markers.filter(item=>item.present).map(item=>item.name).join(", ")||"Aucun marqueur";
  panel.className="diagnostic-panel";
  panel.innerHTML=`
    <div class="diagnostic-heading">
      <div><p class="eyebrow">Diagnostic en lecture seule</p><h2>${data.windows_detected?"Installation Windows détectée":"Installation Windows incertaine"}</h2><p>${markerText}</p></div>
      <span class="diagnostic-badge ${data.windows_detected?"":"warning"}">Confiance ${data.confidence}</span>
    </div>
    <div class="diagnostic-grid">
      <article class="diagnostic-card"><span>Utilisateurs trouvés</span><strong>${users.length}</strong><small>${diagnosticNames(users)}</small></article>
      <article class="diagnostic-card"><span>Taille personnelle estimée</span><strong>${diagnosticFormatBytes(data.estimate.total_size_bytes)}</strong><small>${Number(data.estimate.total_file_count).toLocaleString("fr-FR")} fichiers</small></article>
      <article class="diagnostic-card"><span>Espace libre conseillé</span><strong>${diagnosticFormatBytes(data.estimate.required_free_space_bytes)}</strong><small>Avant toute exclusion</small></article>
      <article class="diagnostic-card"><span>Navigateurs</span><strong>${data.detected_browsers.length}</strong><div class="diagnostic-list">${data.detected_browsers.map(item=>`<span>${item}</span>`).join("")||"<small>Aucun détecté</small>"}</div></article>
      <article class="diagnostic-card"><span>Applications importantes</span><strong>${applications.length}</strong><div class="diagnostic-list">${applications.map(item=>`<span>${item.name}</span>`).join("")||"<small>Aucune détectée</small>"}</div></article>
      <article class="diagnostic-card"><span>Messageries</span><strong>${mail.length}</strong><div class="diagnostic-list">${mail.map(item=>`<span>${item.client} — ${item.user_name}</span>`).join("")||"<small>Aucune détectée</small>"}</div></article>
    </div>
    <div class="diagnostic-users">
      <strong>Profils et dossiers récupérables</strong>
      ${users.map(user=>`<div class="diagnostic-user"><b>${user.name}</b> — ${diagnosticFormatBytes(user.total_size_bytes)} — ${user.total_file_count.toLocaleString("fr-FR")} fichiers<br><small>${user.folders.filter(folder=>folder.present).map(folder=>`${folder.name}: ${diagnosticFormatBytes(folder.size_bytes)}`).join(" · ")||"Aucun dossier personnel détecté"}</small></div>`).join("")}
    </div>
    ${system.architecture||system.system_size_bytes?`<p><small>Système : ${system.architecture??"architecture inconnue"}${system.system_size_bytes?` · Windows ≈ ${diagnosticFormatBytes(system.system_size_bytes)}`:""}</small></p>`:""}
    ${data.warnings.length?`<p class="diagnostic-error"><small>${data.warnings.length} avertissement(s) pendant l’analyse. Les autres éléments ont continué à être inspectés.</small></p>`:""}
  `;
}

async function runSourceDiagnostic(){
  const mode=document.querySelector("#source-mode");
  const source=document.querySelector("#source-root");
  const panel=ensureDiagnosticPanel();
  if(!panel)return;
  if(mode?.value!=="windows_disk"||!source?.value){panel.classList.add("hidden");return;}
  panel.className="diagnostic-panel loading";
  panel.innerHTML="<strong>Analyse du disque en cours…</strong><p>Cette opération est strictement en lecture seule.</p>";
  try{
    const response=await fetch("/api/v1/sources/diagnostic",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({source_root:source.value})});
    const data=await response.json();
    if(!response.ok)throw new Error(data.detail??"Diagnostic impossible.");
    renderSourceDiagnostic(data);
  }catch(error){
    panel.className="diagnostic-panel";
    panel.innerHTML=`<strong>Diagnostic indisponible</strong><p class="diagnostic-error">${error.message}</p>`;
  }
}

document.addEventListener("DOMContentLoaded",()=>{
  ensureDiagnosticPanel();
  document.querySelector("#source-root")?.addEventListener("change",runSourceDiagnostic);
  document.querySelector("#source-mode")?.addEventListener("change",runSourceDiagnostic);
  window.addEventListener("fsbackup:drives-loaded",runSourceDiagnostic);
});
