(() => {
  const dialog = document.getElementById('short-video-dialog');
  if (!dialog) return;
  const frame = dialog.querySelector('.video-dialog__frame');
  const close = dialog.querySelector('.video-dialog__close');
  function stop(){ frame.innerHTML=''; if (dialog.open) dialog.close(); }
  document.querySelectorAll('.short-video-card[data-youtube-id]').forEach(btn => btn.addEventListener('click', () => {
    const id=(btn.dataset.youtubeId||'').replace(/[^A-Za-z0-9_-]/g,'');
    const title=btn.dataset.videoTitle||'Video';
    if (!id) return;
    frame.innerHTML=`<iframe src="https://www.youtube-nocookie.com/embed/${id}?autoplay=1&mute=0&playsinline=1&rel=0" title="${title.replace(/"/g,'&quot;')}" allow="autoplay; encrypted-media; picture-in-picture; web-share" allowfullscreen></iframe>`;
    dialog.showModal();
  }));
  close?.addEventListener('click', stop);
  dialog.addEventListener('click', e => { if (e.target===dialog) stop(); });
  dialog.addEventListener('cancel', e => { e.preventDefault(); stop(); });
})();
