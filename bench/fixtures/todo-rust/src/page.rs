//! The page: the list of items and the form that adds an item.

use crate::store::Item;

pub fn render(items: &[Item]) -> String {
    let list = if items.is_empty() {
        "<p>Nothing to do.</p>\n".to_string()
    } else {
        let rows: String = items.iter().map(|item| format!("<li>{}</li>\n", escape(&item.text))).collect();
        format!("<ul>\n{}</ul>\n", rows)
    };
    format!(
        "<!doctype html>\n<html><head><meta charset=\"utf-8\"><title>To-do</title></head>\n<body>\n\
         <h1>To-do</h1>\n{}<form method=\"post\" action=\"/items\">\
         <input name=\"text\" aria-label=\"New item\"> <button>Add</button></form>\n</body></html>\n",
        list
    )
}

/// The text, safe to put between HTML tags.
pub fn escape(text: &str) -> String {
    text.replace('&', "&amp;").replace('<', "&lt;").replace('>', "&gt;").replace('"', "&quot;")
}
