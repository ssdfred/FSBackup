function validationFormatBytes(value){
  const bytes=Number(value??0);
  if(!bytes)return "0 octet";
  const units=["octets","Ko","Mo","Go","To"];
  const index=Math.min(Math.floor(Math.log(bytes)/Math.log(1024)),units.length-1);
  return `${(bytes/(1024**index)).toLocaleString("fr-FR",{maximumFractionDigits:index?1:0})} ${units[index]}`;
}

function validationFormatDuration(value){
  const milliseconds=Number(value??0);
  if(milliseconds<=0)return "Non mesurée";
  if(milliseconds<1000)return `${milliseconds.toLocaleString("fr-FR")} ms`;
  const seconds=milliseconds/1000;
  if(seconds<60)return `${seconds.toLocaleString("fr-FR",{maximumFractionDigits:1})} s`;
  const minutes=Math.floor(seconds/60);
  const remaining=Math.round(seconds%60);
  return `${minutes} min ${remaining} s`;
}

function validationRatio(report){
  const ratio=Number(report?.compression_ratio??0);
  if(Number.isFinite(ratio)&&ratio>0)return `${Math.max((1-ratio)*100,0).toLocaleString("fr-FR",{maximumFractionDigits:1})} %`;
  const original=Number(report?.original_size??0);
  const archive=Number(report?.archive_size??0);
  if(!original)return "0 %";
  return `${Math.max((1-(archive/original))*100,0).toLocaleString("fr-FR",{maximumFractionDigits:1})} %`;
}

function ensureValidationReportFields(){
  const grid=document.querySelector("#backup-report .report-grid");
  if(!grid)return null;
  const fields=[
    ["report-original-size","Taille originale"],
    ["report-archive-size","Taille de l’archive"],
    ["report-saved-size","Espace économisé"],
    ["report-compression-ratio","Gain de compression"],
    ["report-duration","Durée de création"],
    ["report-excluded-files","Fichiers exclus"],
    ["report-excluded-size","Volume exclu"],
    ["report-encryption","Chiffrement"],
    ["report-segments","Lots validés"],
    ["report-resumed-segments","Lots repris"],
  ];
  fields.forEach(([id,label])=>{
    if(document.querySelector(`#${id}`))return;
    const wrapper=document.createElement("div");
    const term=document.createElement("dt");
    const value=document.createElement("dd");
    term.textContent=label;
    value.id=id;
    value.textContent="—";
    wrapper.append(term,value);
    grid.appendChild(wrapper);
  });
  let details=document.querySelector("#report-validation-details");
  if(!details){
    details=document.createElement("div");
    details.id="report-validation-details";
    details.className="message";
    grid.insertAdjacentElement("afterend",details);
  }
  return details;
}

function renderValidationDetails(data,verified){
  const archive=data.archive_report??{};
  const integrity=data.integrity_report??null;
  const details=ensureValidationReportFields();
  if(!details)return;
  document.querySelector("#report-original-size").textContent=validationFormatBytes(archive.original_size);
  document.querySelector("#report-archive-size").textContent=validationFormatBytes(archive.archive_size);
  document.querySelector("#report-saved-size").textContent=validationFormatBytes(archive.saved_bytes);
  document.querySelector("#report-compression-ratio").textContent=validationRatio(archive);
  document.querySelector("#report-duration").textContent=validationFormatDuration(archive.duration_ms);
  document.querySelector("#report-excluded-files").textContent=Number(data.excluded_files??0).toLocaleString("fr-FR");
  document.querySelector("#report-excluded-size").textContent=validationFormatBytes(data.excluded_size_bytes);
  document.querySelector("#report-encryption").textContent=archive.encrypted?"Activé":"Désactivé";
  document.querySelector("#report-segments").textContent=data.total_segments?`${Number(data.completed_segments??0).toLocaleString("fr-FR")} / ${Number(data.total_segments).toLocaleString("fr-FR")}`:"Non fractionnée";
  document.querySelector("#report-resumed-segments").textContent=Number(data.resumed_segments??0).toLocaleString("fr-FR");

  const integrityValid=verified&&integrity?.valid===true;
  const archiveSuccess=archive.success!==false;
  const copiedFiles=Number(data.copied_files??0);
  const warnings=Number(data.warnings?.length??0);
  const validated=Boolean(data.success&&archiveSuccess&&copiedFiles>=0&&(!verified||integrityValid));
  const statements=[
    `Archive ${archiveSuccess?"créée":"en échec"}`,
    `${copiedFiles.toLocaleString("fr-FR")} fichier(s) copié(s)`,
    verified?(integrityValid?"intégrité validée":"intégrité non validée"):"intégrité non demandée",
    `${warnings} avertissement(s)`,
  ];
  details.className=`message ${validated?"success":"error"}`;
  details.innerHTML=`<strong>${validated?"Validation de sauvegarde réussie":"Validation de sauvegarde à contrôler"}</strong><p>${statements.join(" · ")}.</p>`;

  const badge=document.querySelector("#report-badge");
  if(badge)badge.textContent=validated?"Validée":"À contrôler";
}

function installValidationReport(){
  if(window.fsbackupValidationReportInstalled)return;
  if(typeof window.renderReport!=="function"){
    setTimeout(installValidationReport,50);
    return;
  }
  window.fsbackupValidationReportInstalled=true;
  const originalRenderReport=window.renderReport;
  window.renderReport=function(data,verified){
    originalRenderReport(data,verified);
    renderValidationDetails(data,verified);
  };
}

installValidationReport();
