(ns todo.page
  "The page: the list of items and the form that adds an item."
  (:require [clojure.string :as str]))

(defn escape
  "The text, safe to put between HTML tags."
  [text]
  (str/escape text {\& "&amp;" \< "&lt;" \> "&gt;" \" "&quot;"}))

(defn render [items]
  (str "<!doctype html>\n<html><head><meta charset=\"utf-8\"><title>To-do</title></head>\n<body>\n"
       "<h1>To-do</h1>\n"
       (if (empty? items)
         "<p>Nothing to do.</p>\n"
         (str "<ul>\n" (apply str (map #(str "<li>" (escape (:text %)) "</li>\n") items)) "</ul>\n"))
       "<form method=\"post\" action=\"/items\">"
       "<input name=\"text\" aria-label=\"New item\"> <button>Add</button></form>\n"
       "</body></html>\n"))
