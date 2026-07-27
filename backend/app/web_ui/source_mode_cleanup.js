const sourceModeCleanupState={windowsMode:null};

function setWindowsPanelsVisibility(windowsMode){
  [
    "#source-diagnostic",
    "#root-inventory",
    "#exclusion-suggestions",
    "#backup-capacity-diagnostic",
  ].forEach(selector=>{
    const panel=document.querySelector(selector);
    if(panel&&panel.hidden===windowsMode)panel.hidden=!windowsMode;
  });
}

function resetWindowsPlanningState(){
  window.fsbackupApprovedExclusions=[];
  window.fsbackupExclusionsConfirmed=true;
  window.fsbackupDestinationCapacityValid=true;
  window.dispatchEvent(new CustomEvent("fsbackup:plan-selection-changed"));
  window.dispatchEvent(new CustomEvent("fsbackup:source-mode-reset",{
    detail:{mode:"custom_folder"},
  }));
}

function updateSourceSpecificPanels({force=false}={}){
  const windowsMode=document.querySelector("#source-mode")?.value==="windows_disk";
  const modeChanged=sourceModeCleanupState.windowsMode!==windowsMode;
  sourceModeCleanupState.windowsMode=windowsMode;
  setWindowsPanelsVisibility(windowsMode);

  if(!windowsMode&&(modeChanged||force))resetWindowsPlanningState();

  if(windowsMode&&modeChanged){
    window.dispatchEvent(new CustomEvent("fsbackup:source-mode-restored",{
      detail:{mode:"windows_disk"},
    }));
  }
}

function scheduleSourceSpecificPanelUpdate(){
  updateSourceSpecificPanels({force:true});
  requestAnimationFrame(()=>updateSourceSpecificPanels());
  setTimeout(()=>updateSourceSpecificPanels(),100);
}

function initSourceModeCleanup(){
  document.querySelector("#source-mode")?.addEventListener(
    "change",scheduleSourceSpecificPanelUpdate
  );
  window.addEventListener("fsbackup:inventory-status-changed",()=>{
    setWindowsPanelsVisibility(
      document.querySelector("#source-mode")?.value==="windows_disk"
    );
  });
  window.addEventListener("fsbackup:drives-loaded",()=>updateSourceSpecificPanels());
  scheduleSourceSpecificPanelUpdate();
}

if(document.readyState==="loading"){
  document.addEventListener("DOMContentLoaded",initSourceModeCleanup);
}else{
  initSourceModeCleanup();
}
