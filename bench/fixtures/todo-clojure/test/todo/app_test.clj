(ns todo.app-test
  (:require [clojure.java.io :as io]
            [clojure.string :as str]
            [clojure.test :refer [deftest is]]
            [todo.app :as app]
            [todo.http :as http]))

(defn- data-file [name]
  (let [file (io/file (System/getProperty "java.io.tmpdir") (str "todo-app-" name ".txt"))]
    (.delete file)
    (.getPath file)))

(defn- request [method path body]
  {:method method :path path :query "" :headers {} :body body})

(deftest adding-an-item-redirects-to-the-page-that-lists-it
  (let [file (data-file "add")
        added (app/handle file (request "POST" "/items" "text=oat+milk%21"))
        page (app/handle file (request "GET" "/" ""))]
    (is (= 303 (:status added)))
    (is (= "/" (:location added)))
    (is (= 200 (:status page)))
    (is (str/includes? (:body page) "<li>oat milk!</li>"))))

(deftest empty-text-is-an-error
  (let [response (app/handle (data-file "empty") (request "POST" "/items" "text=++"))]
    (is (= 400 (:status response)))
    (is (= "error: text is empty\n" (:body response)))))

(deftest an-unknown-path-is-not-found
  (let [response (app/handle (data-file "unknown") (request "GET" "/nowhere" ""))]
    (is (= 404 (:status response)))
    (is (= "error: not found\n" (:body response)))))

(deftest form-values-are-decoded
  (is (= "x y z" (http/form-value "a=1&text=x%20y+z" "text")))
  (is (nil? (http/form-value "a=1" "text"))))
