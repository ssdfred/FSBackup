const descriptions={backup:"Créer une archive complète, compressée et éventuellement chiffrée.",catalog:"Parcourir et contrôler les archives disponibles sur ce poste.",restore:"Vérifier puis restaurer une sauvegarde dans un dossier choisi.",retention_simulation:"Prévisualiser les archives à conserver ou à supprimer.",retention_execution:"Supprimer uniquement les archives confirmées par l’utilisateur."};
const icons={backup:"↥",catalog:"▣",restore:"↺",retention_simulation:"◷",retention_execution:"!"};
const labels={backup:"Nouvelle sauvegarde",catalog:"Mes sauvegardes",restore:"Restaurer",retention_simulation:"Simuler la rétention",retention_execution:"Exécuter la rétention"};
const views={backup:"backup",catalog:"archives",restore:"restore",retention_simulation:"retention",retention_execution:"retention"};

function showView(name){
  document.querySelectorAll(".view").forEach(view=>view.classList.toggle("active-view",view.id===`${name}-view`));
  document.querySelectorAll(".sidebar nav a").forEach(link=>link.classList.toggle("active",link.dataset.view===name));
  window.location.hash=name;
  window.scrollTo({top:0,behavior:"smooth"});
}

function bindNavigation(){
  document.querySelectorAll("[data-view]").forEach(element=>{
    if(element.dataset.bound)return;
    element.dataset.bound="true";
    element.addEventListener("click",event=>{event.preventDefault();showView(element.dataset.view);});
  });
}

async function loadDashboard(){
  const status=document.querySelector("#api-status");
  const dot=document.querySelector("#api-dot");
  const container=document.querySelector("#capabilities");
  try{
    const response=await fetch("/api/v1/dashboard/summary");
    if(!response.ok)throw new Error("API indisponible");
    const data=await response.json();
    dot.className="status-dot online";
    status.textContent="Moteur connecté";
    document.querySelector("#engine-state").textContent=data.status==="ready"?"Prêt":"Indisponible";
    document.querySelector("#api-version").textContent=`API ${data.api_version}`;
    document.querySelector("#capability-count").textContent=data.capabilities.length;
    document.querySelector("#destructive-count").textContent=data.capabilities.filter(item=>item.destructive).length;
    container.innerHTML=data.capabilities.map(item=>{
      const view=views[item.key];
      return `<article class="capability-card ${item.destructive?"danger":""}"><div class="icon">${icons[item.key]??"•"}</div><h3>${labels[item.key]??item.label}</h3><p>${descriptions[item.key]??item.label}</p><a href="#${view??item.key}" ${view?`data-view="${view}"`:""}>${item.destructive?"Action protégée":"Ouvrir"} →</a></article>`;
    }).join("");
    bindNavigation();
  }catch(error){
    dot.className="status-dot offline";
    status.textContent="Moteur indisponible";
    document.querySelector("#engine-state").textContent="Hors ligne";
    container.innerHTML=`<article class="capability-card danger"><h3>Connexion impossible</h3><p>${error.message}. Vérifiez que le backend FSBackup est démarré.</p></article>`;
  }
}

function setMessage(text,type=""){
  const message=document.querySelector("#backup-message");
  message.textContent=text;
  message.className=`message ${type}`;
}

function setProgress(step,title,percent,state="En cours"){
  const panel=document.querySelector("#backup-progress");
  panel.classList.remove("hidden");
  panel.classList.remove("failed");
  document.querySelector("#progress-title").textContent=title;
  document.querySelector("#progress-state").textContent=state;
  document.querySelector("#progress-bar").style.width=`${percent}%`;
  const order=["prepare","copy","archive","verify"];
  const current=order.indexOf(step);
  document.querySelectorAll(".progress-steps li").forEach((item,index)=>{
    item.classList.toggle("done",index<current);
    item.classList.toggle("active",index===current);
  });
}

function renderReport(data,verified){
  const report=document.querySelector("#backup-report");
  report.classList.remove("hidden");
  document.querySelector("#report-path").textContent=data.archive_path??"Archive créée";
  document.querySelector("#report-files").textContent=data.copied_files??0;
  document.querySelector("#report-integrity").textContent=verified?(data.integrity_report?.valid===false?"Échec":"Validée"):"Non demandée";
  document.querySelector("#report-warnings").textContent=data.warnings?.length??0;
}

function resetBackupResult(){
  document.querySelector("#backup-progress").classList.add("hidden");
  document.querySelector("#backup-report").classList.add("hidden");
  document.querySelector("#backup-message").className="message hidden";
  document.querySelector("#progress-bar").style.width="0%";
}

function bindBackupForm(){
  const encryption=document.querySelector("#enable-encryption");
  const segmentation=document.querySelector("#enable-segmentation");
  const segmentSizeField=document.querySelector("#segment-size-field");
  const verifyIntegrity=document.querySelector("#verify-integrity");
  const passwordFields=document.querySelector("#password-fields");
  const sourceMode=document.querySelector("#source-mode");
  const driveField=document.querySelector("#source-drive-field");
  const folderField=document.querySelector("#source-folder-field");
  const customSource=document.querySelector("#custom-source-root");
  encryption.addEventListener("change",()=>passwordFields.classList.toggle("hidden",!encryption.checked));
  const syncSegmentation=()=>{
    segmentSizeField.classList.toggle("hidden",!segmentation.checked);
    verifyIntegrity.checked=segmentation.checked||verifyIntegrity.checked;
    verifyIntegrity.disabled=segmentation.checked;
  };
  segmentation.addEventListener("change",syncSegmentation);
  syncSegmentation();
  sourceMode.addEventListener("change",()=>{
    const custom=sourceMode.value==="custom_folder";
    driveField.classList.toggle("hidden",custom);
    folderField.classList.toggle("hidden",!custom);
    customSource.required=custom;
  });
  document.querySelector("#new-backup").addEventListener("click",()=>{resetBackupResult();document.querySelector("#backup-form").scrollIntoView({behavior:"smooth"});});
  document.querySelector("#backup-form").addEventListener("submit",async event=>{
    event.preventDefault();
    resetBackupResult();
    const submit=document.querySelector("#submit-backup");
    const password=document.querySelector("#encryption-password").value;
    const confirmation=document.querySelector("#encryption-confirmation").value;
    if(encryption.checked&&password!==confirmation){setMessage("Les mots de passe ne correspondent pas.","error");return;}
    if(encryption.checked&&password.length<8){setMessage("Le mot de passe doit contenir au moins 8 caractères.","error");return;}
    const level=Number(document.querySelector("#compression-level").value);
    const verify=verifyIntegrity.checked;
    const mode=sourceMode.value;
    const sourceRoot=(mode==="custom_folder"?customSource.value:document.querySelector("#source-root").value).trim();
    if(!sourceRoot){setMessage("Sélectionnez une source à sauvegarder.","error");return;}
    const segmented=segmentation.checked;
    const payload={source_root:sourceRoot,source_mode:mode,destination_directory:document.querySelector("#destination-directory").value.trim(),archive_name:document.querySelector("#archive-name").value.trim(),compression:{method:level===0?"stored":"deflated",level},encryption:encryption.checked?{password}:null,verify_integrity:verify,segmented,segment_size_bytes:Number(document.querySelector("#segment-size").value),resume:true};
    submit.disabled=true;
    submit.textContent="Sauvegarde en cours…";
    setProgress("prepare","Analyse de la demande",12);
    const copyTimer=setTimeout(()=>setProgress("copy","Copie des fichiers",38),180);
    const archiveTimer=setTimeout(()=>setProgress("archive","Création de l’archive",66),650);
    const verifyTimer=setTimeout(()=>setProgress("verify",verify?"Vérification de l’intégrité":"Finalisation",86),1200);
    try{
      const response=await fetch("/api/v1/backup/run",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});
      const data=await response.json();
      if(!response.ok)throw new Error(data.error?.message??"La requête a échoué.");
      if(!data.success){
        const preserved=data.total_segments?` ${data.completed_segments} lot(s) sur ${data.total_segments} sont déjà sécurisés. Relancez la même sauvegarde pour reprendre.`:"";
        throw new Error(`${data.error??"La sauvegarde n’a pas pu être créée."}${preserved}`);
      }
      setProgress("verify","Sauvegarde terminée",100,"Terminée");
      document.querySelectorAll(".progress-steps li").forEach(item=>{item.classList.add("done");item.classList.remove("active");});
      const resumeMessage=data.resumed_segments?` ${data.resumed_segments} lot(s) déjà validé(s) ont été réutilisé(s).`:"";
      setMessage(segmented?`Le jeu de sauvegarde a été créé avec ${data.completed_segments} lot(s).${resumeMessage}`:"La sauvegarde a été créée avec succès.","success");
      renderReport(data,verify);
    }catch(error){document.querySelector("#progress-state").textContent="Échec";document.querySelector("#backup-progress").classList.add("failed");setMessage(error.message,"error");}
    finally{[copyTimer,archiveTimer,verifyTimer].forEach(clearTimeout);submit.disabled=false;submit.textContent="Lancer la sauvegarde";}
  });
}

function formatBytes(value){
  if(!value)return "0 octet";
  const units=["octets","Ko","Mo","Go","To"];
  const index=Math.min(Math.floor(Math.log(value)/Math.log(1024)),units.length-1);
  const amount=value/(1024**index);
  return `${amount.toLocaleString("fr-FR",{maximumFractionDigits:index?1:0})} ${units[index]}`;
}

function formatDate(value){
  if(!value)return "Date inconnue";
  return new Intl.DateTimeFormat("fr-FR",{dateStyle:"medium",timeStyle:"short"}).format(new Date(value));
}

function catalogStatus(entry){
  if(entry.status==="valid")return ["Valide","valid"];
  if(entry.status==="password_required")return ["Mot de passe requis","locked"];
  return ["Invalide","invalid"];
}

function catalogActionIcon(kind){
  if(kind==="folder")return '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3.5 6.5h6l1.75 2h9.25v9.75a2 2 0 0 1-2 2h-13a2 2 0 0 1-2-2z"/><path d="M8 12h8"/></svg>';
  return '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="8" y="8" width="10" height="11" rx="2"/><path d="M6 16H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>';
}

function catalogMessage(text,type="success"){
  const message=document.querySelector("#catalog-message");
  message.textContent=text;
  message.className=`message ${type}`;
}

function prepareRestoreFromCatalog(path){
  const mode=document.querySelector("#restore-archive-mode");
  const custom=document.querySelector("#restore-archive-custom");
  const archive=document.querySelector("#restore-archive");
  mode.value="custom";
  mode.dispatchEvent(new Event("change",{bubbles:true}));
  custom.value=path;
  custom.dispatchEvent(new Event("input",{bubbles:true}));
  custom.dispatchEvent(new Event("change",{bubbles:true}));
  archive.value=path;
  document.querySelector("#restore-message").className="message hidden";
  document.querySelector("#restore-report").classList.add("hidden");
  showView("restore");
  custom.focus();
}

async function copyCatalogPath(path){
  try{
    await navigator.clipboard.writeText(path);
    catalogMessage("Le chemin de l’archive a été copié.");
  }catch(error){
    catalogMessage(`Impossible de copier le chemin : ${error.message}`,"error");
  }
}

async function openCatalogLocation(path,button){
  button.disabled=true;
  try{
    const response=await fetch("/api/v1/system/picker/open",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({path})});
    const report=await response.json();
    if(!response.ok||!report.success)throw new Error(report.error??"Impossible d’ouvrir le dossier.");
    catalogMessage("Le dossier de l’archive a été ouvert.");
  }catch(error){
    catalogMessage(error.message,"error");
  }finally{
    button.disabled=false;
  }
}

function renderCatalog(data){
  document.querySelector("#catalog-summary").classList.remove("hidden");
  document.querySelector("#catalog-total").textContent=data.summary.total;
  document.querySelector("#catalog-size").textContent=formatBytes(data.summary.total_size_bytes);
  document.querySelector("#catalog-valid").textContent=data.summary.valid;
  document.querySelector("#catalog-alerts").textContent=data.summary.invalid+data.summary.password_required;
  const list=document.querySelector("#catalog-list");
  if(!data.archives.length){list.innerHTML='<div class="empty-state"><strong>Aucune archive trouvée</strong><p>Le dossier ne contient aucun fichier .fsb ou .fsbe.</p></div>';return;}
  list.innerHTML=data.archives.map(entry=>{
    const [label,status]=catalogStatus(entry);
    const encoded=encodeURIComponent(entry.path);
    const restore=entry.status==="valid"?`<button class="secondary-action" type="button" data-restore-archive="${encoded}">Restaurer</button>`:'<button class="secondary-action" type="button" disabled>Indisponible</button>';
    const actions=`<div class="archive-actions">${restore}<button class="icon-action" type="button" data-open-archive="${encoded}" aria-label="Ouvrir le dossier" title="Ouvrir le dossier">${catalogActionIcon("folder")}</button><button class="icon-action" type="button" data-copy-archive="${encoded}" aria-label="Copier le chemin" title="Copier le chemin">${catalogActionIcon("copy")}</button></div>`;
    const segments=entry.backup_set?`<span>${entry.completed_segments} / ${entry.segment_count} lot(s)</span>`:"";
    return `<article class="archive-card"><div class="archive-main"><div class="archive-icon">${entry.encrypted?"🔒":entry.backup_set?"▦":"▣"}</div><div><div class="archive-title"><h3>${entry.name}</h3><span class="archive-status ${status}">${label}</span></div><p class="archive-path">${entry.path}</p><div class="archive-meta"><span>${formatDate(entry.created_at??entry.modified_at)}</span><span>${formatBytes(entry.size_bytes)}</span><span>${entry.file_count??"—"} fichier(s)</span>${segments}${entry.application_version?`<span>FSBackup ${entry.application_version}</span>`:""}</div>${entry.error?`<p class="archive-error">${entry.error}</p>`:""}</div></div>${actions}</article>`;
  }).join("");
}

function bindCatalogActions(){
  document.querySelector("#catalog-list").addEventListener("click",event=>{
    const restore=event.target.closest("[data-restore-archive]");
    if(restore){prepareRestoreFromCatalog(decodeURIComponent(restore.dataset.restoreArchive));return;}
    const copy=event.target.closest("[data-copy-archive]");
    if(copy){copyCatalogPath(decodeURIComponent(copy.dataset.copyArchive));return;}
    const open=event.target.closest("[data-open-archive]");
    if(open)openCatalogLocation(decodeURIComponent(open.dataset.openArchive),open);
  });
}

function bindCatalogForm(){
  document.querySelector("#catalog-form").addEventListener("submit",async event=>{
    event.preventDefault();
    const button=document.querySelector("#scan-catalog");
    const message=document.querySelector("#catalog-message");
    button.disabled=true;
    button.textContent="Analyse en cours…";
    message.textContent="Recherche et vérification des archives…";
    message.className="message";
    try{
      const response=await fetch("/api/v1/backups/catalog",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({directory:document.querySelector("#catalog-directory").value.trim(),recursive:document.querySelector("#catalog-recursive").checked})});
      const data=await response.json();
      if(!response.ok)throw new Error(data.error?.message??"L’analyse a échoué.");
      renderCatalog(data);
      message.textContent=`Analyse terminée : ${data.summary.total} archive(s) trouvée(s).`;
      message.className="message success";
    }catch(error){message.textContent=error.message;message.className="message error";}
    finally{button.disabled=false;button.textContent="Analyser le dossier";}
  });
}

document.querySelector("#refresh").addEventListener("click",loadDashboard);
bindNavigation();
bindBackupForm();
bindCatalogActions();
bindCatalogForm();
loadDashboard();
const initial=window.location.hash.slice(1);
if(["backup","archives","restore","retention"].includes(initial))showView(initial);
