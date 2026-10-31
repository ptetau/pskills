(ns todo.app
  "The routes of the to-do app."
  (:require [clojure.string :as str]
            [todo.http :as http]
            [todo.page :as page]
            [todo.store :as store]))

(defn handle
  "Answers one request. The data file holds the items between requests."
  [data-file {:keys [method path body]}]
  (try
    (cond
      (and (= method "GET") (= path "/"))
      (http/html 200 (page/render (store/load-items data-file)))

      (and (= method "POST") (= path "/items"))
      (let [text (str/trim (or (http/form-value body "text") ""))]
        (if (str/blank? text)
          (http/text 400 "error: text is empty")
          (do (store/add! data-file text) (http/redirect "/"))))

      :else (http/text 404 "error: not found"))
    (catch java.io.IOException e
      (http/text 500 (str "error: " (.getMessage e))))))
