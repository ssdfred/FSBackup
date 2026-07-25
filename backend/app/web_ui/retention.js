const RETENTION_CONFIRMATION="SUPPRIMER LES SAUVEGARDES SÉLECTIONNÉES";
let retentionSimulation=null;

function retentionMessage(text,type=""){
  const message=document.querySelector("#retention-message");
  message.textContent=text;
  message.className=`message ${type}`;
}

function executionMessage(text,type=""){
  const message=document.querySelector("#retention-execution-message");
  message.textContent=text;
  message.className=`message ${type}`;
}

function retentionDecision(decision){
  if(decision==="keep")return ["Conserver","valid"];
  if(decision==="delete")return ["Supprimer","invalid"];
  return ["Protéger","locked"];
}

function renderRetention(simulation){
  retentionSimulation=simulation;
  document.querySelector("#retention-summary").classList.remove("hidden");
  document.querySelector("#retention-keep").textContent=simulation.summary.keep;
  document.querySelector("#retention-delete").textContent=simulation.summary.delete;
  document.querySelector("#retention-protect").textContent=simulation.summary.protect;
  document.querySelector("#retention-reclaimable").textContent=`${formatBytes(simulation.summary.reclaimable_bytes)} récupérable`;

  const list=document.querySelector("#retention-list");
  list.innerHTML=simulation.decisions.length?simulation.decisions.map(item=>{
    const [label,status]=retentionDecision(item.decision);
    return `<article class="archive-card"><div class="archive-main"><div class="archive-icon">${item.decision==="delete"?"!":"▣"}</div><div><div class="archive-title"><h3>${item.name}</h3><span class="archive-status ${status}">${label}</span></div><p class="archive-path">${item.path}</p><div class="archive-meta"><span>${formatBytes(item.size_bytes)}</span><span>${item.reason}</span></div></div></div></article>`;
  }).join(""):'<div class="empty-state"><strong>Aucune décision</strong><p>Aucune archive n’a été trouvée dans ce dossier.</p></div>';

  const execution=document.querySelector("#retention-execution");
  execution.classList.toggle("hidden",simulation.summary.delete===0);
  document.querySelector("#retention-confirmation").value="";
  document.querySelector("#execute-retention").disabled=true;
  executionMessage("","hidden");
}

async function simulateRetention(){
  const directory=document.querySelector("#retention-directory").value.trim();
  const recursive=document.querySelector("#retention-recursive").checked;
  const catalogResponse=await fetch("/api/v1/backups/catalog",{
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({directory,recursive})
  });
  const catalog=await catalogResponse.json();
  if(!catalogResponse.ok)throw new Error(catalog.error?.message??"Le catalogue n’a pas pu être construit.");

  const policy={
    keep_last:Number(document.querySelector("#retention-last").value),
    keep_daily_days:Number(document.querySelector("#retention-daily").value),
    keep_weekly_weeks:Number(document.querySelector("#retention-weekly").value),
    keep_monthly_months:Number(document.querySelector("#retention-monthly").value)
  };
  const response=await fetch("/api/v1/backups/retention/simulate",{
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({catalog,policy})
  });
  const simulation=await response.json();
  if(!response.ok)throw new Error(simulation.error?.message??"La simulation a échoué.");
  return simulation;
}

function bindRetention(){
  const form=document.querySelector("#retention-form");
  const confirmation=document.querySelector("#retention-confirmation");
  const execute=document.querySelector("#execute-retention");

  form.addEventListener("submit",async event=>{
    event.preventDefault();
    const button=document.querySelector("#simulate-retention");
    button.disabled=true;
    button.textContent="Simulation en cours…";
    retentionMessage("Analyse du catalogue et application de la politique…");
    document.querySelector("#retention-execution").classList.add("hidden");
    try{
      const simulation=await simulateRetention();
      renderRetention(simulation);
      retentionMessage(`Simulation terminée : ${simulation.summary.delete} archive(s) supprimable(s).`,"success");
    }catch(error){
      retentionSimulation=null;
      retentionMessage(error.message,"error");
    }finally{
      button.disabled=false;
      button.textContent="Simuler la rétention";
    }
  });

  confirmation.addEventListener("input",()=>{
    execute.disabled=!retentionSimulation||confirmation.value!==RETENTION_CONFIRMATION;
  });

  execute.addEventListener("click",async()=>{
    if(!retentionSimulation||confirmation.value!==RETENTION_CONFIRMATION)return;
    execute.disabled=true;
    execute.textContent="Suppression en cours…";
    executionMessage("Suppression des seules archives confirmées…");
    try{
      const response=await fetch("/api/v1/backups/retention/execute",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({simulation:retentionSimulation,confirmation:confirmation.value})
      });
      const report=await response.json();
      if(!response.ok)throw new Error(report.error?.message??"La suppression a échoué.");
      if(!report.success)throw new Error(report.error??"Certaines archives n’ont pas pu être supprimées.");
      executionMessage(`${report.summary.deleted} archive(s) supprimée(s), ${formatBytes(report.summary.reclaimed_bytes)} récupéré(s).`,"success");
      retentionSimulation=null;
      execute.textContent="Suppression terminée";
      confirmation.disabled=true;
    }catch(error){
      executionMessage(error.message,"error");
      execute.disabled=false;
      execute.textContent="Supprimer les archives sélectionnées";
    }
  });
}

document.addEventListener("DOMContentLoaded",bindRetention);
