const pickerBindings=[
  {target:"custom-source-root",kind:"directory",mode:"source-mode",modeValue:"custom_folder"},
  {target:"backup-destination-custom",kind:"directory",mode:"backup-destination-mode",modeValue:"custom"},
  {target:"catalog-custom-directory",kind:"directory",mode:"catalog-location-mode",modeValue:"custom"},
  {target:"restore-archive-custom",kind:"archive",mode:"restore-archive-mode",modeValue:"custom"},
  {target:"restore-destination-custom",kind:"directory",mode:"restore-destination-mode",modeValue:"custom"},
  {target:"retention-custom-directory",kind:"directory",mode:"retention-location-mode",modeValue:"custom"}
];

function ensurePickerStyles(){
  if(document.querySelector('link[data-picker-styles]'))return;
  const link=document.createElement("link");
  link.rel="stylesheet";
  link.href="/app/picker.css";
  link.dataset.pickerStyles="true";
  document.head.appendChild(link);
}

function pickerMessage(text,type=""){
  const message=document.querySelector("#backup-message");
  if(!message)return;
  message.textContent=text;
  message.className=`message ${type}`;
}

function catalogActionMessage(text,type="success"){
  const message=document.querySelector("#catalog-message");
  if(!message)return;
  message.textContent=text;
  message.className=`message ${type}`;
}

function pickerIcon(kind){
  if(kind==="archive"){
    return '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 2.75h8l4.25 4.25v14.25H6z"/><path d="M14 2.75V7h4.25"/><path d="M9 12h6M9 15h6"/></svg>';
  }
  return '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3.5 6.5h6l1.75 2h9.25v9.75a2 2 0 0 1-2 2h-13a2 2 0 0 1-2-2z"/></svg>';
}

async function openNativePicker(binding,button){
  const target=document.querySelector(`#${binding.target}`);
  if(!target)return;
  button.disabled=true;
  button.classList.add("is-loading");
  try{
    const response=await fetch(`/api/v1/system/picker/${binding.kind}`,{
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({initial_path:target.value.trim()||null})
    });
    const report=await response.json();
    if(!response.ok)throw new Error(report.error?.message??"Le sélecteur n’a pas pu être ouvert.");
    if(report.error)throw new Error(report.error);
    if(!report.selected)return;

    const mode=document.querySelector(`#${binding.mode}`);
    if(mode){
      mode.value=binding.modeValue;
      mode.dispatchEvent(new Event("change",{bubbles:true}));
    }
    target.value=report.path;
    target.dispatchEvent(new Event("input",{bubbles:true}));
    target.dispatchEvent(new Event("change",{bubbles:true}));
  }catch(error){
    pickerMessage(error.message,"error");
  }finally{
    button.disabled=false;
    button.classList.remove("is-loading");
  }
}

async function copyArchivePath(path){
  try{
    await navigator.clipboard.writeText(path);
    catalogActionMessage("Le chemin de l’archive a été copié.");
  }catch{
    const textarea=document.createElement("textarea");
    textarea.value=path;
    textarea.style.position="fixed";
    textarea.style.opacity="0";
    document.body.appendChild(textarea);
    textarea.select();
    const copied=document.execCommand("copy");
    textarea.remove();
    catalogActionMessage(
      copied?"Le chemin de l’archive a été copié.":"Impossible de copier le chemin.",
      copied?"success":"error"
    );
  }
}

async function openArchiveLocation(path,button){
  button.disabled=true;
  try{
    const response=await fetch("/api/v1/system/picker/open",{
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({path})
    });
    const report=await response.json();
    if(!response.ok||!report.success){
      throw new Error(report.error?.message??report.error??"Impossible d’ouvrir le dossier.");
    }
    catalogActionMessage("Le dossier de l’archive a été ouvert.");
  }catch(error){
    catalogActionMessage(error.message,"error");
  }finally{
    button.disabled=false;
  }
}

function enhanceCatalogCards(){
  document.querySelectorAll("#catalog-list .archive-card").forEach(card=>{
    if(card.dataset.quickActionsBound)return;
    const path=card.querySelector(".archive-path")?.textContent?.trim();
    if(!path)return;
    card.dataset.quickActionsBound="true";
    const existing=card.querySelector(":scope > button");
    const actions=document.createElement("div");
    actions.className="archive-actions";
    if(existing)actions.appendChild(existing);

    const openButton=document.createElement("button");
    openButton.type="button";
    openButton.className="icon-action";
    openButton.title="Ouvrir le dossier";
    openButton.setAttribute("aria-label","Ouvrir le dossier de l’archive");
    openButton.innerHTML='<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3.5 6.5h6l1.75 2h9.25v9.75a2 2 0 0 1-2 2h-13a2 2 0 0 1-2-2z"/><path d="M8 13h8M13 10l3 3-3 3"/></svg>';
    openButton.addEventListener("click",()=>openArchiveLocation(path,openButton));

    const copyButton=document.createElement("button");
    copyButton.type="button";
    copyButton.className="icon-action";
    copyButton.title="Copier le chemin";
    copyButton.setAttribute("aria-label","Copier le chemin de l’archive");
    copyButton.innerHTML='<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="8" y="8" width="11" height="11" rx="2"/><path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2"/></svg>';
    copyButton.addEventListener("click",()=>copyArchivePath(path));

    actions.append(openButton,copyButton);
    card.appendChild(actions);
  });
}

function bindNativePickers(){
  ensurePickerStyles();
  pickerBindings.forEach(binding=>{
    const target=document.querySelector(`#${binding.target}`);
    if(!target||target.dataset.pickerBound)return;
    target.dataset.pickerBound="true";
    const wrapper=document.createElement("span");
    wrapper.className="path-picker";
    target.parentNode.insertBefore(wrapper,target);
    wrapper.appendChild(target);
    const button=document.createElement("button");
    const label=binding.kind==="archive"?"Choisir une archive":"Choisir un dossier";
    button.type="button";
    button.className="picker-button";
    button.setAttribute("aria-label",label);
    button.title=label;
    button.innerHTML=pickerIcon(binding.kind);
    button.addEventListener("click",()=>openNativePicker(binding,button));
    wrapper.appendChild(button);
  });

  const catalog=document.querySelector("#catalog-list");
  if(catalog&&!catalog.dataset.actionsObserved){
    catalog.dataset.actionsObserved="true";
    new MutationObserver(enhanceCatalogCards).observe(catalog,{childList:true,subtree:true});
    enhanceCatalogCards();
  }
}

if(document.readyState==="loading"){
  document.addEventListener("DOMContentLoaded",bindNativePickers);
}else{
  bindNativePickers();
}
