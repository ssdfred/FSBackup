const descriptions={backup:"Créer une archive complète, compressée et éventuellement chiffrée.",catalog:"Parcourir et contrôler les archives disponibles sur ce poste.",restore:"Vérifier puis restaurer une sauvegarde dans un dossier choisi.",retention_simulation:"Prévisualiser les archives à conserver ou à supprimer.",retention_execution:"Supprimer uniquement les archives confirmées par l’utilisateur."};
const icons={backup:"↥",catalog:"▣",restore:"↺",retention_simulation:"◷",retention_execution:"!"};
const labels={backup:"Nouvelle sauvegarde",catalog:"Mes sauvegardes",restore:"Restaurer",retention_simulation:"Simuler la rétention",retention_execution:"Exécuter la rétention"};

function showView(name){
  document.querySelectorAll(".view").forEach(view=>view.classList.toggle("active-view",view.id===`${name}-view`));
  document.querySelectorAll(".sidebar nav a").forEach(link=>link.classList.toggle("active",link.dataset.view===name));
  window.location.hash=name;
  window.scrollTo({top:0,behavior:"smooth"});
}

function bindNavigation(){
  document.querySelectorAll("[data-view]").forEach(element=>element.addEventListener("click",event=>{
    event.preventDefault();
    showView(element.dataset.view);
  }));
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
    container.innerHTML=data.capabilities.map(item=>`<article class="capability-card ${item.destructive?"danger":""}"><div class="icon">${icons[item.key]??"•"}</div><h3>${labels[item.key]??item.label}</h3><p>${descriptions[item.key]??item.label}</p><a href="#${item.key}" ${item.key==="backup"?'data-view="backup"':""}>${item.destructive?"Action protégée":"Ouvrir"} →</a></article>`).join("");
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

function bindBackupForm(){
  const encryption=document.querySelector("#enable-encryption");
  const passwordFields=document.querySelector("#password-fields");
  encryption.addEventListener("change",()=>passwordFields.classList.toggle("hidden",!encryption.checked));
  document.querySelector("#backup-form").addEventListener("submit",async event=>{
    event.preventDefault();
    const submit=document.querySelector("#submit-backup");
    const password=document.querySelector("#encryption-password").value;
    const confirmation=document.querySelector("#encryption-confirmation").value;
    if(encryption.checked&&password!==confirmation){setMessage("Les mots de passe ne correspondent pas.","error");return;}
    if(encryption.checked&&password.length<8){setMessage("Le mot de passe doit contenir au moins 8 caractères.","error");return;}
    const level=Number(document.querySelector("#compression-level").value);
    const payload={
      source_root:document.querySelector("#source-root").value.trim(),
      destination_directory:document.querySelector("#destination-directory").value.trim(),
      archive_name:document.querySelector("#archive-name").value.trim(),
      compression:{method:level===0?"stored":"deflated",level},
      encryption:encryption.checked?{password}:null,
      verify_integrity:document.querySelector("#verify-integrity").checked
    };
    submit.disabled=true;
    submit.textContent="Sauvegarde en cours…";
    setMessage("Préparation et création de l’archive…");
    try{
      const response=await fetch("/api/v1/backup/run",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});
      const data=await response.json();
      if(!response.ok)throw new Error(data.error?.message??"La requête a échoué.");
      if(!data.success)throw new Error(data.error??"La sauvegarde n’a pas pu être créée.");
      setMessage(`Sauvegarde terminée : ${data.archive_path??"archive créée"}. ${data.copied_files} fichier(s) copié(s).`,"success");
    }catch(error){setMessage(error.message,"error");}
    finally{submit.disabled=false;submit.textContent="Lancer la sauvegarde";}
  });
}

document.querySelector("#refresh").addEventListener("click",loadDashboard);
bindNavigation();
bindBackupForm();
loadDashboard();
if(window.location.hash==="#backup")showView("backup");
