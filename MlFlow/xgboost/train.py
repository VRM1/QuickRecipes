import argparse

from sklearn import datasets
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, log_loss
import xgboost as xgb
import matplotlib as mpl
import time

import mlflow
import mlflow.xgboost
from mlflow.tracking import MlflowClient

mpl.use("Agg")

class Plotting(xgb.callback.TrainingCallback):

    def __init__(self, rounds):

        self.rounds = rounds

    def after_iteration(self, model, epoch, evals_log):

        for data, metric in evals_log.items():
            for metric_name, log in metric.items():        
                mlflow.log_metric(key="vin_"+metric_name, value=log[epoch], step=epoch)
        # time.sleep(2)
        return False


def parse_args():
    
    parser = argparse.ArgumentParser(description="XGBoost example")
    parser.add_argument(
        "--learning-rate",
        type=float,
        default=0.3,
        help="learning rate to update step size at each boosting step (default: 0.3)",
    )
    parser.add_argument(
        "--colsample-bytree",
        type=float,
        default=1.0,
        help="subsample ratio of columns when constructing each tree (default: 1.0)",
    )
    parser.add_argument(
        "--subsample",
        type=float,
        default=1.0,
        help="subsample ratio of the training instances (default: 1.0)",
    )
    return parser.parse_args()

# the conventional way of training the model
def main_regular():

    client = MlflowClient()
    try:
        experiment_id = client.create_experiment("XGboost")
    except:
        experiment_id = client.get_experiment_by_name("XGboost").experiment_id
    # parse command-line arguments
    args = parse_args()

    # prepare train and test data
    iris = datasets.load_iris()
    X = iris.data
    y = iris.target
    num_boost_round = 1000
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    plotting = Plotting(num_boost_round)
    # enable auto logging
    mlflow.xgboost.autolog()

    dtrain = xgb.DMatrix(X_train, label=y_train)
    dtest = xgb.DMatrix(X_test, label=y_test)

    with mlflow.start_run(experiment_id=experiment_id):

        # train model
        params = {
            "objective": "multi:softprob",
            "num_class": 3,
            "learning_rate": args.learning_rate,
            "eval_metric": "mlogloss",
            "colsample_bytree": args.colsample_bytree,
            "subsample": args.subsample,
            "seed": 42,
        }
        
        model = xgb.train(params, dtrain, evals=[(dtest, "test")],\
             num_boost_round=num_boost_round, callbacks=[plotting], \
                  early_stopping_rounds=10)

        # evaluate model
        y_proba = model.predict(dtest)
        y_pred = y_proba.argmax(axis=1)
        loss = log_loss(y_test, y_proba)
        acc = accuracy_score(y_test, y_pred)

        # log metrics
        mlflow.log_metrics({"log_loss": loss, "accuracy": acc})

# a cross validation way of training the model
def main_cross_validate():

    client = MlflowClient()
    try:
        experiment_id = client.create_experiment("XGboost")
    except:
        experiment_id = client.get_experiment_by_name("XGboost").experiment_id
    # parse command-line arguments
    args = parse_args()

    # prepare train and test data
    iris = datasets.load_iris()
    X = iris.data
    y = iris.target
    num_boost_round = 1000
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    plotting = Plotting(num_boost_round)
    # enable auto logging
    mlflow.xgboost.autolog()

    dtrain = xgb.DMatrix(X_train, label=y_train)
    dtest = xgb.DMatrix(X_test, label=y_test)

    with mlflow.start_run(experiment_id=experiment_id):

        # train model
        params = {
            "objective": "multi:softprob",
            "num_class": 3,
            "learning_rate": args.learning_rate,
            "eval_metric": "auc",
            "colsample_bytree": args.colsample_bytree,
            "subsample": args.subsample,
            "seed": 42,
        }
        
        # list of all metrics https://xgboost.readthedocs.io/en/stable/parameter.html
        
        xgb_cv_results = xgb.cv(
        params=params,
        dtrain=dtrain,
        num_boost_round=num_boost_round,
        early_stopping_rounds=10,
        verbose_eval=False,
        nfold=10,
        stratified=True,
    )
    '''
    Note: unlike xgb.train, which returns several objects such as score, best model, etc., 
    xgb.cv, returns just a pandas dataframe with final results.
    See here: https://stackoverflow.com/questions/66681443/how-can-i-get-the-trained-model-from-xgboost-cv
    '''
    print(xgb_cv_results)

if __name__ == "__main__":
    main_cross_validate()