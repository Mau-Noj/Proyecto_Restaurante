/**
 * navigator.clipboard requiere HTTPS o localhost. En LAN (http://IP:puerto)
 * los navegadores lo bloquean sin avisar, así que hay que caer a
 * document.execCommand('copy') con un textarea oculto.
 */
function copyToClipboard(text, buttonEl) {
  function showCopied() {
    if (!buttonEl) return;
    const original = buttonEl.innerHTML;
    buttonEl.innerHTML = '<span class="material-symbols-outlined text-[18px] text-neon-cyan">check</span>';
    setTimeout(() => {
      buttonEl.innerHTML = original;
    }, 1200);
  }

  function fallbackCopy() {
    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.style.position = "fixed";
    textarea.style.opacity = "0";
    document.body.appendChild(textarea);
    textarea.focus();
    textarea.select();
    try {
      document.execCommand("copy");
      showCopied();
    } catch (err) {
      console.error("No se pudo copiar al portapapeles", err);
    }
    document.body.removeChild(textarea);
  }

  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(text).then(showCopied, fallbackCopy);
  } else {
    fallbackCopy();
  }
}
