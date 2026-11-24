(function () {
  document.documentElement.classList.add("js");

  var storageKey = "orrofi-platform";

  function storedPlatform() {
    try {
      return localStorage.getItem(storageKey) === "android" ? "android" : "iphone";
    } catch (err) {
      return "iphone";
    }
  }

  function applyPlatform(platform) {
    var android = platform === "android";
    document.documentElement.classList.toggle("platform-android", android);
    document.querySelectorAll(".platform-switch input").forEach(function (input) {
      input.checked = input.value === platform;
    });
  }

  function rememberPlatform(platform) {
    try {
      localStorage.setItem(storageKey, platform);
    } catch (err) {
      /* ignore */
    }
  }

  document.querySelectorAll(".platform-switch input").forEach(function (input) {
    input.addEventListener("change", function () {
      if (input.checked) {
        applyPlatform(input.value);
        rememberPlatform(input.value);
      }
    });
  });

  window.addEventListener("storage", function (event) {
    if (event.key === storageKey) {
      applyPlatform(event.newValue === "android" ? "android" : "iphone");
    }
  });

  applyPlatform(storedPlatform());

  var toggle = document.querySelector(".nav-toggle");
  var nav = document.querySelector("#nav");
  if (!toggle || !nav) {
    return;
  }

  function setOpen(open) {
    nav.classList.toggle("is-open", open);
    toggle.setAttribute("aria-expanded", open ? "true" : "false");
    toggle.textContent = open
      ? toggle.getAttribute("data-close")
      : toggle.getAttribute("data-open");
  }

  toggle.addEventListener("click", function () {
    setOpen(!nav.classList.contains("is-open"));
  });

  nav.querySelectorAll("a").forEach(function (link) {
    link.addEventListener("click", function () {
      setOpen(false);
    });
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") {
      setOpen(false);
    }
  });
})();
