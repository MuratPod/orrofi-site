(function () {
  document.documentElement.classList.add("js");
  try {
    if (localStorage.getItem("orrofi-platform") === "android") {
      document.documentElement.classList.add("platform-android");
    }
  } catch (err) {
    /* Storage can be blocked; iPhone stays the default. */
  }
})();
