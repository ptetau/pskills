use std::env;
use std::net::TcpListener;

use todo::{handle, http, store::Store};

fn main() {
    let port = env::var("PORT").unwrap_or_else(|_| "8080".to_string());
    let data = env::var("DATA_FILE").unwrap_or_else(|_| "todo.txt".to_string());
    let listener = TcpListener::bind(format!("127.0.0.1:{}", port)).unwrap_or_else(|error| {
        eprintln!("error: cannot listen on port {}: {}", port, error);
        std::process::exit(2);
    });
    let store = Store::new(data);
    println!("listening on http://127.0.0.1:{}", port);
    for stream in listener.incoming() {
        let Ok(mut stream) = stream else { continue };
        match http::read_request(&mut stream) {
            Ok(request) => {
                let _ = handle(&store, &request).write_to(&mut stream);
            }
            Err(_) => {
                let _ = http::Response::text(400, "error: bad request").write_to(&mut stream);
            }
        }
    }
}
