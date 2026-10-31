(ns todo.run-tests
  "Runs each test namespace under test/: the files whose name ends with _test.clj. With
  arguments, it runs only the tests whose name holds one of them."
  (:require [clojure.java.io :as io]
            [clojure.string :as str]
            [clojure.test :as t]))

(defn- test-namespaces []
  (->> (file-seq (io/file "test"))
       (map #(.getPath %))
       (filter #(str/ends-with? % "_test.clj"))
       sort
       (map #(-> % (str/replace #"^test/" "") (str/replace #"\.clj$" "")
                 (str/replace "/" ".") (str/replace "_" "-") symbol))))

(defn -main [& patterns]
  (let [names (test-namespaces)]
    (apply require names)
    (let [result (if (seq patterns)
                   ;; Only the tests whose name holds one of the patterns, with the usual summary.
                   (binding [t/*report-counters* (ref t/*initial-report-counters*)]
                     (t/test-vars (for [n names [_ v] (sort-by key (ns-interns n))
                                        :when (and (:test (meta v)) (some #(str/includes? (str v) %) patterns))]
                                    v))
                     (t/do-report (assoc @t/*report-counters* :type :summary))
                     @t/*report-counters*)
                   (apply t/run-tests names))
          failed (+ (:fail result 0) (:error result 0))]
      (shutdown-agents)
      (System/exit (if (pos? failed) 1 0)))))
