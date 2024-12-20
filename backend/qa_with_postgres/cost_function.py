# import numpy as np

# from sklearn.model_selection import train_test_split
# import matplotlib.pyplot as plt
# import pandas as pd
# from sqlalchemy import create_engine
# import os
# from dotenv import load_dotenv
# from lab_utils_uni import plt_intuition, plt_stationary, plt_update_onclick, soup_bowl
# plt.style.use('./deeplearning.mplstyle')
# from sklearn.preprocessing import MinMaxScaler

# scaler = MinMaxScaler()



# # Load environment variables
# load_dotenv()

# # Database connection setup
# DB_USER = os.getenv('POSTGRES_USER')
# DB_PASSWORD = os.getenv('POSTGRES_PASSWORD')
# DB_NAME = os.getenv('POSTGRES_DB')
# DB_HOST = os.getenv('POSTGRES_HOST')
# DB_PORT = os.getenv('POSTGRES_PORT')

# db_url = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# # Load data from the SQL table
# def create_dataframe_from_sql(table_name: str, db_url: str):
#     engine = create_engine(db_url)
#     df = pd.read_sql(f"SELECT * FROM {table_name}", con=engine)
#     return df

# try:
#     df = create_dataframe_from_sql('housing', db_url)
# except Exception as e:
#     print(f"Error loading data: {e}")
#     exit()

# # outlier treatment for price
# plt.boxplot(df.price)
# Q1 = df.price.quantile(0.25)
# Q3 = df.price.quantile(0.75)
# IQR = Q3 - Q1
# housing = df[(df.price >= Q1 - 1.5*IQR) & (df.price <= Q3 + 1.5*IQR)]

# # outlier treatment for area
# plt.boxplot(df.area)
# Q1 = df.area.quantile(0.25)
# Q3 = df.area.quantile(0.75)
# IQR = Q3 - Q1
# df = df[(df.area >= Q1 - 1.5*IQR) & (df.area <= Q3 + 1.5*IQR)]

# df_train, df_test = train_test_split(df, train_size = 0.7, test_size = 0.3, random_state = 100)

# num_vars = ["area", "price"]

# df_train[num_vars] = scaler.fit_transform(df_train[num_vars])

# y_train = df_train.pop('price')
# x_train = df_train.pop('area')
# print("area: ",x_train)

# x_train = x_train.to_numpy()
# y_train = y_train.to_numpy()


# def compute_cost(x, y, w, b): 
#     """
#     Computes the cost function for linear regression.
    
#     Args:
#       x (ndarray (m,)): Data, m examples 
#       y (ndarray (m,)): target values
#       w,b (scalar)    : model parameters  
    
#     Returns
#         total_cost (float): The cost of using w,b as the parameters for linear regression
#                to fit the data points in x and y
#     """
#     # number of training examples
#     m = x.shape[0] 
    
#     cost_sum = 0 
#     for i in range(m): 
#         f_wb = w * x[i] + b   
#         cost = (f_wb - y[i]) ** 2  
#         cost_sum = cost_sum + cost  
#     total_cost = (1 / (2 * m)) * cost_sum  

#     return total_cost




# plt_intuition(x_train,y_train)

# plt.close('all') 
# fig, ax, dyn_items = plt_stationary(x_train, y_train)
# updater = plt_update_onclick(fig, ax, x_train, y_train, dyn_items)
# soup_bowl(updater)





# -------------------------------------------------------------------------------------------------------------------------------------------- #


import matplotlib.pyplot as plt
import numpy as np

# original data set
X = [1, 2, 3]
y = [1, 2.5, 3.5]

# slope of best_fit_1 is 0.5
# slope of best_fit_2 is 1.0
# slope of best_fit_3 is 1.5

hyps = [0.5, 1.0, 1.5] 

# mutiply the original X values by the theta 
# to produce hypothesis values for each X
def multiply_matrix(mat, theta):
    mutated = []
    for i in range(len(mat)):
        mutated.append(mat[i] * theta)

    return mutated

# calculate cost by looping each sample
# subtract hyp(x) from y
# square the result
# sum them all together
def calc_cost(m, X, y):
    total = 0
    for i in range(m):
        squared_error = (y[i] - X[i]) ** 2
        total += squared_error
    
    return total * (1 / (2*m))

# calculate cost for each hypothesis
for i in range(len(hyps)):
    hyp_values = multiply_matrix(X, hyps[i])

    print("Cost for ", hyps[i], " is ", calc_cost(len(X), y, hyp_values))