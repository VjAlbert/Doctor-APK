// Hide the extra console window on Windows release builds.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod port;

use std::sync::Mutex;

use tauri::{Manager, RunEvent, State};
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;

/// The analysis engine runs as a sidecar process serving on a random loopback port.
#[derive(Default)]
struct Engine {
    port: Mutex<Option<u16>>,
    child: Mutex<Option<CommandChild>>,
}

/// The UI polls this until the engine has announced its port.
#[tauri::command]
fn engine_port(state: State<'_, Engine>) -> Option<u16> {
    *state.port.lock().unwrap()
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(Engine::default())
        .invoke_handler(tauri::generate_handler![engine_port])
        .setup(|app| {
            let (mut events, child) = app
                .shell()
                .sidecar("apkguard-engine")?
                .args(["serve", "--port", "0", "--exit-with-parent"])
                .spawn()?;
            *app.state::<Engine>().child.lock().unwrap() = Some(child);

            let handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                while let Some(event) = events.recv().await {
                    if let CommandEvent::Stdout(bytes) = event {
                        if let Some(found) = port::parse_port(&String::from_utf8_lossy(&bytes)) {
                            *handle.state::<Engine>().port.lock().unwrap() = Some(found);
                        }
                    }
                }
            });
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("failed to build the APKGuard app")
        .run(|app, event| {
            if let RunEvent::Exit = event {
                if let Some(child) = app.state::<Engine>().child.lock().unwrap().take() {
                    let _ = child.kill();
                }
            }
        });
}
