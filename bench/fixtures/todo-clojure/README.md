# todo

todo is a small to-do list web app. It has one page with the list and a form that adds an
item. It uses only Clojure 1.11 and the Java standard library.

## Use

```
clojure -cp src -m todo.main
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

- `src/todo/store.clj`: the storage of the items.
- `src/todo/page.clj`: the HTML of the page.
- `src/todo/http.clj`: the HTTP reader and writer.
- `src/todo/app.clj`: the routes. `src/todo/main.clj`: the server.

## Test

```
clojure -cp src:test -m todo.run-tests
```

With arguments, the runner runs only the tests whose name holds one of them, for example
`clojure -cp src:test -m todo.run-tests empty`.
