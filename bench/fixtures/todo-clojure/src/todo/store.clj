(ns todo.store
  "Item storage: the to-do items in a text file, one item on each line.

  Each line is the id, a tab, and the text. A missing file holds no items."
  (:require [clojure.java.io :as io]
            [clojure.string :as str]))

(defn- parse-line [line]
  (let [[id text] (str/split line #"\t" 2)]
    (when (and text (re-matches #"\d+" id))
      {:id (Long/parseLong id) :text text})))

(defn load-items
  "Each item, in the order in which it was added."
  [path]
  (let [file (io/file path)]
    (if (.exists file)
      (->> (str/split-lines (slurp file)) (keep parse-line) vec)
      [])))

(defn- save! [path items]
  (spit path (apply str (map #(str (:id %) "\t" (:text %) "\n") items))))

(defn add!
  "Adds an item with the next free id. Tabs and line breaks in the text become spaces."
  [path text]
  (let [items (load-items path)
        id (inc (reduce max 0 (map :id items)))
        item {:id id :text (str/replace text #"[\t\r\n]" " ")}]
    (save! path (conj items item))
    item))
