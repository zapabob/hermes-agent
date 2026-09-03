// Hermes Agent Windows Workstation - Interactivity & i18n Controller

document.addEventListener("DOMContentLoaded", () => {
  const DEFAULT_LANG = "en-GB";
  const SUPPORTED_LANGS = ["en-GB", "ja", "zh-CN"];
  let currentLang = DEFAULT_LANG;

  // Initialize Language from URL, localStorage, or Navigator
  function initLanguage() {
    const urlParams = new URLSearchParams(window.location.search);
    const langParam = urlParams.get("lang");
    if (langParam && SUPPORTED_LANGS.includes(langParam)) {
      return langParam;
    }

    const saved = localStorage.getItem("hermes_workstation_lang");
    if (saved && SUPPORTED_LANGS.includes(saved)) {
      return saved;
    }

    const browserLang = navigator.language || navigator.userLanguage || "";
    if (browserLang.startsWith("ja")) return "ja";
    if (browserLang.startsWith("zh")) return "zh-CN";

    return DEFAULT_LANG;
  }

  // Deep object resolver for i18n keys (e.g. "hero.headline")
  function getTranslation(lang, key) {
    const dict = window.HermesTranslations[lang] || window.HermesTranslations[DEFAULT_LANG];
    const parts = key.split(".");
    let current = dict;
    for (const p of parts) {
      if (current && typeof current === "object" && p in current) {
        current = current[p];
      } else {
        // Fallback to default language
        let fallback = window.HermesTranslations[DEFAULT_LANG];
        for (const fp of parts) {
          if (fallback && typeof fallback === "object" && fp in fallback) {
            fallback = fallback[fp];
          } else {
            return key;
          }
        }
        return fallback;
      }
    }
    return current;
  }

  // Apply Language to DOM
  function setLanguage(lang) {
    if (!SUPPORTED_LANGS.includes(lang)) lang = DEFAULT_LANG;
    currentLang = lang;
    localStorage.setItem("hermes_workstation_lang", lang);

    // Update HTML lang attribute
    document.documentElement.lang = lang === "zh-CN" ? "zh-Hans" : lang;

    // Update Title & Meta
    const metaTitle = getTranslation(lang, "meta.title");
    const metaDesc = getTranslation(lang, "meta.description");
    if (metaTitle) document.title = metaTitle;
    const descEl = document.querySelector('meta[name="description"]');
    if (descEl && metaDesc) descEl.setAttribute("content", metaDesc);

    // Update Elements with data-i18n
    const elements = document.querySelectorAll("[data-i18n]");
    elements.forEach(el => {
      const key = el.getAttribute("data-i18n");
      const trans = getTranslation(lang, key);
      if (trans) {
        if (el.tagName === "INPUT" || el.tagName === "TEXTAREA") {
          el.value = trans;
        } else {
          el.textContent = trans;
        }
      }
    });

    // Update elements with data-i18n-html
    const htmlElements = document.querySelectorAll("[data-i18n-html]");
    htmlElements.forEach(el => {
      const key = el.getAttribute("data-i18n-html");
      const trans = getTranslation(lang, key);
      if (trans) {
        el.innerHTML = trans;
      }
    });

    // Update Language Buttons UI state
    document.querySelectorAll(".lang-btn").forEach(btn => {
      if (btn.getAttribute("data-lang") === lang) {
        btn.classList.add("active");
      } else {
        btn.classList.remove("active");
      }
    });

    // Update URL query param without reload
    const url = new URL(window.location);
    url.searchParams.set("lang", lang);
    window.history.replaceState({}, "", url);
  }

  // Setup Language Buttons
  document.querySelectorAll(".lang-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const targetLang = btn.getAttribute("data-lang");
      setLanguage(targetLang);
    });
  });

  // Showcase Tabs (Home Screen vs Security Center)
  const tabButtons = document.querySelectorAll(".tab-btn");
  const panes = document.querySelectorAll(".showcase-content-pane");

  tabButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      const targetTab = btn.getAttribute("data-tab");

      tabButtons.forEach(b => b.classList.remove("active"));
      panes.forEach(p => p.classList.remove("active"));

      btn.classList.add("active");
      const targetPane = document.getElementById(`pane-${targetTab}`);
      if (targetPane) targetPane.classList.add("active");
    });
  });

  // Lightbox Modal for Screenshots
  const modal = document.getElementById("lightbox-modal");
  const lightboxImg = document.getElementById("lightbox-img");
  const zoomWrappers = document.querySelectorAll(".img-zoom-wrapper");
  const closeBtn = document.querySelector(".lightbox-close");

  zoomWrappers.forEach(wrap => {
    wrap.addEventListener("click", () => {
      const img = wrap.querySelector("img");
      if (img && modal && lightboxImg) {
        lightboxImg.src = img.src;
        lightboxImg.alt = img.alt;
        modal.classList.add("active");
        document.body.style.overflow = "hidden";
      }
    });
  });

  function closeModal() {
    if (modal) {
      modal.classList.remove("active");
      document.body.style.overflow = "";
    }
  }

  if (closeBtn) closeBtn.addEventListener("click", closeModal);
  if (modal) {
    modal.addEventListener("click", (e) => {
      if (e.target === modal) closeModal();
    });
  }
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeModal();
  });

  // Copy Clone Command & Toast Notification
  const copyBtn = document.getElementById("btn-copy-clone");
  const toast = document.getElementById("toast-notice");
  const cloneText = document.getElementById("clone-text");

  if (copyBtn && cloneText) {
    copyBtn.addEventListener("click", async () => {
      const textToCopy = cloneText.textContent.trim();
      try {
        await navigator.clipboard.writeText(textToCopy);
        showToast();
      } catch (err) {
        console.warn("navigator.clipboard failed, falling back to execCommand copy:", err);
        // Fallback
        const textarea = document.createElement("textarea");
        textarea.value = textToCopy;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand("copy");
        document.body.removeChild(textarea);
        showToast();
      }
    });
  }

  function showToast() {
    if (!toast) return;
    toast.classList.add("show");
    setTimeout(() => {
      toast.classList.remove("show");
    }, 3000);
  }

  // Initial render
  currentLang = initLanguage();
  setLanguage(currentLang);
});
