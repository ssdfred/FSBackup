function driveOptions(drives){
  return '<option value="">Choisir un disque</option>'+drives.map(drive=>{
    const suffix=drive.system?" — disque système":"";
    return `<option value="${drive.root}">${drive.label}${suffix}</option>`;
  }).join("");
}

function joinWindowsPath(root,subdirectory){
  const cleanRoot=root.replace(/[\\/]+$/,"");
  const cleanSubdirectory=subdirectory.trim().replace(/^[\\/]+|[\\/]+$/g,"");
  return cleanSubdirectory?`${cleanRoot}\\${cleanSubdirectory}`:`${cleanRoot}\\`;
}

function syncCatalogDirectory(){
  const target=document.querySelector("#catalog-directory");
  const mode=document.querySelector("#catalog-location-mode");
  if(!target||!mode)return;

  if(mode.value==="custom"){
    target.value=document.querySelector("#catalog-custom-directory").value.trim();
    return;
  }

  const root=document.querySelector("#catalog-drive").value;
  const subdirectory=document.querySelector("#catalog-subdirectory").value;
  target.value=root?joinWindowsPath(root,subdirectory):"";
}

function bindCatalogLocation(){
  const mode=document.querySelector("#catalog-location-mode");
  if(!mode)return;

  const driveField=document.querySelector("#catalog-drive-field");
  const subdirectoryField=document.querySelector("#catalog-subdirectory-field");
  const customField=document.querySelector("#catalog-custom-field");
  const refresh=()=>{
    const custom=mode.value==="custom";
    driveField.classList.toggle("hidden",custom);
    subdirectoryField.classList.toggle("hidden",custom);
    customField.classList.toggle("hidden",!custom);
    syncCatalogDirectory();
  };

  mode.addEventListener("change",refresh);
  document.querySelector("#catalog-drive").addEventListener("change",syncCatalogDirectory);
  document.querySelector("#catalog-subdirectory").addEventListener("input",syncCatalogDirectory);
  document.querySelector("#catalog-custom-directory").addEventListener("input",syncCatalogDirectory);
  refresh();
}

async function loadAvailableDrives(){
  const sourceSelect=document.querySelector("#source-root");
  const catalogSelect=document.querySelector("#catalog-drive");
  const selects=[sourceSelect,catalogSelect].filter(Boolean);
  if(!selects.length)return;

  selects.forEach(select=>{
    select.disabled=true;
    select.innerHTML='<option value="">Détection des lecteurs…</option>';
  });

  try{
    const response=await fetch("/api/v1/sources/drives");
    const data=await response.json();
    if(!response.ok)throw new Error(data.error?.message??"Impossible de détecter les lecteurs.");
    if(!data.drives.length){
      selects.forEach(select=>select.innerHTML='<option value="">Aucun lecteur disponible</option>');
      return;
    }

    const options=driveOptions(data.drives);
    selects.forEach(select=>select.innerHTML=options);
    const systemDrive=data.drives.find(drive=>drive.system);
    if(systemDrive&&sourceSelect)sourceSelect.value=systemDrive.root;
    if(catalogSelect){
      const preferred=data.drives.find(drive=>drive.root.toUpperCase().startsWith("H:"))??systemDrive??data.drives[0];
      catalogSelect.value=preferred.root;
      syncCatalogDirectory();
    }
  }catch(error){
    selects.forEach(select=>select.innerHTML='<option value="">Détection impossible</option>');
    const message=document.querySelector("#backup-message");
    if(message){
      message.textContent=error.message;
      message.className="message error";
    }
  }finally{
    selects.forEach(select=>select.disabled=false);
  }
}

document.addEventListener("DOMContentLoaded",()=>{
  bindCatalogLocation();
  loadAvailableDrives();
});