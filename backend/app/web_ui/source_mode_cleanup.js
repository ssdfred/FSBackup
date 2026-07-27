function updateSourceSpecificPanels(){
  const windowsMode=document.querySelector("#source-mode")?.value==="windows_disk";
  [
    "#source-diagnostic",
    "#root-inventory",
    "#exclusion-suggestions",
    "#backup-capacity-diagnostic",
  ].forEach(selector=>{
    const panel=document.querySelector(selector);
    if(panel)panel.hidden=!windowsMode;
  });

  if(!windowsMode){
    window.fsbackupApprovedExclusions=[];
    window.fsbackupExclusionsConfirmed=true;
    window.fsbackupDestinationCapacityValid=true;
    window.dispatchEvent(new CustomEvent("fsbackup:plan-selection-changed"));
    window.dispatchEvent(new CustomEvent("fsbackup:exclusions-changed",{
      detail:{selectedSize:0,applicableSize:0,applicableCount:0},
    }));
  }
}

function scheduleSourceSpecificPanelUpdate(){
  updateSourceSpecificPanels();
  setTimeout(updateSourceSpecificPanels,0);
  setTimeout(updateSourceSpecificPanels,150);
}

function initSourceModeCleanup(){
  document.querySelector("#source-mode")?.addEventListener(
    "change",scheduleSourceSpecificPanelUpdate
  );
  window.addEventListener("fsbackup:inventory-status-changed",updateSourceSpecificPanels);
  window.addEventListener("fsbackup:exclusions-changed",updateSourceSpecificPanels);
  window.addEventListener("fsbackup:drives-loaded",updateSourceSpecificPanels);

  const form=document.querySelector("#backup-form");
  if(form){
    new MutationObserver(updateSourceSpecificPanels).observe(form,{
      childList:true,
      subtree:true,
    });
  }
  scheduleSourceSpecificPanelUpdate();
}

if(document.readyState==="loading"){
  document.addEventListener("DOMContentLoaded",initSourceModeCleanup);
}else{
  initSourceModeCleanup();
}
