# TODO generalize so different datasets can be used
from sklearn import model_selection

import cupsnbottles.load_cupsnbottles as load_cupsnbottles
import tools.basics as tools

print(__doc__)
import pandas as pd
import numpy as np
from sklearn.neural_network import MLPClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import SVC
from sklearn.gaussian_process import GaussianProcessClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.discriminant_analysis import QuadraticDiscriminantAnalysis
from sklearn.decomposition import PCA
from sklearn.model_selection import GridSearchCV
from joblib import dump, load
# installation: pip install git+https://github.com/vlosing/ILVQ.git Quelle: https://github.com/vlosing/ILVQ/blob/master/ILVQ/GLVQ.py
from ILVQ.TrainTestSplitsManager import TrainTestSplitsManager
from ILVQ.hyperParameterFactory import getDefaultHyperParams
from ILVQ.auxiliaryFunctions import trainClassifier, updateClassifierEvaluations, getTrainSetCfg
from ILVQ.LVQFactory import getLVQClassifier
import os

################################################################################
####################################specify#####################################

classifier = "GLVQ"
num_samples = 2179 #at most 2179, default: None
dims = None # number of dimensions to reduce to before training
dims_method = None
#dims_method = 'pca'
#dims_method = 'tsne'

path_dataset = "dataset01/" # TODO generalize so different datasets can be used
path_trained_classifiers = 'trained_classifiers/' # specify where trained classifiers should be saved to
path_best_params = 'classifiers_best_params/' # specify where best parameters should be saved to

classifier_names = ["Nearest Neighbors", "Linear SVM", "RBF SVM", "Gaussian Process",
          "Decision Tree", "Random Forest", "Neural Net", "Naive Bayes", "QDA", "GLVQ"]

# can be adjusted
parameters = [
    {'n_neighbors': [2, 5, 10], 'weights': ['uniform', 'distance'], 'algorithm': ['auto', 'brute']}, # K Nearest Neighbors
    {'kernel':['linear'], 'C': [1, 5, 10], 'probability': [True], 'random_state':[17, 42]}, # Linear SVM (predict_proba with Platt scaling)
    {'kernel':['rbf'], 'C':[1, 5, 10], 'probability': [True], 'random_state':[17, 42]}, # RBF SVM (predict_proba with Platt scaling)
    {'random_state':[17, 42]}, # Gaussian Process
    {'max_depth':[None, 5, 10], 'min_samples_split': [2, 5, 10], 'random_state':[17, 42]}, # Decision Tree
    {'max_depth':[None, 5, 10], 'n_estimators':[10, 50, 100], 'max_features':[1], 'random_state':[17, 42]}, # Random Forest
    {'alpha': [0.0001, 0.001], 'max_iter': [1000, 2000], 'random_state':[17, 42]}, # Neural Net
    {}, # Naive Bayes
    #{'var_smoothing': [1e-9]}, # Naive Bayes this does not work eventough it's the default value
    {'reg_param': [0.0, 0.5],'tol': [1.0e-2, 1.0e-4, 1.0e-6]}] # Quadratic Discriminant Analysis
    #{} #{'max_iter':[2500, 5000], 'beta':[1, 2], 'random_state':[17, 42]}] # qlvq

classifiers = [
     KNeighborsClassifier(),
     SVC(),
     SVC(),
     GaussianProcessClassifier(),
     DecisionTreeClassifier(),
     RandomForestClassifier(),
     MLPClassifier(),
     GaussianNB(),
     QuadraticDiscriminantAnalysis()]



################################################################################
def save_grid_search_results(clf, classifier_name):
    result_path_params = os.path.join(path_best_params, path_dataset)
    if not os.path.isdir(result_path_params):
        os.mkdir(result_path_params)

    result_path_clf= os.path.join(path_trained_classifiers, path_dataset)
    if not os.path.isdir(result_path_clf):
        os.mkdir(result_path_clf)

    result_df = pd.DataFrame.from_dict(clf.cv_results_)
    result_df.insert(0, "Params", clf.cv_results_['params'], True)
    result_df.to_csv(result_path_params + "grid_search_" + classifier_name.replace(' ', '_') + ".csv", mode='w', sep=";", index=False)
    dump(clf, result_path_clf + classifier.replace(' ', '_') + '.joblib')
    dump(clf.best_params_, result_path_params+ classifier.replace(' ', '_') + '_params.joblib')

    print('The best parameters for ' +  classifier_name + ' are: ', clf.best_params_, ' with score: ', clf.best_score_)


def run_GLVQ(X, y_encoded, label_names):
    X_train, X_test, y_train, y_test = model_selection.train_test_split(X, y_encoded, test_size=0.33, random_state=42)

    clf = getLVQClassifier(netType='GLVQ', insertionStrategy='samplingCost')

    predictedLabels, complexity, complexityNumParameterMetric = clf.trainOnline(X_train, y_train, label_names, metaData=None, chunkSize=1)

    result_path_clf = os.path.join(path_trained_classifiers, path_dataset)
    if not os.path.isdir(result_path_clf):
        os.mkdir(result_path_clf)
    dump(clf, result_path_clf + classifier.replace(' ', '_') + '.joblib')
    print("Acc: ", clf.getAccuracy(X_test, y_test))
    print(complexity)
    print(complexityNumParameterMetric)

def grid_search(X, y, label_names, classifier=None):
    """
    Performs grid search of either a specific or all implemented classifiers and
    saves the trained classifier in /trained_classifiers
    :param: X = dataset
    :param: y = labels
    :param: classifier = some string in classifier_names to specify the model (optional)
    :returns: trained classifier (or list of those) with best parameters
    """

    gs_classifiers = []

    # perform grid search over specified classifier
    if classifier is not None:
        if classifier == "GLVQ":
            run_GLVQ(X, y, label_names)
        else:
            clf_index = classifier_names.index(classifier)
            clf = GridSearchCV(classifiers[clf_index], parameters[clf_index], return_train_score=True)
            #clf = classifiers[clf_index]
            clf.fit(X, y)
            gs_classifiers.append(clf)
            save_grid_search_results(clf, classifier)
        print('>> DONE')

    # perform grid search over all classifier
    else:
        for i, classifier in enumerate(classifiers):

            clf = GridSearchCV(classifier, parameters[i], return_train_score=True)
            clf.fit(X, y)
            gs_classifiers.append(clf)
            save_grid_search_results(clf, classifier_names[i])
        print('>> DONE')

    return gs_classifiers


def dim_red(X, dims=2, init='pca'):
    """
    :param: X = dataset
    :param: dims = number of dimensions
    :param: init = either 'pca' or 'tsne'
    """
    if init == 'pca':
        pca = PCA(dims)
        X_embedded = pca.fit_transform(X)

    elif init == 'tsne':
        X_embedded = tools.t_sne(X, dims)
    return X_embedded


def main():
    # load the data
    X, y_encoded, y, label_names, df = tools.load_gt_data(num_samples, path=path_dataset)

    if dims is not None:
        if dims_method:
            X = dim_red(X, dims, dims_method)
        else:
            X = dim_red(X, dims)

    gs_classifiers = grid_search(X, y_encoded, label_names, classifier)

if __name__ == "__main__":
    main()
