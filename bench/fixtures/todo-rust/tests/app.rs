use std::fs;

use todo::handle;
use todo::http::{form_value, Request};
use todo::store::Store;

fn store(name: &str) -> Store {
    let dir = std::env::temp_dir().join(format!("todo-app-{}-{}", std::process::id(), name));
    fs::create_dir_all(&dir).unwrap();
    let path = dir.join("todo.txt");
    let _ = fs::remove_file(&path);
    Store::new(path)
}

#[test]
fn adding_an_item_redirects_to_the_page_that_lists_it() {
    let store = store("add");
    let added = handle(&store, &Request::new("POST", "/items", "text=oat+milk%21"));
    assert_eq!(added.status, 303);
    assert_eq!(added.location.as_deref(), Some("/"));
    let page = handle(&store, &Request::new("GET", "/", ""));
    assert_eq!(page.status, 200);
    assert!(page.body.contains("<li>oat milk!</li>"));
}

#[test]
fn empty_text_is_an_error() {
    let store = store("empty");
    let response = handle(&store, &Request::new("POST", "/items", "text=++"));
    assert_eq!(response.status, 400);
    assert_eq!(response.body, "error: text is empty\n");
}

#[test]
fn an_unknown_path_is_not_found() {
    let store = store("unknown");
    let response = handle(&store, &Request::new("GET", "/nowhere", ""));
    assert_eq!(response.status, 404);
    assert_eq!(response.body, "error: not found\n");
}

#[test]
fn form_values_are_decoded() {
    assert_eq!(form_value("a=1&text=x%20y+z", "text").as_deref(), Some("x y z"));
    assert_eq!(form_value("a=1", "text"), None);
}
