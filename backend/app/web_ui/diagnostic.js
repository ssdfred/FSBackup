function diagnosticFormatBytes(value){
  if(!value)return "0 octet";
  const units=["octets","Ko","Mo","Go","To"];
  const index=Math.min(Math.floor(Math.log(value)/Math.log(1024)),units.length-1);
  return `${(value/(1024**index)).toLocaleString("fr-FR",{maximumFractionDigits:index?1:0})} ${units[index]}`;
}

const exclusionState={suggestions:[],confirmed:false,sourceRoot:"",sourceSize:0};

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
      .diagnostic-panel.loading{opacity:.75}.diagnostic-heading{display:flex;justify-content:space-between;gap:1rem;align-items:flex-start;margin-bottom:1rem}
      .diagnostic-heading h2{margin:.2rem 0}.diagnostic-badge{padding:.35rem .65rem;border-radius:999px;background:#e8ebff;color:#3f4bc1;font-weight:700}
      .diagnostic-badge.warning{background:#fff0d8;color:#925c00}.diagnostic-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.8rem}
      .diagnostic-card{background:white;border:1px solid #e6e8f1;border-radius:14px;padding:1rem}.diagnostic-card strong{display:block;font-size:1.2rem;margin:.25rem 0}
      .diagnostic-list{display:flex;flex-wrap:wrap;gap:.4rem;margin-top:.5rem}.diagnostic-list span{background:#eef0ff;border-radius:999px;padding:.28rem .55rem;font-size:.86rem}
      .diagnostic-users{margin-top:1rem}.diagnostic-user{padding:.7rem 0;border-top:1px solid #e2e5ef}.diagnostic-error{color:#a11b1b}
      .exclusion-panel{margin-top:1.25rem;padding-top:1.25rem;border-top:1px solid #dfe3f2}.exclusion-summary{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.75rem;margin:1rem 0}
      .exclusion-summary div{padding:.8rem;background:#fff;border:1px solid #e6e8f1;border-radius:12px}.exclusion-summary strong{display:block;margin-top:.25rem}
      .exclusion-item{display:grid;grid-template-columns:auto 1fr auto;gap:.8rem;align-items:start;padding:1rem;margin:.7rem 0;background:#fff;border:1px solid #e6e8f1;border-radius:14px}
      .exclusion-item input{margin-top:.25rem}.exclusion-item p{margin:.25rem 0}.exclusion-meta{display:flex;flex-wrap:wrap;gap:.45rem;margin-top:.45rem}.risk-badge{border-radius:999px;padding:.2rem .5rem;font-size:.8rem;font-weight:700}
      .risk-faible{background:#e5f7ec;color:#176638}.risk-moyen{background:#fff2d9;color:#8a5900}.risk-élevé{background:#fde8e8;color:#a11b1b}.exclusion-path{word-break:break-all;font-family:ui-monospace,monospace;font-size:.85rem}
      .exclusion-confirm{margin-top:1rem;padding:1rem;border:1px solid #efc66f;border-radius:14px;background:#fff8e8}.exclusion-confirm.hidden{display:none}.exclusion-actions{display:flex;gap:.7rem;justify-content:flex-end;margin-top:.8rem}
      @media(max-width:900px){.diagnostic-grid,.exclusion-summary{grid-template-columns:1fr}.exclusion-item{grid-template-columns:auto 1fr}.exclusion-item>strong{grid-column:2}}
    `;
    document.head.appendChild(style);
  }
  return panel;
}

function diagnosticNames(items,property="name"){
  return items?.length?items.map(item=>item[property]).join(", "):"Aucun";
}

function selectedExclusions(){
  return exclusionState.suggestions.filter(item=>item.selected);
}

function updateExclusionSummary(){
  const selected=selectedExclusions();
  const selectedSize=selected.reduce((total,item)=>total+item.size_bytes,0);
  const selectedFiles=selected.reduce((total,item)=>total+item.file_count,0);
  const after=Math.max(0,exclusionState.sourceSize-selectedSize);
  const count=document.querySelector("#exclusion-selected-count");
  const size=document.querySelector("#exclusion-selected-size");
  const afterElement=document.querySelector("#exclusion-after-size");
  if(count)count.textContent=`${selected.length} dossier(s) — ${selectedFiles.toLocaleString("fr-FR")} fichiers`;
  if(size)size.textContent=diagnosticFormatBytes(selectedSize);
  if(afterElement)afterElement.textContent=diagnosticFormatBytes(after);
  const confirmation=document.querySelector("#exclusion-confirmation");
  if(confirmation){
    confirmation.classList.toggle("hidden",selected.length===0);
    confirmation.querySelector("p").textContent=`Vous avez choisi d’exclure ${selected.length} dossier(s) représentant environ ${diagnosticFormatBytes(selectedSize)}. Ces données ne seront pas présentes dans l’archive.`;
  }
  const status=document.querySelector("#exclusion-confirmation-status");
  if(status)status.textContent=exclusionState.confirmed?"Exclusions confirmées":"Confirmation obligatoire";
}

function renderExclusions(report){
  const host=document.querySelector("#exclusion-suggestions");
  if(!host)return;
  exclusionState.suggestions=(report.suggestions??[]).map(item=>({...item,selected:false}));
  exclusionState.confirmed=false;
  if(!exclusionState.suggestions.length){
    host.innerHTML='<div class="exclusion-panel"><h3>Exclusions proposées</h3><p>Aucune exclusion sûre et conditionnelle n’a été détectée. En cas de doute, FSBackup sauvegarde les fichiers.</p></div>';
    return;
  }
  host.innerHTML=`
    <div class="exclusion-panel">
      <p class="eyebrow">Optimisation facultative</p><h3>Exclusions proposées</h3>
      <p>Aucune exclusion n’est active par défaut. Cochez uniquement les dossiers que vous acceptez de ne pas inclure.</p>
      <div class="exclusion-summary"><div>Source estimée<strong>${diagnosticFormatBytes(exclusionState.sourceSize)}</strong></div><div>Sélection<strong id="exclusion-selected-size">0 octet</strong><small id="exclusion-selected-count">0 dossier</small></div><div>Après exclusions<strong id="exclusion-after-size">${diagnosticFormatBytes(exclusionState.sourceSize)}</strong></div></div>
      <div>${exclusionState.suggestions.map((item,index)=>`
        <label class="exclusion-item">
          <input type="checkbox" data-exclusion-index="${index}">
          <span><b>${item.pattern}</b><p class="exclusion-path">${item.path}</p><p>${item.reason}</p><div class="exclusion-meta"><span>${diagnosticFormatBytes(item.size_bytes)}</span><span>${item.file_count.toLocaleString("fr-FR")} fichiers</span><span>${item.category.replaceAll("_"," ")}</span></div></span>
          <strong class="risk-badge risk-${item.risk}">Risque ${item.risk}</strong>
        </label>`).join("")}</div>
      <div id="exclusion-confirmation" class="exclusion-confirm hidden"><strong>Validation séparée obligatoire</strong><p></p><div class="exclusion-actions"><button id="cancel-exclusions" type="button" class="secondary-action">Retour à la sélection</button><button id="confirm-exclusions" type="button" class="submit-action">Confirmer les exclusions</button></div><small id="exclusion-confirmation-status">Confirmation obligatoire</small></div>
    </div>`;
  host.querySelectorAll("[data-exclusion-index]").forEach(input=>input.addEventListener("change",()=>{
    exclusionState.suggestions[Number(input.dataset.exclusionIndex)].selected=input.checked;
    exclusionState.confirmed=false;
    updateExclusionSummary();
  }));
  document.querySelector("#cancel-exclusions")?.addEventListener("click",()=>{
    exclusionState.confirmed=false;
    document.querySelector("#exclusion-suggestions")?.scrollIntoView({behavior:"smooth",block:"center"});
    updateExclusionSummary();
  });
  document.querySelector("#confirm-exclusions")?.addEventListener("click",()=>{
    if(!selectedExclusions().length)return;
    exclusionState.confirmed=true;
    updateExclusionSummary();
    document.querySelector("#submit-backup")?.focus();
  });
  updateExclusionSummary();
}

async function loadExclusionSuggestions(sourceRoot){
  const host=document.querySelector("#exclusion-suggestions");
  if(!host)return;
  host.innerHTML='<div class="exclusion-panel"><strong>Recherche des exclusions proposées…</strong><p>Analyse en lecture seule, sans sélection automatique.</p></div>';
  try{
    const response=await fetch("/api/v1/sources/exclusions/suggestions",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({source_root:sourceRoot})});
    const report=await response.json();
    if(!response.ok)throw new Error(report.detail??"Suggestions indisponibles.");
    renderExclusions(report);
  }catch(error){host.innerHTML=`<div class="exclusion-panel"><strong>Suggestions indisponibles</strong><p class="diagnostic-error">${error.message}</p></div>`;}
}

function renderSourceDiagnostic(data){
  const panel=ensureDiagnosticPanel();
  if(!panel)return;
  const users=data.users??[];
  const applications=data.applications??[];
  const mail=data.messaging_profiles??[];
  const system=data.system??{};
  exclusionState.sourceRoot=data.source_root;
  exclusionState.sourceSize=data.estimate?.total_size_bytes??0;
  exclusionState.confirmed=false;
  const markerText=data.markers.filter(item=>item.present).map(item=>item.name).join(", ")||"Aucun marqueur";
  panel.className="diagnostic-panel";
  panel.innerHTML=`
    <div class="diagnostic-heading"><div><p class="eyebrow">Diagnostic en lecture seule</p><h2>${data.windows_detected?"Installation Windows détectée":"Installation Windows incertaine"}</h2><p>${markerText}</p></div><span class="diagnostic-badge ${data.windows_detected?"":"warning"}">Confiance ${data.confidence}</span></div>
    <div class="diagnostic-grid">
      <article class="diagnostic-card"><span>Utilisateurs trouvés</span><strong>${users.length}</strong><small>${diagnosticNames(users)}</small></article>
      <article class="diagnostic-card"><span>Taille personnelle estimée</span><strong>${diagnosticFormatBytes(data.estimate.total_size_bytes)}</strong><small>${Number(data.estimate.total_file_count).toLocaleString("fr-FR")} fichiers</small></article>
      <article class="diagnostic-card"><span>Espace libre conseillé</span><strong>${diagnosticFormatBytes(data.estimate.required_free_space_bytes)}</strong><small>Avant toute exclusion</small></article>
      <article class="diagnostic-card"><span>Navigateurs</span><strong>${data.detected_browsers.length}</strong><div class="diagnostic-list">${data.detected_browsers.map(item=>`<span>${item}</span>`).join("")||"<small>Aucun détecté</small>"}</div></article>
      <article class="diagnostic-card"><span>Applications importantes</span><strong>${applications.length}</strong><div class="diagnostic-list">${applications.map(item=>`<span>${item.name}</span>`).join("")||"<small>Aucune détectée</small>"}</div></article>
      <article class="diagnostic-card"><span>Messageries</span><strong>${mail.length}</strong><div class="diagnostic-list">${mail.map(item=>`<span>${item.client} — ${item.user_name}</span>`).join("")||"<small>Aucune détectée</small>"}</div></article>
    </div>
    <div class="diagnostic-users"><strong>Profils et dossiers récupérables</strong>${users.map(user=>`<div class="diagnostic-user"><b>${user.name}</b> — ${diagnosticFormatBytes(user.total_size_bytes)} — ${user.total_file_count.toLocaleString("fr-FR")} fichiers<br><small>${user.folders.filter(folder=>folder.present).map(folder=>`${folder.name}: ${diagnosticFormatBytes(folder.size_bytes)}`).join(" · ")||"Aucun dossier personnel détecté"}</small></div>`).join("")}</div>
    ${system.architecture||system.system_size_bytes?`<p><small>Système : ${system.architecture??"architecture inconnue"}${system.system_size_bytes?` · Windows ≈ ${diagnosticFormatBytes(system.system_size_bytes)}`:""}</small></p>`:""}
    ${data.warnings.length?`<p class="diagnostic-error"><small>${data.warnings.length} avertissement(s) pendant l’analyse. Les autres éléments ont continué à être inspectés.</small></p>`:""}
    <div id="exclusion-suggestions"></div>`;
  loadExclusionSuggestions(data.source_root);
}

async function runSourceDiagnostic(){
  const mode=document.querySelector("#source-mode");
  const source=document.querySelector("#source-root");
  const panel=ensureDiagnosticPanel();
  exclusionState.suggestions=[];exclusionState.confirmed=false;exclusionState.sourceRoot="";
  if(!panel)return;
  if(mode?.value!=="windows_disk"||!source?.value){panel.classList.add("hidden");return;}
  panel.className="diagnostic-panel loading";
  panel.innerHTML="<strong>Analyse du disque en cours…</strong><p>Cette opération est strictement en lecture seule.</p>";
  try{
    const response=await fetch("/api/v1/sources/diagnostic",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({source_root:source.value})});
    const data=await response.json();
    if(!response.ok)throw new Error(data.detail??"Diagnostic impossible.");
    renderSourceDiagnostic(data);
  }catch(error){panel.className="diagnostic-panel";panel.innerHTML=`<strong>Diagnostic indisponible</strong><p class="diagnostic-error">${error.message}</p>`;}
}

function bindSafeExclusionSubmission(){
  const form=document.querySelector("#backup-form");
  if(!form)return;
  form.addEventListener("submit",event=>{
    const selected=selectedExclusions();
    if(selected.length&&!exclusionState.confirmed){
      event.preventDefault();event.stopImmediatePropagation();
      const confirmation=document.querySelector("#exclusion-confirmation");
      confirmation?.classList.remove("hidden");
      confirmation?.scrollIntoView({behavior:"smooth",block:"center"});
      document.querySelector("#exclusion-confirmation-status").textContent="Confirmez séparément avant de lancer la sauvegarde";
    }
  },true);
  const originalFetch=window.fetch.bind(window);
  window.fetch=async(input,init={})=>{
    const url=typeof input==="string"?input:input.url;
    if(url.includes("/api/v1/backup/run")&&init.body){
      try{
        const payload=JSON.parse(init.body);
        const selected=selectedExclusions();
        payload.approved_exclusions=selected.map(item=>({path:item.path,reason:item.reason,risk:item.risk,approved_by_user:true}));
        payload.exclusions_confirmed=selected.length>0&&exclusionState.confirmed;
        init={...init,body:JSON.stringify(payload)};
      }catch(_error){/* Le backend validera la requête originale. */}
    }
    return originalFetch(input,init);
  };
}

document.addEventListener("DOMContentLoaded",()=>{
  ensureDiagnosticPanel();bindSafeExclusionSubmission();
  document.querySelector("#source-root")?.addEventListener("change",runSourceDiagnostic);
  document.querySelector("#source-mode")?.addEventListener("change",runSourceDiagnostic);
  window.addEventListener("fsbackup:drives-loaded",runSourceDiagnostic);
});
