async function loadAvailableDrives(){
  const select=document.querySelector("#source-root");
  if(!select)return;

  select.disabled=true;
  select.innerHTML='<option value="">Détection des lecteurs…</option>';
  try{
    const response=await fetch("/api/v1/sources/drives");
    const data=await response.json();
    if(!response.ok)throw new Error(data.error?.message??"Impossible de détecter les lecteurs.");
    if(!data.drives.length){
      select.innerHTML='<option value="">Aucun lecteur disponible</option>';
      return;
    }
    select.innerHTML='<option value="">Choisir un disque</option>'+data.drives.map(drive=>{
      const suffix=drive.system?" — disque système":"";
      return `<option value="${drive.root}">${drive.label}${suffix}</option>`;
    }).join("");
    const systemDrive=data.drives.find(drive=>drive.system);
    if(systemDrive)select.value=systemDrive.root;
  }catch(error){
    select.innerHTML='<option value="">Détection impossible</option>';
    const message=document.querySelector("#backup-message");
    if(message){
      message.textContent=error.message;
      message.className="message error";
    }
  }finally{
    select.disabled=false;
  }
}

document.addEventListener("DOMContentLoaded",loadAvailableDrives);
