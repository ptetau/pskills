(ns todo.main
  "The server: listens on 127.0.0.1 and answers one request at a time."
  (:require [todo.app :as app]
            [todo.http :as http])
  (:import [java.net InetAddress ServerSocket])
  (:gen-class))

(defn -main [& _]
  (let [port (parse-long (or (System/getenv "PORT") "8080"))
        data-file (or (System/getenv "DATA_FILE") "todo.txt")
        server (try (ServerSocket. port 50 (InetAddress/getByName "127.0.0.1"))
                    (catch java.io.IOException e
                      (binding [*out* *err*] (println (str "error: cannot listen on port " port ": " (.getMessage e))))
                      (System/exit 2)))]
    (println (str "listening on http://127.0.0.1:" port))
    (flush)
    (loop []
      (with-open [socket (.accept server)]
        ;; A client that closes the connection early does not stop the server.
        (try
          (let [request (try (http/read-request (.getInputStream socket)) (catch Exception _ nil))]
            (http/write-response (.getOutputStream socket)
                                 (if request (app/handle data-file request) (http/text 400 "error: bad request"))))
          (catch java.io.IOException _)))
      (recur))))
