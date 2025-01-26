#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import os
import tempfile
import unittest

import numpy as np

from pyspark.ml.evaluation import BinaryClassificationEvaluator
from pyspark.ml.linalg import Vectors
from pyspark.ml.classification import LogisticRegression
from pyspark.ml.tuning import ParamGridBuilder, CrossValidator, CrossValidatorModel
from pyspark.testing.sqlutils import ReusedSQLTestCase


class TuningTestsMixin:
    def test_cross_validator(self):
        dataset = self.spark.createDataFrame(
            [
                (Vectors.dense([0.0]), 0.0),
                (Vectors.dense([0.4]), 1.0),
                (Vectors.dense([0.5]), 0.0),
                (Vectors.dense([0.6]), 1.0),
                (Vectors.dense([1.0]), 1.0),
            ]
            * 10,
            ["features", "label"],
        )
        lr = LogisticRegression()
        grid = ParamGridBuilder().addGrid(lr.maxIter, [0, 1]).build()
        evaluator = BinaryClassificationEvaluator()
        cv = CrossValidator(
            estimator=lr, estimatorParamMaps=grid, evaluator=evaluator, parallelism=1
        )

        self.assertEqual(cv.getEstimator(), lr)
        self.assertEqual(cv.getEvaluator(), evaluator)
        self.assertEqual(cv.getParallelism(), 1)
        self.assertEqual(cv.getEstimatorParamMaps(), grid)

        model = cv.fit(dataset)
        self.assertEqual(model.getEstimator(), lr)
        self.assertEqual(model.getEvaluator(), evaluator)
        self.assertEqual(model.getEstimatorParamMaps(), grid)
        self.assertTrue(np.isclose(model.avgMetrics[0], 0.5, atol=1e-4))

        output = model.transform(dataset)
        self.assertEqual(
            output.columns, ["features", "label", "rawPrediction", "probability", "prediction"]
        )
        self.assertEqual(output.count(), 50)

        # save & load
        with tempfile.TemporaryDirectory(prefix="cv_lr") as d:
            path1 = os.path.join(d, "cv")
            cv.write().save(path1)
            cv2 = CrossValidator.load(path1)
            self.assertEqual(str(cv), str(cv2))
            self.assertEqual(str(cv.getEstimator()), str(cv2.getEstimator()))
            self.assertEqual(str(cv.getEvaluator()), str(cv2.getEvaluator()))

            path2 = os.path.join(d, "cv_model")
            model.write().save(path2)
            model2 = CrossValidatorModel.load(path2)
            self.assertEqual(str(model), str(model2))
            self.assertEqual(str(model.getEstimator()), str(model2.getEstimator()))
            self.assertEqual(str(model.getEvaluator()), str(model2.getEvaluator()))


class TuningTests(TuningTestsMixin, ReusedSQLTestCase):
    pass


if __name__ == "__main__":
    from pyspark.ml.tests.test_tuning import *  # noqa: F401

    try:
        import xmlrunner

        testRunner = xmlrunner.XMLTestRunner(output="target/test-reports", verbosity=2)
    except ImportError:
        testRunner = None
    unittest.main(testRunner=testRunner, verbosity=2)
