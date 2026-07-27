(function installExclusionSummaryLayout(){
  if(window.fsbackupExclusionSummaryLayoutInstalled)return;
  window.fsbackupExclusionSummaryLayoutInstalled=true;

  function placeSummaryBelowExclusionList(){
    const panel=document.querySelector("#exclusion-suggestions .exclusion-panel");
    const summary=panel?.querySelector(":scope > .exclusion-summary");
    const confirmation=panel?.querySelector(":scope > #exclusion-confirmation");
    if(!panel||!summary)return;

    const exclusionList=[...panel.children].find(child=>
      child!==summary&&
      child!==confirmation&&
      child.querySelector?.("[data-exclusion-index]")
    );
    if(!exclusionList)return;

    if(summary.previousElementSibling!==exclusionList){
      exclusionList.insertAdjacentElement("afterend",summary);
    }
  }

  function scheduleLayout(){
    placeSummaryBelowExclusionList();
    setTimeout(placeSummaryBelowExclusionList,0);
    setTimeout(placeSummaryBelowExclusionList,150);
  }

  window.addEventListener("fsbackup:exclusions-changed",scheduleLayout);
  window.addEventListener("fsbackup:inventory-status-changed",scheduleLayout);

  if(document.readyState==="loading"){
    document.addEventListener("DOMContentLoaded",scheduleLayout);
  }else{
    scheduleLayout();
  }
})();
