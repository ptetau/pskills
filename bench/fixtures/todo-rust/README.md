# todo

todo is a small to-do list web app. It has one page with the list and a form that adds an
item. It uses only the Rust standard library.

## Use

```
cargo run --release
```

Then open http://127.0.0.1:8080/. The `PORT` variable sets the port, and `DATA_FILE` sets
the file that holds the items (`todo.txt` by default).

- `GET /` shows the page. Each item is one entry of the list, in the order in which it was
  added. With no items, the page says "Nothing to do."
- `POST /items` with the form field `text` adds an item, and answers 303 to `/`. The text
  loses the spaces at its start and end. Empty text answers 400 with
  `error: text is empty`.
- Any other request answers 404 with `error: not found`.

The data file has one item on each line: the id, a tab, and the text. Ids start at 1. A
missing file holds no items.

## Code

- `src/store.rs`: the storage of the items.
- `src/page.rs`: the HTML of the page.
- `src/http.rs`: the HTTP reader and writer.
- `src/lib.rs`: the routes. `src/main.rs`: the server.

## Test

```
cargo test
```
