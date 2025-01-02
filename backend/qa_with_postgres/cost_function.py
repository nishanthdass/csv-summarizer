import pandas as pd
import os

HOUSING_PATH = os.path.join("datasets", "housing")


def load_housing_data(housing_path=HOUSING_PATH):
    csv_path = os.path.join(housing_path, "housing.csv")
    return pd.read_csv(csv_path)

df = load_housing_data()

# print(df.head())

# print(df.info())

# # Sort the "median_income" column in ascending order
# sorted_income = df["median_income"].sort_values()

# print(sorted_income)


# print(df.describe())

# import matplotlib.pyplot as plt
# df.hist(bins=50, figsize=(20,15))
# plt.show()


from sklearn.model_selection import train_test_split
import numpy as np



df["income_cat"] = pd.cut(df["median_income"], bins=[0., 1.5, 3.0, 4.5, 6., np.inf], labels=[1, 2, 3, 4, 5])


import matplotlib.pyplot as plt
# df["income_cat"].hist(bins=50, figsize=(20,15))
# plt.show()

from sklearn.model_selection import StratifiedShuffleSplit
split = StratifiedShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
for train_index, test_index in split.split(df, df["income_cat"]):
    strat_train_set = df.loc[train_index]
    strat_test_set = df.loc[test_index]

# extra code – computes the data for Figure 2–10

def income_cat_proportions(data):
    return data["income_cat"].value_counts() / len(data)



train_set, test_set = train_test_split(df, test_size=0.2, random_state=42)

compare_props = pd.DataFrame({
    "Overall %": income_cat_proportions(df),
    "Random %": income_cat_proportions(test_set),
    "Stratified %":  strat_test_set["income_cat"].value_counts() / len(strat_test_set),
}).sort_index()
compare_props.index.name = "Income Category"
compare_props["Rand. Error %"] = (compare_props["Random %"] /
                                  compare_props["Overall %"] - 1) * 100
compare_props["Strat. Error %"] = (compare_props["Stratified %"] /
                                   compare_props["Overall %"] - 1) * 100


print((compare_props))

for set_ in (strat_train_set, strat_test_set):
 set_.drop("income_cat", axis=1, inplace=True)


housing = strat_train_set.copy()

print(housing.info())

from pandas.plotting import scatter_matrix
# attributes = ["median_house_value", "median_income", "total_rooms", "housing_median_age"]
# scatter_matrix(housing[attributes], figsize=(12, 8))

housing.plot(kind="scatter", x="median_income", y="median_house_value", alpha=0.1)

plt.show()