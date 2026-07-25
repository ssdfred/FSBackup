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

function bindLocation(config){
  const mode=document.querySelector(`#${config.mode}`);
  const target=document.querySelector(`#${config.target}`);
  if(!mode||!target)return;

  const drive=document.querySelector(`#${config.drive}`);
  const relative=document.querySelector(`#${config.relative}`);
  const custom=document.querySelector(`#${config.custom}`);
  const driveField=document.querySelector(`#${config.driveField}`);
  const relativeField=document.querySelector(`#${config.relativeField}`);
  const customField=document.querySelector(`#${config.customField}`);

  const sync=()=>{
    const customMode=mode.value==="custom";
    driveField.classList.toggle("hidden",customMode);
    relativeField.classList.toggle("hidden",customMode);
    customField.classList.toggle("hidden",!customMode);
    target.value=customMode?custom.value.trim():(drive.value?joinWindowsPath(drive.value,relative.value):"");
  };

  mode.addEventListener("change",sync);
  drive.addEventListener("change",sync);
  relative.addEventListener("input",sync);
  custom.addEventListener("input",sync);
  sync();
  return sync;
}

const locationConfigs=[
  {mode:"backup-destination-mode",target:"destination-directory",drive:"backup-destination-drive",relative:"backup-destination-subdirectory",custom:"backup-destination-custom",driveField:"backup-destination-drive-field",relativeField:"backup-destination-subdirectory-field",customField:"backup-destination-custom-field"},
  {mode:"catalog-location-mode",target:"catalog-directory",drive:"catalog-drive",relative:"catalog-subdirectory",custom:"catalog-custom-directory",driveField:"catalog-drive-field",relativeField:"catalog-subdirectory-field",customField:"catalog-custom-field"},
  {mode:"restore-archive-mode",target:"restore-archive",drive:"restore-archive-drive",relative:"restore-archive-relative",custom:"restore-archive-custom",driveField:"restore-archive-drive-field",relativeField:"restore-archive-relative-field",customField:"restore-archive-custom-field"},
  {mode:"restore-destination-mode",target:"restore-destination",drive:"restore-destination-drive",relative:"restore-destination-subdirectory",custom:"restore-destination-custom",driveField:"restore-destination-drive-field",relativeField:"restore-destination-subdirectory-field",customField:"restore-destination-custom-field"},
  {mode:"retention-location-mode",target:"retention-directory",drive:"retention-drive",relative:"retention-subdirectory",custom:"retention-custom-directory",driveField:"retention-drive-field",relativeField:"retention-subdirectory-field",customField:"retention-custom-field"}
];

async function loadAvailableDrives(){
  const selectIds=["source-root","backup-destination-drive","catalog-drive","restore-archive-drive","restore-destination-drive","retention-drive"];
  const selects=selectIds.map(id=>document.querySelector(`#${id}`)).filter(Boolean);
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
    const systemDrive=data.drives.find(drive=>drive.system)??data.drives[0];
    const preferred=data.drives.find(drive=>drive.root.toUpperCase().startsWith("H:"))??systemDrive;

    const source=document.querySelector("#source-root");
    if(source)source.value=systemDrive.root;
    ["backup-destination-drive","catalog-drive","restore-archive-drive","restore-destination-drive","retention-drive"].forEach(id=>{
      const select=document.querySelector(`#${id}`);
      if(select)select.value=preferred.root;
    });
    locationConfigs.forEach(config=>{
      const element=document.querySelector(`#${config.drive}`);
      if(element)element.dispatchEvent(new Event("change"));
    });
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

function loadNativePickerScript(){
  if(document.querySelector('script[data-native-picker]'))return;
  const script=document.createElement("script");
  script.src="/app/picker.js";
  script.defer=true;
  script.dataset.nativePicker="true";
  document.head.appendChild(script);
}

document.addEventListener("DOMContentLoaded",()=>{
  locationConfigs.forEach(bindLocation);
  loadAvailableDrives();
  loadNativePickerScript();
});
