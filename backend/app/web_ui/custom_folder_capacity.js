const customFolderState={timer:null,requestId:0,report:null,suggestions:[],confirmed:true};

function customFormatBytes(value){
  if(!value)return "0 octet";
  const units=["octets","Ko","Mo","Go","To"];
  const index=Math.min(Math.floor(Math.log(value)/Math.log(1024)),units.length-1);
  return `${(value/(1024**index)).toLocaleString("fr-FR",{maximumFractionDigits:index?1:0})} ${units[index]}`;
}

function customModeActive(){
  return document.querySelector("#source-mode")?.value==="custom_folder";
}

function customSource(){
  return document.querySelector("#custom-source-root")?.value?.trim()??"";
}

function customDestination(){
  return document.querySelector("#backup-destination-custom")?.value?.trim()??"";
}

function selectedCustomExclusions(){
  return customFolderState.suggestions.filter(item=>item.selected);
}

function customExcludedSize(){
  return selectedCustomExclusions().reduce(
    (total,item)=>total+Number(item.size_bytes??0),0
  );
}

function ensureCustomFolderPanel(){
  let panel=document.querySelector("#custom-folder-diagnostic");
  if(panel)return panel;
  const form=document.querySelector("#backup-form");
  const options=form?.querySelector(".option-list");
  if(!form||!options)return null;
  panel=document.createElement("section");
  panel.id="custom-folder-diagnostic";
  panel.className="capacity-panel hidden";
  options.insertAdjacentElement("beforebegin",panel);
  return panel;
}

function syncCustomExclusionPayload(){
  const selected=selectedCustomExclusions();
  window.fsbackupApprovedExclusions=selected.map(item=>({
    path:item.path,
    reason:item.reason,
    risk:item.risk,
    approved_by_user:true,
  }));
  window.fsbackupExclusionsConfirmed=selected.length===0||customFolderState.confirmed;
}

function renderCustomFolderDiagnostic(){
  const panel=ensureCustomFolderPanel();
  const report=customFolderState.report;
  if(!panel||!report||!customModeActive())return;
  const excluded=customExcludedSize();
  const planned=Math.max(Number(report.size_bytes??0)-excluded,0);
  const destinationFree=Number(report.destination_disk?.free_bytes??0);
  const compatible=destinationFree>=planned&&planned>=0;
  const selected=selectedCustomExclusions();
  panel.className="capacity-panel";
  panel.hidden=false;
  panel.innerHTML=`
    <p class="eyebrow">Analyse du dossier personnalisé</p>
    <h3>Optimisation facultative</h3>
    <p>Aucune exclusion n’est active par défaut. Les exclusions proposées ci-dessous concernent uniquement le dossier choisi.</p>
    <div class="capacity-grid">
      <article class="capacity-card"><span>Taille du dossier source</span><strong>${customFormatBytes(report.size_bytes)}</strong><small>${Number(report.file_count??0).toLocaleString("fr-FR")} fichiers</small></article>
      <article class="capacity-card"><span>Exclusions sélectionnées</span><strong>${customFormatBytes(excluded)}</strong><small>${selected.length} dossier(s)</small></article>
      <article class="capacity-card"><span>Plan final estimé</span><strong>${customFormatBytes(planned)}</strong><small>Taille source moins les exclusions confirmées</small></article>
      <article class="capacity-card"><span>Destination disponible</span><strong>${customFormatBytes(destinationFree)}</strong><small>${report.destination_root??"Destination non renseignée"}</small></article>
    </div>
    <div class="custom-exclusion-list">${customFolderState.suggestions.length?customFolderState.suggestions.map((item,index)=>`
      <label class="exclusion-item">
        <input type="checkbox" data-custom-exclusion-index="${index}" ${item.selected?"checked":""}>
        <span><b>${item.pattern}</b><p class="exclusion-path">${item.path}</p><p>${item.reason}</p><div class="exclusion-meta"><span>${customFormatBytes(item.size_bytes)}</span><span>${Number(item.file_count??0).toLocaleString("fr-FR")} fichiers</span></div></span>
        <strong class="risk-badge risk-${item.risk}">Risque ${item.risk}</strong>
      </label>`).join(""):'<p>Aucune exclusion proposée dans ce dossier.</p>'}</div>
    ${selected.length?`<div class="exclusion-confirm"><strong>Validation séparée obligatoire</strong><p>${selected.length} exclusion(s) représentent ${customFormatBytes(excluded)}.</p><div class="exclusion-actions"><button id="confirm-custom-exclusions" type="button" class="submit-action">Confirmer les exclusions</button></div><small>${customFolderState.confirmed?"Exclusions confirmées":"Confirmation obligatoire"}</small></div>`:""}
    <p class="${compatible?"capacity-ok":"capacity-error"}">${compatible?`Destination compatible : ${customFormatBytes(destinationFree)} libres pour un plan estimé à ${customFormatBytes(planned)}.`:`Espace insuffisant ou destination non mesurable pour un plan estimé à ${customFormatBytes(planned)}.`}</p>`;
  panel.querySelectorAll("[data-custom-exclusion-index]").forEach(input=>input.addEventListener("change",()=>{
    customFolderState.suggestions[Number(input.dataset.customExclusionIndex)].selected=input.checked;
    customFolderState.confirmed=false;
    syncCustomExclusionPayload();
    renderCustomFolderDiagnostic();
  }));
  panel.querySelector("#confirm-custom-exclusions")?.addEventListener("click",()=>{
    customFolderState.confirmed=true;
    syncCustomExclusionPayload();
    renderCustomFolderDiagnostic();
  });
  syncCustomExclusionPayload();
  window.fsbackupDestinationCapacityValid=compatible;
}

async function runCustomFolderDiagnostic(){
  const panel=ensureCustomFolderPanel();
  if(!panel)return;
  if(!customModeActive()){
    panel.hidden=true;
    panel.classList.add("hidden");
    customFolderState.report=null;
    customFolderState.suggestions=[];
    customFolderState.confirmed=true;
    syncCustomExclusionPayload();
    return;
  }
  const source=customSource();
  const destination=customDestination();
  if(!source||!destination){
    panel.hidden=false;
    panel.className="capacity-panel";
    panel.innerHTML="<strong>Renseignez le dossier source et la destination pour lancer le calcul.</strong>";
    return;
  }
  const requestId=++customFolderState.requestId;
  panel.hidden=false;
  panel.className="capacity-panel";
  panel.innerHTML="<strong>Analyse du dossier personnalisé en cours…</strong><p>Comptage des fichiers, calcul de la taille et contrôle de la destination.</p>";
  try{
    const [diagnosticResponse,exclusionsResponse]=await Promise.all([
      fetch("/api/v1/sources/folder-diagnostic",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({source_root:source,destination_root:destination})}),
      fetch("/api/v1/sources/exclusions/suggestions",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({source_root:source})}),
    ]);
    const diagnostic=await diagnosticResponse.json();
    const exclusions=await exclusionsResponse.json();
    if(!diagnosticResponse.ok)throw new Error(diagnostic.detail??"Analyse impossible.");
    if(requestId!==customFolderState.requestId||!customModeActive())return;
    customFolderState.report=diagnostic;
    customFolderState.suggestions=(exclusionsResponse.ok?exclusions.suggestions??[]:[]).map(item=>({...item,selected:false}));
    customFolderState.confirmed=true;
    renderCustomFolderDiagnostic();
  }catch(error){
    if(requestId!==customFolderState.requestId)return;
    panel.innerHTML=`<div class="capacity-error">${error.message}</div>`;
    window.fsbackupDestinationCapacityValid=false;
  }
}

function scheduleCustomFolderDiagnostic(delay=300){
  if(customFolderState.timer)clearTimeout(customFolderState.timer);
  customFolderState.timer=setTimeout(()=>{
    customFolderState.timer=null;
    runCustomFolderDiagnostic();
  },delay);
}

function initCustomFolderDiagnostic(){
  ensureCustomFolderPanel();
  document.querySelector("#source-mode")?.addEventListener("change",()=>scheduleCustomFolderDiagnostic(0));
  document.querySelector("#custom-source-root")?.addEventListener("change",()=>scheduleCustomFolderDiagnostic());
  document.querySelector("#custom-source-root")?.addEventListener("blur",()=>scheduleCustomFolderDiagnostic());
  document.querySelector("#backup-destination-custom")?.addEventListener("change",()=>scheduleCustomFolderDiagnostic());
  document.querySelector("#backup-destination-custom")?.addEventListener("blur",()=>scheduleCustomFolderDiagnostic());
  document.querySelector("#backup-form")?.addEventListener("submit",event=>{
    if(!customModeActive())return;
    if(selectedCustomExclusions().length&&!customFolderState.confirmed){
      event.preventDefault();
      event.stopImmediatePropagation();
      ensureCustomFolderPanel()?.scrollIntoView({behavior:"smooth",block:"center"});
    }
  },true);
  scheduleCustomFolderDiagnostic(0);
}

if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",initCustomFolderDiagnostic);else initCustomFolderDiagnostic();
