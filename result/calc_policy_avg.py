import pandas as pd

file = 'DEBUG_LOGNORMAL_CYCLES_all1_results.csv'
mean_file = 'DEBUG_LOGNORMAL_CYCLES_all1_results_avg.csv'

df = pd.read_csv(file)
df.rename(columns={'Unnamed: 0': 'policy_id'}, inplace=True)

df_mean = df.groupby('policy_id').mean()
print(df_mean.head())
df_mean.to_csv(mean_file)