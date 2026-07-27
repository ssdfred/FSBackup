const backupLayoutState={scheduled:false,observer:null};

function placeBackupPlanningPanels(){
  backupLayoutState.scheduled=false;
  const form=document.querySelector("#backup-form");
  const inventory=document.querySelector("#root-inventory");
  const exclusions=document.querySelector("#exclusion-suggestions");
  const capacity=document.querySelector("#backup-capacity-diagnostic");
  const options=form?.querySelector(".option-list");
  if(!form||!options)return;

  let anchor=inventory;
  if(exclusions){
    const expectedPrevious=anchor;
    if(expectedPrevious&&exclusions.previousElementSibling!==expectedPrevious){
      expectedPrevious.insertAdjacentElement("afterend",exclusions);
    }else if(!expectedPrevious&&exclusions.nextElementSibling!==options){
      options.insertAdjacentElement("beforebegin",exclusions);
    }
    anchor=exclusions;
  }

  if(capacity){
    if(anchor&&capacity.previousElementSibling!==anchor){
      anchor.insertAdjacentElement("afterend",capacity);
    }else if(!anchor&&capacity.nextElementSibling!==options){
      options.insertAdjacentElement("beforebegin",capacity);
    }
  }
}

function scheduleBackupPlanningLayout(){
  if(backupLayoutState.scheduled)return;
  backupLayoutState.scheduled=true;
  requestAnimationFrame(placeBackupPlanningPanels);
}

function initBackupPlanningLayout(){
  scheduleBackupPlanningLayout();
  [
    "fsbackup:drives-loaded",
    "fsbackup:inventory-status-changed",
    "fsbackup:plan-selection-changed",
    "fsbackup:exclusions-changed",
    "fsbackup:destination-changed",
  ].forEach(name=>window.addEventListener(name,scheduleBackupPlanningLayout));

  const form=document.querySelector("#backup-form");
  if(form&&!backupLayoutState.observer){
    backupLayoutState.observer=new MutationObserver(scheduleBackupPlanningLayout);
    backupLayoutState.observer.observe(form,{childList:true,subtree:true});
  }
}

if(document.readyState==="loading"){
  document.addEventListener("DOMContentLoaded",initBackupPlanningLayout);
}else{
  initBackupPlanningLayout();
}
