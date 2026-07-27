const backupLayoutState={scheduled:false,observer:null,timers:[]};

function activeExclusionPanel(){
  const panels=[...document.querySelectorAll("#exclusion-suggestions")];
  return panels.find(panel=>panel.querySelector(".exclusion-panel"))??panels[0]??null;
}

function removeEmptyDuplicateExclusionPanels(active){
  document.querySelectorAll("#exclusion-suggestions").forEach(panel=>{
    if(panel!==active&&!panel.hasChildNodes())panel.remove();
  });
}

function placeBackupPlanningPanels(){
  backupLayoutState.scheduled=false;
  const form=document.querySelector("#backup-form");
  const inventory=document.querySelector("#root-inventory");
  const exclusions=activeExclusionPanel();
  const capacity=document.querySelector("#backup-capacity-diagnostic");
  const options=form?.querySelector(".option-list");
  if(!form||!options)return;

  removeEmptyDuplicateExclusionPanels(exclusions);

  if(exclusions){
    if(inventory){
      if(exclusions.previousElementSibling!==inventory){
        inventory.insertAdjacentElement("afterend",exclusions);
      }
    }else if(exclusions.nextElementSibling!==options){
      options.insertAdjacentElement("beforebegin",exclusions);
    }
  }

  if(capacity){
    const anchor=exclusions??inventory;
    if(anchor){
      if(capacity.previousElementSibling!==anchor){
        anchor.insertAdjacentElement("afterend",capacity);
      }
    }else if(capacity.nextElementSibling!==options){
      options.insertAdjacentElement("beforebegin",capacity);
    }
  }
}

function scheduleBackupPlanningLayout(){
  if(!backupLayoutState.scheduled){
    backupLayoutState.scheduled=true;
    requestAnimationFrame(placeBackupPlanningPanels);
  }

  backupLayoutState.timers.forEach(timer=>clearTimeout(timer));
  backupLayoutState.timers=[50,200,600].map(delay=>
    setTimeout(placeBackupPlanningPanels,delay)
  );
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
