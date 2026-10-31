(ns todo.http
  "A small HTTP/1.1 reader and writer, enough for one page and one form."
  (:require [clojure.string :as str])
  (:import [java.io BufferedInputStream ByteArrayOutputStream]
           [java.net URLDecoder]
           [java.nio.charset StandardCharsets]))

(defn- read-line* [^BufferedInputStream in]
  (let [out (ByteArrayOutputStream.)]
    (loop []
      (let [b (.read in)]
        (cond
          (= b -1) (when (pos? (.size out)) (String. (.toByteArray out) StandardCharsets/UTF_8))
          (= b 10) (str/replace (String. (.toByteArray out) StandardCharsets/UTF_8) #"\r$" "")
          :else (do (.write out b) (recur)))))))

(defn read-request
  "One request: the method, the path, the query, the headers, and the body."
  [input]
  (let [in (BufferedInputStream. input)
        [method target] (some-> (read-line* in) (str/split #" "))]
    (when (and method target)
      (let [headers (loop [acc {}]
                      (let [line (read-line* in)]
                        (if (str/blank? line)
                          acc
                          (let [[k v] (str/split line #":" 2)]
                            (recur (assoc acc (str/lower-case (str/trim k)) (str/trim (or v ""))))))))
            length (parse-long (get headers "content-length" "0"))
            body (byte-array (or length 0))]
        (loop [read 0]
          (when (< read (alength body))
            (let [n (.read in body read (- (alength body) read))]
              (when (pos? n) (recur (+ read n))))))
        (let [[path query] (str/split target #"\?" 2)]
          {:method method :path path :query (or query "") :headers headers
           :body (String. body StandardCharsets/UTF_8)})))))

(defn form-value
  "The decoded value of one field of a form body (application/x-www-form-urlencoded)."
  [body field]
  (some (fn [pair]
          (let [[k v] (str/split pair #"=" 2)]
            (when (= (URLDecoder/decode k "UTF-8") field)
              (URLDecoder/decode (or v "") "UTF-8"))))
        (str/split body #"&")))

(def ^:private reasons {200 "OK" 303 "See Other" 400 "Bad Request" 404 "Not Found" 500 "Internal Server Error"})

(defn write-response [output {:keys [status content-type location body]}]
  (let [bytes (.getBytes ^String body StandardCharsets/UTF_8)
        head (str "HTTP/1.1 " status " " (reasons status "Error") "\r\n"
                  "Content-Type: " content-type "\r\n"
                  (when location (str "Location: " location "\r\n"))
                  "Content-Length: " (alength bytes) "\r\nConnection: close\r\n\r\n")]
    (.write output (.getBytes head StandardCharsets/UTF_8))
    (.write output bytes)
    (.flush output)))

(defn html [status body] {:status status :content-type "text/html; charset=utf-8" :body body})
(defn text [status body] {:status status :content-type "text/plain; charset=utf-8" :body (str body "\n")})
(defn redirect [location] {:status 303 :content-type "text/plain; charset=utf-8" :location location :body ""})
