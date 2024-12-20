import pandas as pd
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv
import matplotlib.pyplot as plt
import numpy as np
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from sklearn import linear_model
from sklearn.metrics import mean_squared_error, r2_score
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns 
import warnings
warnings.filterwarnings("ignore")

# Load environment variables
load_dotenv()

# Database connection setup
DB_USER = os.getenv('POSTGRES_USER')
DB_PASSWORD = os.getenv('POSTGRES_PASSWORD')
DB_NAME = os.getenv('POSTGRES_DB')
DB_HOST = os.getenv('POSTGRES_HOST')
DB_PORT = os.getenv('POSTGRES_PORT')

db_url = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Load data from the SQL table
def create_dataframe_from_sql(table_name: str, db_url: str):
    engine = create_engine(db_url)
    df = pd.read_sql(f"SELECT * FROM {table_name}", con=engine)
    return df

try:
    df = create_dataframe_from_sql('housing', db_url)
except Exception as e:
    print(f"Error loading data: {e}")
    exit()

# outlier treatment for price
plt.boxplot(df.price)
Q1 = df.price.quantile(0.25)
Q3 = df.price.quantile(0.75)
IQR = Q3 - Q1
housing = df[(df.price >= Q1 - 1.5*IQR) & (df.price <= Q3 + 1.5*IQR)]

# outlier treatment for area
plt.boxplot(df.area)
Q1 = df.area.quantile(0.25)
Q3 = df.area.quantile(0.75)
IQR = Q3 - Q1
df = df[(df.area >= Q1 - 1.5*IQR) & (df.area <= Q3 + 1.5*IQR)]

# Define boolean equivalents
boolean_values = {
    "yes", "no",
    "true", "false",
    "1", "0",
    "on", "off"
}

num_vars = []

# Detect and convert boolean-like columns
for column in df.columns:
    if df[column].dtype == 'object' and df[column].nunique() == 2:
        num_vars.append(column)
        unique_values = set(df[column].str.lower().dropna().unique())
        if unique_values.issubset(boolean_values):
            df[column] = df[column].str.lower().map({
                "yes": 1, "no": 0,
                "true": 1, "false": 0,
                "1": 1, "0": 0,
                "on": 1, "off": 0
            })

    elif df[column].dtype == 'object' and df[column].nunique() == 3:
        # Create dummy variables for three-category columns
        status = pd.get_dummies(df[column], dtype=int, drop_first=True)
        df = df.drop(column, axis=1)  # Drop the original column
        df = pd.concat([df, status], axis=1)  # Add new columns
        for col in status.columns:
            num_vars.append(col)


from sklearn.model_selection import train_test_split

# print(df.describe())
# We specify this so that the train and test data set always have the same rows, respectively
np.random.seed(0)
df_train, df_test = train_test_split(df, train_size = 0.7, test_size = 0.3, random_state = 100)

from sklearn.preprocessing import MinMaxScaler

scaler = MinMaxScaler()


df_train[num_vars] = scaler.fit_transform(df_train[num_vars])

# print(df_train.describe())

# plt.figure(figsize = (16, 10))
# sns.heatmap(df_train.corr(), annot = True, cmap="YlGnBu")
# plt.show()

y_train = df_train.pop('price')
X_train = df_train

# Importing RFE and LinearRegression
from sklearn.feature_selection import RFE
from sklearn.linear_model import LinearRegression

# Running RFE with the output number of the variable equal to 10
lm = LinearRegression()
lm.fit(X_train, y_train)

print(lm)

rfe = RFE(lm, step=6)             # running RFE
rfe = rfe.fit(X_train, y_train)

list(zip(X_train.columns,rfe.support_,rfe.ranking_))

col = X_train.columns[rfe.support_]
col

X_train.columns[~rfe.support_]

# Creating X_test dataframe with RFE selected variables
X_train_rfe = X_train[col]

# Adding a constant variable 
import statsmodels.api as sm  
X_train_rfe = sm.add_constant(X_train_rfe)


lm = sm.OLS(y_train,X_train_rfe).fit()   # Running the linear model

print(lm.summary())

# Calculate the VIFs for the model
from statsmodels.stats.outliers_influence import variance_inflation_factor

vif = pd.DataFrame()
X = X_train_rfe
vif['Features'] = X.columns
vif['VIF'] = [variance_inflation_factor(X.values, i) for i in range(X.shape[1])]
vif['VIF'] = round(vif['VIF'], 2)
vif = vif.sort_values(by = "VIF", ascending = False)
vif

y_train_price = lm.predict(X_train_rfe)

res = (y_train_price - y_train)

# Importing the required libraries for plots.
import matplotlib.pyplot as plt
import seaborn as sns
# %matplotlib inline

# Plot the histogram of the error terms
fig = plt.figure()
sns.distplot((y_train - y_train_price), bins = 20)
fig.suptitle('Error Terms', fontsize = 20)                  # Plot heading 
plt.xlabel('Errors', fontsize = 18)                         # X-label

plt.scatter(y_train,res)
plt.show()

num_vars = ['area','stories', 'bathrooms', 'airconditioning', 'prefarea','parking','price']

df_test[num_vars] = scaler.fit_transform(df_test[num_vars])

y_test = df_test.pop('price')
X_test = df_test

# Adding constant variable to test dataframe
X_test = sm.add_constant(X_test)

# Creating X_test_new dataframe by dropping variables from X_test
X_test_rfe = X_test[X_train_rfe.columns]

# Making predictions
y_pred = lm.predict(X_test_rfe)

from sklearn.metrics import r2_score 
r2_score(y_test, y_pred)

# Plotting y_test and y_pred to understand the spread.
fig = plt.figure()
plt.scatter(y_test,y_pred)
fig.suptitle('y_test vs y_pred', fontsize=20)              # Plot heading 
plt.xlabel('y_test', fontsize=18)                          # X-label
plt.ylabel('y_pred', fontsize=16)                          # Y-label
plt.show()