(ns todo.store-test
  (:require [clojure.java.io :as io]
            [clojure.test :refer [deftest is]]
            [todo.store :as store]))

(defn- temp-file [name]
  (let [file (io/file (System/getProperty "java.io.tmpdir") (str "todo-test-" name ".txt"))]
    (.delete file)
    (.getPath file)))

(deftest a-missing-file-holds-no-items
  (is (= [] (store/load-items (temp-file "missing")))))

(deftest items-keep-their-order-and-get-the-next-id
  (let [path (temp-file "order")]
    (store/add! path "milk")
    (store/add! path "eggs")
    (is (= [{:id 1 :text "milk"} {:id 2 :text "eggs"}] (store/load-items path)))
    (is (= "1\tmilk\n2\teggs\n" (slurp path)))))

(deftest tabs-and-line-breaks-become-spaces
  (is (= "a b c" (:text (store/add! (temp-file "tabs") "a\tb\nc")))))
