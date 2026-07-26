function driveFormatBytes(value){
  if(!value)return "0 octet";
  const units=["octets","Ko","Mo","Go","To"];
  const index=Math.min(Math.floor(Math.log(value)/Math.log(1024)),units.length-1);
  return `${(value/(1024**index)).toLocaleString("fr-FR",{maximumFractionDigits:index?1:0})} ${units[index]}`;
}

function driveOptions(drives){
  return '<option value="">Choisir un disque</option>'+drives.map(drive=>{
    const suffix=drive.system?" — disque système":"";
    const free=drive.free_bytes?` — ${driveFormatBytes(drive.free_bytes)} libres`:"";
    return `<option value="${drive.root}">${drive.label}${suffix}${free}</option>`;
  }).join("");
}

function joinWindowsPath(root,subdirectory){
  const cleanRoot=root.replace(/[\\/]+$/m,"");
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
  if(!drive||!relative||!custom||!driveField||!relativeField||!customField)return;

  const sync=()=>{
    const customMode=mode.value==="custom";
    driveField.classList.toggle("hidden",customMode);
    relativeField.classList.toggle("hidden",customMode);
    customField.classList.toggle("hidden",!customMode);
    target.value=customMode?custom.value.trim():(drive.value?joinWindowsPath(drive.value,relative.value):"");
    window.dispatchEvent(new CustomEvent("fsbackup:destination-changed"));
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
  {mode:"restore-destination-mode",target:"restore-destination",drive:"restore-destination-drive",relative:"restore-destination-subdirectory",custom:"restore-destination-custom",driveField:"restore-destination-drive-field",relativeField:"restore-destination-relative-field",customField:"restore-destination-custom-field"},
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
    window.fsbackupDrives=data.drives??[];
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
    window.dispatchEvent(new CustomEvent("fsbackup:drives-loaded"));
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

const UI_MODULE_VERSION="10.7.6";

function loadOptionalModule(src,attribute){
  const alreadyLoaded=[...document.scripts].some(script=>{
    const scriptUrl=new URL(script.src||"",window.location.href);
    return script.hasAttribute(attribute)||scriptUrl.pathname===src;
  });
  if(alreadyLoaded)return;
  const script=document.createElement("script");
  const separator=src.includes("?")?"&":"?";
  script.src=`${src}${separator}v=${encodeURIComponent(UI_MODULE_VERSION)}`;
  script.defer=true;
  script.setAttribute(attribute,"true");
  document.body.appendChild(script);
}

document.addEventListener("DOMContentLoaded",()=>{
  loadOptionalModule("/app/diagnostic.js","data-fsbackup-diagnostic");
  loadOptionalModule("/app/capacity.js","data-fsbackup-capacity");
  loadOptionalModule("/app/root_inventory.js","data-fsbackup-root-inventory");
  loadOptionalModule("/app/exclusion_payload.js","data-fsbackup-payload-bridge");
  locationConfigs.forEach(bindLocation);
  loadAvailableDrives();
});