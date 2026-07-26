function inventoryFormatBytes(value){
  if(value===null||value===undefined)return "Non mesuré";
  if(!value)return "0 octet";
  const units=["octets","Ko","Mo","Go","To"];
  const index=Math.min(Math.floor(Math.log(value)/Math.log(1024)),units.length-1);
  return `${(value/(1024**index)).toLocaleString("fr-FR",{maximumFractionDigits:index?1:0})} ${units[index]}`;
}

const inventoryState={selectable:[],selected:new Set(),recovery:[],selectedRecovery:new Set()};
const inventoryLabels={
  "données_personnelles":"Données personnelles à la racine",
  "à_examiner":"Dossiers et projets à examiner",
  "système_non_inclus":"Éléments système non inclus",
  "ancienne_installation_windows":"Ancienne installation Windows"
};

window.getSelectedAdditionalPaths=()=>[...inventoryState.selected];
window.getSelectedAdditionalSize=()=>inventoryState.selectable
  .filter(item=>inventoryState.selected.has(item.path))
  .reduce((total,item)=>total+Number(item.size_bytes??0),0);
window.getSelectedRecoveryPaths=()=>[...inventoryState.selectedRecovery];
window.getSelectedRecoverySize=()=>inventoryState.recovery
  .filter(item=>inventoryState.selectedRecovery.has(item.path))
  .reduce((total,item)=>total+Number(item.profile_kind==="current"?item.additional_size_bytes:item.total_size_bytes),0);
window.getDetectedRecoverableProfileSize=()=>inventoryState.recovery
  .reduce((total,item)=>total+Number(item.profile_kind==="current"?item.additional_size_bytes:item.total_size_bytes),0);

function notifyInventorySelection(){
  window.dispatchEvent(new CustomEvent("fsbackup:plan-selection-changed"));
}

function ensureRootInventoryPanel(){
  let panel=document.querySelector("#root-inventory");
  if(panel)return panel;
  const diagnostic=document.querySelector("#source-diagnostic");
  if(!diagnostic)return null;
  panel=document.createElement("section");
  panel.id="root-inventory";
  panel.className="diagnostic-panel root-inventory-panel";
  diagnostic.insertAdjacentElement("afterend",panel);
  if(!document.querySelector("#root-inventory-styles")){
    const style=document.createElement("style");
    style.id="root-inventory-styles";
    style.textContent=`
      .root-inventory-panel{margin-top:1rem}.inventory-warning{padding:1rem;border:1px solid #efc66f;border-radius:14px;background:#fff8e8;margin-bottom:1rem}
      .inventory-group{margin-top:1rem}.inventory-group h3{margin-bottom:.6rem}.inventory-entry{padding:.8rem 0;border-top:1px solid #e2e5ef}
      .inventory-entry-head{display:flex;justify-content:space-between;gap:1rem}.inventory-path{font-family:ui-monospace,monospace;word-break:break-all;font-size:.84rem}
      .inventory-old{padding:.8rem;margin-top:.7rem;background:#fff;border:1px solid #e6e8f1;border-radius:12px}.inventory-select{display:flex;gap:.7rem;align-items:flex-start}.inventory-select input{margin-top:.25rem}
    `;
    document.head.appendChild(style);
  }
  return panel;
}

function selectableEntry(item){
  return item.category==="à_examiner"||item.category==="données_personnelles";
}

function renderInventoryEntry(item){
  const details=`<div><div class="inventory-entry-head"><b>${item.name}</b><span>${inventoryFormatBytes(item.size_bytes)}</span></div><div class="inventory-path">${item.path}</div><small>${item.reason}${item.file_count!==null&&item.file_count!==undefined?` · ${Number(item.file_count).toLocaleString("fr-FR")} fichiers`:""}</small></div>`;
  if(!selectableEntry(item))return `<div class="inventory-entry">${details}</div>`;
  return `<label class="inventory-entry inventory-select"><input type="checkbox" data-inventory-path="${encodeURIComponent(item.path)}"><span>${details}</span></label>`;
}

function renderRecoveryProfile(profile){
  const current=profile.profile_kind==="current";
  const addedSize=current?profile.additional_size_bytes:profile.total_size_bytes;
  const addedFiles=current?profile.additional_file_count:profile.total_file_count;
  const title=current?`${profile.name} — compléter le profil actuel`:`${profile.name} — ancien profil Windows`;
  const detail=current
    ?`${inventoryFormatBytes(profile.standard_size_bytes)} déjà inclus · ${inventoryFormatBytes(addedSize)} supplémentaires récupérables`
    :`${inventoryFormatBytes(profile.total_size_bytes)} récupérables dans Windows.old`;
  return `<label class="inventory-old inventory-select"><input type="checkbox" data-recovery-path="${encodeURIComponent(profile.path)}"><span><b>${title}</b><div class="inventory-path">${profile.path}</div><small>${detail} · ${Number(addedFiles).toLocaleString("fr-FR")} fichiers supplémentaires</small></span></label>`;
}

function renderRootInventory(report){
  const panel=ensureRootInventoryPanel();
  if(!panel)return;
  inventoryState.selected.clear();
  inventoryState.selectedRecovery.clear();
  inventoryState.selectable=(report.entries??[]).filter(selectableEntry);
  inventoryState.recovery=[...(report.current_windows_profiles??[]),...(report.old_windows_profiles??[])];
  const groups={};
  (report.entries??[]).forEach(item=>(groups[item.category]??=[]).push(item));
  const order=["données_personnelles","à_examiner","ancienne_installation_windows","système_non_inclus"];
  const currentProfiles=inventoryState.recovery.filter(item=>item.profile_kind==="current");
  const oldProfiles=inventoryState.recovery.filter(item=>item.profile_kind==="old");
  panel.innerHTML=`
    <p class="eyebrow">Périmètre du disque</p><h2>Inventaire des données récupérables</h2>
    <div class="inventory-warning"><strong>Les données standards sont incluses, les compléments restent facultatifs.</strong><p>Cochez un profil complet, un ancien profil ou un projet pour l’ajouter réellement au plan et à l’archive.</p></div>
    <div class="diagnostic-grid">
      <article class="diagnostic-card"><span>Projets sélectionnables</span><strong>${inventoryState.selectable.length}</strong><small>${inventoryFormatBytes(report.review_size_bytes)} détectés</small></article>
      <article class="diagnostic-card"><span>Compléments de profils</span><strong>${inventoryState.recovery.length}</strong><small>${inventoryFormatBytes(window.getDetectedRecoverableProfileSize())} récupérables en plus</small></article>
      <article class="diagnostic-card"><span>Éléments système</span><strong>${(groups["système_non_inclus"]??[]).length}</strong><small>Non sélectionnables</small></article>
    </div>
    ${currentProfiles.length?`<div class="inventory-group"><h3>Profils Windows actuels à compléter</h3><p>Les dossiers standards sont déjà inclus. Cette option ajoute AppData et les autres fichiers accessibles du profil.</p>${currentProfiles.map(renderRecoveryProfile).join("")}</div>`:""}
    ${oldProfiles.length?`<div class="inventory-group"><h3>Profils récupérables dans Windows.old</h3><p>Ces données ne sont jamais ajoutées sans sélection explicite.</p>${oldProfiles.map(renderRecoveryProfile).join("")}</div>`:""}
    ${order.map(category=>{const entries=groups[category]??[];if(!entries.length)return "";return `<div class="inventory-group"><h3>${inventoryLabels[category]}</h3>${entries.map(renderInventoryEntry).join("")}</div>`;}).join("")}`;
  panel.querySelectorAll("[data-inventory-path]").forEach(input=>input.addEventListener("change",()=>{
    const path=decodeURIComponent(input.dataset.inventoryPath);
    if(input.checked)inventoryState.selected.add(path);else inventoryState.selected.delete(path);
    notifyInventorySelection();
  }));
  panel.querySelectorAll("[data-recovery-path]").forEach(input=>input.addEventListener("change",()=>{
    const path=decodeURIComponent(input.dataset.recoveryPath);
    if(input.checked)inventoryState.selectedRecovery.add(path);else inventoryState.selectedRecovery.delete(path);
    notifyInventorySelection();
  }));
  notifyInventorySelection();
}

async function runRootInventory(){
  const mode=document.querySelector("#source-mode");
  const source=document.querySelector("#source-root");
  if(mode?.value!=="windows_disk"||!source?.value)return;
  const panel=ensureRootInventoryPanel();
  if(!panel){setTimeout(runRootInventory,100);return;}
  panel.innerHTML="<strong>Inventaire des profils et dossiers récupérables…</strong><p>Analyse en lecture seule, sans sélection automatique.</p>";
  try{
    const response=await fetch("/api/v1/sources/root-inventory",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({source_root:source.value})});
    const report=await response.json();
    if(!response.ok)throw new Error(report.detail??"Inventaire indisponible.");
    renderRootInventory(report);
  }catch(error){panel.innerHTML=`<strong>Inventaire indisponible</strong><p class="diagnostic-error">${error.message}</p>`;}
}

function initRootInventory(){
  document.querySelector("#source-root")?.addEventListener("change",()=>setTimeout(runRootInventory,0));
  document.querySelector("#source-mode")?.addEventListener("change",()=>setTimeout(runRootInventory,0));
  window.addEventListener("fsbackup:drives-loaded",()=>setTimeout(runRootInventory,0));
  setTimeout(runRootInventory,0);
}

if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",initRootInventory);else initRootInventory();
