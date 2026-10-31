//! A tiny to-do list web app: one page with the list and a form to add an item.

pub mod http;
pub mod page;
pub mod store;

use http::{Request, Response};
use store::Store;

/// Answers one request. The store holds the items between requests.
pub fn handle(store: &Store, request: &Request) -> Response {
    match (request.method.as_str(), request.path.as_str()) {
        ("GET", "/") => match store.load() {
            Ok(items) => Response::html(200, page::render(&items)),
            Err(error) => Response::text(500, &format!("error: {}", error)),
        },
        ("POST", "/items") => {
            let text = http::form_value(&request.body, "text").unwrap_or_default();
            let text = text.trim();
            if text.is_empty() {
                return Response::text(400, "error: text is empty");
            }
            match store.add(text) {
                Ok(_) => Response::redirect("/"),
                Err(error) => Response::text(500, &format!("error: {}", error)),
            }
        }
        _ => Response::text(404, "error: not found"),
    }
}
