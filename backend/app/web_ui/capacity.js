const capacityState={diagnostic:null,loading:false,initialized:false};

function capacityFormatBytes(value){
  if(!value)return "0 octet";
  const units=["octets","Ko","Mo","Go","To"];
  const index=Math.min(Math.floor(Math.log(value)/Math.log(1024)),units.length-1);
  return `${(value/(1024**index)).toLocaleString("fr-FR",{maximumFractionDigits:index?1:0})} ${units[index]}`;
}

function normalizeDriveRoot(value){
  const match=String(value??"").trim().match(/^([a-zA-Z]:)/);
  return match?`${match[1].toUpperCase()}\\`:"";
}

function selectedDestinationDrive(){
  const destination=document.querySelector("#destination-directory")?.value??"";
  const root=normalizeDriveRoot(destination);
  return (window.fsbackupDrives??[]).find(drive=>drive.root.toUpperCase()===root.toUpperCase())??null;
}

function ensureCapacityPanel(){
  let panel=document.querySelector("#backup-capacity-diagnostic");
  if(panel)return panel;
  const diagnostic=document.querySelector("#source-diagnostic");
  const form=document.querySelector("#backup-form");
  if(!form)return null;
  panel=document.createElement("section");
  panel.id="backup-capacity-diagnostic";
  panel.className="capacity-panel hidden";
  (diagnostic??form.querySelector(".form-grid"))?.insertAdjacentElement("afterend",panel);
  if(!document.querySelector("#capacity-styles")){
    const style=document.createElement("style");
    style.id="capacity-styles";
    style.textContent=`
      .capacity-panel{margin:1rem 0;padding:1.1rem;border:1px solid #dfe3f2;border-radius:16px;background:#fff}
      .capacity-panel.hidden{display:none}.capacity-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.7rem;margin-top:.8rem}
      .capacity-card{padding:.8rem;border:1px solid #e6e8f1;border-radius:12px;background:#f8f9ff}.capacity-card strong{display:block;margin:.25rem 0;font-size:1.1rem}
      .capacity-warning{margin-top:.8rem;padding:.8rem;border-radius:12px;background:#fff2d9;color:#714900}.capacity-error{margin-top:.8rem;padding:.8rem;border-radius:12px;background:#fde8e8;color:#941d1d}
      .capacity-ok{margin-top:.8rem;padding:.8rem;border-radius:12px;background:#e5f7ec;color:#176638}@media(max-width:1100px){.capacity-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:700px){.capacity-grid{grid-template-columns:1fr}}
    `;
    document.head.appendChild(style);
  }
  return panel;
}

function clarifyDiagnosticSummary(){
  document.querySelectorAll("#source-diagnostic .diagnostic-card").forEach(card=>{
    const label=card.querySelector("span");
    const small=card.querySelector("small");
    if(label?.textContent==="Espace libre conseillé"){
      label.textContent="Plan de base inclus";
      if(small)small.textContent="Avant profils complets, anciennes données et projets";
    }
    if(label?.textContent==="Taille personnelle estimée"&&small){
      small.textContent=`${small.textContent} dans les dossiers standards`;
    }
  });
}

function renderCapacityDiagnostic(){
  const panel=ensureCapacityPanel();
  const data=capacityState.diagnostic;
  if(!panel||!data)return;
  const disk=data.disk??{};
  const estimate=data.estimate??{};
  const destination=selectedDestinationDrive();
  const defaultPlanned=Number(estimate.planned_size_bytes??0);
  const additionalSize=Number(window.getSelectedAdditionalSize?.()??0);
  const recoverySize=Number(window.getSelectedRecoverySize?.()??0);
  const detectedRecoverySize=Number(window.getDetectedRecoverableProfileSize?.()??0);
  const planned=defaultPlanned+additionalSize+recoverySize;
  const maximumDetected=defaultPlanned+detectedRecoverySize+additionalSize;
  const usedBytes=Number(disk.used_bytes??0);
  const unexplainedBytes=Math.max(usedBytes-maximumDetected,0);
  const destinationFree=Number(destination?.free_bytes??0);
  const enough=Boolean(destination&&planned>0&&destinationFree>=planned);
  const destinationStatus=!destination
    ?'<div class="capacity-error">Destination inconnue : FSBackup ne peut pas vérifier l’espace disponible.</div>'
    :planned<=0
      ?'<div class="capacity-error">Le plan réel est vide ou indéterminé. La sauvegarde reste bloquée.</div>'
      :enough
        ?`<div class="capacity-ok">Destination compatible : ${capacityFormatBytes(destinationFree)} libres pour un plan estimé à ${capacityFormatBytes(planned)}.</div>`
        :`<div class="capacity-error">Espace insuffisant sur ${destination.label} : ${capacityFormatBytes(destinationFree)} libres pour ${capacityFormatBytes(planned)} prévus.</div>`;
  panel.className="capacity-panel";
  panel.innerHTML=`
    <p class="eyebrow">Périmètre réel de la sauvegarde</p><h3>Ce qui sera réellement inclus</h3>
    <div class="capacity-grid">
      <article class="capacity-card"><span>Capacité du lecteur source</span><strong>${capacityFormatBytes(disk.total_bytes)}</strong><small>${capacityFormatBytes(usedBytes)} utilisés · ${capacityFormatBytes(disk.free_bytes)} libres</small></article>
      <article class="capacity-card"><span>Dossiers standards inclus</span><strong>${capacityFormatBytes(estimate.total_size_bytes)}</strong><small>${Number(estimate.total_file_count??0).toLocaleString("fr-FR")} fichiers personnels</small></article>
      <article class="capacity-card"><span>Compléments de profils détectés</span><strong>${capacityFormatBytes(detectedRecoverySize)}</strong><small>AppData et autres fichiers accessibles, facultatifs</small></article>
      <article class="capacity-card"><span>Plan actuellement sélectionné</span><strong>${capacityFormatBytes(planned)}</strong><small>${capacityFormatBytes(defaultPlanned)} de base · ${capacityFormatBytes(recoverySize)} de profils · ${capacityFormatBytes(additionalSize)} de projets</small></article>
      <article class="capacity-card"><span>Total récupérable visible</span><strong>${capacityFormatBytes(maximumDetected)}</strong><small>Profils détectés et projets déjà cochés</small></article>
      <article class="capacity-card"><span>Données utilisées non classées</span><strong>${capacityFormatBytes(unexplainedBytes)}</strong><small>Système, programmes, fichiers protégés ou dossiers encore non mesurés</small></article>
      <article class="capacity-card"><span>Destination</span><strong>${destination?destination.label:"Inconnue"}</strong><small>${destination?`${capacityFormatBytes(destinationFree)} libres`:"Sélectionnez un lecteur détecté"}</small></article>
    </div>
    <div class="capacity-warning"><strong>Périmètre :</strong> le plan de base inclut les dossiers standards et les données reconnues. Cochez « compléter le profil » pour ajouter AppData et les autres fichiers accessibles. Les projets et anciens profils restent facultatifs. Windows et les programmes installés restent exclus.</div>
    ${destinationStatus}`;
  window.fsbackupDestinationCapacityValid=enough;
  clarifyDiagnosticSummary();
}

async function refreshCapacityDiagnostic(){
  const mode=document.querySelector("#source-mode")?.value;
  const source=document.querySelector("#source-root")?.value;
  const panel=ensureCapacityPanel();
  if(!panel)return;
  if(mode!=="windows_disk"||!source){panel.classList.add("hidden");return;}
  if(capacityState.loading)return;
  capacityState.loading=true;
  panel.className="capacity-panel";
  panel.innerHTML="<strong>Calcul du périmètre réel et contrôle de la destination…</strong>";
  try{
    const response=await fetch("/api/v1/sources/diagnostic",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({source_root:source})});
    const data=await response.json();
    if(!response.ok)throw new Error(data.detail??"Diagnostic impossible.");
    capacityState.diagnostic=data;
    renderCapacityDiagnostic();
    setTimeout(clarifyDiagnosticSummary,0);
  }catch(error){
    capacityState.diagnostic=null;
    window.fsbackupDestinationCapacityValid=false;
    panel.innerHTML=`<div class="capacity-error">${error.message}</div>`;
  }finally{capacityState.loading=false;}
}

function renameWindowsSourceMode(){
  const option=document.querySelector('#source-mode option[value="windows_disk"]');
  if(option)option.textContent="Données Windows récupérables";
}

function bindCapacityGuard(){
  const form=document.querySelector("#backup-form");
  if(!form)return;
  form.addEventListener("submit",event=>{
    if(document.querySelector("#source-mode")?.value!=="windows_disk")return;
    if(window.fsbackupDestinationCapacityValid===true)return;
    event.preventDefault();
    event.stopImmediatePropagation();
    ensureCapacityPanel()?.scrollIntoView({behavior:"smooth",block:"center"});
  },true);
}

function initCapacity(){
  if(capacityState.initialized)return;
  capacityState.initialized=true;
  renameWindowsSourceMode();
  ensureCapacityPanel();
  bindCapacityGuard();
  document.querySelector("#source-root")?.addEventListener("change",refreshCapacityDiagnostic);
  document.querySelector("#source-mode")?.addEventListener("change",refreshCapacityDiagnostic);
  document.querySelector("#backup-destination-drive")?.addEventListener("change",renderCapacityDiagnostic);
  window.addEventListener("fsbackup:destination-changed",renderCapacityDiagnostic);
  window.addEventListener("fsbackup:plan-selection-changed",renderCapacityDiagnostic);
  window.addEventListener("fsbackup:drives-loaded",refreshCapacityDiagnostic);
  setTimeout(refreshCapacityDiagnostic,0);
}

if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",initCapacity);else initCapacity();
