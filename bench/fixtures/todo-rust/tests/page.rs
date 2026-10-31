use todo::page::render;
use todo::store::Item;

#[test]
fn an_empty_list_says_nothing_to_do() {
    let html = render(&[]);
    assert!(html.contains("<p>Nothing to do.</p>"));
    assert!(html.contains("<form method=\"post\" action=\"/items\">"));
}

#[test]
fn each_item_is_a_list_entry_with_escaped_text() {
    let html = render(&[Item { id: 1, text: "milk".into() }, Item { id: 2, text: "<b>&".into() }]);
    assert!(html.contains("<li>milk</li>"));
    assert!(html.contains("<li>&lt;b&gt;&amp;</li>"));
}
