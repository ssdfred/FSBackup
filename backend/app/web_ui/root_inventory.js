function inventoryFormatBytes(value){
  if(value===null||value===undefined)return "Non mesuré";
  if(!value)return "0 octet";
  const units=["octets","Ko","Mo","Go","To"];
  const index=Math.min(Math.floor(Math.log(value)/Math.log(1024)),units.length-1);
  return `${(value/(1024**index)).toLocaleString("fr-FR",{maximumFractionDigits:index?1:0})} ${units[index]}`;
}

const inventoryLabels={
  "données_personnelles":"Données personnelles à la racine",
  "à_examiner":"Dossiers et projets à examiner",
  "système_non_inclus":"Éléments système non inclus",
  "ancienne_installation_windows":"Ancienne installation Windows"
};

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
      .inventory-old{padding:.8rem;margin-top:.7rem;background:#fff;border:1px solid #e6e8f1;border-radius:12px}
    `;
    document.head.appendChild(style);
  }
  return panel;
}

function renderRootInventory(report){
  const panel=ensureRootInventoryPanel();
  if(!panel)return;
  const groups={};
  (report.entries??[]).forEach(item=>{
    (groups[item.category]??=[]).push(item);
  });
  const order=["données_personnelles","à_examiner","ancienne_installation_windows","système_non_inclus"];
  panel.innerHTML=`
    <p class="eyebrow">Périmètre du disque</p>
    <h2>Inventaire des dossiers à la racine</h2>
    <div class="inventory-warning"><strong>Ces dossiers ne sont pas automatiquement ajoutés.</strong><p>FSBackup les affiche pour éviter qu’un projet, une base de données ou une ancienne installation Windows soit oublié.</p></div>
    <div class="diagnostic-grid">
      <article class="diagnostic-card"><span>Dossiers à examiner</span><strong>${(groups["à_examiner"]??[]).length}</strong><small>${inventoryFormatBytes(report.review_size_bytes)} · ${Number(report.review_file_count??0).toLocaleString("fr-FR")} fichiers</small></article>
      <article class="diagnostic-card"><span>Anciennes installations</span><strong>${(groups["ancienne_installation_windows"]??[]).length}</strong><small>${(report.old_windows_profiles??[]).length} profil(s) utilisateur trouvé(s)</small></article>
      <article class="diagnostic-card"><span>Éléments système</span><strong>${(groups["système_non_inclus"]??[]).length}</strong><small>Affichés, mais non inclus par défaut</small></article>
    </div>
    ${order.map(category=>{
      const entries=groups[category]??[];
      if(!entries.length)return "";
      return `<div class="inventory-group"><h3>${inventoryLabels[category]}</h3>${entries.map(item=>`<div class="inventory-entry"><div class="inventory-entry-head"><b>${item.name}</b><span>${inventoryFormatBytes(item.size_bytes)}</span></div><div class="inventory-path">${item.path}</div><small>${item.reason}${item.file_count!==null&&item.file_count!==undefined?` · ${Number(item.file_count).toLocaleString("fr-FR")} fichiers`:""}</small></div>`).join("")}</div>`;
    }).join("")}
    ${(report.old_windows_profiles??[]).length?`<div class="inventory-group"><h3>Profils récupérables dans Windows.old</h3>${report.old_windows_profiles.map(profile=>`<div class="inventory-old"><b>${profile.name}</b><div class="inventory-path">${profile.path}</div><small>${inventoryFormatBytes(profile.personal_size_bytes)} · ${Number(profile.personal_file_count).toLocaleString("fr-FR")} fichiers personnels repérés</small></div>`).join("")}</div>`:""}
    ${(report.warnings??[]).length?`<p class="diagnostic-error"><small>${report.warnings.length} avertissement(s) pendant cet inventaire.</small></p>`:""}
  `;
}

async function runRootInventory(){
  const mode=document.querySelector("#source-mode");
  const source=document.querySelector("#source-root");
  if(mode?.value!=="windows_disk"||!source?.value)return;
  const panel=ensureRootInventoryPanel();
  if(!panel){setTimeout(runRootInventory,100);return;}
  panel.innerHTML="<strong>Inventaire des dossiers de la racine…</strong><p>Analyse en lecture seule, sans sélection automatique.</p>";
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

if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",initRootInventory);
else initRootInventory();
