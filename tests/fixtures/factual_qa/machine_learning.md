# Machine learning interpretation notes

## Probabilities

Increasing the softmax temperature makes the predicted class distribution
flatter. Temperature scaling changes confidence calibration but does not change
the ordering of logits.

## Evaluation

Macro F1 computes the F1 score for each class and then gives every class equal
weight in the average. This makes minority classes visible in the aggregate.

## Data boundaries

Fitting preprocessing statistics on the complete dataset leaks information from
the evaluation split. The statistics must be fitted on training data and then
applied unchanged to validation and test data.

## Calibration

A calibrated 0.8 confidence means that, across comparable predictions, roughly
80 percent should be correct. It does not guarantee that a particular
prediction is correct.
