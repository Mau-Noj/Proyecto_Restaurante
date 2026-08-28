/**
 * Mini tour guiado (sin dependencias externas) para señalar en la misma
 * pantalla qué campos pertenecen a un plan superior y por qué.
 *
 * Uso:
 *   startFeatureTour([
 *     { selector: '#feature-2fa', title: '2FA', text: '...' },
 *     ...
 *   ], 'zennin');
 */
(function (window) {
  "use strict";

  const ACCENTS = {
    zennin: { border: "#a855f7", glow: "rgba(168, 85, 247, 0.6)", text: "#c084fc" },
    shin: { border: "#f59e0b", glow: "rgba(245, 158, 11, 0.6)", text: "#fcd34d" },
  };

  let state = null;

  function cleanup() {
    if (!state) return;
    if (state.currentTarget) {
      state.currentTarget.classList.remove("feature-tour-highlight");
      state.currentTarget.style.removeProperty("--tour-glow");
    }
    if (state.backdrop) state.backdrop.remove();
    if (state.tooltip) state.tooltip.remove();
    document.removeEventListener("keydown", state.onKeydown);
    window.removeEventListener("resize", state.onReposition);
    const onEnd = state.onEnd;
    state = null;
    if (typeof onEnd === "function") onEnd();
  }

  function renderStep() {
    const { steps, index, accent } = state;
    const step = steps[index];
    const target = document.querySelector(step.selector);

    if (state.currentTarget) {
      state.currentTarget.classList.remove("feature-tour-highlight");
      state.currentTarget.style.removeProperty("--tour-glow");
    }

    if (!target) {
      // Paso sin elemento anclado en esta pantalla: mostrar el tooltip centrado.
      state.currentTarget = null;
      positionTooltipCentered();
    } else {
      target.classList.add("feature-tour-highlight");
      target.style.setProperty("--tour-glow", ACCENTS[accent].glow);
      target.scrollIntoView({ behavior: "smooth", block: "center" });
      state.currentTarget = target;
      // Esperar al scroll suave antes de posicionar.
      setTimeout(() => positionTooltipNear(target), 250);
    }

    state.tooltip.querySelector(".ft-title").textContent = step.title;
    state.tooltip.querySelector(".ft-text").textContent = step.text;
    state.tooltip.querySelector(".ft-progress").textContent =
      (index + 1) + " / " + steps.length;

    const backBtn = state.tooltip.querySelector(".ft-back");
    const nextBtn = state.tooltip.querySelector(".ft-next");
    backBtn.disabled = index === 0;
    nextBtn.textContent = index === steps.length - 1 ? "Entendido" : "Siguiente";
  }

  function positionTooltipNear(target) {
    const tooltip = state.tooltip;
    const rect = target.getBoundingClientRect();
    const tRect = tooltip.getBoundingClientRect();
    let top = rect.bottom + window.scrollY + 12;
    let left = rect.left + window.scrollX;

    if (left + tRect.width > window.scrollX + window.innerWidth - 16) {
      left = window.scrollX + window.innerWidth - tRect.width - 16;
    }
    if (left < window.scrollX + 16) left = window.scrollX + 16;

    if (top + tRect.height > window.scrollY + window.innerHeight - 16) {
      // No cabe abajo: colocarlo arriba del elemento.
      top = rect.top + window.scrollY - tRect.height - 12;
    }

    tooltip.style.top = top + "px";
    tooltip.style.left = left + "px";
    tooltip.style.transform = "none";
  }

  function positionTooltipCentered() {
    const tooltip = state.tooltip;
    tooltip.style.top = "50%";
    tooltip.style.left = "50%";
    tooltip.style.transform = "translate(-50%, -50%)";
  }

  function next() {
    if (state.index < state.steps.length - 1) {
      state.index += 1;
      renderStep();
    } else {
      cleanup();
    }
  }

  function back() {
    if (state.index > 0) {
      state.index -= 1;
      renderStep();
    }
  }

  function buildTooltip(accent) {
    const colors = ACCENTS[accent];
    const tooltip = document.createElement("div");
    tooltip.className = "feature-tour-tooltip";
    tooltip.style.borderColor = colors.border;
    tooltip.innerHTML =
      '<div class="ft-header">' +
      '<span class="ft-title" style="color:' + colors.text + '"></span>' +
      '<button type="button" class="ft-close" aria-label="Cerrar">&times;</button>' +
      "</div>" +
      '<p class="ft-text"></p>' +
      '<div class="ft-footer">' +
      '<span class="ft-progress"></span>' +
      '<div class="ft-buttons">' +
      '<button type="button" class="ft-back">Atrás</button>' +
      '<button type="button" class="ft-next" style="background:' + colors.border + '"></button>' +
      "</div></div>";
    document.body.appendChild(tooltip);
    tooltip.querySelector(".ft-close").addEventListener("click", cleanup);
    tooltip.querySelector(".ft-back").addEventListener("click", back);
    tooltip.querySelector(".ft-next").addEventListener("click", next);
    return tooltip;
  }

  function startFeatureTour(steps, accent, options) {
    if (!steps || !steps.length) return;
    cleanup();
    options = options || {};

    if (typeof options.onStart === "function") options.onStart();

    const backdrop = document.createElement("div");
    backdrop.className = "feature-tour-backdrop";
    backdrop.addEventListener("click", cleanup);
    document.body.appendChild(backdrop);

    state = {
      steps: steps,
      index: 0,
      accent: accent,
      backdrop: backdrop,
      tooltip: buildTooltip(accent),
      currentTarget: null,
      onEnd: options.onEnd,
      onKeydown: (e) => {
        if (e.key === "Escape") cleanup();
        if (e.key === "ArrowRight") next();
        if (e.key === "ArrowLeft") back();
      },
      onReposition: () => {
        if (state && state.currentTarget) positionTooltipNear(state.currentTarget);
      },
    };
    document.addEventListener("keydown", state.onKeydown);
    window.addEventListener("resize", state.onReposition);

    // Dar tiempo a que un onStart que cambia el layout (ej. mostrar un panel
    // oculto) termine su transicion antes de medir posiciones.
    setTimeout(renderStep, 50);
  }

  window.startFeatureTour = startFeatureTour;
})(window);
