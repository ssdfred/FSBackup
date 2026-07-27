const fsbackupDriveCapacityState={loading:false,loaded:false};

function fsbackupDriveKey(value){
  const match=String(value??"").trim().match(/^([a-zA-Z]:)/);
  return match?match[1].toUpperCase():"";
}

function fsbackupFormatDriveBytes(value){
  const bytes=Number(value??0);
  if(!bytes)return "0 octet";
  const units=["octets","Ko","Mo","Go","To"];
  const index=Math.min(Math.floor(Math.log(bytes)/Math.log(1024)),units.length-1);
  return `${(bytes/(1024**index)).toLocaleString("fr-FR",{maximumFractionDigits:index?1:0})} ${units[index]}`;
}

function selectedDestinationDrive(){
  const selectedDrive=document.querySelector("#backup-destination-drive")?.value??"";
  const destination=document.querySelector("#destination-directory")?.value??"";
  const key=fsbackupDriveKey(selectedDrive)||fsbackupDriveKey(destination);
  return (window.fsbackupDrives??[]).find(drive=>fsbackupDriveKey(drive.root)===key)??null;
}

function refreshDriveCapacityLabels(){
  const drives=window.fsbackupDrives??[];
  const selects=document.querySelectorAll(
    "#source-root,#backup-destination-drive,#catalog-drive,#restore-archive-drive,#restore-destination-drive,#retention-drive"
  );
  selects.forEach(select=>{
    const selectedValue=select.value;
    [...select.options].forEach(option=>{
      const drive=drives.find(item=>fsbackupDriveKey(item.root)===fsbackupDriveKey(option.value));
      if(!drive)return;
      const system=drive.system?" — disque système":"";
      option.textContent=`${drive.label}${system} — ${fsbackupFormatDriveBytes(drive.free_bytes)} libres`;
    });
    select.value=selectedValue;
  });
  if(typeof renderCapacityDiagnostic==="function")renderCapacityDiagnostic();
}

async function loadDriveCapacities(){
  if(fsbackupDriveCapacityState.loading)return;
  fsbackupDriveCapacityState.loading=true;
  try{
    const response=await fetch("/api/v1/sources/drives",{cache:"no-store"});
    const data=await response.json();
    if(!response.ok)throw new Error(data.detail??"Capacités des lecteurs indisponibles.");
    window.fsbackupDrives=data.drives??[];
    fsbackupDriveCapacityState.loaded=true;
    refreshDriveCapacityLabels();
    window.dispatchEvent(new CustomEvent("fsbackup:drive-capacities-loaded"));
  }catch(error){
    console.error("FSBackup: impossible de charger les capacités des lecteurs",error);
  }finally{
    fsbackupDriveCapacityState.loading=false;
  }
}

window.addEventListener("fsbackup:drives-loaded",()=>{
  refreshDriveCapacityLabels();
  if(!(window.fsbackupDrives??[]).some(drive=>Number(drive.free_bytes??0)>0))loadDriveCapacities();
});
window.addEventListener("fsbackup:destination-changed",refreshDriveCapacityLabels);

document.addEventListener("DOMContentLoaded",()=>{
  document.querySelector("#backup-destination-drive")?.addEventListener("change",refreshDriveCapacityLabels);
  document.querySelector("#source-root")?.addEventListener("change",refreshDriveCapacityLabels);
  loadDriveCapacities();
});

if(document.readyState!=="loading")loadDriveCapacities();