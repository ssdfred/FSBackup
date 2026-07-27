function exclusionSummaryFormatBytes(value){
  if(!value)return "0 octet";
  const units=["octets","Ko","Mo","Go","To"];
  const index=Math.min(Math.floor(Math.log(value)/Math.log(1024)),units.length-1);
  return `${(value/(1024**index)).toLocaleString("fr-FR",{maximumFractionDigits:index?1:0})} ${units[index]}`;
}

function refreshExclusionConfirmationSummary(event){
  const confirmation=document.querySelector("#exclusion-confirmation");
  const paragraph=confirmation?.querySelector("p");
  if(!confirmation||!paragraph)return;

  const selectedCount=document.querySelectorAll(
    '#exclusion-suggestions input[data-exclusion-index]:checked'
  ).length;
  if(selectedCount===0)return;

  const applicableCount=Number(
    event?.detail?.applicableCount??window.getSelectedApplicableExclusionCount?.()??0
  );
  const applicableSize=Number(
    event?.detail?.applicableSize??window.getSelectedApplicableExclusionSize?.()??0
  );
  const ignoredCount=Math.max(selectedCount-applicableCount,0);

  paragraph.textContent=
    `${selectedCount} exclusion(s) sélectionnée(s), dont ${applicableCount} applicable(s) `+
    `au périmètre actuel. Économie réellement déduite du plan : `+
    `${exclusionSummaryFormatBytes(applicableSize)}.`+
    (ignoredCount
      ? ` ${ignoredCount} exclusion(s) se trouve(nt) dans des dossiers non sélectionnés et ne modifie(nt) pas le plan.`
      : " Toutes les exclusions sélectionnées sont applicables.");
}

window.addEventListener("fsbackup:exclusions-changed",event=>{
  setTimeout(()=>refreshExclusionConfirmationSummary(event),0);
});
window.addEventListener("fsbackup:plan-selection-changed",()=>{
  setTimeout(()=>refreshExclusionConfirmationSummary(),0);
});

document.addEventListener("DOMContentLoaded",()=>{
  setTimeout(()=>refreshExclusionConfirmationSummary(),500);
});
