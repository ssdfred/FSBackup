function fsbackupDriveKey(value){
  const match=String(value??"").trim().match(/^([a-zA-Z]:)/);
  return match?match[1].toUpperCase():"";
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
    [...select.options].forEach(option=>{
      const drive=drives.find(item=>fsbackupDriveKey(item.root)===fsbackupDriveKey(option.value));
      if(!drive)return;
      const system=drive.system?" — disque système":"";
      const free=typeof driveFormatBytes==="function"
        ?driveFormatBytes(drive.free_bytes)
        :`${Number(drive.free_bytes??0).toLocaleString("fr-FR")} octets`;
      option.textContent=`${drive.label}${system} — ${free} libres`;
    });
  });
  if(typeof renderCapacityDiagnostic==="function")renderCapacityDiagnostic();
}

window.addEventListener("fsbackup:drives-loaded",()=>setTimeout(refreshDriveCapacityLabels,0));
window.addEventListener("fsbackup:destination-changed",()=>setTimeout(refreshDriveCapacityLabels,0));

document.addEventListener("DOMContentLoaded",()=>{
  document.querySelector("#backup-destination-drive")?.addEventListener(
    "change",()=>setTimeout(refreshDriveCapacityLabels,0)
  );
  setTimeout(refreshDriveCapacityLabels,250);
});
