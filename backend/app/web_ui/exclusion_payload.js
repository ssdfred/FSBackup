(function installExclusionPayloadBridge(){
  if(window.fsbackupExclusionPayloadBridgeInstalled)return;
  window.fsbackupExclusionPayloadBridgeInstalled=true;

  const originalFetch=window.fetch.bind(window);
  window.fetch=(input,options={})=>{
    const url=typeof input==="string"?input:input?.url??"";
    const method=(options.method??"GET").toUpperCase();
    if(url==="/api/v1/backup/run"&&method==="POST"&&typeof options.body==="string"){
      try{
        const payload=JSON.parse(options.body);
        payload.approved_exclusions=window.getApprovedBackupExclusions?.()??[];
        payload.exclusions_confirmed=window.areBackupExclusionsConfirmed?.()??true;
        payload.selected_additional_paths=window.getSelectedAdditionalPaths?.()??[];
        options={...options,body:JSON.stringify(payload)};
      }catch(_error){
        // Le backend validera la requête originale si le corps n'est pas du JSON valide.
      }
    }
    return originalFetch(input,options);
  };
})();
