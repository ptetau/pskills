(ns todo.page-test
  (:require [clojure.string :as str]
            [clojure.test :refer [deftest is]]
            [todo.page :as page]))

(deftest an-empty-list-says-nothing-to-do
  (let [html (page/render [])]
    (is (str/includes? html "<p>Nothing to do.</p>"))
    (is (str/includes? html "<form method=\"post\" action=\"/items\">"))))

(deftest each-item-is-a-list-entry-with-escaped-text
  (let [html (page/render [{:id 1 :text "milk"} {:id 2 :text "<b>&"}])]
    (is (str/includes? html "<li>milk</li>"))
    (is (str/includes? html "<li>&lt;b&gt;&amp;</li>"))))
