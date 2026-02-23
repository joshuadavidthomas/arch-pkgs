## Multi-monitor reproduction and one-line fix

I'm seeing this reliably on a **4-monitor setup** (3× 1080p + 1× 4K) connected via USB-C dock. Works fine on the laptop screen alone — the crashes only happen with the additional monitors connected. This makes sense: each new `wl_output` triggers geometry, mode, scale, and `xdg_output` events to every client, and with 4 outputs the burst easily overflows the 4 KiB buffer.

**Kill log from a single day** (every app closure matched a `Data too big for buffer` error):

| Time  | App killed              |
|-------|-------------------------|
| 03:30 | (unknown)               |
| 10:51 | helium-browser          |
| 10:59 | zoom (2×)               |
| 11:03 | helium-browser          |
| 11:26 | helium-browser          |
| 11:34 | ghostty                 |
| 12:04 | xwayland-satellite      |
| 12:05 | ghostty                 |
| 12:57 | helium-browser, ghostty (2×) |

**Environment:** niri 25.11, Arch Linux, wayland 1.24.0, Intel GPU

### Fix

Sway ([swaywm/sway#8532](https://github.com/swaywm/sway/pull/8532)) and Hyprland both fix this by calling `wl_display_set_default_max_buffer_size()` (available since libwayland 1.23) to increase the buffer to 1 MiB. Here's a working patch for niri:

```diff
diff --git a/src/main.rs b/src/main.rs
index 995960e..3d5c299 100644
--- a/src/main.rs
+++ b/src/main.rs
@@ -38,6 +38,39 @@ const DEFAULT_LOG_FILTER: &str = "niri=debug,smithay::backend::renderer::gles=er
 static GLOBAL: tracy_client::ProfiledAllocator<std::alloc::System> =
     tracy_client::ProfiledAllocator::new(std::alloc::System, 100);
 
+/// Increase the Wayland client buffer size from the 4 KiB default.
+///
+/// The default is too small when many wl_output events are sent at once
+/// (e.g. multi-monitor setups with 4K displays), causing libwayland to
+/// emit "Data too big for buffer" and disconnect the client.
+///
+/// See: <https://github.com/YaLTeR/niri/issues/2437>
+fn set_max_wayland_buffer_size(display: &mut Display<State>, size: usize) {
+    // SAFETY: display_ptr() returns a valid *mut wl_display that outlives this call.
+    // wl_display_set_default_max_buffer_size is available since libwayland 1.23 and
+    // simply sets an integer field on the display — no complex invariants.
+    unsafe {
+        let wl_display = display.backend().handle().display_ptr();
+        let lib = libc::dlopen(
+            c"libwayland-server.so.0".as_ptr(),
+            libc::RTLD_NOLOAD | libc::RTLD_NOW,
+        );
+        if lib.is_null() {
+            warn!("could not find loaded libwayland-server; buffer size unchanged");
+            return;
+        }
+        let sym = libc::dlsym(lib, c"wl_display_set_default_max_buffer_size".as_ptr());
+        libc::dlclose(lib);
+        if sym.is_null() {
+            warn!("wl_display_set_default_max_buffer_size unavailable (need libwayland >= 1.23)");
+            return;
+        }
+        let f: unsafe extern "C" fn(*mut std::ffi::c_void, usize) = std::mem::transmute(sym);
+        f(wl_display.cast(), size);
+    }
+    info!("set Wayland max client buffer size to {size} bytes");
+}
+
 fn main() -> Result<(), Box<dyn std::error::Error>> {
     // Set backtrace defaults if not set.
     if env::var_os("RUST_BACKTRACE").is_none() {
@@ -168,7 +201,8 @@ fn main() -> Result<(), Box<dyn std::error::Error>> {
     niri::utils::signals::listen(&event_loop.handle());
 
     // Create the compositor.
-    let display = Display::new().unwrap();
+    let mut display = Display::new().unwrap();
+    set_max_wayland_buffer_size(&mut display, 1024 * 1024);
     let mut state = State::new(
         config,
         event_loop.handle(),
```

The `dlopen`/`dlsym` approach is used because `wayland-sys` 0.31 doesn't expose this symbol, but niri links libwayland-server dynamically at runtime anyway. An alternative would be to add the binding upstream in `wayland-sys` or `smithay`.

Ideally this would be a one-liner in smithay's `Display::new()` but until then, this works.
