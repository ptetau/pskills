use std::fs;

use todo::store::{Item, Store};

fn temp_file(name: &str) -> std::path::PathBuf {
    let dir = std::env::temp_dir().join(format!("todo-test-{}-{}", std::process::id(), name));
    fs::create_dir_all(&dir).unwrap();
    let path = dir.join("todo.txt");
    let _ = fs::remove_file(&path);
    path
}

#[test]
fn a_missing_file_holds_no_items() {
    let store = Store::new(temp_file("missing"));
    assert_eq!(store.load().unwrap(), Vec::<Item>::new());
}

#[test]
fn items_keep_their_order_and_get_the_next_id() {
    let path = temp_file("order");
    let store = Store::new(&path);
    store.add("milk").unwrap();
    store.add("eggs").unwrap();
    let items = store.load().unwrap();
    assert_eq!(items, vec![Item { id: 1, text: "milk".into() }, Item { id: 2, text: "eggs".into() }]);
    assert_eq!(fs::read_to_string(&path).unwrap(), "1\tmilk\n2\teggs\n");
}

#[test]
fn tabs_and_line_breaks_become_spaces() {
    let store = Store::new(temp_file("tabs"));
    let item = store.add("a\tb\nc").unwrap();
    assert_eq!(item.text, "a b c");
}
